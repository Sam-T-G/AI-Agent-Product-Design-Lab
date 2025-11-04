"""Pydantic models for API requests/responses."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ToolConfig(BaseModel):
    """Tool configuration."""
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)


class AgentBase(BaseModel):
    """Base agent model."""
    name: str
    role: str
    system_prompt: str
    tools: List[ToolConfig] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentCreate(AgentBase):
    """Request model for creating an agent."""
    parent_id: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None


class AgentUpdate(BaseModel):
    """Request model for updating an agent."""
    name: Optional[str] = None
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[List[ToolConfig]] = None
    parameters: Optional[Dict[str, Any]] = None
    parent_id: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None


class Agent(AgentBase):
    """Agent response model."""
    id: str
    parent_id: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
    }


class LinkCreate(BaseModel):
    """Request model for creating a link."""
    parent_agent_id: str
    child_agent_id: str


class Link(BaseModel):
    """Link response model."""
    id: str
    parent_agent_id: str
    child_agent_id: str
    created_at: datetime
    
    model_config = {
        "from_attributes": True,
    }


class RunRequest(BaseModel):
    """Request model for executing a run."""
    root_agent_id: str
    input: Dict[str, Any] = Field(default_factory=dict)


class RunLog(BaseModel):
    """Log entry for agent execution."""
    agent_id: str
    timestamp: datetime
    message: str
    level: str = "info"


class Run(BaseModel):
    """Run response model."""
    id: str
    root_agent_id: str
    status: str  # pending, running, completed, failed, cancelled
    input: Dict[str, Any]
    output: Dict[str, str] = Field(default_factory=dict)
    logs: List[RunLog] = Field(default_factory=list)
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    
    model_config = {
        "from_attributes": True,
    }


