# Demo Spec (Minimal, Actionable)

## Goal

Create and run a multi-agent product workflow via a no-code canvas:
- Add agents (+)
- Link parent → child
- Edit prompts
- Run and stream outputs

## Scope (MVP)

- Agents: `ProductManager` (root), `Researcher`, `Designer` (children)
- Tools: HTTP fetch (for web research)
- Models: Gemini 2.5 Flash (default), temperature 0.7
- Streaming: SSE

## API Endpoints (must exist)

- `GET /api/agents` — list
- `POST /api/agents` — create `{ name, role, system_prompt, parameters?, parent_id? }`
- `PUT /api/agents/{id}` — update
- `DELETE /api/agents/{id}` — delete
- `POST /api/links` — create link `{ parent_agent_id, child_agent_id }`
- `DELETE /api/links` — delete link
- `POST /api/runs` — start `{ root_agent_id, input }` → `{ id, status }`
- `GET /api/runs/{id}/stream` — SSE stream of events

Event format:
```json
{
  "type": "log" | "output" | "status" | "error",
  "agent_id": "agent-123",
  "data": "..." 
}
```

## Frontend (pages/components)

- `app/(lab)/page.tsx` — canvas + drawer + console
- Components
  - `AgentCanvas` (React Flow, controlled nodes/edges)
  - `AgentDrawer` (name, role, system_prompt, temperature, model)
  - `RunsConsole` (start, stream logs/outputs)

Zustand store slices:
- `graphSlice`: nodes, edges, selection, actions (add/remove/link)
- `agentSlice`: CRUD via react-query; optimistic updates
- `runSlice`: current run id/status; SSE subscription

## Orchestration (backend)

- Execution: topological (parent first), fan-out per level in parallel
- Input routing: root gets user input; children get parent output
- Streaming: send `status -> output_chunk -> output` per agent
- Error handling: retries (3) with backoff; status `failed` with error

## Prompts (initial)

- ProductManager (root):
  "You orchestrate a product brief. Outline key questions for Researcher and deliver a final brief using their findings."

- Researcher (child):
  "You research the problem on the web and summarize 5 key findings with sources."

- Designer (child):
  "You propose 3 UX concepts based on ProductManager's brief and Researcher insights."

## Tool: HTTP Fetch (backend)

- `httpx` GET with timeout, user-agent
- Allowlist domains (MVP: `wikipedia.org`, `arxiv.org`, `developer.android.com`)
- Extract `<title>` and first 800 chars of `<body>`

## Run Flow

1. User clicks Run (root = ProductManager)
2. Orchestrator executes ProductManager → emits outline
3. Parallel execute Researcher/Designer with parent output
4. Stream logs/outputs to UI
5. Mark run `completed`

## Safety & Guardrails (MVP)

- Strip URLs not in allowlist
- Max tokens per call (1k)
- Temperature 0.7 default; 0.3 for Researcher

## References (succinct)

- Anthropic multi-agent research system (orchestrator/worker, parallelization)
- ReAct and Reflection patterns for reliability
- SSE first; WebSocket for bidirectional control later


