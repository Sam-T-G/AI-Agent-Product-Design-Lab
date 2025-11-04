"""Run execution endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json

from db.database import get_db_session
from db.schemas import RunModel, AgentModel
from core.models import Run, RunRequest
from core.orchestrator import AgentOrchestrator
from core.logging import get_logger

logger = get_logger("runs")
router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=Run, status_code=status.HTTP_201_CREATED)
async def create_run(run_data: RunRequest, db: Session = Depends(get_db_session)):
    """Create a new run."""
    # Verify root agent exists
    root_agent = db.query(AgentModel).filter(AgentModel.id == run_data.root_agent_id).first()
    if not root_agent:
        raise HTTPException(status_code=404, detail="Root agent not found")
    
    run = RunModel(
        root_agent_id=run_data.root_agent_id,
        status="pending",
        input=run_data.input,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    logger.info("run_created", run_id=run.id, root_agent_id=run_data.root_agent_id)
    return Run.model_validate(run)


@router.get("/{run_id}", response_model=Run)
async def get_run(run_id: str, db: Session = Depends(get_db_session)):
    """Get run status and details."""
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return Run.model_validate(run)


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, db: Session = Depends(get_db_session)):
    """Stream run execution events via Server-Sent Events."""
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    orchestrator = AgentOrchestrator(db)
    
    async def event_generator():
        """Generate SSE events."""
        try:
            # Send initial connection event
            yield f"event: connected\n"
            yield f"data: {json.dumps({'run_id': run_id})}\n\n"
            
            event_count = 0
            async for event in orchestrator.execute_run(
                run_id=run_id,
                root_agent_id=run.root_agent_id,
                input_data=run.input,
            ):
                # Format as SSE
                event_type = event.get("type", "log")
                agent_id = event.get("agent_id", "")
                data = event.get("data", "")
                
                # Send event
                event_json = json.dumps({
                    "type": event_type,
                    "agent_id": agent_id,
                    "data": data,
                })
                yield f"event: {event_type}\n"
                yield f"data: {event_json}\n\n"
                
                event_count += 1
                
                # Send heartbeat every 10 events (instead of every event)
                if event_count % 10 == 0:
                    yield f": heartbeat\n\n"
            
            # Send completion
            yield f"event: completed\n"
            yield f"data: {json.dumps({'status': 'completed', 'run_id': run_id})}\n\n"
            
        except GeneratorExit:
            # Client disconnected
            logger.info("sse_client_disconnected", run_id=run_id)
            raise
        except Exception as e:
            logger.error("sse_error", run_id=run_id, error=str(e), exc_info=True)
            try:
                error_json = json.dumps({"error": str(e), "run_id": run_id})
                yield f"event: error\n"
                yield f"data: {error_json}\n\n"
            except:
                pass  # Client may have disconnected
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
        },
    )

