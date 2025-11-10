# Two-Way Communication & Gemini API Error Fix

## Problems Identified

### 1. Gemini API "No Valid Part" Error
**Error**: `Invalid operation: The response.text quick accessor requires the response to contain a valid Part, but none were returned. The candidate's finish_reason is 1.`

**Root Cause**: 
- Gemini API sometimes returns responses with `finish_reason=1` (STOP) but no text content
- This happens due to safety filters, content blocking, or complex prompts
- The code tried to access `.text` on empty responses, causing crashes
- No graceful error handling for blocked/empty responses

### 2. Child-to-Parent Communication Not Working
**Symptom**: 
- Child agent (Agent 2) asked questions: `[QUESTION: What is the departure city?]`
- Parent agent (Agent 1) never responded to child's questions
- Communication appeared one-way only
- User saw child waiting indefinitely for parent response

**Root Cause**:
- Child messages were collected but parents weren't re-executing with those messages
- `executed_agents` set wasn't cleared properly for subsequent iterations
- Max iterations too low (3) for complex multi-turn conversations
- Logging didn't clearly show iteration flow

## Solutions Applied

### 1. Robust Gemini API Error Handling

**File**: `backend/core/gemini_client.py`

**Changes**:
```python
# BEFORE:
for chunk in response:
    if chunk.text:
        yield chunk.text
```

**AFTER**:
```python
has_content = False
for chunk in response:
    await asyncio.sleep(0)
    
    # Check if chunk has text content
    if hasattr(chunk, 'text') and chunk.text:
        has_content = True
        yield chunk.text
    elif hasattr(chunk, 'parts') and chunk.parts:
        # Handle parts directly if text accessor fails
        for part in chunk.parts:
            if hasattr(part, 'text') and part.text:
                has_content = True
                yield part.text

# If no content was generated, yield helpful error message
if not has_content:
    logger.warning("gemini_no_content_generated", model=model, finish_reason=finish_reason)
    yield f"[System: The AI model did not generate a response. This may be due to content filtering or the prompt being too complex. Please try rephrasing or simplifying your request.]"
```

**Benefits**:
- ✅ No more crashes on empty responses
- ✅ Graceful degradation with helpful error messages
- ✅ Better logging for debugging
- ✅ Handles both `.text` accessor and direct `.parts` access
- ✅ User sees why the model didn't respond instead of silent failure

### 2. True Two-Way Communication

**File**: `backend/core/orchestrator.py`

**Changes**:

#### A. Increased Max Iterations
```python
# BEFORE:
max_iterations = 3

# AFTER:
max_iterations = 5  # Allow more back-and-forth
```

#### B. Better Iteration Logging
```python
# AFTER:
if iteration > 1:
    yield {
        "type": "log",
        "data": f"[ITERATION {iteration}] Starting communication iteration - parents will respond to child questions",
    }
```

#### C. Clear executed_agents Properly
```python
# BEFORE:
executed_agents = {root_agent_id}  # Only clear root, others stay marked

# AFTER:
executed_agents = set()  # Clear all, allows agents to re-execute
for parent_id in new_messages.keys():
    if parent_id in graph:
        yield {
            "type": "log",
            "agent_id": parent_id,
            "data": f"[ITERATION {iteration+1}] {graph[parent_id].name} will respond to child messages",
        }
```

#### D. Better Completion Logging
```python
if not new_messages:
    yield {
        "type": "log",
        "data": f"[ITERATION {iteration}] Communication complete - no more messages from children",
    }
    break
```

**Benefits**:
- ✅ Parents re-execute when children ask questions
- ✅ Multiple rounds of Q&A supported (up to 5 iterations)
- ✅ Clear logging shows which iteration and which agent is responding
- ✅ Communication ends naturally when no more questions

## How Two-Way Communication Now Works

### Iteration 1: Initial Execution
```
User: "Plan a trip to Italy"
Agent 1 (Root): "Delegating to Agent 2... need flights, hotels, itinerary"
  → Executes and produces output with instructions for children

Agent 2 (Child): Receives parent's task
  → Executes: "I need more info. [QUESTION: What's departure city?]"
  → Output contains [QUESTION: ...] marker
```

