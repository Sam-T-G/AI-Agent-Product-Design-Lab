"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from core.settings import settings
from core.logging import configure_logging, get_logger
from api.router import api_router
from db.database import init_db
from db.database import get_db
from core.pipeline_registry import PipelineRegistry

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
# Allow common local dev hosts and local network IPs (e.g., 192.168.x.x:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^http://(localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|192\\.168\\.\\d+\\.\\d+):\\d{2,5}$",
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
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


@app.on_event("startup")
async def _startup_refresh_pipeline() -> None:
    """Build pipeline awareness at startup."""
    try:
        with get_db() as db:
            PipelineRegistry.instance().refresh(db)
            logger.info("pipeline_registry_initialized")
    except Exception as e:
        logger.warning("pipeline_registry_init_failed", error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )

