# AI Agent Product Design Lab

Design, compose, and deploy modular AI agents for product development. Create new agent instances dynamically from the UI, visually wire parent/child relationships, and edit each agent's independent prompting without code.

**Built with**: Next.js, Tailwind CSS, Python FastAPI, and Google Gemini

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd AI-Agent-Product-Design-Lab

# Backend setup
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# Frontend setup
cd frontend
npm install

# Set up environment variables
# Copy .env.example to .env and add your Gemini API key
# See docs/implementation/setup-guide.md for details

# Run development servers
# Terminal 1: Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Visit http://localhost:3000 to see the application.

**📖 For detailed setup instructions, see [Setup Guide](docs/implementation/setup-guide.md)**

## ✨ Features

- **No-code agent composition**: Add agents with a plus button, visually connect parent/child relationships
- **Modular agents**: Each agent has a role, tools, and customizable prompt
- **Visual graph editor**: Drag-and-drop interface for building agent workflows
- **Real-time execution**: Stream agent outputs and logs as they execute
- **Gemini-powered**: Uses Google's Gemini API for agent reasoning

## 📚 Documentation

### Planning & Vision

- [Product Vision](docs/planning/product-vision.md) - Goals, target users, success metrics
- [Roadmap](docs/planning/roadmap.md) - Development phases and milestones
- [Architecture Decisions](docs/planning/architecture-decisions.md) - ADRs for key technical choices

### Implementation

- [System Architecture](docs/implementation/system-architecture.md) - High-level system design
- [API Design](docs/implementation/api-design.md) - REST API endpoints and specifications
- [Data Models](docs/implementation/data-models.md) - Pydantic models and database schemas
- [UI/UX Specification](docs/implementation/ui-ux-spec.md) - Interface design and interactions
- [Setup Guide](docs/implementation/setup-guide.md) - Development environment setup
- [Tech Stack](docs/implementation/tech-stack.md) - Technology choices and rationale
- [Gemini Integration](docs/implementation/gemini-integration.md) - AI API integration guide
- [Agent Execution](docs/implementation/agent-execution.md) - Graph execution logic
- [Demo Spec](docs/implementation/demo-spec.md) - Minimal steps to build and run the demo
- [AI Implementation Plan](docs/implementation/ai-implementation-plan.md) - Step-by-step tasks with checks

### Project Structure

- [Project Structure](PROJECT_STRUCTURE.md) - Codebase organization
- [Contributing Guide](CONTRIBUTING.md) - How to contribute
- [Changelog](CHANGELOG.md) - Version history

## 🏗️ Architecture

```
┌─────────────────┐         ┌─────────────────┐
│  Next.js        │ ◄─────► │  FastAPI        │
│  Frontend       │   REST  │  Backend        │
│                 │         │                 │
│  - Canvas       │         │  - Orchestrator │
│  - Drawer       │         │  - Gemini Client│
│  - Console      │         │  - API Routes   │
└─────────────────┘         └─────────────────┘
```

**See [System Architecture](docs/implementation/system-architecture.md) for details.**

## 🛠️ Tech Stack

- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS, React Flow, Zustand
- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, Google Generative AI
- **Database**: SQLite (development), PostgreSQL (production-ready)

**See [Tech Stack](docs/implementation/tech-stack.md) for complete list.**

## 📋 Requirements

- Node.js 18+
- Python 3.10+
- Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 🗺️ Roadmap

- [x] Project structure and documentation
- [ ] Visual agent graph with React Flow
- [ ] Agent CRUD operations
- [ ] Basic execution engine
- [ ] Streaming outputs
- [ ] Tool system
- [ ] Template library
- [ ] Graph persistence

**See [Roadmap](docs/planning/roadmap.md) for complete development plan.**

## 💡 Learn More

- Explore the [documentation](docs/README.md) for detailed guides
- Check [architecture decisions](docs/planning/architecture-decisions.md) to understand design choices
- Review [API design](docs/implementation/api-design.md) for integration details

---

**Need help?** Open an issue or check the documentation in the `docs/` folder.
