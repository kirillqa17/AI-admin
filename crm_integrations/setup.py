"""
Setup для CRM Integrations пакета
"""

from setuptools import setup, find_packages

setup(
    name="ai-admin-crm-integrations",
    version="0.1.0",
    description="CRM integrations for AI-Admin",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.9.0",
        "pydantic>=2.5.0",
    ],
    python_requires=">=3.10",
)
