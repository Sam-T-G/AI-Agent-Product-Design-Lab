# Agent Communication Protocol - Design Document

## Current Issues

1. **Execution Hangs**: Multi-iteration loops without clear exit conditions
2. **No Validation**: No way to confirm messages were received/processed
3. **Unclear Flow**: Parent-child communication is implicit, not explicit
4. **Always-On Execution**: All agents execute even when not needed
5. **No User Interaction**: Can't request info from user mid-execution

## New Protocol Design

### Core Principles

1. **Explicit Communication**: Messages are explicit objects, not implicit data flow
2. **Validation Required**: Every message must be acknowledged
3. **On-Demand Execution**: Agents only execute when explicitly invoked
4. **User-in-the-Loop**: Agents can request user input and wait for response
5. **State Machine**: Clear states (idle, processing, waiting, completed, error)

### Communication Types

#### 1. DELEGATE (Parent → Child)
Parent assigns a task to a child agent.
```python
{
  "type": "DELEGATE",
  "from": "parent_agent_id",
  "to": "child_agent_id",
  "task": "Research flights from LAX to Italy",
  "context": {...},
  "message_id": "uuid",
  "requires_response": true
}
```

#### 2. REPORT (Child → Parent)
Child reports results back to parent.
```python
{
  "type": "REPORT",
  "from": "child_agent_id",
  "to": "parent_agent_id",
  "result": "Found 3 flight options...",
  "status": "completed" | "partial" | "needs_help",
  "message_id": "uuid",
  "in_response_to": "parent_message_id"
}
```

#### 3. REQUEST_USER_INPUT (Agent → User)
Agent needs information from the user.
```python
{
  "type": "REQUEST_USER_INPUT",
  "from": "agent_id",
  "question": "What is your departure city?",
  "context": "I need this to search for flights",
  "message_id": "uuid",
  "awaiting_response": true
}
```

#### 4. USER_RESPONSE (User → Agent)
User provides requested information.
```python
{
  "type": "USER_RESPONSE",
  "to": "agent_id",
  "answer": "LAX",
  "message_id": "uuid",
  "in_response_to": "request_message_id"
}
```

#### 5. QUERY (Child → Parent)
Child asks parent for clarification or additional context.
```python
{
  "type": "QUERY",
  "from": "child_agent_id",
  "to": "parent_agent_id",
  "question": "Should I prioritize price or convenience?",
  "message_id": "uuid",
  "requires_response": true
}
```

#### 6. ANSWER (Parent → Child)
Parent answers child's query.
```python
{
  "type": "ANSWER",
  "from": "parent_agent_id",
  "to": "child_agent_id",
  "answer": "Prioritize price",
  "message_id": "uuid",
  "in_response_to": "query_message_id"
}
```

### Agent States

```python
class AgentState(Enum):
    IDLE = "idle"                    # Not doing anything
    ANALYZING = "analyzing"          # Understanding task
    EXECUTING = "executing"          # Performing work
    WAITING_FOR_CHILD = "waiting_for_child"    # Delegated to child
    WAITING_FOR_PARENT = "waiting_for_parent"  # Needs parent help
    WAITING_FOR_USER = "waiting_for_user"      # Needs user input
    COMPLETED = "completed"          # Task done
    ERROR = "error"                  # Something failed
```

### Execution Flow

```
1. User sends initial prompt
   ↓
2. Root agent enters ANALYZING state
   ↓
3. Root agent decides: Can I handle this alone?
   ├─ Yes → Execute and return result
   └─ No → Identify which child agents are needed
   ↓
4. Root agent DELEGATEs to specific children (not all)
   - State: WAITING_FOR_CHILD
   ↓
5. Child agents receive DELEGATE messages
   - State: ANALYZING → EXECUTING
   ↓
6. Child agents work on their tasks
   - If stuck → QUERY parent or REQUEST_USER_INPUT
   - If done → REPORT back
   ↓
7. Parent receives REPORTs
   - Validates: "Did child answer my question?"
   - If yes → Synthesize results
   - If no → Send follow-up DELEGATE or QUERY
   ↓
8. Root agent compiles final response
   - State: COMPLETED
   ↓
9. Stream to user
```

