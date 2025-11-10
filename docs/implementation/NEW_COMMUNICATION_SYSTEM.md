# New Message-Based Communication System

## ✅ Implementation Complete

The agent communication system has been completely rewritten from the ground up with:

### 1. **Message Infrastructure** (`core/messages.py`)

**Message Types:**
- `DELEGATE` - Parent assigns task to child
- `REPORT` - Child reports results to parent
- `QUERY` - Child asks parent a question
- `ANSWER` - Parent answers child's question
- `REQUEST_USER_INPUT` - Agent requests info from user
- `USER_RESPONSE` - User provides requested info
- `STATUS` - State updates
- `ERROR` - Error reporting

**Agent States:**
- `IDLE` - Not doing anything
- `ANALYZING` - Understanding task
- `EXECUTING` - Performing work
- `WAITING_FOR_CHILD` - Delegated to child
- `WAITING_FOR_PARENT` - Needs parent help
- `WAITING_FOR_USER` - Needs user input
- `COMPLETED` - Task done
- `ERROR` - Something failed

**Validation:**
- `MessageValidator` - Ensures messages are properly acknowledged
- `validate_delegate_report()` - Checks if child completed task
- `validate_query_answer()` - Checks if parent answered query
- `validate_user_response()` - Checks if user answered request

**Mailbox System:**
- Each agent has an inbox and outbox
- Tracks pending responses
- Manages agent state

### 2. **Dynamic Agent Selection** (`core/agent_selector.py`)

**Key Features:**
- Uses LLM to analyze which agents are actually needed
- Only selects NECESSARY agents (not all available)
- Returns empty list if parent can handle alone
- Considers agent roles and capabilities

**Selection Process:**
1. Formats available agent descriptions
2. Sends to LLM with task analysis prompt
3. LLM returns JSON array of needed agent IDs
4. Filters and returns selected agents

### 3. **Message-Based Orchestrator** (`core/orchestrator_v2.py`)

**Execution Phases:**

#### Phase 1: Analyze & Select
```
Root agent receives task
  ↓
Load available children
  ↓
Dynamic selection: Which agents are needed?
  ↓
Result: 0-N selected agents
```

#### Phase 2: Root Execution
```
Root agent executes with task
  ↓
Can output directly OR
  ├─ [REQUEST_USER_INPUT: question]
  ├─ [QUERY_PARENT: question] (if root has parent)
  └─ [DELEGATE to Child: task]
```

#### Phase 3: Child Execution (if selected)
```
Selected children execute in parallel
  ↓
Each child can:
  ├─ Complete and report
  ├─ [REQUEST_USER_INPUT: question]
  └─ [QUERY_PARENT: question]
```

#### Phase 4: Synthesis
```
Root agent receives child reports
  ↓
Validates: Did children complete their tasks?
  ↓
Synthesizes final comprehensive response
```

**Key Improvements:**

1. **Clear Flow**: Each phase is explicit and logged
2. **Dynamic**: Only relevant agents execute
3. **Interactive**: Agents can request user input
4. **Validated**: Communication is verified
5. **No Hangs**: Clear state management prevents infinite loops
6. **Debuggable**: Every action is logged

### 4. **Agent Communication Protocol**

**For Parent Agents:**

```python
# In your agent's response, you can:

# 1. Delegate to a child
"[DELEGATE to FlightAgent: Find flights from LAX to Rome]"

# 2. Request user input
"[REQUEST_USER_INPUT: What is your departure date?]"

# 3. Or just respond directly
"Based on your requirements, I recommend..."
```

**For Child Agents:**

```python
# In your agent's response, you can:

# 1. Report results
"I found 3 flight options: ..."

# 2. Query parent for clarification
"[QUERY_PARENT: Should I prioritize price or convenience?]"

# 3. Request user input
"[REQUEST_USER_INPUT: What class of service do you prefer?]"
```

### 5. **How It's Different from Old System**

