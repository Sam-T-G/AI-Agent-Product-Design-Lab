# Project Structure

## Overview

This document explains the organization of the AI Agent Product Design Lab codebase.

## Directory Structure

```
AI-Agent-Product-Design-Lab/
├── backend/                  # Python FastAPI backend
│   ├── main.py              # Application entry point
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # Environment variables (gitignored)
│   ├── api/                 # API routes
│   │   ├── routes/
│   │   │   ├── agents.py    # Agent CRUD endpoints
│   │   │   ├── links.py     # Link management endpoints
│   │   │   ├── runs.py      # Run execution endpoints
│   │   │   └── templates.py # Template/library endpoints
│   │   └── middleware.py    # Custom middleware
│   ├── core/                # Core business logic
│   │   ├── orchestrator.py  # Agent graph execution
│   │   ├── gemini_client.py # Gemini API wrapper
│   │   └── models.py        # Pydantic models
│   ├── db/                  # Database layer
│   │   ├── database.py      # Database connection
│   │   ├── schemas.py       # SQLAlchemy models
│   │   └── init.py          # Database initialization
│   └── utils/               # Utility functions
│       └── tools.py         # Tool implementations
│
├── frontend/                # Next.js frontend
│   ├── package.json         # Node dependencies
│   ├── .env.local           # Environment variables (gitignored)
│   ├── app/                 # Next.js App Router
│   │   ├── (lab)/           # Lab route group
│   │   │   ├── page.tsx     # Main canvas page
│   │   │   └── layout.tsx   # Layout wrapper
│   │   ├── api/             # Next.js API routes (if needed)
│   │   └── layout.tsx       # Root layout
│   ├── components/          # React components
│   │   ├── canvas/          # Canvas-related components
│   │   │   ├── AgentNode.tsx
│   │   │   ├── AgentCanvas.tsx
│   │   │   └── ConnectionHandle.tsx
│   │   ├── drawer/          # Drawer components
│   │   │   ├── AgentDrawer.tsx
│   │   │   └── PromptEditor.tsx
│   │   ├── console/         # Console components
│   │   │   └── RunsConsole.tsx
│   │   └── library/         # Library components
│   │       └── TemplatesLibrary.tsx
│   ├── lib/                 # Utility libraries
│   │   ├── api.ts           # API client functions
│   │   ├── store.ts         # Zustand store
│   │   └── types.ts         # TypeScript type definitions
│   └── hooks/               # Custom React hooks
│       └── useAgentExecution.ts
│
├── docs/                    # Documentation
│   ├── README.md            # Docs overview
│   ├── planning/            # Planning documents
│   │   ├── product-vision.md
│   │   ├── roadmap.md
│   │   └── architecture-decisions.md
│   ├── implementation/      # Implementation docs
│   │   ├── system-architecture.md
│   │   ├── api-design.md
│   │   ├── data-models.md
│   │   ├── ui-ux-spec.md
│   │   ├── setup-guide.md
│   │   ├── tech-stack.md
│   │   ├── gemini-integration.md
│   │   └── agent-execution.md
│   └── notes-lessons-learned/  # Retrospectives and notes
│
├── .gitignore               # Git ignore rules
├── .env.example             # Environment variable template
├── README.md                # Main project README
├── PROJECT_STRUCTURE.md     # This file
├── CONTRIBUTING.md          # Contribution guidelines
└── CHANGELOG.md             # Version history
```

## Key Conventions

### Naming Conventions

- **Files**: `kebab-case` for files, `PascalCase` for React components
- **Python modules**: `snake_case`
- **TypeScript/JavaScript**: `camelCase` for variables, `PascalCase` for types/components

### Code Organization

- **Separation of concerns**: Business logic in `core/`, API routes in `api/routes/`
- **Type safety**: TypeScript on frontend, Pydantic on backend
- **Reusability**: Shared utilities in `lib/` or `utils/`

### File Locations

- **New API endpoint**: Add to `backend/api/routes/`
- **New React component**: Add to `frontend/components/`
- **New utility function**: Add to `frontend/lib/` or `backend/utils/`
- **New documentation**: Add to appropriate `docs/` subfolder

## Development Workflow

1. **Feature branch**: Create from `main`
2. **Make changes**: Follow existing structure
3. **Documentation**: Update relevant docs if architecture changes
4. **Testing**: Add tests for new features
5. **Review**: Submit PR with clear description

## Database Migrations

- **Location**: `backend/db/migrations/` (to be created)
- **Tool**: Alembic (when using SQLAlchemy)
- **Process**: Create migration, review, apply

## Environment Variables

- **Backend**: `backend/.env` (see `.env.example`)
- **Frontend**: `frontend/.env.local` (see `.env.example`)
- **Never commit**: Actual `.env` files (gitignored)

## Future Structure Considerations

As the project grows, consider:

- **Tests**: `backend/tests/`, `frontend/__tests__/`
- **Scripts**: `scripts/` for deployment and utilities
- **Docker**: `Dockerfile`, `docker-compose.yml`
- **CI/CD**: `.github/workflows/` or `.gitlab-ci.yml`

