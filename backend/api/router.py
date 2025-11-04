"""API router aggregation."""
from fastapi import APIRouter

from api.routes import agents, links, runs

api_router = APIRouter(prefix="/api")

api_router.include_router(agents.router)
api_router.include_router(links.router)
api_router.include_router(runs.router)


