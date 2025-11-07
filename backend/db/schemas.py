"""SQLAlchemy database models."""
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


def generate_id() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class SessionModel(Base):
    """Session database model for multi-tenant isolation."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agents = relationship("AgentModel", back_populates="session", cascade="all, delete-orphan")
    links = relationship("LinkModel", back_populates="session", cascade="all, delete-orphan")
    runs = relationship("RunModel", back_populates="session", cascade="all, delete-orphan")


class AgentModel(Base):
    """Agent database model."""
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_id)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
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
    session = relationship("SessionModel", back_populates="agents")
    parent = relationship("AgentModel", remote_side=[id], backref="children")
    
    # Index for efficient session queries
    __table_args__ = (Index("ix_agents_session_id", "session_id"),)


class LinkModel(Base):
    """Link between parent and child agents."""
    __tablename__ = "links"

    id = Column(String, primary_key=True, default=generate_id)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    child_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("SessionModel", back_populates="links")
    
    # Index for efficient session queries
    __table_args__ = (Index("ix_links_session_id", "session_id"),)


class RunModel(Base):
    """Run execution model."""
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=generate_id)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    root_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed, cancelled
    input = Column(JSON, default=dict)
    output = Column(JSON, default=dict)  # agent_id -> output string
    logs = Column(JSON, default=list)  # List of RunLog dicts
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    # Relationships
    session = relationship("SessionModel", back_populates="runs")
    
    # Index for efficient session queries
    __table_args__ = (Index("ix_runs_session_id", "session_id"),)


