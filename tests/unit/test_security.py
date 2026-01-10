"""
Unit tests for API Gateway security
"""

import pytest
import hashlib
import hmac
from datetime import datetime, timezone, timedelta

from api_gateway.src.core.security import SecurityService


class TestSecurityService:
    """Tests for security service"""

    @pytest.fixture
    def security(self):
        """Create SecurityService with test secrets"""
        return SecurityService(
            api_key_secret="test-api-key-secret",
            webhook_secret="test-webhook-secret"
        )

    def test_verify_api_key_valid(self, security):
        """Test valid API key verification"""
        assert security.verify_api_key("test-api-key-secret") is True

    def test_verify_api_key_invalid(self, security):
        """Test invalid API key rejection"""
        assert security.verify_api_key("wrong-key") is False
        assert security.verify_api_key("") is False
        assert security.verify_api_key(None) is False

    def test_verify_webhook_signature_valid(self, security):
        """Test valid webhook signature verification"""
        payload = b'{"event": "test"}'

        # Calculate expected signature
        signature = hmac.new(
            b"test-webhook-secret",
            payload,
            hashlib.sha256
        ).hexdigest()

        assert security.verify_webhook_signature(payload, signature) is True

    def test_verify_webhook_signature_invalid(self, security):
        """Test invalid webhook signature rejection"""
        payload = b'{"event": "test"}'
        wrong_signature = "invalid_signature"

        assert security.verify_webhook_signature(payload, wrong_signature) is False

    def test_verify_webhook_signature_with_timestamp(self, security):
        """Test webhook signature with valid timestamp"""
        payload = b'{"event": "test"}'
        signature = hmac.new(
            b"test-webhook-secret",
            payload,
            hashlib.sha256
        ).hexdigest()

        # Current timestamp
        timestamp = datetime.now(timezone.utc).isoformat()

        assert security.verify_webhook_signature(
            payload, signature, timestamp
        ) is True

    def test_verify_webhook_signature_expired_timestamp(self, security):
        """Test webhook signature rejection with expired timestamp"""
        payload = b'{"event": "test"}'
        signature = hmac.new(
            b"test-webhook-secret",
            payload,
            hashlib.sha256
        ).hexdigest()

        # Old timestamp (10 minutes ago)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        timestamp = old_time.isoformat()

        assert security.verify_webhook_signature(
            payload, signature, timestamp, max_age_seconds=300
        ) is False

    def test_verify_webhook_signature_missing(self, security):
        """Test missing signature rejection"""
        payload = b'{"event": "test"}'

        assert security.verify_webhook_signature(payload, "") is False
        assert security.verify_webhook_signature(payload, None) is False

    def test_generate_api_key(self):
        """Test API key generation"""
        key1 = SecurityService.generate_api_key()
        key2 = SecurityService.generate_api_key()

        # Keys should be unique
        assert key1 != key2

        # Keys should be reasonable length
        assert len(key1) >= 32

    def test_timing_safe_comparison(self, security):
        """Test that API key comparison is timing-safe"""
        # This is a basic test - proper timing attack tests would need more setup
        # Just verify it handles various inputs safely
        assert security.verify_api_key("a" * 100) is False
        assert security.verify_api_key("test-api-key-secret") is True
