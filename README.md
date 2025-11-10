# AI Agent Product Design Lab

> **A production-ready, full-stack platform for designing and orchestrating multi-agent AI workflows with visual composition, recursive delegation, and real-time execution.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)

## Overview

**AI Agent Product Design Lab** is a sophisticated, enterprise-grade platform that enables users to visually design, compose, and execute complex multi-agent AI workflows without writing code. Built from the ground up with modern full-stack architecture, it solves the critical challenge of orchestrating hierarchical AI agent systems with recursive delegation, session isolation, and real-time streaming execution.

### Key Problem Solved

Traditional AI agent frameworks require extensive coding to coordinate multiple agents, handle delegation, and manage execution flow. This platform provides a **no-code visual interface** where users can:
- Design agent hierarchies of unlimited depth
- Define parent-child relationships through drag-and-drop
- Enable recursive delegation where agents autonomously delegate to their children
- Execute complex workflows with real-time streaming feedback
- Isolate conversations per session for multi-user scenarios

## Core Features

### Visual Graph Editor
- **React Flow-based canvas** for intuitive agent composition
- Drag-and-drop interface for creating agent nodes
- Visual connection system for defining parent-child relationships
- Real-time graph updates with optimistic UI patterns
- Session-based graph persistence

### Multi-Level Agent Orchestration
- **Recursive delegation engine** supporting unlimited hierarchy depth
- Intelligent agent capability discovery using LLM analysis
- Circuit breaker pattern for fault tolerance
- Parallel branch exploration for efficient execution
- Context-aware message passing through agent trees

### Real-Time Execution
- **Server-Sent Events (SSE)** for live streaming of agent outputs
- Per-agent execution logs with structured logging
- Status tracking (idle, processing, completed, error)
- Session isolation ensuring conversation privacy
- Optimistic UI updates with rollback on errors

### Production-Ready Architecture
- **FastAPI backend** with async/await patterns throughout
- **Next.js 14** frontend with App Router and React Server Components
- SQLAlchemy ORM with Alembic migrations
- Docker containerization for easy deployment
- Structured logging with correlation IDs
- API key management and validation

### Advanced Technical Features
- **Agent tree caching** for O(1) capability lookups
- Depth-limited recursion with cycle detection
- Timeout management and graceful degradation
- Response aggregation from parallel child agents
- Photo injection support for vision-capable agents
- Database-backed persistence with SQLite (dev) / PostgreSQL (prod)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Canvas     │  │   Drawer     │  │   Console    │      │
│  │ (React Flow) │  │ (Properties) │  │  (Streaming) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │ REST API + SSE                  │
└────────────────────────────┼─────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Orchestrator Engine                     │   │
│  │  ┌──────────────┐  ┌──────────────┐                │   │
│  │  │ Recursive    │  │   Agent      │                │   │
│  │  │ Delegator    │  │   Selector   │                │   │
│  │  └──────────────┘  └──────────────┘                │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Gemini Client (Streaming)                    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         SQLAlchemy + Alembic                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- **Node.js** 18+ and npm
- **Python** 3.10+
- **Gemini API Key** ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd AI-Agent-Product-Design-Lab

# Backend setup
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# Create backend/.env
echo "GEMINI_API_KEY=your_api_key_here" > backend/.env
echo "DATABASE_URL=sqlite:///./agents.db" >> backend/.env

# Frontend setup
cd frontend
npm install

# Create frontend/.env.local
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api" > .env.local
```

### Running the Application

```bash
# Terminal 1: Start backend
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev
```

Visit **http://localhost:3000** to access the application.

**API Documentation**: http://localhost:8000/docs (FastAPI auto-generated Swagger UI)

## Technology Stack

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **React Flow** - Graph visualization library
- **Zustand** - Lightweight state management
- **TanStack Query** - Server state management with optimistic updates

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migration tool
- **Google Generative AI** - Gemini API integration
- **Pydantic** - Data validation and settings management
- **Structlog** - Structured logging

### Infrastructure
- **Docker** - Containerization
- **SQLite** - Development database
- **PostgreSQL** - Production-ready database support

## Technical Highlights

### Recursive Delegation System
The platform implements a sophisticated recursive delegation engine that allows agents to autonomously delegate tasks to their children, who can further delegate to their grandchildren, supporting unlimited depth:

- **DelegationRequest/Response** objects with path tracking
- **Cycle detection** to prevent infinite loops
- **Depth limits** (configurable, default: 10 hops)
- **Circuit breaker** pattern for fault tolerance
- **Parallel branch exploration** for efficiency

### Agent Capability Discovery
Using LLM analysis, the system automatically discovers what each agent can do:
- Keyword/topic extraction from agent prompts
- Recursive capability mapping through agent trees
- Confidence scoring for delegation decisions
- Cached capability lookups for performance

### Session Isolation
Multi-user support with complete conversation isolation:
- Session-based agent graphs
- Isolated conversation histories
- Per-session run tracking
- Database-level session scoping

### Real-Time Streaming
Server-Sent Events (SSE) provide live execution feedback:
- Per-agent log streaming
- Status updates (running, completed, error)
- Structured event types for frontend consumption
- Graceful reconnection handling

## Documentation

Comprehensive documentation is organized in the `docs/` folder:

- **[Setup Guide](docs/implementation/setup-guide.md)** - Detailed installation and configuration
- **[System Architecture](docs/implementation/system-architecture.md)** - Deep dive into system design
- **[API Design](docs/implementation/api-design.md)** - REST API specifications
- **[Testing Guide](docs/implementation/TESTING_GUIDE.md)** - Testing strategies and examples
- **[Deployment Guide](docs/implementation/README_DEPLOY.md)** - Production deployment instructions

### Implementation Notes
- **[Recursive Delegation](docs/implementation/RECURSIVE_DELEGATION_COMPLETE.md)** - Multi-level delegation implementation
- **[Agent Communication Protocol](docs/implementation/AGENT_COMMUNICATION_PROTOCOL.md)** - Message passing design
- **[Session Isolation](docs/implementation/SESSION_ISOLATION_REPORT.md)** - Multi-user architecture

## Example Use Case

**Travel Planning Agent System:**
1. **Head Travel Agent** - Coordinates overall trip planning
2. **Scheduling Agent** (child) - Manages dates and timelines
3. **Financial Agent** (child) - Handles budget constraints
   - **Flight Agent** (grandchild) - Books flights within budget
   - **Experiences Agent** (grandchild) - Finds activities within budget
   - **Food Agent** (grandchild) - Suggests restaurants within budget

The Head Agent receives a request, delegates to Scheduling and Financial agents. The Financial Agent further delegates to its children, each respecting budget constraints. All agents execute in parallel where possible, with results aggregated back up the tree.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details

## Roadmap

- [x] Visual agent graph with React Flow
- [x] Agent CRUD operations
- [x] Multi-level recursive delegation
- [x] Real-time streaming execution
- [x] Session isolation
- [x] Agent capability discovery
- [ ] Tool system (web search, HTTP fetch, file operations)
- [ ] Agent template library
- [ ] Graph versioning and rollback
- [ ] Execution analytics and cost tracking
- [ ] WebSocket upgrade for bidirectional control

See [Roadmap](docs/planning/roadmap.md) for complete development plan.

---

**Built with Next.js, FastAPI, and Google Gemini**
