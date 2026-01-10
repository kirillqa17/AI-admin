"""
Pytest configuration and fixtures
"""

import os
import sys
import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set test environment variables
os.environ.setdefault("ENCRYPTION_MASTER_KEY", "test-encryption-key-for-testing")
os.environ.setdefault("API_KEY_SECRET", "test-api-key-secret")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("POSTGRES_PASSWORD", "test-password")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis(mocker):
    """Mock Redis client"""
    mock = mocker.MagicMock()
    mock.get = mocker.AsyncMock(return_value=None)
    mock.set = mocker.AsyncMock(return_value=True)
    mock.setex = mocker.AsyncMock(return_value=True)
    mock.delete = mocker.AsyncMock(return_value=1)
    mock.ping = mocker.AsyncMock(return_value=True)
    mock.close = mocker.AsyncMock()
    return mock


@pytest.fixture
def mock_db_session(mocker):
    """Mock database session"""
    mock = mocker.MagicMock()
    mock.execute = mocker.AsyncMock()
    mock.commit = mocker.AsyncMock()
    mock.rollback = mocker.AsyncMock()
    return mock
