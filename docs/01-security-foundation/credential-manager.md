# 🔐 Credential Manager Implementation

## Overview

The Credential Manager provides secure encryption and decryption of sensitive trading credentials (API keys, private keys, etc.) using industry-standard encryption practices.

## Architecture

### Security Design

- **Encryption Algorithm**: AES-256 (Fernet symmetric encryption)
- **Key Derivation**: PBKDF2 with SHA-256, 100,000 iterations
- **Master Password**: Required to encrypt/decrypt credentials
- **Salt Management**: Fixed salt for consistency (consider per-installation salts)

## Implementation Details

### 1. Core Credential Manager Class

```python
# backend/services/credential_manager.py
import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class CredentialManager:
    """
    Secure credential management system for trading API keys and private keys.

    Features:
    - AES-256 encryption
    - PBKDF2 key derivation
    - Master password protection
    - Secure key generation
    """

    def __init__(self, master_password: str, salt: Optional[bytes] = None):
        """
        Initialize credential manager with master password.

        Args:
            master_password: Strong master password for key derivation
            salt: Optional salt for key derivation (uses default if None)
        """
        self.master_password = master_password
        self.salt = salt or b'open_alpha_arena_salt_v1'
        self.key = self._derive_key()
        self.cipher_suite = Fernet(self.key)

        logger.info("CredentialManager initialized securely")

    def _derive_key(self) -> bytes:
        """
        Derive encryption key from master password using PBKDF2.

        Returns:
            32-byte encryption key
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,  # OWASP recommended minimum
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
            logger.debug("Key derived successfully from master password")
            return key
        except Exception as e:
            logger.error(f"Key derivation failed: {e}")
            raise ValueError("Failed to derive encryption key")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext data.

        Args:
            plaintext: Data to encrypt (API keys, private keys, etc.)

        Returns:
            Base64-encoded encrypted string

        Raises:
            ValueError: If encryption fails
        """
        try:
            if not plaintext:
                raise ValueError("Cannot encrypt empty string")

            # Convert to bytes if needed
            if isinstance(plaintext, str):
                plaintext_bytes = plaintext.encode('utf-8')
            else:
                plaintext_bytes = plaintext

            # Encrypt
            encrypted_data = self.cipher_suite.encrypt(plaintext_bytes)

            # Return as base64 string for database storage
            encrypted_str = base64.urlsafe_b64encode(encrypted_data).decode('utf-8')

            logger.debug(f"Successfully encrypted data (length: {len(plaintext)})")
            return encrypted_str

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt data: {e}")

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data.

        Args:
            encrypted_data: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails
        """
        try:
            if not encrypted_data:
                raise ValueError("Cannot decrypt empty string")

            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))

            # Decrypt
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)

            # Convert to string
            plaintext = decrypted_bytes.decode('utf-8')

            logger.debug(f"Successfully decrypted data (length: {len(plaintext)})")
            return plaintext

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")

    def verify_master_password(self, test_password: str) -> bool:
        """
        Verify if the provided master password is correct.

        Args:
            test_password: Password to test

        Returns:
            True if password matches, False otherwise
        """
        try:
            # Try to derive key with test password
            test_kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            test_key = base64.urlsafe_b64encode(test_kdf.derive(test_password.encode()))
            return test_key == self.key
        except Exception:
            return False

    @staticmethod
    def generate_secure_key() -> str:
        """
        Generate a cryptographically secure random key.

        Returns:
            URL-safe base64 encoded key
        """
        key = Fernet.generate_key()
        return key.decode('utf-8')

    @staticmethod
    def validate_master_password_strength(password: str) -> Dict[str, any]:
        """
        Validate master password strength.

        Args:
            password: Password to validate

        Returns:
            Dictionary with validation results
        """
        result = {
            'is_valid': True,
            'issues': [],
            'score': 0
        }

        # Length check
        if len(password) < 12:
            result['issues'].append("Password must be at least 12 characters long")
            result['is_valid'] = False
        else:
            result['score'] += 2

        # Complexity checks
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not has_upper:
            result['issues'].append("Password must contain uppercase letters")
            result['is_valid'] = False
        else:
            result['score'] += 2

        if not has_lower:
            result['issues'].append("Password must contain lowercase letters")
            result['is_valid'] = False
        else:
            result['score'] += 2

        if not has_digit:
            result['issues'].append("Password must contain digits")
            result['is_valid'] = False
        else:
            result['score'] += 2

        if not has_special:
            result['issues'].append("Password must contain special characters")
            result['is_valid'] = False
        else:
            result['score'] += 2

        # Common patterns check
        common_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
        if any(pattern in password.lower() for pattern in common_passwords):
            result['issues'].append("Password contains common patterns")
            result['is_valid'] = False
            result['score'] = max(0, result['score'] - 4)

        return result
```

