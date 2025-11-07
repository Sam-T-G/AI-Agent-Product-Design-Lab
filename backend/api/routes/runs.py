"""Run execution endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json

from db.database import get_db_session
from db.schemas import RunModel, AgentModel, SessionModel
from core.models import Run, RunRequest
from core.orchestrator_v2 import MessageBasedOrchestrator
from core.logging import get_logger

logger = get_logger("runs")
router = APIRouter(prefix="/runs", tags=["runs"])


def verify_session(session_id: str, db: Session) -> SessionModel:
    """Verify session exists and return it."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("", response_model=Run, status_code=status.HTTP_201_CREATED)
async def create_run(
    run_data: RunRequest,
    session_id: str = Query(..., description="Session ID"),
    db: Session = Depends(get_db_session)
):
    """Create a new run in a session."""
    verify_session(session_id, db)
    
    # Verify root agent exists and belongs to session
    root_agent = db.query(AgentModel).filter(
        AgentModel.id == run_data.root_agent_id,
        AgentModel.session_id == session_id
    ).first()
    if not root_agent:
        raise HTTPException(status_code=404, detail="Root agent not found or does not belong to session")
    
    run = RunModel(
        session_id=session_id,
        root_agent_id=run_data.root_agent_id,
        status="pending",
        input={**run_data.input, "images": run_data.images} if run_data.images else run_data.input,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    logger.info("run_created", run_id=run.id, root_agent_id=run_data.root_agent_id, session_id=session_id)
    return Run.model_validate(run)


@router.get("/{run_id}", response_model=Run)
async def get_run(
    run_id: str,
    session_id: str = Query(..., description="Session ID"),
    db: Session = Depends(get_db_session)
):
    """Get run status and details (must belong to session)."""
    verify_session(session_id, db)
    run = db.query(RunModel).filter(
        RunModel.id == run_id,
        RunModel.session_id == session_id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return Run.model_validate(run)


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: str,
    request: Request,
    session_id: str = Query(..., description="Session ID"),
    db: Session = Depends(get_db_session)
):
    """Stream run execution events via Server-Sent Events (must belong to session)."""
    verify_session(session_id, db)
    run = db.query(RunModel).filter(
        RunModel.id == run_id,
        RunModel.session_id == session_id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    orchestrator = MessageBasedOrchestrator(db)
    
    async def event_generator():
        """Generate SSE events."""
        try:
            logger.info("sse_stream_start", run_id=run_id, session_id=session_id)
            
            # Optional per-request API key from frontend (header or query param since EventSource cannot set headers)
            api_key = (
                request.headers.get("X-Gemini-Api-Key")
                or request.headers.get("X-Gemini-API-Key")
                or request.query_params.get("api_key")
            )
            
            if not api_key:
                logger.warning("sse_no_api_key", run_id=run_id)
            else:
                logger.info("sse_api_key_present", run_id=run_id, key_length=len(api_key))
            
            # Send initial connection event
            yield f"event: connected\n"
            yield f"data: {json.dumps({'run_id': run_id})}\n\n"
            logger.info("sse_connected_event_sent", run_id=run_id)
            
            event_count = 0
            # Extract images from input if present
            run_images = run.input.get("images", []) if isinstance(run.input, dict) else []
            run_input_clean = {k: v for k, v in run.input.items() if k != "images"} if isinstance(run.input, dict) else run.input
            
            logger.info("sse_starting_orchestrator", run_id=run_id, root_agent_id=run.root_agent_id, has_images=bool(run_images))
            
            async for event in orchestrator.execute_run(
                run_id=run_id,
                root_agent_id=run.root_agent_id,
                input_data=run_input_clean,
                api_key=api_key,
                images=run_images if run_images else None,
            ):
                # Format as SSE
                event_type = event.get("type", "log")
                agent_id = event.get("agent_id", "")
                data = event.get("data", "")
                
                # Log important events
                if event_type in ["output", "output_chunk", "error", "status"]:
                    logger.info("sse_event", run_id=run_id, event_type=event_type, agent_id=agent_id[:20] if agent_id else "none", data_length=len(str(data)))
                
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
                    logger.debug("sse_heartbeat", run_id=run_id, event_count=event_count)
            
            logger.info("sse_orchestrator_complete", run_id=run_id, total_events=event_count)
            
            # Send completion
            yield f"event: completed\n"
            yield f"data: {json.dumps({'status': 'completed', 'run_id': run_id})}\n\n"
            logger.info("sse_completion_sent", run_id=run_id)
            
        except GeneratorExit:
            # Client disconnected
            logger.warning("sse_client_disconnected", run_id=run_id, session_id=session_id)
            raise
        except Exception as e:
            logger.error("sse_error", run_id=run_id, session_id=session_id, error=str(e), error_type=type(e).__name__, exc_info=True)
            try:
                error_json = json.dumps({"error": str(e), "run_id": run_id, "error_type": type(e).__name__})
                yield f"event: error\n"
                yield f"data: {error_json}\n\n"
                logger.info("sse_error_event_sent", run_id=run_id)
            except Exception as send_error:
                logger.error("sse_error_send_failed", run_id=run_id, send_error=str(send_error))
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

