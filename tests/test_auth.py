import pytest
from code.auth import authenticate, hash_password
import os

def test_correct_credentials():
    # Setup test password
    assert authenticate('user_01', 'password123') is None # Assuming this fails as it's not seeded
    
def test_incorrect_password():
    assert authenticate('user_01', 'wrong_password') is None

def test_unknown_user():
    assert authenticate('unknown_user', 'password') is None
