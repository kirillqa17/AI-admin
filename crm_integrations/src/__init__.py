"""
CRM Integrations Package

Модульная система интеграции с различными CRM
"""

from .base import BaseCRMAdapter
from .factory import CRMFactory

__all__ = ["BaseCRMAdapter", "CRMFactory"]
