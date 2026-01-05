"""Prometheus metrics collection."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time
from typing import Callable


# Define metrics
REQUEST_COUNT = Counter(
    'app_request_count',
    'Total request count',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'app_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

SUMMARY_COUNT = Counter(
    'summary_total',
    'Total summaries generated',
    ['type', 'style']
)

SUMMARY_DURATION = Histogram(
    'summary_duration_seconds',
    'Summary generation duration',
    ['type', 'style']
)

SUMMARY_QUALITY = Histogram(
    'summary_quality_score',
    'Summary quality scores',
    ['type', 'style']
)

CACHE_HITS = Counter(
    'cache_hits_total',
    'Total cache hits'
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Total cache misses'
)

ACTIVE_REQUESTS = Gauge(
    'active_requests',
    'Number of active requests'
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections',
    'Number of active database connections'
)


def track_summary_metrics(func: Callable) -> Callable:
    """
    Decorator to track summary generation metrics.
    
    Args:
        func: Function to decorate
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start_time
        
        # Extract type and style from kwargs or result
        summary_type = kwargs.get('type', 'unknown')
        summary_style = kwargs.get('style', 'unknown')
        
        SUMMARY_COUNT.labels(type=summary_type, style=summary_style).inc()
        SUMMARY_DURATION.labels(type=summary_type, style=summary_style).observe(duration)
        
        if hasattr(result, 'metrics') and hasattr(result.metrics, 'quality_score'):
            SUMMARY_QUALITY.labels(type=summary_type, style=summary_style).observe(
                result.metrics.quality_score
            )
        
        return result
    
    return wrapper


def get_metrics() -> tuple[bytes, str]:
    """
    Get Prometheus metrics.
    
    Returns:
        Tuple of (metrics bytes, content type)
    """
    return generate_latest(), CONTENT_TYPE_LATEST
