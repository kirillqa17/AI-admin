"""
Rate Limiting Middleware for API Gateway

Implements sliding window rate limiting using Redis
"""

import time
from typing import Optional, Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis sliding window

    Limits:
    - Per IP: 100 requests per minute (default)
    - Per API key: 1000 requests per minute
    - Webhooks: 200 requests per minute per company

    Headers added to response:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Remaining requests
    - X-RateLimit-Reset: Unix timestamp when limit resets
    """

    def __init__(
        self,
        app: ASGIApp,
        redis_url: str,
        default_limit: int = 100,
        window_seconds: int = 60,
        enabled: bool = True
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    def get_client_identifier(self, request: Request) -> str:
        """
        Get unique client identifier for rate limiting

        Priority:
        1. API Key (if present)
        2. Forwarded IP (X-Forwarded-For)
        3. Client IP
        """
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key[:16]}"  # Use first 16 chars as identifier

        # Check for forwarded IP (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get first IP in chain (original client)
            client_ip = forwarded.split(",")[0].strip()
            return f"ip:{client_ip}"

        # Use client host
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def get_rate_limit(self, request: Request) -> int:
        """
        Get rate limit for request

        Different limits for different endpoints/clients
        """
        path = request.url.path

        # Higher limit for authenticated requests
        if request.headers.get("X-API-Key"):
            return 1000

        # Webhook endpoints
        if "/webhook" in path or "/telegram" in path or "/whatsapp" in path:
            return 200

        # Health checks - very high limit
        if "/health" in path:
            return 10000

        # Default limit
        return self.default_limit

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit

        Uses Redis sliding window algorithm

        Args:
            identifier: Unique client identifier
            limit: Maximum requests allowed

        Returns:
            Tuple of (allowed, remaining, reset_timestamp)
        """
        redis_client = await self.get_redis()
        now = time.time()
        window_start = now - self.window_seconds
        key = f"ratelimit:{identifier}"

        try:
            # Use pipeline for atomic operations
            pipe = redis_client.pipeline()

            # Remove old entries outside window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiry
            pipe.expire(key, self.window_seconds)

            results = await pipe.execute()
            current_count = results[1]

            remaining = max(0, limit - current_count - 1)
            reset_time = int(now + self.window_seconds)

            if current_count >= limit:
                return False, 0, reset_time

            return True, remaining, reset_time

        except redis.RedisError as e:
            logger.error("rate_limit_redis_error", error=str(e))
            # Fail open - allow request if Redis is unavailable
            return True, limit, int(now + self.window_seconds)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with rate limiting"""

        # Skip if disabled
        if not self.enabled:
            return await call_next(request)

        # Skip for certain paths
        skip_paths = ["/docs", "/openapi.json", "/redoc"]
        if any(request.url.path.startswith(p) for p in skip_paths):
            return await call_next(request)

        identifier = self.get_client_identifier(request)
        limit = self.get_rate_limit(request)

        allowed, remaining, reset_time = await self.check_rate_limit(
            identifier, limit
        )

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                limit=limit,
                path=request.url.path
            )
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(self.window_seconds)
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


def create_rate_limit_middleware(
    app: ASGIApp,
    enabled: bool = True
) -> RateLimitMiddleware:
    """
    Factory function to create rate limit middleware

    Args:
        app: FastAPI/Starlette application
        enabled: Whether rate limiting is enabled

    Returns:
        Configured RateLimitMiddleware
    """
    return RateLimitMiddleware(
        app=app,
        redis_url=settings.redis_url,
        default_limit=100,
        window_seconds=60,
        enabled=enabled
    )
