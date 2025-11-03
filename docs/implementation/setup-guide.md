# Setup Guide

## Prerequisites

- **Node.js**: 18+ (recommended: use nvm or fnm)
- **Python**: 3.10+ (recommended: use pyenv)
- **Git**: For version control
- **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd AI-Agent-Product-Design-Lab
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Environment Variables

Create `.env` files:

**Backend** (`backend/.env`):

```bash
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./agents.db
```

**Frontend** (`frontend/.env.local`):

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

### 5. Initialize Database

```bash
# From backend directory
python -m db.init
```

### 6. Run Development Servers

**Terminal 1 - Backend:**

```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd frontend
npm run dev
```

### 7. Access Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Detailed Setup

### Backend Dependencies

Create `backend/requirements.txt`:

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
google-generativeai==0.3.1
pydantic==2.5.0
pydantic-settings==2.1.0
sqlalchemy==2.0.23
python-multipart==0.0.6
python-dotenv==1.0.0
httpx==0.27.2
structlog==24.2.0
alembic==1.13.2
slowapi==0.1.9
```

Install:

```bash
pip install -r backend/requirements.txt
```

### Frontend Dependencies

The frontend will be set up with:

```bash
cd frontend
npm create next@latest . --yes --ts --tailwind --app
npm install zustand @tanstack/react-query reactflow
```

Key dependencies:

- `next`: React framework
- `react`: UI library
- `tailwindcss`: Styling
- `zustand`: State management
- `@tanstack/react-query`: Data fetching
- `reactflow`: Graph visualization

### Database Setup

For SQLite (default):

```bash
# Database file created automatically on first run
# No additional setup needed
```

For PostgreSQL (production):

```bash
# Install PostgreSQL
# Update DATABASE_URL in backend/.env
DATABASE_URL=postgresql://user:password@localhost:5432/agents_db

# Run migrations
python -m db.migrate
```

## Project Structure

```
AI-Agent-Product-Design-Lab/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env
│   ├── api/
│   │   └── routes/
│   ├── core/
│   ├── db/
│   └── utils/
├── frontend/
│   ├── package.json
│   ├── .env.local
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── hooks/
├── docs/
│   ├── planning/
│   ├── implementation/
│   └── notes-lessons-learned/
└── README.md
```

## Troubleshooting

### Backend Issues

**Port already in use:**

```bash
# Change port in uvicorn command
uvicorn main:app --reload --port 8001
```

**Import errors:**

```bash
# Ensure virtual environment is activated
# Reinstall dependencies
pip install -r backend/requirements.txt --force-reinstall
```

**Gemini API errors:**

- Verify API key is correct in `.env`
- Check API key has proper permissions
- Ensure you have API quota remaining

### Frontend Issues

**Port already in use:**

```bash
# Change port
npm run dev -- -p 3001
```

**Module not found:**

```bash
# Clear cache and reinstall
rm -rf node_modules .next
npm install
```

**API connection errors:**

- Verify backend is running on port 8000
- Check `NEXT_PUBLIC_API_BASE_URL` in `.env.local`
- Check CORS settings in backend

### Database Issues

**SQLite locked:**

- Ensure only one process is accessing the database
- Close any database viewers
- Restart backend server

**Migration errors:**

- Delete database file and recreate
- Check database URL format

## Development Workflow

### Making Changes

1. Create a feature branch
2. Make changes
3. Test locally
4. Commit with descriptive messages
5. Push and create PR

### Testing

**Backend:**

```bash
cd backend
pytest
```

**Frontend:**

```bash
cd frontend
npm test
```

### Code Quality

**Backend:**

```bash
# Format with black
black .

# Lint with ruff
ruff check .

# Run pre-commit hooks locally (optional)
pre-commit run --all-files
```

**Frontend:**

```bash
# Format with Prettier
npm run format

# Lint with ESLint
npm run lint
```

## Production Setup

See [deployment guide](../planning/deployment.md) for production deployment instructions.
