"""
Unit tests for CryptoService
"""

import os
import pytest
from shared.utils.crypto import CryptoService


class TestCryptoService:
    """Tests for encryption/decryption functionality"""

    @pytest.fixture
    def crypto(self):
        """Create CryptoService with test key"""
        return CryptoService(master_key="test-master-key-for-testing-only")

    def test_encrypt_decrypt_roundtrip(self, crypto):
        """Test that encryption and decryption are reversible"""
        original = "my_secret_api_key_123"
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)

        assert decrypted == original
        assert encrypted != original

    def test_encrypt_produces_different_output(self, crypto):
        """Test that same input produces different ciphertext each time"""
        plaintext = "same_value"
        encrypted1 = crypto.encrypt(plaintext)
        encrypted2 = crypto.encrypt(plaintext)

        # Fernet uses random IV, so ciphertexts should differ
        assert encrypted1 != encrypted2

        # But both should decrypt to same value
        assert crypto.decrypt(encrypted1) == plaintext
        assert crypto.decrypt(encrypted2) == plaintext

    def test_empty_string(self, crypto):
        """Test handling of empty strings"""
        assert crypto.encrypt("") == ""
        assert crypto.decrypt("") == ""

    def test_unicode_support(self, crypto):
        """Test encryption of unicode characters"""
        original = "Привет мир! 你好世界 🔐"
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)

        assert decrypted == original

    def test_is_encrypted_detection(self, crypto):
        """Test detection of encrypted values"""
        encrypted = crypto.encrypt("test_value")

        assert crypto.is_encrypted(encrypted) is True
        assert crypto.is_encrypted("plaintext") is False
        assert crypto.is_encrypted("") is False
        assert crypto.is_encrypted("gAAAAA_fake") is True  # Starts with Fernet prefix

    def test_encrypt_if_needed(self, crypto):
        """Test conditional encryption"""
        plaintext = "my_api_key"

        # First encryption
        encrypted = crypto.encrypt_if_needed(plaintext)
        assert crypto.is_encrypted(encrypted)

        # Second call should not re-encrypt
        double_encrypted = crypto.encrypt_if_needed(encrypted)
        assert double_encrypted == encrypted

    def test_generate_master_key(self):
        """Test master key generation"""
        key1 = CryptoService.generate_master_key()
        key2 = CryptoService.generate_master_key()

        # Keys should be different
        assert key1 != key2

        # Keys should be valid base64
        assert len(key1) > 32

    def test_wrong_key_fails_decryption(self):
        """Test that wrong key fails to decrypt"""
        crypto1 = CryptoService(master_key="key-one")
        crypto2 = CryptoService(master_key="key-two")

        encrypted = crypto1.encrypt("secret")

        with pytest.raises(Exception):
            crypto2.decrypt(encrypted)

    def test_missing_master_key_raises_error(self):
        """Test that missing master key raises error"""
        # Clear environment variable if set
        old_value = os.environ.pop("ENCRYPTION_MASTER_KEY", None)

        try:
            with pytest.raises(ValueError, match="ENCRYPTION_MASTER_KEY is required"):
                CryptoService()
        finally:
            # Restore if was set
            if old_value:
                os.environ["ENCRYPTION_MASTER_KEY"] = old_value

    def test_long_values(self, crypto):
        """Test encryption of long values"""
        long_value = "x" * 10000
        encrypted = crypto.encrypt(long_value)
        decrypted = crypto.decrypt(encrypted)

        assert decrypted == long_value
