# Chat Communication Debug Flow

## Current Issue
All runs stuck in "running" status, never completing. No agent responses visible.

## Sequential Execution Flow

### 1. Frontend: User Input → Run Creation
```
Location: frontend/components/chat/ChatInterface.tsx:handleSend()
├─ User types message
├─ Input validation
├─ Convert to base64 (if images)
├─ Call createRun API
└─ Start SSE stream

Debug Points:
- Line 246: createRun() call
- Line 269: streamRun() call
```

### 2. Frontend: API Layer
```
Location: frontend/lib/api.ts
├─ createRun() → POST /api/runs
├─ streamRun() → GET /api/runs/{id}/stream (EventSource)
└─ Event listeners (output_chunk, output, status, error)

Debug Points:
- API call success/failure
- EventSource connection
- Event reception
```

### 3. Backend: Run Creation
```
Location: backend/api/routes/runs.py:create_run()
├─ Verify session
├─ Verify root agent
├─ Create RunModel (status="pending")
├─ Store in database
└─ Return run

Debug Points:
- Session validation
- Agent validation
- Run creation
```

### 4. Backend: SSE Stream Start
```
Location: backend/api/routes/runs.py:stream_run()
├─ Verify session & run
├─ Create AgentOrchestrator
├─ Start event_generator()
├─ Extract API key
├─ Extract images
└─ Call orchestrator.execute_run()

Debug Points:
- API key extraction
- Run input preparation
- Orchestrator invocation
```

### 5. Backend: Orchestrator Execution
```
Location: backend/core/orchestrator.py:execute_run()
├─ Update run status to "running"
├─ Load agent graph (session-filtered)
├─ Get hierarchical levels
├─ Start iteration loop (max 5)
├─ Execute each level
│   ├─ Sequential (single agent)
│   └─ Parallel (multiple agents)
├─ Collect child messages
├─ Re-execute if new messages
└─ Mark run as "completed"

Debug Points:
- Graph loading
- Level execution
- Agent execution
- Child message collection
- Completion
```

### 6. Backend: Agent Execution
```
Location: backend/core/orchestrator.py:_execute_agent_streaming()
├─ Get agent model & temperature
├─ Migrate old model names
├─ Build context
└─ Call generate_streaming()

Debug Points:
- Model selection
- Context building
- Gemini API call
```

### 7. Backend: Gemini API Call
```
Location: backend/core/gemini_client.py:generate_streaming()
├─ Configure Gemini API
├─ Process images (if any)
├─ Create model client
├─ Generate content (streaming)
├─ Yield chunks
└─ Handle errors

Debug Points:
- API key configuration
- Model initialization
- Content generation
- Chunk streaming
- Error handling
```

### 8. Backend: Stream Events to Frontend
```
Location: backend/api/routes/runs.py:event_generator()
├─ Receive orchestrator events
├─ Format as SSE
├─ Yield to client
└─ Send completion event

Debug Points:
- Event formatting
- SSE yield
- Completion signal
```

### 9. Frontend: Receive Events
```
Location: frontend/components/chat/ChatInterface.tsx
├─ EventSource receives events
├─ Parse event data
├─ Update chat messages
├─ Handle completion
└─ Display to user

Debug Points:
- Event reception
- Message creation
- UI update
```

## Common Failure Points

### 1. No Response at All
- [ ] Orchestrator never starts
- [ ] Agent graph loading fails
- [ ] Gemini API key invalid
- [ ] SSE connection drops

### 2. Stuck in "Running"
- [ ] Orchestrator starts but never completes
- [ ] Infinite loop in iterations
- [ ] Exception not caught
- [ ] Completion event not sent

### 3. Partial Response
- [ ] First agent responds, children don't
- [ ] Output not streamed properly
- [ ] Frontend filters messages

### 4. Silent Failure
- [ ] Exception caught but not logged
- [ ] Error event not sent to frontend
- [ ] Frontend doesn't display errors

## Runs Currently Stuck
```sql
SELECT id, status, created_at, error 
FROM runs 
WHERE status = 'running' 
ORDER BY created_at DESC;
```

All stuck in "running" status with no error.

