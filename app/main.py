"""Main FastAPI application."""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from contextlib import asynccontextmanager
import time
import sentry_sdk

from app.config import settings
from app.api.routes import router
from app.api.dependencies import create_tables
from app.services.cache import cache_service
from app.utils.logger import logger
from app.utils.metrics import REQUEST_COUNT, REQUEST_DURATION, ACTIVE_REQUESTS, get_metrics


# Initialize Sentry if DSN is provided
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=1.0,
    )
    logger.info("Sentry initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Args:
        app: FastAPI application
    """
    # Startup
    logger.info("Application starting...")
    
    # Create database tables
    await create_tables()
    
    # Connect to Redis
    await cache_service.connect()
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    
    # Disconnect from Redis
    await cache_service.disconnect()
    
    logger.info("Application shut down successfully")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="LangGraph-based text summarization service",
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all HTTP requests.
    
    Args:
        request: HTTP request
        call_next: Next middleware/handler
        
    Returns:
        HTTP response
    """
    start_time = time.time()
    
    # Track active requests
    ACTIVE_REQUESTS.inc()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration:.3f}s"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Request error: {e}")
        raise
    
    finally:
        ACTIVE_REQUESTS.dec()


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all uncaught exceptions.
    
    Args:
        request: HTTP request
        exc: Exception
        
    Returns:
        Error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return Response(
        content=f"Internal server error: {str(exc)}",
        status_code=500
    )


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """
    Expose Prometheus metrics.
    
    Returns:
        Prometheus metrics
    """
    metrics_data, content_type = get_metrics()
    return Response(content=metrics_data, media_type=content_type)


# Include routers
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint.
    
    Returns:
        Welcome message
    """
    return {
        "message": "Welcome to LangGraph Summary Service",
        "version": settings.app_version,
        "docs": "/docs"
    }
