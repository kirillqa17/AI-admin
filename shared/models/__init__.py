"""
Shared data models используемые всеми микросервисами
"""

from .message import Message, MessageType, Channel
from .session import Session, SessionState
from .crm import (
    CRMClient,
    CRMAppointment,
    CRMService,
    CRMTimeSlot,
    CRMEmployee,
)

__all__ = [
    "Message",
    "MessageType",
    "Channel",
    "Session",
    "SessionState",
    "CRMClient",
    "CRMAppointment",
    "CRMService",
    "CRMTimeSlot",
    "CRMEmployee",
]