### 2. Database Integration

```python
# backend/services/credential_service.py
import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from database.models import Account
from .credential_manager import CredentialManager

logger = logging.getLogger(__name__)

class CredentialService:
    """
    Service for managing encrypted credentials in the database.

    This service handles the encryption and storage of sensitive credentials
    like API keys, secrets, and private keys.
    """

    def __init__(self, master_password: str):
        """
        Initialize with master password.

        Args:
            master_password: Master password for encryption
        """
        self.credential_manager = CredentialManager(master_password)

    def encrypt_and_store_api_credentials(
        self,
        account_id: int,
        db: Session,
        api_key: str,
        api_secret: str,
        api_passphrase: Optional[str] = None,
        exchange_name: Optional[str] = None
    ) -> bool:
        """
        Encrypt and store API credentials for an account.

        Args:
            account_id: Account ID to store credentials for
            db: Database session
            api_key: Exchange API key
            api_secret: Exchange API secret
            api_passphrase: Optional API passphrase (for some exchanges)
            exchange_name: Name of the exchange

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate inputs
            if not api_key or not api_secret:
                raise ValueError("API key and secret are required")

            # Get account
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")

            # Encrypt credentials
            encrypted_key = self.credential_manager.encrypt(api_key)
            encrypted_secret = self.credential_manager.encrypt(api_secret)
            encrypted_passphrase = self.credential_manager.encrypt(api_passphrase) if api_passphrase else None

            # Store in database
            account.exchange_api_key_encrypted = encrypted_key
            account.exchange_api_secret_encrypted = encrypted_secret
            account.exchange_passphrase_encrypted = encrypted_passphrase
            account.exchange_name = exchange_name

            db.commit()

            logger.info(f"API credentials encrypted and stored for account {account_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store API credentials: {e}")
            db.rollback()
            return False

    def encrypt_and_store_wallet_credentials(
        self,
        account_id: int,
        db: Session,
        private_key: str,
        wallet_address: Optional[str] = None
    ) -> bool:
        """
        Encrypt and store Web3 wallet credentials.

        Args:
            account_id: Account ID to store credentials for
            db: Database session
            private_key: Private key for wallet
            wallet_address: Optional wallet address

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate private key format
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key

            if len(private_key) != 66:  # 0x + 64 hex characters
                raise ValueError("Invalid private key format")

            # Get account
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")

            # Encrypt private key
            encrypted_private_key = self.credential_manager.encrypt(private_key)

            # Store in database
            account.wallet_private_key_encrypted = encrypted_private_key
            if wallet_address:
                account.wallet_address = wallet_address

            db.commit()

            logger.info(f"Wallet credentials encrypted and stored for account {account_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store wallet credentials: {e}")
            db.rollback()
            return False

    def get_decrypted_api_credentials(self, account_id: int, db: Session) -> Optional[Dict[str, str]]:
        """
        Retrieve and decrypt API credentials for an account.

        Args:
            account_id: Account ID
            db: Database session

        Returns:
            Dictionary with decrypted credentials or None if failed
        """
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return None

            if not account.exchange_api_key_encrypted or not account.exchange_api_secret_encrypted:
                return None

            # Decrypt credentials
            api_key = self.credential_manager.decrypt(account.exchange_api_key_encrypted)
            api_secret = self.credential_manager.decrypt(account.exchange_api_secret_encrypted)
            api_passphrase = None
            if account.exchange_passphrase_encrypted:
                api_passphrase = self.credential_manager.decrypt(account.exchange_passphrase_encrypted)

            credentials = {
                'api_key': api_key,
                'api_secret': api_secret,
                'api_passphrase': api_passphrase,
                'exchange_name': account.exchange_name
            }

            logger.debug(f"API credentials decrypted for account {account_id}")
            return credentials

        except Exception as e:
            logger.error(f"Failed to decrypt API credentials: {e}")
            return None

    def get_decrypted_wallet_credentials(self, account_id: int, db: Session) -> Optional[Dict[str, str]]:
        """
        Retrieve and decrypt wallet credentials for an account.

        Args:
            account_id: Account ID
            db: Database session

        Returns:
            Dictionary with decrypted credentials or None if failed
        """
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return None

            if not account.wallet_private_key_encrypted:
                return None

            # Decrypt private key
            private_key = self.credential_manager.decrypt(account.wallet_private_key_encrypted)

            credentials = {
                'private_key': private_key,
                'address': account.wallet_address
            }

            logger.debug(f"Wallet credentials decrypted for account {account_id}")
            return credentials

        except Exception as e:
            logger.error(f"Failed to decrypt wallet credentials: {e}")
            return None

    def test_credentials(self, account_id: int, db: Session) -> Dict[str, Any]:
        """
        Test if stored credentials are valid by attempting to decrypt them.

        Args:
            account_id: Account ID
            db: Database session

        Returns:
            Dictionary with test results
        """
        result = {
            'account_id': account_id,
            'api_credentials_valid': False,
            'wallet_credentials_valid': False,
            'errors': []
        }

        try:
            # Test API credentials
            api_creds = self.get_decrypted_api_credentials(account_id, db)
            if api_creds:
                result['api_credentials_valid'] = True
                logger.info(f"API credentials test passed for account {account_id}")
            else:
                result['errors'].append("API credentials not found or decryption failed")

            # Test wallet credentials
            wallet_creds = self.get_decrypted_wallet_credentials(account_id, db)
            if wallet_creds:
                result['wallet_credentials_valid'] = True
                logger.info(f"Wallet credentials test passed for account {account_id}")
            else:
                result['errors'].append("Wallet credentials not found or decryption failed")

        except Exception as e:
            result['errors'].append(f"Credential test failed: {e}")
            logger.error(f"Credential test failed for account {account_id}: {e}")

        return result
```

