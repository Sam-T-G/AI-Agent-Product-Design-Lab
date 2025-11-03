## Implementation Docs

Design details and developer-facing documentation.

### Suggested Files

- system-architecture.md
- api-design.md
- data-models.md
- ui-ux-spec.md
- setup-guide.md
- tech-stack.md
- gemini-integration.md
- agent-execution.md

### Template: API Spec

```
# Endpoint: /api/example

Method: POST
Auth: none | bearer | session | key

Request Body
{
  "field": "value"
}

Response 200
{
  "result": "..."
}

Errors
- 400: ValidationError
- 401: Unauthorized
```
