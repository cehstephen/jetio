# ---------------------------------------------------------------------------
# Jetio Framework
# Website: https://jetio.org
#
# Copyright (c) 2025 Stephen Burabari Tete. All Rights Reserved.
# 
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#
# Author:   Stephen Burabari Tete
# Contact:  cehtete [at] gmail.com
# LinkedIn: https://www.linkedin.com/in/tete-stephen/ 
# ---------------------------------------------------------------------------

"""
jetio.auth
==========

Authentication helpers for Jetio.

This module provides:
- password hashing and verification via Passlib
- JSON Web Token (JWT) creation and decoding via PyJWT

Typical usage
-------------
Jetio does not force a specific auth model, but a common pattern is:

1) Hash a user's password on registration using :func:`get_password_hash`
2) Verify credentials on login using :func:`verify_password`
3) Issue an access token using :func:`create_access_token`
4) Decode and validate tokens on protected endpoints using :func:`decode_access_token`
   (usually inside a dependency used with :class:`jetio.framework.Depends`)

Security notes
--------------
- Tokens are signed with ``settings.SECRET_KEY`` and the HS256 algorithm.
- :func:`decode_access_token` returns ``None`` on invalid or expired tokens.
- Consider adding standard claims (e.g. ``sub`` for user id/email) to your payload.
"""


import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from typing import Optional

from .config import settings


# --- Password Hashing ---

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    deprecated="auto",  # pbkdf2_sha256 is preferred; bcrypt is kept for backward compatibility
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored hash.

    Supports verification of both the preferred ``pbkdf2_sha256`` hashes and
    legacy ``bcrypt`` hashes.

    Args:
        plain_password: Candidate password in plain text.
        hashed_password: Stored password hash.

    Returns:
        bool: ``True`` if the password matches the hash, otherwise ``False``.
    """

    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage.

    New passwords are hashed using the preferred ``pbkdf2_sha256`` scheme.
    Legacy ``bcrypt`` hashes remain verifiable for backward compatibility.

    Args:
        password: Plain-text password.

    Returns:
        str: A password hash suitable for storing in the database.

    Notes:
        The hashing scheme is managed by Passlib via ``pwd_context``.
        Applications should always store the returned hash and never store
        raw passwords.
    """

    return pwd_context.hash(password)


# --- JSON Web Tokens (JWT) ---

ALGORITHM = "HS256" # JWT signing algorithm


def _require_secret_key() -> str:
    """settings.SECRET_KEY has no default (see jetio.config.Settings) --
    a fixed value shipped in this package's own published source would be
    public, not secret. Checked here, at the point a token is actually
    signed/verified, rather than at import time: most of the framework
    (CRUD-only apps, anything not using JWT auth) never needs this set at
    all, so failing at `import jetio` would block apps that were never
    going to call these functions in the first place."""
    if not settings.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is not set. create_access_token()/decode_access_token() "
            "need a real secret to sign/verify JWTs -- set the SECRET_KEY "
            "environment variable (e.g. `openssl rand -hex 32`) or a .env file "
            "before issuing or validating tokens."
        )
    return settings.SECRET_KEY


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token.

    The token includes an expiration claim (``exp``). If ``expires_delta`` is not
    provided, the default lifespan is 30 minutes.

    Args:
        data: Payload to encode into the token. Common claims include:
            - ``sub``: subject (user id or email)
            - ``role`` / ``scopes``: authorization context
        expires_delta: Optional token lifespan override.

    Returns:
        str: Encoded JWT string.

    Examples:
        Basic usage:

        ```python
        token = create_access_token({"sub": str(user.id)})
        payload = decode_access_token(token)
        assert payload and payload["sub"] == str(user.id)
        ```

    Security:
        - Tokens are signed with ``settings.SECRET_KEY``.
        - Invalid or expired tokens return ``None`` when decoded.
    """

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, _require_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token.

    Validates the signature and expiry (``exp``). Returns ``None`` if the token
    is invalid, expired, or cannot be decoded.

    Args:
        token: Encoded JWT string (e.g. from an Authorization header).

    Returns:
        Optional[dict]: Decoded token payload, or ``None`` if invalid.

    Notes:
        This function does not enforce any required claims beyond signature/expiry.
        Application code should validate expected fields (e.g. ``sub``).

    Examples:
        ```python
        payload = decode_access_token(token)
        if payload:
            user_id = payload["sub"]
        ```
    """

    try:
        payload = jwt.decode(token, _require_secret_key(), algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