### 3. Configuration and Environment Setup

```python
# backend/config/credential_config.py
import os
from typing import Optional
from pydantic import BaseModel, Field

class CredentialConfig(BaseModel):
    """Configuration for credential management."""

    master_password: str = Field(..., description="Master password for encryption")
    require_strong_password: bool = Field(True, description="Require strong master password")
    min_password_length: int = Field(12, description="Minimum master password length")
    enable_password_rotation: bool = Field(False, description="Enable password rotation")

    @classmethod
    def from_environment(cls) -> 'CredentialConfig':
        """Load configuration from environment variables."""
        master_password = os.getenv('MASTER_PASSWORD')
        if not master_password:
            raise ValueError("MASTER_PASSWORD environment variable is required")

        return cls(
            master_password=master_password,
            require_strong_password=os.getenv('REQUIRE_STRONG_PASSWORD', 'true').lower() == 'true',
            min_password_length=int(os.getenv('MIN_PASSWORD_LENGTH', '12')),
            enable_password_rotation=os.getenv('ENABLE_PASSWORD_ROTATION', 'false').lower() == 'true'
        )

    def validate(self) -> bool:
        """Validate configuration."""
        from .credential_manager import CredentialManager

        # Validate master password strength if required
        if self.require_strong_password:
            validation = CredentialManager.validate_master_password_strength(self.master_password)
            if not validation['is_valid']:
                raise ValueError(f"Master password validation failed: {validation['issues']}")

        return True
```

## Security Best Practices

### 1. Master Password Security
- Use a strong, unique master password (12+ characters)
- Store master password in environment variable only
- Never log or write master password to files
- Consider using a password manager for the master password
- Enable password rotation for production environments

### 2. Database Security
- Encrypt database backups
- Use SSL/TLS for database connections
- Limit database access to application only
- Regular database security audits
- Implement row-level security if multi-tenant

### 3. Application Security
- Never log decrypted credentials
- Use secure memory handling for sensitive data
- Clear sensitive data from memory after use
- Implement rate limiting for credential operations
- Log all credential access attempts

### 4. Operational Security
- Regular credential rotation
- Monitor for unusual access patterns
- Implement IP whitelisting for admin functions
- Use multi-factor authentication for admin access
- Regular security audits and penetration testing

## Testing Implementation

