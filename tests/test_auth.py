
from jetio.auth import get_password_hash, verify_password, create_access_token, decode_access_token

def test_password_hashing_and_verification():
    """
    Verifies that a password can be hashed and then correctly verified.
    """
    password = "my-secret-password"
    hashed_password = get_password_hash(password)

    assert password != hashed_password
    assert verify_password(password, hashed_password) is True
    assert verify_password("wrong-password", hashed_password) is False
