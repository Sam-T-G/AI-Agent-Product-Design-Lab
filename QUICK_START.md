# Quick Start Guide

## ✅ Implementation Status

All core components are implemented and validated:

- ✅ Backend API (FastAPI + SQLAlchemy + Alembic)
- ✅ Gemini Integration with streaming
- ✅ Agent Orchestrator with SSE
- ✅ Frontend Canvas (React Flow)
- ✅ Agent Drawer (Property Editor)
- ✅ Runs Console (SSE Streaming)
- ✅ Full Integration

## 🚀 Running the Application

### Backend

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

**API Documentation**: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm run dev
```

**Application**: http://localhost:3000

**Note**: Create `.env.local` in `frontend/` with:
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

### Backend Environment

Create `backend/.env` with:
```
GEMINI_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./agents.db
```

## 🧪 Testing the Demo

1. **Start Backend**: `cd backend && source ../.venv/bin/activate && uvicorn main:app --reload`
2. **Start Frontend**: `cd frontend && npm run dev`
3. **Open**: http://localhost:3000
4. **Add Agent**: Click the "+" button on canvas
5. **Edit Agent**: Click an agent node to open drawer
6. **Connect Agents**: Drag from parent node's bottom handle to child's top handle
7. **Run Workflow**: Select root agent, click "Start Run" in console

## 📊 Validation Results

- ✅ Backend API endpoints: All responding (200)
- ✅ Frontend build: Successful
- ✅ TypeScript: No errors
- ✅ Database: Migrations applied
- ✅ Components: All building correctly

## 🎯 Next Steps (Optional Enhancements)

- Add agent templates
- Implement HTTP fetch tool
- Add error retry logic
- Enhance UI styling
- Add graph persistence


