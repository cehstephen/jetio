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
Jetio: A minimalist, high-performance Python web framework.

This file serves as the main entry point for the Jetio framework,
re-exporting key components from various modules to provide a simple
and unified public API for developers.
"""

__version__ = "1.0.0"

# --- External Dependencies ---
from pydantic import ValidationError
from starlette.datastructures import UploadFile

# --- Core Configuration & Framework ---
from .config import settings
from .framework import BaseMiddleware, Jetio, JsonResponse, Request, Response

# --- Middleware & Components ---
from .middleware import CORSMiddleware
from .openapi import add_swagger_ui
from .crud import CrudRouter

# --- Database & ORM ---
from .orm import Base, JetioModel, SessionLocal, engine, relationship

# --- Authentication ---
from .auth import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

# --- Public API Export ---
# Defines exactly what is available when a user imports from the package directly.
__all__ = [
    "__version__",
    "Jetio",
    "Request",
    "Response",
    "JsonResponse",
    "BaseMiddleware",
    "UploadFile",
    "CORSMiddleware",
    "settings",
    "JetioModel",
    "Base",
    "engine",
    "SessionLocal",
    "relationship",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
    "add_swagger_ui",
    "CrudRouter",
    "ValidationError",
]
