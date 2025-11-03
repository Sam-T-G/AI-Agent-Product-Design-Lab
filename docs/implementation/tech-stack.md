# Tech Stack

## Frontend

### Core Framework
- **Next.js 14+** (App Router)
  - Server-side rendering and static generation
  - Built-in API routes
  - Image optimization
  - TypeScript support

### Styling
- **Tailwind CSS**
  - Utility-first CSS framework
  - Rapid UI development
  - Small bundle size with purging

### State Management
- **Zustand + Immer**
  - Minimal global state with immutable updates
  - Co-locate feature slices; avoid monolithic stores
  - Persist selected slices (e.g., graph layout) with middleware

### Data Fetching
- **@tanstack/react-query**
  - Server state management and caching
  - Optimistic updates and retry policies
  - Query keys per resource (`['agents', id]`, `['runs', id]`)

### Graph Visualization
- **React Flow**
  - Node-based graph UI with custom nodes/edges
  - Use `useEdgesState`/`useNodesState` for controlled graphs
  - Enable `fitView`, `minimap`, `controls` for usability
  - Virtualization for large graphs (Pro/enterprise later if needed)

### Additional Libraries
- **Zod**: Runtime validation for frontend inputs
- **React**: UI library
- **TypeScript**: Type safety
- **fetch** (native) or **Axios**: HTTP client
- **date-fns**: Date utilities (avoid moment)

## Backend

### Web Framework
- **FastAPI**
  - Modern Python web framework
  - Automatic API documentation
  - Async/await support
  - Pydantic integration

### AI Integration
- **google-generativeai**
  - Gemini 1.5 models, streaming support
  - Add abstraction to allow swapping providers later

### Database
- **SQLAlchemy + Alembic**
  - ORM with migrations
  - Start with SQLite; target PostgreSQL in prod

### Validation
- **Pydantic v2 + pydantic-settings**
  - Fast validation and settings management

### Server
- **Uvicorn** (dev) + **Gunicorn** (prod) or Fly/Render native
- **SSE/WebSockets** via FastAPI for realtime

### Additional Libraries
- **python-dotenv**: Environment variable management
- **python-multipart**: Form data handling
- **structlog**: Structured logging
- **slowapi**: Rate limiting (optional)
- **httpx**: Async HTTP client for tool calls

## Development Tools

### Frontend
- **ESLint**: Linting
- **Prettier**: Code formatting
- **TypeScript**: Type checking

### Backend
- **Black**: Code formatting
- **Ruff**: Linting
- **pytest** + **pytest-asyncio**: Testing
- **pre-commit**: Enforce formatting/linting on commit

## Deployment

### Frontend
- **Vercel** (recommended)
  - Native Next.js support
  - Automatic deployments
  - Edge functions

- **Netlify**
  - Static site hosting
  - Serverless functions

### Backend
- **Fly.io** / **Render** / **Railway** / **Cloud Run**
  - Container-based, autoscaling
  - Prefer Postgres-managed service
  - Use healthchecks and readiness probes

## Future Considerations

### Database
- **PostgreSQL**: For production scaling
- **Redis**: Caching and session storage

### Real-time
- **SSE**: Simpler server-to-client streaming (MVP)
- **WebSockets**: Bidirectional control (pause/resume, tools)

### Monitoring
- **Sentry**: Error tracking
- **PostHog** or **Plausible**: Analytics

### CI/CD
- **GitHub Actions**: Automated testing and deployment
- **GitLab CI**: Alternative CI/CD

### Observability
- Structured logs to stdout
- `/health` and `/ready` endpoints

