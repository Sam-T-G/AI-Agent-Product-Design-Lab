# API Design

Base URL: `/api`

All endpoints return JSON. Use standard HTTP status codes.

## Authentication

Currently: None (for MVP). Future: Bearer token or session-based auth.

## Agents

### List Agents

```
GET /api/agents
```

**Response 200**
```json
{
  "agents": [
    {
      "id": "agent-123",
      "name": "Product Manager",
      "role": "pm",
      "system_prompt": "You are a product manager...",
      "tools": [],
      "parameters": {
        "temperature": 0.7,
        "max_tokens": 1000
      },
      "parent_id": null,
      "created_at": "2025-01-XX...",
      "updated_at": "2025-01-XX..."
    }
  ]
}
```

### Create Agent

```
POST /api/agents
```

**Request Body**
```json
{
  "name": "New Agent",
  "role": "worker",
  "system_prompt": "You are a helpful agent.",
  "tools": [],
  "parameters": {
    "temperature": 0.7
  },
  "parent_id": null
}
```

**Response 201**
```json
{
  "id": "agent-456",
  "name": "New Agent",
  "role": "worker",
  "system_prompt": "You are a helpful agent.",
  "tools": [],
  "parameters": {
    "temperature": 0.7
  },
  "parent_id": null,
  "created_at": "2025-01-XX...",
  "updated_at": "2025-01-XX..."
}
```

**Errors**
- `400`: ValidationError - Invalid request body
- `422`: UnprocessableEntity - Missing required fields

### Get Agent

```
GET /api/agents/{id}
```

**Response 200**
```json
{
  "id": "agent-123",
  "name": "Product Manager",
  "role": "pm",
  "system_prompt": "You are a product manager...",
  "tools": [],
  "parameters": {},
  "parent_id": null,
  "created_at": "2025-01-XX...",
  "updated_at": "2025-01-XX..."
}
```

**Errors**
- `404`: Agent not found

### Update Agent

```
PUT /api/agents/{id}
```

**Request Body**
```json
{
  "name": "Updated Name",
  "system_prompt": "Updated prompt...",
  "tools": [{"name": "web_search"}],
  "parameters": {
    "temperature": 0.8
  }
}
```

**Response 200**: Same as Get Agent

**Errors**
- `400`: ValidationError
- `404`: Agent not found

### Delete Agent

```
DELETE /api/agents/{id}
```

**Response 204**: No content

**Errors**
- `404`: Agent not found
- `409`: Agent has children (must detach or delete children first)

## Links

Links represent parent/child relationships between agents. Alternatively, this can be managed via `parent_id` in the agent model.

### Create Link

```
POST /api/links
```

**Request Body**
```json
{
  "parent_agent_id": "agent-123",
  "child_agent_id": "agent-456"
}
```

**Response 201**
```json
{
  "parent_agent_id": "agent-123",
  "child_agent_id": "agent-456",
  "created_at": "2025-01-XX..."
}
```

**Errors**
- `400`: ValidationError
- `404`: One or both agents not found
- `409`: Link already exists or would create cycle

### Delete Link

```
DELETE /api/links
```

**Request Body**
```json
{
  "parent_agent_id": "agent-123",
  "child_agent_id": "agent-456"
}
```

**Response 204**: No content

**Errors**
- `404`: Link not found

## Runs

### Execute Run

```
POST /api/runs
```

**Request Body**
```json
{
  "root_agent_id": "agent-123",
  "input": {
    "task": "Create a product brief for a habit tracker"
  }
}
```

**Response 201**
```json
{
  "id": "run-789",
  "root_agent_id": "agent-123",
  "status": "running",
  "created_at": "2025-01-XX..."
}
```

### Get Run Status

```
GET /api/runs/{id}
```

**Response 200**
```json
{
  "id": "run-789",
  "root_agent_id": "agent-123",
  "status": "completed",
  "input": {...},
  "output": {
    "agent-123": "Output from root agent...",
    "agent-456": "Output from child agent..."
  },
  "logs": [
    {
      "agent_id": "agent-123",
      "timestamp": "2025-01-XX...",
      "message": "Starting execution..."
    }
  ],
  "created_at": "2025-01-XX...",
  "finished_at": "2025-01-XX..."
}
```

**Status Values**: `pending`, `running`, `completed`, `failed`, `cancelled`

### Stream Run Logs

```
GET /api/runs/{id}/stream
```

**Content-Type**: `text/event-stream`

**Stream Format** (Server-Sent Events):
```
event: log
data: {"agent_id": "agent-123", "timestamp": "...", "message": "Starting..."}

event: output
data: {"agent_id": "agent-123", "output": "Result..."}

event: status
data: {"status": "completed"}

event: error
data: {"agent_id": "agent-123", "error": "Error message"}
```

## Templates & Library

### List Templates

```
GET /api/templates
```

**Response 200**
```json
{
  "templates": [
    {
      "id": "template-pm",
      "name": "Product Manager",
      "role": "pm",
      "system_prompt": "You are a product manager...",
      "tools": ["web_search"],
      "description": "Manages product strategy and requirements"
    }
  ]
}
```

### List Tools

```
GET /api/tools
```

**Response 200**
```json
{
  "tools": [
    {
      "name": "web_search",
      "description": "Search the web for information",
      "parameters": {
        "query": {
          "type": "string",
          "required": true,
          "description": "Search query"
        }
      }
    }
  ]
}
```

## Error Response Format

All errors follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request body",
    "details": {
      "field": "system_prompt",
      "issue": "Field is required"
    }
  }
}
```

Common error codes:
- `VALIDATION_ERROR`: Invalid request data
- `NOT_FOUND`: Resource not found
- `CONFLICT`: Resource conflict (e.g., duplicate link)
- `INTERNAL_ERROR`: Server error
- `RATE_LIMIT_EXCEEDED`: Too many requests

