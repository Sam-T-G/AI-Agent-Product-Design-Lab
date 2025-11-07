"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from core.settings import settings
from core.logging import configure_logging, get_logger
from api.router import api_router
from db.database import init_db

# Configure logging
configure_logging()
logger = get_logger("main")

# Create FastAPI app
app = FastAPI(
    title="AI Agent Product Design Lab API",
    description="Backend API for multi-agent orchestration",
    version="0.1.0",
)

# CORS middleware - must be added before routes
cors_origins = settings.cors_origins or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Initialize database
init_db()

# Include API routes
app.include_router(api_router)

# Request model for test prompt
class PromptRequest(BaseModel):
    system_prompt: str
    user_input: str
    model: str = "gemini-2.5-flash"


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/test-prompt")
async def test_prompt(req: PromptRequest) -> Dict[str, Any]:
    """Test endpoint for Gemini prompt (placeholder)."""
    logger.info("test_prompt_called", model=req.model)
    return {
        "text": f"Test response for: {req.user_input}",
        "note": "Gemini integration not yet implemented",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )

