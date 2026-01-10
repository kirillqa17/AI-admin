"""
Cryptographic utilities for secure API key storage

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256)
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

logger = structlog.get_logger(__name__)


class CryptoService:
    """
    Service for encrypting and decrypting sensitive data (API keys, etc.)

    Uses Fernet symmetric encryption which provides:
    - AES-128-CBC encryption
    - HMAC-SHA256 authentication
    - Automatic IV generation

    Usage:
        crypto = CryptoService(master_key="your-secret-master-key")
        encrypted = crypto.encrypt("api_key_123")
        decrypted = crypto.decrypt(encrypted)
    """

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize CryptoService

        Args:
            master_key: Master encryption key. If not provided, uses
                       ENCRYPTION_MASTER_KEY environment variable
        """
        self._master_key = master_key or os.getenv("ENCRYPTION_MASTER_KEY")

        if not self._master_key:
            raise ValueError(
                "ENCRYPTION_MASTER_KEY is required. "
                "Set it via environment variable or pass to constructor."
            )

        self._fernet = self._create_fernet(self._master_key)
        logger.info("crypto_service_initialized")

    def _create_fernet(self, master_key: str) -> Fernet:
        """
        Create Fernet cipher from master key

        Uses PBKDF2 to derive a proper encryption key from the master key
        """
        # Use a fixed salt for deterministic key derivation
        # In production, you might want to use a per-installation salt
        salt = b"ai-admin-salt-v1"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommended minimum for PBKDF2-SHA256
        )

        # Derive key from master_key
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))

        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error("encryption_failed", error=str(e))
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        if not ciphertext:
            return ""

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("decryption_failed", reason="invalid_token")
            raise
        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            raise

    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value appears to be encrypted

        Args:
            value: String to check

        Returns:
            True if value looks like Fernet-encrypted data
        """
        if not value:
            return False

        # Fernet tokens are base64-encoded and start with 'gAAAAA'
        try:
            if value.startswith("gAAAAA"):
                return True
            return False
        except Exception:
            return False

    def encrypt_if_needed(self, value: str) -> str:
        """
        Encrypt value only if it's not already encrypted

        Args:
            value: String to encrypt

        Returns:
            Encrypted string
        """
        if self.is_encrypted(value):
            return value
        return self.encrypt(value)

    @staticmethod
    def generate_master_key() -> str:
        """
        Generate a new random master key

        Returns:
            Base64-encoded 32-byte random key
        """
        return base64.urlsafe_b64encode(os.urandom(32)).decode()


# Singleton instance
_crypto_service: Optional[CryptoService] = None


def get_crypto_service(master_key: Optional[str] = None) -> CryptoService:
    """
    Get or create CryptoService singleton

    Args:
        master_key: Optional master key (only used on first call)

    Returns:
        CryptoService instance
    """
    global _crypto_service

    if _crypto_service is None:
        _crypto_service = CryptoService(master_key)

    return _crypto_service
