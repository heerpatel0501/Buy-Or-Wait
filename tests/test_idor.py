import pytest
from code.security import SecurityContext
import uuid

def test_cross_user_request():
    ctx = SecurityContext(str(uuid.uuid4()), "user_01")
    with pytest.raises(PermissionError):
        ctx.verify_ownership("user_02")

def test_same_user_request():
    ctx = SecurityContext(str(uuid.uuid4()), "user_01")
    # Should not raise
    ctx.verify_ownership("user_01")