### Validation Mechanisms

#### Message Acknowledgment
Every message expects a response within a timeout period.

```python
class MessageValidator:
    def __init__(self, message: Message):
        self.message = message
        self.timeout = 30  # seconds
        self.acknowledged = False
        
    async def wait_for_ack(self) -> bool:
        """Wait for message to be acknowledged."""
        start = time.time()
        while time.time() - start < self.timeout:
            if self.acknowledged:
                return True
            await asyncio.sleep(0.1)
        return False  # Timeout
```

#### Task Completion Validator
Verify that a delegated task was actually completed.

```python
class TaskValidator:
    def validate_report(self, task: str, report: str) -> ValidationResult:
        """
        Check if the report addresses the task.
        Uses LLM to determine if task was completed.
        """
        prompt = f"""
        Task assigned: {task}
        Report received: {report}
        
        Did the report successfully complete the task? 
        Respond with JSON: {{"completed": true/false, "reason": "..."}}
        """
        # Call LLM for validation
        result = self.validate_with_llm(prompt)
        return result
```

#### User Input Validator
Ensure user response answers the question.

```python
class UserInputValidator:
    def validate_response(self, question: str, answer: str) -> bool:
        """Check if answer addresses the question."""
        # Simple heuristic: answer is not empty and relevant
        if not answer.strip():
            return False
        # Could use LLM for complex validation
        return True
```

### Message Queue System

Each agent has an inbox and outbox.

```python
class AgentMailbox:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.inbox: Queue[Message] = Queue()
        self.outbox: Queue[Message] = Queue()
        self.pending_responses: Dict[str, Message] = {}
        
    async def send(self, message: Message):
        """Send a message and track if response expected."""
        self.outbox.put(message)
        if message.requires_response:
            self.pending_responses[message.message_id] = message
            
    async def receive(self) -> Optional[Message]:
        """Get next message from inbox."""
        if not self.inbox.empty():
            return self.inbox.get()
        return None
        
    def acknowledge(self, message_id: str, response: Message):
        """Mark a message as acknowledged."""
        if message_id in self.pending_responses:
            del self.pending_responses[message_id]
```

### Dynamic Agent Selection

Parent evaluates which children are relevant for a task.

```python
class AgentSelector:
    def select_agents(self, task: str, available_agents: List[Agent]) -> List[Agent]:
        """
        Determine which agents are needed for this task.
        """
        # Use LLM to analyze task and agent capabilities
        prompt = f"""
        Task: {task}
        
        Available agents:
        {self._format_agent_list(available_agents)}
        
        Which agents are needed for this task? Return JSON array of agent IDs.
        Only select agents that are NECESSARY. Don't select all agents.
        """
        
        selected_ids = self.llm_select(prompt)
        return [a for a in available_agents if a.id in selected_ids]
```

## Implementation Plan

### Phase 1: Message Infrastructure
1. Create Message classes (DELEGATE, REPORT, etc.)
2. Implement AgentMailbox system
3. Add message routing logic

### Phase 2: Validators
1. MessageValidator for acknowledgments
2. TaskValidator for completion checking
3. UserInputValidator for response validation

### Phase 3: Orchestrator Rewrite
1. Replace iteration loop with message processing loop
2. Implement state machine for agents
3. Add dynamic agent selection

### Phase 4: User Interaction
1. Add REQUEST_USER_INPUT streaming event
2. Frontend modal/input for user responses
3. Resume execution after user input

### Phase 5: Testing
1. Test simple parent-child delegation
2. Test bidirectional queries
3. Test user input requests
4. Test validation failures and retries

## Benefits

1. **Clear Flow**: Every interaction is explicit and traceable
2. **Resilient**: Timeouts and validation prevent hangs
3. **Efficient**: Only relevant agents execute
4. **Interactive**: User can be involved at any point
5. **Debuggable**: Message logs show exact communication flow
6. **Scalable**: Easy to add new message types and agents

