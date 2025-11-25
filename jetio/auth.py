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
Core authentication and security utilities for the Jetio framework.

This module provides essential functions for password hashing and verification,
as well as for creating and decoding JSON Web Tokens (JWTs) for user authentication
and session management. It uses `passlib` for robust password handling and `PyJWT`
for JWT operations.
"""

import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from typing import Optional

from .config import settings


# --- Password Hashing ---

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed one.

    Args:
        plain_password: The password to verify, in plain text.
        hashed_password: The hashed password to compare against.

    Returns:
        True if the password is correct, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password using the configured scheme (bcrypt).

    Args:
        password: The plain-text password to hash.

    Returns:
        The hashed password as a string.
    """
    return pwd_context.hash(password)


# --- JSON Web Tokens (JWT) ---

ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a new JWT access token containing a specified payload.

    The token includes an expiration claim ('exp'). If no expiration delta is
    provided, a default lifespan is used.

    Args:
        data: The payload to encode into the token.
        expires_delta: The lifespan of the token. Defaults to 30 minutes.

    Returns:
        The encoded JWT as a string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes and validates a JWT access token.

    It checks the signature and expiration time.

    Args:
        token: The JWT to decode.

    Returns:
        The decoded payload as a dictionary if the token is valid,
        otherwise None.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
