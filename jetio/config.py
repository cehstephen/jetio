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
Centralized configuration management for the Jetio framework.

This module uses Pydantic's `BaseSettings` to manage application settings,
allowing for configuration via environment variables or a `.env` file. This
approach provides a robust and type-safe way to handle configuration.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine the project root directory relative to this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """
    Manages application-wide settings.

    It automatically reads from environment variables or a .env file.
    This provides a single source of truth for configuration values like
    database URLs and secret keys.

    Attributes:
        DATABASE_URL: The connection string for the application's database.
                      Defaults to an async SQLite database in the local directory.
        SECRET_KEY: A secret key for cryptographic signing (e.g., for JWTs).
                    No default -- a fixed value shipped in this package's
                    own published source would be public, not secret:
                    anyone could forge a valid JWT for any user, including
                    an admin, with zero credentials. Optional here (apps
                    that never call create_access_token()/
                    decode_access_token() don't need it, and settings is
                    imported unconditionally by the whole package) --
                    jetio.auth raises a clear error the first time either
                    of those is actually called without one configured.
                    Set it via the SECRET_KEY environment variable or a
                    .env file, e.g. `openssl rand -hex 32`.
    """
    DATABASE_URL: str = "sqlite+aiosqlite:///./jetio.db" # Async driver
    SECRET_KEY: Optional[str] = None
    DOMAIN: str = "http://127.0.0.1:8000"

    # Mail Configuration
    MAIL_MODE: str = "console"  # Can be 'smtp' or 'console'
    MAIL_USERNAME: str = "default_user"
    MAIL_PASSWORD: str = "default_pass"
    MAIL_FROM: str = "default@example.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.example.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    MAIL_USE_CREDENTIALS: bool = True
    MAIL_VALIDATE_CERTS: bool = True

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", 
        env_file_encoding='utf-8',
        # Ignore extra environment variables that don't match fields in this model
        extra='ignore'
    )

# Create a single instance of the settings to be used across the application
settings = Settings()
