"""
Sumatic Modern IoT - Encryption at Rest
Provides encryption/decryption for sensitive data stored in the database.
Uses AES-256-GCM for authenticated encryption.
"""
import base64
import os
from typing import Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from app.config import get_settings

settings = get_settings()


class EncryptionError(Exception):
    """Custom exception for encryption/decryption errors."""
    pass


class DataEncryption:
    """
    AES-256-GCM encryption for sensitive data at rest.
    
    This class provides methods to encrypt and decrypt sensitive data
    that needs to be stored in the database. Uses AES-256-GCM which
    provides both confidentiality and integrity.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the encryption handler.
        
        Args:
            encryption_key: Base64-encoded encryption key. If not provided,
                          will use ENCRYPTION_KEY from environment settings.
        
        Raises:
            EncryptionError: If encryption key is not available or invalid.
        """
        self._key: Optional[bytes] = None
        
        if encryption_key:
            try:
                self._key = base64.b64decode(encryption_key.encode())
                if len(self._key) not in [16, 24, 32]:
                    raise EncryptionError(
                        f"Invalid encryption key length: {len(self._key)} bytes. "
                        "Key must be 16, 24, or 32 bytes (128, 192, or 256 bits)."
                    )
            except Exception as e:
                raise EncryptionError(f"Failed to decode encryption key: {e}")
        else:
            # Try to get from environment
            env_key = getattr(settings, 'ENCRYPTION_KEY', None)
            if env_key:
                try:
                    self._key = base64.b64decode(env_key.encode())
                    if len(self._key) not in [16, 24, 32]:
                        raise EncryptionError(
                            f"Invalid ENCRYPTION_KEY length: {len(self._key)} bytes. "
                            "Key must be 16, 24, or 32 bytes (128, 192, or 256 bits)."
                        )
                except Exception as e:
                    raise EncryptionError(f"Failed to decode ENCRYPTION_KEY from environment: {e}")
            else:
                # Generate a warning but don't fail - allow for testing
                import warnings
                warnings.warn(
                    "⚠️ SECURITY WARNING: ENCRYPTION_KEY not set. "
                    "Data encryption is disabled. Set ENCRYPTION_KEY environment variable "
                    "to a base64-encoded 32-byte random key for production. "
                    "Generate with: python -c \"import os, base64; print(base64.b64encode(os.urandom(32)).decode())\"",
                    SecurityWarning,
                    stacklevel=2
                )
    
    def _ensure_key(self) -> bytes:
        """Ensure encryption key is available."""
        if self._key is None:
            raise EncryptionError(
                "Encryption key not available. Cannot encrypt/decrypt data. "
                "Set ENCRYPTION_KEY environment variable."
            )
        return self._key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext data.
        
        Args:
            plaintext: The data to encrypt (string).
        
        Returns:
            Base64-encoded encrypted data including nonce.
        
        Raises:
            EncryptionError: If encryption fails.
        """
        if not plaintext:
            return plaintext
        
        try:
            key = self._ensure_key()
            
            # Generate a random 96-bit (12-byte) nonce
            nonce = os.urandom(12)
            
            # Create AES-GCM cipher
            aesgcm = AESGCM(key)
            
            # Encrypt the data
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
            
            # Combine nonce and ciphertext, then encode as base64
            combined = nonce + ciphertext
            return base64.b64encode(combined).decode('utf-8')
            
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data.
        
        Args:
            encrypted_data: Base64-encoded encrypted data including nonce.
        
        Returns:
            Decrypted plaintext string.
        
        Raises:
            EncryptionError: If decryption fails.
        """
        if not encrypted_data:
            return encrypted_data
        
        try:
            key = self._ensure_key()
            
            # Decode base64
            combined = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract nonce (first 12 bytes) and ciphertext
            nonce = combined[:12]
            ciphertext = combined[12:]
            
            # Create AES-GCM cipher
            aesgcm = AESGCM(key)
            
            # Decrypt the data
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")
    
    def is_encrypted(self, data: str) -> bool:
        """
        Check if data appears to be encrypted (base64 encoded with nonce).
        
        Args:
            data: The data to check.
        
        Returns:
            True if data appears to be encrypted, False otherwise.
        """
        if not data or len(data) < 20:  # Minimum length for valid encrypted data
            return False
        
        try:
            decoded = base64.b64decode(data.encode('utf-8'))
            # Valid encrypted data should be at least 12 bytes (nonce) + 16 bytes (tag) + some data
            return len(decoded) >= 28
        except Exception:
            return False
    
    def encrypt_dict_field(self, data_dict: dict, field_name: str) -> dict:
        """
        Encrypt a specific field in a dictionary.
        
        Args:
            data_dict: Dictionary containing the field to encrypt.
            field_name: Name of the field to encrypt.
        
        Returns:
            Dictionary with the specified field encrypted.
        """
        if field_name in data_dict and data_dict[field_name]:
            data_dict[field_name] = self.encrypt(str(data_dict[field_name]))
        return data_dict
    
    def decrypt_dict_field(self, data_dict: dict, field_name: str) -> dict:
        """
        Decrypt a specific field in a dictionary.
        
        Args:
            data_dict: Dictionary containing the field to decrypt.
            field_name: Name of the field to decrypt.
        
        Returns:
            Dictionary with the specified field decrypted.
        """
        if field_name in data_dict and data_dict[field_name]:
            try:
                data_dict[field_name] = self.decrypt(data_dict[field_name])
            except EncryptionError:
                # If decryption fails, leave as-is (might not be encrypted)
                pass
        return data_dict


# Global encryption instance
_encryption_instance: Optional[DataEncryption] = None


def get_encryption() -> DataEncryption:
    """
    Get the global encryption instance (singleton pattern).
    
    Returns:
        DataEncryption instance.
    """
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = DataEncryption()
    return _encryption_instance


def generate_encryption_key() -> str:
    """
    Generate a new random encryption key.
    
    Returns:
        Base64-encoded 32-byte (256-bit) encryption key.
    
    Example:
        >>> key = generate_encryption_key()
        >>> print(f"ENCRYPTION_KEY={key}")
    """
    key = os.urandom(32)  # 256-bit key
    return base64.b64encode(key).decode('utf-8')


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
    """
    Derive an encryption key from a password using PBKDF2.
    
    WARNING: This is less secure than a random key. Use only for compatibility
    with existing systems. For new systems, use generate_encryption_key().
    
    Args:
        password: Password to derive key from.
        salt: Salt for key derivation. If None, generates random salt.
    
    Returns:
        Tuple of (base64_encoded_key, salt_used).
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = kdf.derive(password.encode('utf-8'))
    return base64.b64encode(key).decode('utf-8'), salt
