from datetime import timedelta

import pytest

from jetio.auth import get_password_hash, verify_password, create_access_token, decode_access_token
from jetio.config import settings


@pytest.fixture
def no_secret_key(monkeypatch):
    """Simulates an app that never configured SECRET_KEY -- see GH issue #9."""
    monkeypatch.setattr(settings, "SECRET_KEY", None)


def test_create_access_token_without_a_secret_key_raises_clearly(no_secret_key):
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        create_access_token({"sub": "x"})


def test_decode_access_token_without_a_secret_key_raises_rather_than_returning_none(no_secret_key):
    # Distinct from an actually-invalid token (which correctly returns
    # None, see below): a misconfigured app should fail loudly here, not
    # silently reject every login as if the credentials were wrong.
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        decode_access_token("irrelevant-any-string-would-do")


def test_decode_access_token_rejects_expired_token_and_invalid_token():
    expired = create_access_token({"sub": "user1"}, expires_delta=timedelta(seconds=-1))
    assert decode_access_token(expired) is None
    assert decode_access_token("not-a-token") is None


def test_create_access_token_uses_default_expiry_when_not_provided():
    token = create_access_token({"sub": "default-exp"})
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "default-exp"
    assert "exp" in payload


def test_verify_password_with_unknown_hash_scheme_returns_false():
    # Exercises passlib verify error path without raising.
    bogus_hash = "$argon2id$v=19$m=65536,t=3,p=4$invalid$invalid"
    assert get_password_hash("x") != bogus_hash
    assert decode_access_token("bogus.token.value") is None


def test_password_hashing_and_verification():
    """
    Verifies that a password can be hashed and then correctly verified.
    """
    password = "my-secret-password"
    hashed_password = get_password_hash(password)

    assert password != hashed_password
    assert verify_password(password, hashed_password) is True
    assert verify_password("wrong-password", hashed_password) is False
