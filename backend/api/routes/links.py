"""Link management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db_session
from db.schemas import LinkModel, AgentModel
from core.models import Link, LinkCreate
from core.logging import get_logger

logger = get_logger("links")
router = APIRouter(prefix="/links", tags=["links"])


def check_cycle(parent_id: str, child_id: str, db: Session) -> bool:
    """Check if creating a link would create a cycle."""
    # Simple check: if child is already a parent of parent, it's a cycle
    current = parent_id
    visited = set()
    while current:
        if current == child_id:
            return True
        if current in visited:
            break
        visited.add(current)
        agent = db.query(AgentModel).filter(AgentModel.id == current).first()
        if not agent or not agent.parent_id:
            break
        current = agent.parent_id
    return False


@router.post("", response_model=Link, status_code=status.HTTP_201_CREATED)
async def create_link(link_data: LinkCreate, db: Session = Depends(get_db_session)):
    """Create a link between parent and child agents."""
    # Verify both agents exist
    parent = db.query(AgentModel).filter(AgentModel.id == link_data.parent_agent_id).first()
    child = db.query(AgentModel).filter(AgentModel.id == link_data.child_agent_id).first()
    
    if not parent:
        raise HTTPException(status_code=404, detail="Parent agent not found")
    if not child:
        raise HTTPException(status_code=404, detail="Child agent not found")
    
    # Check for duplicate link
    existing = db.query(LinkModel).filter(
        LinkModel.parent_agent_id == link_data.parent_agent_id,
        LinkModel.child_agent_id == link_data.child_agent_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Link already exists")
    
    # Check for cycle
    if check_cycle(link_data.parent_agent_id, link_data.child_agent_id, db):
        raise HTTPException(status_code=409, detail="Link would create a cycle")
    
    # Create link
    link = LinkModel(
        parent_agent_id=link_data.parent_agent_id,
        child_agent_id=link_data.child_agent_id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    
    # Update child's parent_id
    child.parent_id = link_data.parent_agent_id
    db.commit()
    
    logger.info("link_created", parent_id=link_data.parent_agent_id, child_id=link_data.child_agent_id)
    return Link.model_validate(link)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(link_data: LinkCreate, db: Session = Depends(get_db_session)):
    """Delete a link."""
    link = db.query(LinkModel).filter(
        LinkModel.parent_agent_id == link_data.parent_agent_id,
        LinkModel.child_agent_id == link_data.child_agent_id,
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Update child's parent_id to None
    child = db.query(AgentModel).filter(AgentModel.id == link_data.child_agent_id).first()
    if child:
        child.parent_id = None
    
    db.delete(link)
    db.commit()
    logger.info("link_deleted", parent_id=link_data.parent_agent_id, child_id=link_data.child_agent_id)


