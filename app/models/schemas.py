"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SummaryType(str, Enum):
    """Summary type enumeration."""
    EMAIL = "email"
    CHAT = "chat"
    DOCUMENT = "document"


class SummaryStyle(str, Enum):
    """Summary style enumeration."""
    BRIEF = "brief"
    DETAILED = "detailed"
    BULLET = "bullet"
    EXECUTIVE = "executive"


# Auth schemas
class UserRegister(BaseModel):
    """User registration schema."""
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema."""
    email: Optional[str] = None


# Summary schemas
class SummarizeRequest(BaseModel):
    """Single text summarization request."""
    text: str = Field(min_length=50, max_length=50000)
    type: SummaryType = SummaryType.DOCUMENT
    style: SummaryStyle = SummaryStyle.BRIEF
    
    @validator('text')
    def validate_text(cls, v):
        """Validate text is not empty after stripping."""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()


class BatchSummarizeRequest(BaseModel):
    """Batch summarization request."""
    texts: List[str] = Field(min_items=1, max_items=10)
    type: SummaryType = SummaryType.DOCUMENT
    style: SummaryStyle = SummaryStyle.BRIEF
    
    @validator('texts')
    def validate_texts(cls, v):
        """Validate all texts meet requirements."""
        for text in v:
            if len(text.strip()) < 50:
                raise ValueError("Each text must be at least 50 characters")
            if len(text) > 50000:
                raise ValueError("Each text must not exceed 50000 characters")
        return [text.strip() for text in v]


class SummaryMetrics(BaseModel):
    """Summary metrics schema."""
    quality_score: float
    processing_time: float
    token_count: int
    cost: float


class SummaryResponse(BaseModel):
    """Summary response schema."""
    id: int
    summary: str
    key_points: List[str]
    metrics: SummaryMetrics
    created_at: datetime
    
    class Config:
        from_attributes = True


class BatchSummaryResponse(BaseModel):
    """Batch summary response schema."""
    summaries: List[SummaryResponse]
    total_cost: float
    total_time: float


class SummaryListResponse(BaseModel):
    """Summary list response schema."""
    id: int
    type: str
    style: str
    summary: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UsageStats(BaseModel):
    """Usage statistics schema."""
    summary_count: int
    token_count: int
    total_cost: float
    period: str


class HealthCheck(BaseModel):
    """Health check response schema."""
    status: str
    database: str
    redis: str
    timestamp: datetime
