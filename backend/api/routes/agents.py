"""Agent CRUD endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db_session
from db.schemas import AgentModel, LinkModel
from core.models import Agent, AgentCreate, AgentUpdate
from core.logging import get_logger
from core.pipeline_registry import PipelineRegistry

logger = get_logger("agents")
router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=List[Agent])
async def list_agents(db: Session = Depends(get_db_session)):
    """List all agents."""
    agents = db.query(AgentModel).all()
    return [Agent.model_validate(agent) for agent in agents]


@router.post("", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_data: AgentCreate, db: Session = Depends(get_db_session)):
    """Create a new agent."""
    agent = AgentModel(
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
    logger.info("agent_created", agent_id=agent.id, name=agent.name)
    # Refresh pipeline registry for system-wide awareness
    try:
        PipelineRegistry.instance().refresh(db)
    except Exception:
        pass
    return Agent.model_validate(agent)


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, db: Session = Depends(get_db_session)):
    """Get a single agent by ID."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Agent.model_validate(agent)


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    db: Session = Depends(get_db_session),
):
    """Update an agent."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    update_data = agent_data.model_dump(exclude_unset=True)
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
    try:
        PipelineRegistry.instance().refresh(db)
    except Exception:
        pass
    return Agent.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, db: Session = Depends(get_db_session)):
    """Delete an agent and cascade delete children."""
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Find all children (recursive)
    def get_all_children(parent_id: str, visited: set = None) -> list:
        if visited is None:
            visited = set()
        if parent_id in visited:
            return []
        visited.add(parent_id)
        children = db.query(AgentModel).filter(AgentModel.parent_id == parent_id).all()
        result = list(children)
        for child in children:
            result.extend(get_all_children(child.id, visited))
        return result
    
    # Get all children to delete
    all_children = get_all_children(agent_id)
    all_ids_to_delete = [agent_id] + [child.id for child in all_children]
    
    # Delete all links involving these agents
    db.query(LinkModel).filter(
        (LinkModel.parent_agent_id.in_(all_ids_to_delete)) |
        (LinkModel.child_agent_id.in_(all_ids_to_delete))
    ).delete(synchronize_session=False)
    
    # Delete all child agents first (to respect foreign key constraints)
    for child in all_children:
        db.delete(child)
    
    # Delete the agent itself
    db.delete(agent)
    db.commit()
    
    logger.info("agent_deleted", agent_id=agent_id, children_deleted=len(all_children))
    try:
        PipelineRegistry.instance().refresh(db)
    except Exception:
        pass


