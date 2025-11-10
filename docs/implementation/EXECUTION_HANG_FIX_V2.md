# Execution Hang Fix - Agent Autonomy Issue

## Problem Identified

### Symptom
- Agents were stuck processing indefinitely
- Run status remained "running" forever
- User said "Just decide everything for me!" but agents kept asking for input

### Root Cause
**Three critical issues in `orchestrator_v2.py`:**

1. **System Prompt Told Agents to Request User Input**
```python
# OLD (BROKEN):
prompt = """
Communication Protocol:
- If you need information from the user, output: [REQUEST_USER_INPUT: your question here]
- If you need help from your parent agent, output: [QUERY_PARENT: your question here]
- Otherwise, provide your complete response directly
"""
```

2. **Orchestrator Stopped When It Saw REQUEST_USER_INPUT**
```python
# OLD (BROKEN):
if event["type"] == "request_user_input":
    # Frontend will handle this and send back user response
    yield {
        "type": "status",
        "agent_id": root_agent_id,
        "data": "waiting_for_user"
    }
    # In a real implementation, we'd wait for user response here
    # For now, just log it
    return  # <-- EXECUTION STOPS HERE!
```

3. **Agent Execution Returned Early on REQUEST_USER_INPUT**
```python
# OLD (BROKEN):
if "[REQUEST_USER_INPUT]" in full_output:
    self.mailbox.set_state(AgentState.WAITING_FOR_USER)
    # Extract question
    question = self._extract_user_request(full_output)
    yield {
        "type": "request_user_input",
        "agent_id": self.agent.id,
        "data": {"question": question, "agent_name": self.agent.name}
    }
    return  # <-- AGENT STOPS HERE!
```

### What Was Happening

1. User sends request
2. Root agent analyzes and thinks "I need more info"
3. Root agent outputs: `[REQUEST_USER_INPUT: What are your exact dates?]`
4. Orchestrator sees `[REQUEST_USER_INPUT]` marker
5. Orchestrator yields `request_user_input` event
6. Orchestrator **RETURNS** (stops execution)
7. Run stays in "running" status forever
8. Frontend shows "Sending..." forever
9. No completion event ever sent

## Solution Applied

### 1. Changed System Prompt to Autonomous Mode
```python
# NEW (FIXED):
prompt = f"""{base_prompt}

IMPORTANT INSTRUCTIONS:
- Make decisions autonomously based on best practices and your expertise
- DO NOT ask the user for additional information - make reasonable assumptions
- If you need help, delegate to your child agents
- Provide complete, actionable responses with specific recommendations
"""
```

**Effect:** Agents now make decisions instead of asking questions.

### 2. Removed REQUEST_USER_INPUT Detection
```python
# NEW (FIXED):
# Removed all the code that checks for [REQUEST_USER_INPUT] and stops execution
# Agents now run to completion regardless of output content

# Agent completed successfully
self.mailbox.set_state(AgentState.COMPLETED)
yield {"type": "output", "agent_id": self.agent.id, "data": full_output}
yield {"type": "log", "agent_id": self.agent.id, "data": f"[{self.agent.name}] ✓ Completed"}
```

**Effect:** Agents always complete execution.

### 3. Removed Orchestrator Early Return
```python
# NEW (FIXED):
# Removed the code that returns when seeing request_user_input

# Execute root agent
async for event in root_executor.execute(user_task, context):
    yield event
    
    # Capture final output
    if event["type"] == "output":
        self.agent_outputs[root_agent_id] = event["data"]

# Execution continues to Phase 3 (children)
```

**Effect:** Orchestrator runs through all phases.

## Behavior Change

### Before (Broken)
```
User: "Just decide for me!"
  ↓
Head Agent: "I need to ask: What are your dates?"
  ↓
Orchestrator: "Waiting for user input..."
  ↓
[HANGS FOREVER]
```

### After (Fixed)
```
User: "Just decide for me!"
  ↓
Head Agent: "Based on 'early March', I'll assume March 3-10..."
  ↓
Head Agent: Delegates to Flight Agent, Hotel Agent, Food Agent
  ↓
Children execute and return results
  ↓
Head Agent synthesizes final response
  ↓
Run completes successfully
```

## Why This Matters

1. **User Autonomy**: User can say "just decide" and agents will make smart choices
2. **No Hangs**: Execution always completes (success or error, never stuck)
3. **Proper Delegation**: Agents focus on using their expertise, not asking questions
4. **Better UX**: Faster responses, no waiting for user input

## Trade-offs

### What We Gained
- ✅ No more hanging/stuck runs
- ✅ Agents make autonomous decisions
- ✅ Faster execution
- ✅ Better delegation flow

### What We Lost
- ❌ Can't request additional user input mid-execution
- ❌ Can't do interactive back-and-forth within a run

### If User Input Is Needed
**Option 1:** Agent makes best guess and documents assumptions
```
"Based on your request for 'early March', I'm assuming March 5-12 (7 days). 
If different dates are needed, please specify and I'll adjust the recommendations."
```

**Option 2:** User asks follow-up question in new message
```
User: "Actually, I want to go March 15-22"
Agent: "Perfect! Let me adjust the recommendations for March 15-22..."
```

## Testing Results

- ✅ Cleared stuck run from database
- ✅ Compiled successfully
- ✅ Backend restarted
- ✅ Ready to test with autonomous decision-making

## Files Modified

1. `backend/core/orchestrator_v2.py`
   - Changed system prompt to autonomous mode
   - Removed REQUEST_USER_INPUT detection
   - Removed early returns on user input requests
   - Agents now always complete execution

## Next Steps

1. Test with the travel agent tree
2. Verify agents make reasonable assumptions
3. Confirm full execution flow works
4. Check that multi-level delegation still works

## Summary

The system was designed with interactive user input in mind, but when the user explicitly said "just decide everything", the agents still tried to request input, causing execution to hang forever. The fix makes agents truly autonomous - they make smart decisions based on their expertise and context, complete execution, and never hang waiting for input that will never come.

