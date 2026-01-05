"""API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import List

from app.models import schemas
from app.models.database import User, Summary, Usage
from app.api.dependencies import get_db, get_current_user, rate_limiter
from app.services.auth import hash_password, verify_password, create_access_token, generate_api_key
from app.services.cache import cache_service
from app.agents.summarizer import summarizer_service
from app.utils.logger import logger
from app.utils.metrics import CACHE_HITS, CACHE_MISSES


router = APIRouter()


# Auth routes
@router.post("/api/v1/auth/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: schemas.UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        JWT access token
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_pw = hash_password(user_data.password)
    api_key = generate_api_key()
    
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_pw,
        api_key=api_key,
        tier="free"
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create token
    access_token = create_access_token(data={"sub": new_user.email})
    
    logger.info(f"User registered: {user_data.email}")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/api/v1/auth/login", response_model=schemas.Token)
async def login(user_data: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    """
    User login.
    
    Args:
        user_data: User login data
        db: Database session
        
    Returns:
        JWT access token
    """
    # Get user
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create token
    access_token = create_access_token(data={"sub": user.email})
    
    logger.info(f"User logged in: {user_data.email}")
    
    return {"access_token": access_token, "token_type": "bearer"}


# Summary routes
@router.post("/api/v1/summarize", response_model=schemas.SummaryResponse)
async def summarize_text(
    request: schemas.SummarizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limiter)
):
    """
    Summarize a single text.
    
    Args:
        request: Summarization request
        user: Current user
        db: Database session
        
    Returns:
        Summary response
    """
    # Check cache
    cache_key = cache_service.generate_cache_key(
        request.text,
        request.type.value,
        request.style.value
    )
    
    cached_result = await cache_service.get(cache_key)
    if cached_result:
        CACHE_HITS.inc()
        logger.info(f"Cache hit for user {user.email}")
        
        # Still save to database
        summary = Summary(
            user_id=user.id,
            type=request.type.value,
            style=request.style.value,
            original_text=request.text,
            summary_text=cached_result["summary"],
            key_points=cached_result["key_points"],
            metrics=cached_result["metrics"]
        )
        db.add(summary)
        await db.commit()
        await db.refresh(summary)
        
        return schemas.SummaryResponse(
            id=summary.id,
            summary=cached_result["summary"],
            key_points=cached_result["key_points"],
            metrics=schemas.SummaryMetrics(**cached_result["metrics"]),
            created_at=summary.created_at
        )
    
    CACHE_MISSES.inc()
    
    # Generate summary
    result = await summarizer_service.summarize(
        request.text,
        request.type.value,
        request.style.value
    )
    
    # Cache result
    await cache_service.set(cache_key, result)
    
    # Save to database
    summary = Summary(
        user_id=user.id,
        type=request.type.value,
        style=request.style.value,
        original_text=request.text,
        summary_text=result["summary"],
        key_points=result["key_points"],
        metrics=result["metrics"]
    )
    db.add(summary)
    
    # Update usage
    today = datetime.utcnow().date()
    usage_result = await db.execute(
        select(Usage).where(
            Usage.user_id == user.id,
            func.date(Usage.date) == today
        )
    )
    usage = usage_result.scalar_one_or_none()
    
    if usage:
        usage.summary_count += 1
        usage.token_count += result["metrics"]["token_count"]
        usage.cost += result["metrics"]["cost"]
    else:
        usage = Usage(
            user_id=user.id,
            summary_count=1,
            token_count=result["metrics"]["token_count"],
            cost=result["metrics"]["cost"]
        )
        db.add(usage)
    
    await db.commit()
    await db.refresh(summary)
    
    logger.info(f"Summary created for user {user.email}")
    
    return schemas.SummaryResponse(
        id=summary.id,
        summary=result["summary"],
        key_points=result["key_points"],
        metrics=schemas.SummaryMetrics(**result["metrics"]),
        created_at=summary.created_at
    )


@router.post("/api/v1/summarize/batch", response_model=schemas.BatchSummaryResponse)
async def summarize_batch(
    request: schemas.BatchSummarizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limiter)
):
    """
    Summarize multiple texts.
    
    Args:
        request: Batch summarization request
        user: Current user
        db: Database session
        
    Returns:
        Batch summary response
    """
    batch_result = await summarizer_service.summarize_batch(
        request.texts,
        request.type.value,
        request.style.value
    )
    
    summaries = []
    
    for text, result in zip(request.texts, batch_result["summaries"]):
        # Save to database
        summary = Summary(
            user_id=user.id,
            type=request.type.value,
            style=request.style.value,
            original_text=text,
            summary_text=result["summary"],
            key_points=result["key_points"],
            metrics=result["metrics"]
        )
        db.add(summary)
        await db.flush()
        await db.refresh(summary)
        
        summaries.append(schemas.SummaryResponse(
            id=summary.id,
            summary=result["summary"],
            key_points=result["key_points"],
            metrics=schemas.SummaryMetrics(**result["metrics"]),
            created_at=summary.created_at
        ))
    
    # Update usage
    today = datetime.utcnow().date()
    usage_result = await db.execute(
        select(Usage).where(
            Usage.user_id == user.id,
            func.date(Usage.date) == today
        )
    )
    usage = usage_result.scalar_one_or_none()
    
    if usage:
        usage.summary_count += len(request.texts)
        usage.token_count += sum(s.metrics.token_count for s in summaries)
        usage.cost += batch_result["total_cost"]
    else:
        usage = Usage(
            user_id=user.id,
            summary_count=len(request.texts),
            token_count=sum(s.metrics.token_count for s in summaries),
            cost=batch_result["total_cost"]
        )
        db.add(usage)
    
    await db.commit()
    
    logger.info(f"Batch summary created for user {user.email}")
    
    return schemas.BatchSummaryResponse(
        summaries=summaries,
        total_cost=batch_result["total_cost"],
        total_time=batch_result["total_time"]
    )


@router.get("/api/v1/summaries", response_model=List[schemas.SummaryListResponse])
async def get_summaries(
    skip: int = 0,
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's summaries.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        user: Current user
        db: Database session
        
    Returns:
        List of summaries
    """
    result = await db.execute(
        select(Summary)
        .where(Summary.user_id == user.id)
        .order_by(Summary.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    summaries = result.scalars().all()
    
    return [
        schemas.SummaryListResponse(
            id=s.id,
            type=s.type.value,
            style=s.style.value,
            summary=s.summary_text,
            created_at=s.created_at
        )
        for s in summaries
    ]


@router.get("/api/v1/summaries/{summary_id}", response_model=schemas.SummaryResponse)
async def get_summary(
    summary_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific summary.
    
    Args:
        summary_id: Summary ID
        user: Current user
        db: Database session
        
    Returns:
        Summary details
    """
    result = await db.execute(
        select(Summary).where(
            Summary.id == summary_id,
            Summary.user_id == user.id
        )
    )
    summary = result.scalar_one_or_none()
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )
    
    return schemas.SummaryResponse(
        id=summary.id,
        summary=summary.summary_text,
        key_points=summary.key_points,
        metrics=schemas.SummaryMetrics(**summary.metrics),
        created_at=summary.created_at
    )


@router.get("/api/v1/usage", response_model=schemas.UsageStats)
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's usage statistics.
    
    Args:
        user: Current user
        db: Database session
        
    Returns:
        Usage statistics
    """
    # Get last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    result = await db.execute(
        select(Usage).where(
            Usage.user_id == user.id,
            Usage.date >= thirty_days_ago
        )
    )
    usages = result.scalars().all()
    
    total_summaries = sum(u.summary_count for u in usages)
    total_tokens = sum(u.token_count for u in usages)
    total_cost = sum(u.cost for u in usages)
    
    return schemas.UsageStats(
        summary_count=total_summaries,
        token_count=total_tokens,
        total_cost=total_cost,
        period="last_30_days"
    )


@router.get("/health", response_model=schemas.HealthCheck)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    
    Args:
        db: Database session
        
    Returns:
        Health status
    """
    # Check database
    try:
        await db.execute(select(1))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check Redis
    try:
        redis_status = "healthy" if cache_service.redis_client else "unhealthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    
    return schemas.HealthCheck(
        status="healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
        database=db_status,
        redis=redis_status,
        timestamp=datetime.utcnow()
    )
