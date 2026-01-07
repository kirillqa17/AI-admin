"""
Setup для shared пакета
"""

from setuptools import setup, find_packages

setup(
    name="ai-admin-shared",
    version="0.1.0",
    description="Shared models and utilities for AI-Admin",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.5.0",
        "sqlalchemy[asyncio]>=2.0.0",
        "asyncpg>=0.29.0",
        "structlog>=24.1.0",
        "python-dateutil>=2.8.2",
    ],
    python_requires=">=3.10",
)