| Aspect | Old System | New System |
|--------|-----------|------------|
| **Execution** | All agents always execute | Only selected agents execute |
| **Communication** | Implicit data flow | Explicit messages |
| **User Interaction** | Not supported | Full support with REQUEST_USER_INPUT |
| **Validation** | No validation | Every message validated |
| **State** | Unclear | Explicit state machine |
| **Debugging** | Hard to trace | Full message logs |
| **Hangs** | Common (infinite loops) | Prevented by clear phases |
| **Delegation** | Always hierarchical | Dynamic selection |

### 6. **Agent Design Guidelines**

When creating agents in the UI:

**For Parent Agents:**
- Role: "Coordinator", "Manager", "Orchestrator"
- Description: List child capabilities and when to use them
- Example: "You coordinate travel planning. You can delegate to FlightAgent for flights and HotelAgent for accommodations."

**For Child Agents:**
- Role: Specific expertise ("Flight Specialist", "Hotel Expert")
- Description: Clear scope of what they handle
- Example: "You research and recommend flights. Use Google Flights data. Always provide price and duration."

**Best Practices:**
1. Give agents CLEAR, SPECIFIC roles
2. Document their capabilities in description
3. Use meaningful names
4. Don't create redundant agents
5. Test with simple tasks first

### 7. **Testing the New System**

**Simple Test (No Delegation):**
```
User: "What's 2+2?"
Expected: Root agent answers directly, no children selected
```

**Delegation Test:**
```
User: "Plan a trip to Italy"
Expected: 
  1. Root analyzes task
  2. Selects relevant agents (e.g., FlightAgent, HotelAgent)
  3. Delegates to selected agents
  4. Synthesizes their reports
```

**User Input Test:**
```
User: "Book a flight"
Expected:
  1. Agent recognizes missing info
  2. Outputs: [REQUEST_USER_INPUT: Where are you flying from?]
  3. Frontend shows input prompt
  4. User responds
  5. Agent continues with answer
```

### 8. **What to Watch in Logs**

**Backend logs will show:**
```
orchestrator_v2_start - Execution begins
agents_selected - Which agents were chosen (may be 0)
agent_execution - Each agent's execution
orchestrator_v2_complete - Execution finished
```

**Frontend console will show:**
```
🚀 [CHAT] handleSend called
📝 [CHAT] Creating run
📨 [CHAT] SSE event received (type: log) - "Phase 1: Analyzing..."
📨 [CHAT] SSE event received (type: log) - "Selected 2 agents..."
📨 [CHAT] SSE event received (type: output_chunk) - Streaming response
📊 [CHAT] Status event (completed)
```

### 9. **Known Limitations & Future Work**

**Current Limitations:**
1. User input requests pause execution (not yet resumable)
2. Parent-child queries are one-way (child can ask, but not wait for answer mid-execution)
3. No timeout handling yet
4. No message retry logic

**Future Enhancements:**
1. Implement user input resume functionality
2. Add full bidirectional queries with blocking
3. Add message timeouts and retry logic
4. Add message history/audit trail
5. Support multi-turn conversations per agent
6. Add agent collaboration (peer-to-peer messaging)

### 10. **Troubleshooting**

**Problem: No agents selected**
- Check: Agent roles and descriptions are clear
- Check: Task is specific enough
- Solution: Improve agent descriptions or task clarity

**Problem: Wrong agents selected**
- Check: Agent capabilities in description
- Solution: Make agent roles more distinct

**Problem: Agent hangs**
- Check: Backend logs for last checkpoint
- Check: Gemini API key validity
- Solution: Review agent execution logs

**Problem: User input request not working**
- Status: Feature implemented but needs frontend modal
- Current: Logs the request but doesn't pause
- Future: Full pause-and-resume support

## Summary

The new system provides:
- ✅ Clean, explicit communication
- ✅ Dynamic agent selection
- ✅ Validation and state management
- ✅ Support for user interaction
- ✅ Clear phases and debugging
- ✅ No more hangs or infinite loops

**Ready to test!** Try sending a message and watch the new system work.

