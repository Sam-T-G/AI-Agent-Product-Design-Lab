"""Session management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from db.database import get_db_session
from db.schemas import SessionModel
from core.models import Session, SessionCreate
from core.logging import get_logger
from core.agent_tree_cache import get_agent_tree_cache

logger = get_logger("sessions")
router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=List[Session])
async def list_sessions(db: Session = Depends(get_db_session)):
    """List all sessions."""
    sessions = db.query(SessionModel).order_by(SessionModel.last_accessed.desc()).all()
    return [Session.model_validate(session) for session in sessions]


@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_session(session_data: SessionCreate, db: Session = Depends(get_db_session)):
    """Create a new session."""
    # Check if session name already exists
    existing = db.query(SessionModel).filter(SessionModel.name == session_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session with name '{session_data.name}' already exists"
        )
    
    session = SessionModel(
        name=session_data.name,
        created_at=datetime.utcnow(),
        last_accessed=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("session_created", session_id=session.id, name=session.name)
    return Session.model_validate(session)


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str, db: Session = Depends(get_db_session)):
    """Get a single session by ID."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update last accessed
    session.last_accessed = datetime.utcnow()
    db.commit()
    db.refresh(session)
    
    return Session.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, db: Session = Depends(get_db_session)):
    """Delete a session and all its associated data (cascade)."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    logger.info("session_deleted", session_id=session_id)
    get_agent_tree_cache().clear_session(session_id)
    return None
