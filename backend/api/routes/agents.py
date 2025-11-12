"""Agent CRUD endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db_session
from db.schemas import AgentModel, LinkModel, SessionModel
from core.models import Agent, AgentCreate, AgentUpdate
from core.logging import get_logger
from core.agent_tree_cache import get_agent_tree_cache

logger = get_logger("agents")
router = APIRouter(prefix="/agents", tags=["agents"])


def verify_session(session_id: str, db: Session) -> SessionModel:
    """Verify session exists and return it."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("", response_model=List[Agent])
async def list_agents(
    session_id: str = Query(..., description="Session ID"),
    db: Session = Depends(get_db_session)
):
    """List all agents for a session."""
    verify_session(session_id, db)
    agents = db.query(AgentModel).filter(AgentModel.session_id == session_id).all()
    return [Agent.model_validate(agent) for agent in agents]


@router.post("", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    session_id: str = Query(..., description="Session ID"),
    db: Session = Depends(get_db_session)
):
    """Create a new agent in a session."""
    verify_session(session_id, db)
    
    # Verify parent belongs to same session if provided
    if agent_data.parent_id:
        parent = db.query(AgentModel).filter(AgentModel.id == agent_data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent agent not found")
        if parent.session_id != session_id:
            raise HTTPException(status_code=400, detail="Parent agent must belong to the same session")
    
    agent = AgentModel(
        session_id=session_id,
        name=agent_data.name,
        role=agent_data.role,
        system_prompt=agent_data.system_prompt,
        tools=[tool.model_dump() for tool in agent_data.tools],
        parameters=agent_data.parameters,
        photo_injection_enabled="true" if agent_data.photo_injection_enabled else "false",
        photo_injection_features=agent_data.photo_injection_features or [],
        parent_id=agent_data.parent_id,
        position_x=agent_data.position_x,
        position_y=agent_data.position_y,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    logger.info("agent_created", agent_id=agent.id, name=agent.name, session_id=session_id)
    get_agent_tree_cache().invalidate(session_id)
    return Agent.model_validate(agent)


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: str,
    session_id: str = Query(..., description="Session ID"),
    db: Session = Depends(get_db_session)
):
    """Get a single agent by ID (must belong to session)."""
    verify_session(session_id, db)
    agent = db.query(AgentModel).filter(
        AgentModel.id == agent_id,
        AgentModel.session_id == session_id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Agent.model_validate(agent)


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    session_id: str = Query(..., description="Session ID"),
    db: Session = Depends(get_db_session),
):
    """Update an agent (must belong to session)."""
    verify_session(session_id, db)
    agent = db.query(AgentModel).filter(
        AgentModel.id == agent_id,
        AgentModel.session_id == session_id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    update_data = agent_data.model_dump(exclude_unset=True)
    
    # Verify parent belongs to same session if parent_id is being updated
    if "parent_id" in update_data and update_data["parent_id"]:
        parent = db.query(AgentModel).filter(
            AgentModel.id == update_data["parent_id"],
            AgentModel.session_id == session_id
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent agent not found or does not belong to session")
        # Check for cycle (cannot be parent of itself)
        if update_data["parent_id"] == agent_id:
            raise HTTPException(status_code=400, detail="Agent cannot be its own parent")
        # Check for cycle by traversing up the parent chain
        current = update_data["parent_id"]
        visited = {agent_id, current}
        while current:
            parent_agent = db.query(AgentModel).filter(
                AgentModel.id == current,
                AgentModel.session_id == session_id
            ).first()
            if not parent_agent or not parent_agent.parent_id:
                break
            if parent_agent.parent_id == agent_id:
                raise HTTPException(status_code=400, detail="Cannot create circular parent-child relationship")
            if parent_agent.parent_id in visited:
                break  # Already checked this branch
            visited.add(parent_agent.parent_id)
            current = parent_agent.parent_id
    
    if "tools" in update_data:
        update_data["tools"] = [tool.model_dump() if isinstance(tool, dict) else tool for tool in update_data["tools"]]
    
    # Convert photo_injection_enabled bool to string for database
    if "photo_injection_enabled" in update_data:
        update_data["photo_injection_enabled"] = "true" if update_data["photo_injection_enabled"] else "false"
    
    for key, value in update_data.items():
        setattr(agent, key, value)
    
    db.commit()
    db.refresh(agent)
    logger.info("agent_updated", agent_id=agent.id)
    get_agent_tree_cache().invalidate(session_id)
    return Agent.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    session_id: str = Query(..., description="Session ID"),
    db: Session = Depends(get_db_session)
):
    """Delete an agent and cascade delete children (must belong to session)."""
    verify_session(session_id, db)
    agent = db.query(AgentModel).filter(
        AgentModel.id == agent_id,
        AgentModel.session_id == session_id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Find all children (recursive, within same session)
    def get_all_children(parent_id: str, visited: set = None) -> list:
        if visited is None:
            visited = set()
        if parent_id in visited:
            return []
        visited.add(parent_id)
        children = db.query(AgentModel).filter(
            AgentModel.parent_id == parent_id,
            AgentModel.session_id == session_id
        ).all()
        result = list(children)
        for child in children:
            result.extend(get_all_children(child.id, visited))
        return result
    
    # Get all children to delete
    all_children = get_all_children(agent_id)
    all_ids_to_delete = [agent_id] + [child.id for child in all_children]
    
    # Delete all links involving these agents (within session)
    db.query(LinkModel).filter(
        LinkModel.session_id == session_id,
        ((LinkModel.parent_agent_id.in_(all_ids_to_delete)) |
         (LinkModel.child_agent_id.in_(all_ids_to_delete)))
    ).delete(synchronize_session=False)
    
    # Delete all child agents first (to respect foreign key constraints)
    for child in all_children:
        db.delete(child)
    
    # Delete the agent itself
    db.delete(agent)
    db.commit()
    
    logger.info("agent_deleted", agent_id=agent_id, children_deleted=len(all_children))
    get_agent_tree_cache().invalidate(session_id)