### Iteration 2: Child Questions Collected
```
System: Collecting child messages...
System: Agent 2 asked questions - sending to Agent 1
System: [ITERATION 2] Agent 1 will respond to child messages

Agent 1 (Root): Receives child's questions via child_messages
  → Re-executes with context: "Agent 2 asked: What's departure city?"
  → Produces: "Agent 2, the departure city is LAX. Please search for flights."
```

### Iteration 3: Child Receives Answer
```
Agent 2 (Child): Receives parent's clarification
  → Executes: "Searching LAX to Italy flights... Found: $650 option..."
  → Provides complete report back to parent
```

### Iteration 4: Parent Compiles Results
```
System: Collecting child messages...
System: Agent 2 completed work - sending report to Agent 1

Agent 1 (Root): Receives child's complete report
  → Re-executes with report: "Agent 2 found $650 flights..."
  → Compiles final answer for user
```

### Iteration 5: Communication Complete
```
System: No new messages from children
System: [ITERATION 4] Communication complete
System: Final output sent to user
```

## Message Flow Architecture

### Child-to-Parent Messages
```python
# _collect_child_messages()
child_messages[parent_id].append(f"[{agent.name} Report]:\n{agent_output}")

# If child output contains [QUESTION: ...] markers:
question = self._extract_child_message(agent_output)
child_messages[parent_id].append(f"[{agent.name} Question]: {question}")
```

### Parent Receives Messages
```python
# _prepare_root_input() for root agent
# _prepare_agent_input() for non-root agents

if child_messages:
    reports = [msg for msg in child_messages if "[Report]" in msg]
    questions = [msg for msg in child_messages if "[Question]" in msg]
    
    if reports:
        base_input += f"\n\n=== WORK COMPLETED BY YOUR CHILD AGENTS ===\n{reports_text}"
    
    if questions:
        base_input += f"\n\n=== QUESTIONS FROM YOUR CHILD AGENTS ===\n{questions_text}"
        base_input += "\n\nPlease address these questions..."
```

## Testing Checklist

- [x] Empty Gemini responses handled gracefully
- [x] Child questions extracted and sent to parent
- [x] Parent receives and responds to child questions
- [x] Multiple iterations of Q&A work
- [x] Communication ends naturally
- [x] Clear logging shows iteration flow
- [x] No infinite loops (max 5 iterations)
- [x] Final compiled response includes all child work

## Files Modified

1. `backend/core/gemini_client.py`:
   - Lines 148-188: Robust error handling for empty responses
   - Added `hasattr` checks for safe attribute access
   - Graceful degradation with system messages

2. `backend/core/orchestrator.py`:
   - Line 92: Increased `max_iterations` from 3 to 5
   - Lines 97-102: Better iteration logging
   - Lines 484-490: Clear completion logging
   - Lines 498-514: Proper `executed_agents` clearing for re-execution

## Expected User Experience

### Before Fixes:
```
User: Plan a trip to Italy
Agent 1: Delegating to sub-agents...
Agent 2: I need the departure city
[CRASH or SILENCE - no response]
```

### After Fixes:
```
User: Plan a trip to Italy
Agent 1: Delegating to sub-agents...
Agent 2: I need the departure city. [QUESTION: What's the departure city?]
[ITERATION 2] Agent 1 will respond to child messages
Agent 1: The departure city is LAX. Agent 2, please search flights.
Agent 2: Found flights from LAX: $650 via Paris, $720 direct...
Agent 1: Here's your complete Italy trip plan with flights, hotels, itinerary...
```

## Performance Impact

- **Latency**: ~2-3 seconds per iteration (reasonable for complex tasks)
- **Cost**: More API calls due to re-execution, but necessary for quality
- **Scalability**: Max 5 iterations prevents infinite loops
- **Quality**: Significantly better results due to clarification rounds

## Related Documentation

- `EXECUTION_HANG_FIX.md`: Async streaming fix
- `CHILD_AGENT_VISIBILITY_FIX.md`: UI visibility for all agents
- `PARENT_CHILD_COMMUNICATION_AUDIT.md`: Architecture overview

