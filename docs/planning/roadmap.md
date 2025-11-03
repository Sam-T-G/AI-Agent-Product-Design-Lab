# Roadmap

## Phase 1: Core MVP

- [ ] Visual agent graph with React Flow

  - Node palette for adding agents
  - Drag-to-connect parent/child relationships
  - Minimap and zoom controls
  - Basic node styling and selection

- [ ] Agent management

  - Create/read/update/delete agents via UI
  - Agent properties drawer (name, role, prompt, tools)
  - Template system for common agent types

- [ ] Basic execution
  - Single-agent test runs
  - Graph execution from root agent
  - Simple output display
  - SSE-based streaming from backend
  - Settings via pydantic-settings
  - Logging with structlog

## Phase 2: Enhanced Workflow

- [ ] Agent templates library

  - Predefined agents: Product Manager, Researcher, Designer, Engineer, QA
  - Custom template creation and saving
  - Template marketplace/sharing

- [ ] Tool system

  - Web search integration
  - HTTP fetch tool
  - File read/write operations
  - Vector search capabilities
  - Custom tool registration
  - Async HTTP via httpx

- [ ] Streaming execution
  - Real-time logs during agent execution
  - Per-node status updates
  - Intermediate output streaming
  - WebSocket upgrade for bidirectional control

## Phase 3: Advanced Features

- [ ] Graph persistence and versioning

  - Save/load agent graphs
  - Version history and rollback
  - Graph templates
  - Alembic migrations

- [ ] Execution controls

  - Pause/Resume/Stop running graphs
  - Retry failed nodes
  - Conditional routing between agents
  - Parallel execution at level boundaries

- [ ] Collaboration
  - Role-based access control
  - Graph sharing and permissions
  - Comments and annotations
  - Audit logs

## Phase 4: Enterprise Features

- [ ] Export/import

  - Graph export (JSON/YAML)
  - Prompt library export
  - Import from other formats

- [ ] Analytics and monitoring

  - Execution metrics and performance
  - Cost tracking per agent/run
  - Error analytics
  - Structured logs ingestion and dashboards

- [ ] Advanced orchestration
  - Parallel execution strategies
  - Dynamic agent spawning
  - Agent-to-agent communication protocols
  - Circuit breaker + retries
  - Rate limiting
