# Debugging Information

## 🚀 Servers Running

### Backend
- **URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Status**: ✅ Running

### Frontend
- **URL**: http://localhost:3000
- **Status**: ✅ Running

## 🔍 Debugging Tips

### Backend Debugging

1. **Check logs**: Backend logs are in JSON format via structlog
2. **API Testing**: Use http://localhost:8000/docs for interactive API testing
3. **Database**: SQLite database at `backend/agents.db`
4. **Common Issues**:
   - `GEMINI_API_KEY not set`: Create `backend/.env` with your API key
   - Port already in use: Change port in uvicorn command
   - Database locked: Ensure only one process accessing DB

### Frontend Debugging

1. **Browser Console**: Open DevTools (F12) to see errors
2. **Network Tab**: Check API calls to `/api/*` endpoints
3. **React DevTools**: Install browser extension for component inspection
4. **Common Issues**:
   - CORS errors: Check backend CORS settings
   - API connection errors: Verify `NEXT_PUBLIC_API_BASE_URL` in `.env.local`
   - Build errors: Check TypeScript errors with `npm run build`

### Testing Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List agents
curl http://localhost:8000/api/agents

# Create agent
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Agent","role":"worker","system_prompt":"You are helpful"}'

# Create run
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"root_agent_id":"<agent-id>","input":{}}'
```

## 📝 Log Locations

- **Backend**: Check terminal where uvicorn is running
- **Frontend**: Browser console (F12)
- **Database**: `backend/agents.db` (SQLite)

## 🛠️ Quick Fixes

### Restart Backend
```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Restart Frontend
```bash
cd frontend
npm run dev
```

### Check Database
```bash
cd backend
source ../.venv/bin/activate
python -c "from db.database import engine; from db.schemas import Base; Base.metadata.create_all(engine); print('✅ Database OK')"
```

## 🔑 Environment Variables

**Backend** (`backend/.env`):
```
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///./agents.db
```

**Frontend** (`frontend/.env.local`):
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```


