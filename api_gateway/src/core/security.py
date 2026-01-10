"""
Security utilities for API Gateway

Provides authentication and authorization mechanisms:
- API Key authentication (for internal services)
- Webhook signature verification (for external webhooks)
- JWT tokens (for admin panel - future)
"""

import hmac
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Bearer token (for future JWT)
bearer_scheme = HTTPBearer(auto_error=False)


class SecurityService:
    """
    Security service for API Gateway

    Provides:
    - API key validation for internal services
    - Webhook signature verification
    - Rate limiting helpers
    """

    def __init__(self, api_key_secret: str, webhook_secret: str):
        self.api_key_secret = api_key_secret
        self.webhook_secret = webhook_secret

    def verify_api_key(self, api_key: str) -> bool:
        """
        Verify API key for internal service authentication

        Args:
            api_key: The API key to verify

        Returns:
            True if valid
        """
        if not api_key:
            return False

        # Compare using constant-time comparison to prevent timing attacks
        return secrets.compare_digest(api_key, self.api_key_secret)

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
        max_age_seconds: int = 300
    ) -> bool:
        """
        Verify webhook signature (HMAC-SHA256)

        Args:
            payload: Raw request body
            signature: Signature from X-Webhook-Signature header
            timestamp: Timestamp from X-Webhook-Timestamp header
            max_age_seconds: Maximum age of request in seconds

        Returns:
            True if signature is valid
        """
        if not signature:
            return False

        # Check timestamp if provided (replay attack protection)
        if timestamp:
            try:
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - ts).total_seconds()
                if age > max_age_seconds:
                    logger.warning("webhook_signature_expired", age=age)
                    return False
            except ValueError:
                logger.warning("webhook_invalid_timestamp", timestamp=timestamp)
                return False

        # Calculate expected signature
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison
        return secrets.compare_digest(signature, expected)

    @staticmethod
    def generate_api_key() -> str:
        """Generate a new random API key"""
        return secrets.token_urlsafe(32)


# Global security service instance
_security_service: Optional[SecurityService] = None


def get_security_service() -> SecurityService:
    """Get or create SecurityService instance"""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService(
            api_key_secret=settings.api_key_secret,
            webhook_secret=settings.webhook_secret
        )
    return _security_service


# ============================================
# FASTAPI DEPENDENCIES
# ============================================

async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Dependency to verify API key

    Usage:
        @app.get("/protected")
        async def protected_route(api_key: str = Depends(verify_api_key)):
            ...
    """
    if not api_key:
        logger.warning("api_key_missing")
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    security = get_security_service()
    if not security.verify_api_key(api_key):
        logger.warning("api_key_invalid")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return api_key


async def verify_api_key_optional(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """
    Optional API key verification - returns None if no key provided
    """
    if not api_key:
        return None

    security = get_security_service()
    if not security.verify_api_key(api_key):
        return None

    return api_key


async def verify_webhook_signature(request: Request) -> bool:
    """
    Dependency to verify webhook signature

    Usage:
        @app.post("/webhook")
        async def webhook(verified: bool = Depends(verify_webhook_signature)):
            ...
    """
    signature = request.headers.get("X-Webhook-Signature")
    timestamp = request.headers.get("X-Webhook-Timestamp")

    # Get raw body
    body = await request.body()

    security = get_security_service()
    is_valid = security.verify_webhook_signature(
        payload=body,
        signature=signature,
        timestamp=timestamp
    )

    if not is_valid:
        logger.warning(
            "webhook_signature_invalid",
            has_signature=bool(signature),
            has_timestamp=bool(timestamp)
        )
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return True


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )
