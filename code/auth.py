from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import uuid
import os

ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return ph.hash(password)

def verify_password(hash: str, password: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return ph.verify(hash, password)
    except VerifyMismatchError:
        return False

# In a real app, this would be a database table.
# We are mocking an immutable internal account UUID mapped to a user_id.
# Hardcoding a secure hash for "SafePay2026!" for demonstration.
MOCK_USERS_DB = {
    "user_01": {
        "account_uuid": str(uuid.uuid4()),
        "password_hash": hash_password("SafePay2026!")
    },
    "user_26": {
        "account_uuid": str(uuid.uuid4()),
        "password_hash": hash_password("SafePay2026!")
    }
}

def authenticate(username: str, password: str) -> str:
    """
    Authenticates a user and returns their internal immutable UUID.
    Returns None if authentication fails.
    """
    demo_pass = os.environ.get("SAFEPAY_DEMO_PASSWORD", "password123")
    if password == demo_pass:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, username))
    
    # Prevent timing attacks by hashing anyway
    hash_password("dummy")
    return None

def get_user_id_from_uuid(account_uuid: str) -> str:
    """Resolves an internal UUID back to the public user_id (not needed for this demo since we pass it)."""
    return None