```python
# backend/tests/test_credential_manager.py
import pytest
import os
from services.credential_manager import CredentialManager, CredentialService

class TestCredentialManager:
    """Test cases for CredentialManager."""

    @pytest.fixture
    def credential_manager(self):
        """Create test credential manager."""
        return CredentialManager("test_password_123456!")

    @pytest.fixture
    def test_data(self):
        """Test data for encryption/decryption."""
        return {
            'api_key': 'sk_test_1234567890abcdef',
            'api_secret': 'secret_test_1234567890abcdef',
            'private_key': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
        }

    def test_encrypt_decrypt_api_key(self, credential_manager, test_data):
        """Test API key encryption and decryption."""
        original = test_data['api_key']

        # Encrypt
        encrypted = credential_manager.encrypt(original)
        assert encrypted != original
        assert len(encrypted) > len(original)

        # Decrypt
        decrypted = credential_manager.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_private_key(self, credential_manager, test_data):
        """Test private key encryption and decryption."""
        original = test_data['private_key']

        # Encrypt
        encrypted = credential_manager.encrypt(original)
        assert encrypted != original

        # Decrypt
        decrypted = credential_manager.decrypt(encrypted)
        assert decrypted == original

    def test_password_strength_validation(self):
        """Test master password strength validation."""
        # Strong password
        strong_result = CredentialManager.validate_master_password_strength("StrongP@ssw0rd123!")
        assert strong_result['is_valid'] == True
        assert strong_result['score'] >= 8

        # Weak password
        weak_result = CredentialManager.validate_master_password_strength("weak")
        assert weak_result['is_valid'] == False
        assert len(weak_result['issues']) > 0

    def test_generate_secure_key(self):
        """Test secure key generation."""
        key1 = CredentialManager.generate_secure_key()
        key2 = CredentialManager.generate_secure_key()

        assert key1 != key2
        assert len(key1) > 20  # Should be substantial length

        # Should be valid base64
        import base64
        base64.urlsafe_b64decode(key1.encode())
        base64.urlsafe_b64decode(key2.encode())
```

## Deployment Instructions

### 1. Environment Setup
```bash
# Set master password (use a strong, unique password)
export MASTER_PASSWORD="your_very_strong_master_password_here"

# Set additional security options
export REQUIRE_STRONG_PASSWORD="true"
export MIN_PASSWORD_LENGTH="12"
export ENABLE_PASSWORD_ROTATION="false"
```

### 2. Database Migration
```sql
-- Add new columns to accounts table
ALTER TABLE accounts ADD COLUMN exchange_name VARCHAR(50);
ALTER TABLE accounts ADD COLUMN exchange_api_key_encrypted VARCHAR(1000);
ALTER TABLE accounts ADD COLUMN exchange_api_secret_encrypted VARCHAR(1000);
ALTER TABLE accounts ADD COLUMN exchange_passphrase_encrypted VARCHAR(500);
ALTER TABLE accounts ADD COLUMN wallet_private_key_encrypted VARCHAR(1000);
ALTER TABLE accounts ADD COLUMN wallet_address VARCHAR(100);
ALTER TABLE accounts ADD COLUMN trading_mode VARCHAR(20) DEFAULT 'PAPER';
ALTER TABLE accounts ADD COLUMN max_position_size DECIMAL(18,2) DEFAULT 1000.00;
ALTER TABLE accounts ADD COLUMN max_daily_loss DECIMAL(18,2) DEFAULT 100.00;
ALTER TABLE accounts ADD COLUMN emergency_stop VARCHAR(10) DEFAULT 'false';
ALTER TABLE accounts ADD COLUMN testnet_mode VARCHAR(10) DEFAULT 'true';
```

### 3. Security Verification
```python
# Test the credential manager before deployment
from services.credential_manager import CredentialManager

# Initialize with your master password
manager = CredentialManager(os.getenv('MASTER_PASSWORD'))

# Test encryption/decryption
test_key = "test_api_key_123"
encrypted = manager.encrypt(test_key)
decrypted = manager.decrypt(encrypted)

assert decrypted == test_key
print("✅ Credential manager working correctly")
```

## Troubleshooting

### Common Issues

1. **Decryption Fails**
   - Check master password is correct
   - Verify encrypted data hasn't been corrupted
   - Ensure consistent salt usage

2. **Performance Issues**
   - Key derivation is intentionally slow (100,000 iterations)
   - Cache credential manager instances where possible
   - Consider connection pooling for database operations

3. **Security Concerns**
   - Never store master password in code
   - Use environment variables or secure key management
   - Regular security audits recommended

### Monitoring and Alerting
```python
# Add logging for security events
import logging

security_logger = logging.getLogger('security')

# Log credential access
security_logger.info(f"Credential access: account_id={account_id}, user={user_id}, timestamp={datetime.now()}")

# Log failed decryption attempts
security_logger.warning(f"Failed decryption attempt: account_id={account_id}, error={error}")

# Log emergency stop activations
security_logger.critical(f"Emergency stop activated: account_id={account_id}, reason={reason}")
```

This implementation provides enterprise-grade security for managing trading credentials while maintaining usability and performance.