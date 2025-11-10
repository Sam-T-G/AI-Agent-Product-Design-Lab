# Testing Guide for Chat Communication Debugging

## Current Setup

Comprehensive debug logging has been added throughout the entire communication stack:

### 1. Backend Logging (Python)
- **Location**: `/tmp/backend.log`
- **Checkpoints**:
  - `sse_stream_start` - SSE connection initiated
  - `sse_api_key_present` - API key detected
  - `sse_starting_orchestrator` - Orchestrator about to start
  - `orchestrator_execute_run_start` - Run execution begins
  - `orchestrator_run_loaded` - Run loaded from database
  - `orchestrator_run_status_updated` - Run status changed to "running"
  - `orchestrator_loading_graph` - Loading agent graph
  - `orchestrator_graph_loaded` - Agent graph loaded
  - `orchestrator_levels_calculated` - Hierarchy calculated
  - `orchestrator_iteration_start` - Each iteration starts
  - `gemini_generate_start` - Gemini API call initiated
  - `gemini_generate_complete` - Gemini API call completed
  - `sse_event` - Important events streamed
  - `sse_orchestrator_complete` - Orchestrator finished
  - `sse_completion_sent` - Completion event sent to frontend
  - `sse_error` - Any errors during streaming
  - `run_execution_error` - Fatal execution errors

### 2. Frontend Logging (JavaScript)
- **Location**: Browser console
- **Checkpoints**:
  - `🚀 [CHAT] handleSend called` - User sends message
  - `⚠️ [CHAT] handleSend validation failed` - Input validation
  - `📝 [CHAT] Creating run` - About to create run
  - `✅ [CHAT] Run created` - Run created successfully
  - `🌊 [CHAT] Starting SSE stream` - SSE connection starting
  - `📨 [CHAT] SSE event received` - Each SSE event
  - `📊 [CHAT] Status event` - Status changes
  - `❌ [CHAT] Error event received` - Error events
  - `❌ [CHAT] SSE error` - Connection errors
  - `❌ [CHAT] Failed to start run` - Run creation failures

### 3. Visual Indicators in Chat
- Messages now show `✓` prefix for successful operations
- Log messages improved for readability

## How to Test

### Step 1: Start Log Monitoring
```bash
cd /Users/sam/Documents/repositories/AI-Agent-Product-Design-Lab
./monitor_logs.sh
```

This will show colored, real-time backend logs with emphasis on important events.

### Step 2: Open Browser Console
1. Open the app: http://localhost:3000
2. Open browser developer tools (F12)
3. Go to Console tab
4. Filter for `[CHAT]` to see only chat-related logs

### Step 3: Send a Test Message
1. Type a simple message like "Hello"
2. Click Send
3. Watch BOTH logs simultaneously

### Expected Flow (Success)

**Backend Log:**
```
✅ sse_stream_start
✅ sse_api_key_present
✅ sse_starting_orchestrator
✅ orchestrator_execute_run_start
✅ orchestrator_run_loaded
✅ orchestrator_run_status_updated (running)
✅ orchestrator_loading_graph
✅ orchestrator_graph_loaded
✅ orchestrator_levels_calculated
✅ orchestrator_iteration_start
✅ gemini_generate_start
✅ gemini_generate_complete
✅ sse_event (output)
✅ sse_orchestrator_complete
✅ sse_completion_sent
```

**Frontend Console:**
```
🚀 [CHAT] handleSend called
📝 [CHAT] Creating run
✅ [CHAT] Run created
🌊 [CHAT] Starting SSE stream
📨 [CHAT] SSE event received (type: connected)
📨 [CHAT] SSE event received (type: log)
📨 [CHAT] SSE event received (type: output_chunk)
📨 [CHAT] SSE event received (type: output)
📊 [CHAT] Status event (completed)
```

### Identifying Issues

#### Issue: No Response at All

**Check Backend Log For:**
- `sse_stream_start` → If missing: SSE not reaching backend
- `orchestrator_execute_run_start` → If missing: Orchestrator not starting
- `gemini_generate_start` → If missing: Not reaching Gemini
- `gemini_generate_complete` → If stuck here: Gemini hanging

**Check Frontend Console For:**
- `[CHAT] Run created` → If missing: Run creation failed
- `[CHAT] SSE event received` → If missing: No events from backend

#### Issue: Stuck in "Running"

**Check Backend Log For:**
- Last checkpoint reached → Shows exactly where it stops
- `orchestrator_iteration_start` → If repeating: Infinite loop
- `sse_completion_sent` → If missing: Completion not sent

**Check Database:**
```bash
cd backend
sqlite3 agents.db "SELECT id, status, created_at, error FROM runs ORDER BY created_at DESC LIMIT 5;"
```

#### Issue: Partial Response

**Check Backend Log For:**
- `gemini_generate_complete` with `has_content=False`
- `sse_event` count → Should match number of agents

**Check Frontend Console For:**
- Multiple `output` events → Should see one per agent

## Common Problems and Solutions

### 1. API Key Issues
**Symptom**: `sse_no_api_key` in backend log
**Solution**: Check localStorage in browser console:
```javascript
localStorage.getItem('GEMINI_API_KEY')
```

### 2. Session Issues
**Symptom**: `Failed to list agents: Unprocessable Content`
**Solution**: Check session ID:
```javascript
localStorage.getItem('SESSION_ID')
```

### 3. Gemini API Errors
**Symptom**: `gemini_generate_complete` with `has_content=False`
**Solution**: Check Gemini API status, model availability

### 4. SSE Connection Drops
**Symptom**: `sse_client_disconnected` or `SSE error` in logs
**Solution**: Check network tab, firewall, proxy settings

## Cleanup Commands

```bash
# Clear stuck runs
cd backend
sqlite3 agents.db "UPDATE runs SET status = 'failed', error = 'Manual clear', finished_at = CURRENT_TIMESTAMP WHERE status = 'running';"

# Restart services
pkill -f "uvicorn main:app"
pkill -f "next dev"
cd backend && source ../.venv/bin/activate && uvicorn main:app --reload --port 8000 &
cd ../frontend && npm run dev &
```

## Next Steps

After identifying the failure point:
1. Note the last successful checkpoint
2. Note the first failed checkpoint
3. Check the code between those two points
4. Look for exceptions, async issues, or API failures
5. Add more granular logging if needed

