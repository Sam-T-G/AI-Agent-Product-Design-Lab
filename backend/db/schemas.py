"""SQLAlchemy database models."""
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


def generate_id() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class AgentModel(Base):
    """Agent database model."""
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    tools = Column(JSON, default=list)
    parameters = Column(JSON, default=dict)
    photo_injection_enabled = Column(String, default="false")  # "true" or "false" as string for JSON compatibility
    photo_injection_features = Column(JSON, default=list)  # List of custom features/capabilities
    parent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("AgentModel", remote_side=[id], backref="children")


class LinkModel(Base):
    """Link between parent and child agents."""
    __tablename__ = "links"

    id = Column(String, primary_key=True, default=generate_id)
    parent_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    child_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RunModel(Base):
    """Run execution model."""
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=generate_id)
    root_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed, cancelled
    input = Column(JSON, default=dict)
    output = Column(JSON, default=dict)  # agent_id -> output string
    logs = Column(JSON, default=list)  # List of RunLog dicts
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


