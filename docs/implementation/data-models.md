# Data Models

## Pydantic Models (API)

```python
# backend/core/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ToolConfig(BaseModel):
    """Configuration for an agent tool."""
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    """Agent model for API requests/responses."""
    id: str
    name: str
    role: str
    system_prompt: str
    tools: List[ToolConfig] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    parent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AgentCreate(BaseModel):
    """Request model for creating an agent."""
    name: str
    role: str
    system_prompt: str
    tools: List[ToolConfig] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    parent_id: Optional[str] = None


class AgentUpdate(BaseModel):
    """Request model for updating an agent."""
    name: Optional[str] = None
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[List[ToolConfig]] = None
    parameters: Optional[Dict[str, Any]] = None
    parent_id: Optional[str] = None


class Link(BaseModel):
    """Link between parent and child agents."""
    parent_agent_id: str
    child_agent_id: str
    created_at: datetime


class RunRequest(BaseModel):
    """Request model for executing a run."""
    root_agent_id: str
    input: Dict[str, Any] = Field(default_factory=dict)


class RunLog(BaseModel):
    """Log entry for agent execution."""
    agent_id: str
    timestamp: datetime
    message: str
    level: str = "info"  # info, warning, error


class RunOutput(BaseModel):
    """Output from a single agent in a run."""
    agent_id: str
    output: str
    timestamp: datetime


class Run(BaseModel):
    """Run execution model."""
    id: str
    root_agent_id: str
    status: str  # pending, running, completed, failed, cancelled
    input: Dict[str, Any]
    output: Dict[str, str] = Field(default_factory=dict)  # agent_id -> output
    logs: List[RunLog] = Field(default_factory=list)
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None


class Template(BaseModel):
    """Agent template for library."""
    id: str
    name: str
    role: str
    system_prompt: str
    tools: List[ToolConfig] = Field(default_factory=list)
    description: str
    category: Optional[str] = None


class ToolDefinition(BaseModel):
    """Tool definition for library."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema for parameters
```

## Database Schema (SQLAlchemy)

```python
# backend/db/schemas.py
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    tools = Column(JSON, default=list)  # List of ToolConfig dicts
    parameters = Column(JSON, default=dict)
    parent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("AgentModel", remote_side=[id], backref="children")


class LinkModel(Base):
    __tablename__ = "links"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    child_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Unique constraint: one link per parent/child pair
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class RunModel(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    root_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed, cancelled
    input = Column(JSON, default=dict)
    output = Column(JSON, default=dict)  # agent_id -> output string
    logs = Column(JSON, default=list)  # List of RunLog dicts
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
```

## TypeScript Types (Frontend)

```typescript
// frontend/lib/types.ts

export interface ToolConfig {
  name: string;
  params: Record<string, any>;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  system_prompt: string;
  tools: ToolConfig[];
  parameters: Record<string, any>;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  role: string;
  system_prompt: string;
  tools?: ToolConfig[];
  parameters?: Record<string, any>;
  parent_id?: string | null;
}

export interface Link {
  parent_agent_id: string;
  child_agent_id: string;
  created_at: string;
}

export interface RunLog {
  agent_id: string;
  timestamp: string;
  message: string;
  level?: "info" | "warning" | "error";
}

export interface Run {
  id: string;
  root_agent_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  input: Record<string, any>;
  output: Record<string, string>;
  logs: RunLog[];
  created_at: string;
  started_at?: string;
  finished_at?: string;
  error?: string;
}

export interface Template {
  id: string;
  name: string;
  role: string;
  system_prompt: string;
  tools: ToolConfig[];
  description: string;
  category?: string;
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
}
```

## Graph Data Structure

For the frontend canvas, agents are represented as nodes and links as edges:

```typescript
// React Flow node format
export interface AgentNode {
  id: string;
  type: "agent";
  position: { x: number; y: number };
  data: {
    agent: Agent;
  };
}

// React Flow edge format
export interface AgentEdge {
  id: string;
  source: string;  // parent_agent_id
  target: string;  // child_agent_id
  type?: string;
}
```

