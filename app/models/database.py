"""Database models using SQLAlchemy."""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Enum as SQLEnum, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum


Base = declarative_base()


class SummaryType(enum.Enum):
    """Summary type enumeration."""
    EMAIL = "email"
    CHAT = "chat"
    DOCUMENT = "document"


class SummaryStyle(enum.Enum):
    """Summary style enumeration."""
    BRIEF = "brief"
    DETAILED = "detailed"
    BULLET = "bullet"
    EXECUTIVE = "executive"


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    api_key = Column(String(64), unique=True, index=True)
    tier = Column(String(50), default="free")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    summaries = relationship("Summary", back_populates="user")
    usages = relationship("Usage", back_populates="user")


class Summary(Base):
    """Summary model."""
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(SQLEnum(SummaryType), nullable=False)
    style = Column(SQLEnum(SummaryStyle), nullable=False)
    original_text = Column(Text, nullable=False)
    summary_text = Column(Text, nullable=False)
    key_points = Column(JSON)
    metrics = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="summaries")


class Usage(Base):
    """Usage tracking model."""
    __tablename__ = "usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    summary_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    
    # Relationships
    user = relationship("User", back_populates="usages")
