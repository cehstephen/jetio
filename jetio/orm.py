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
Object-Relational Mapping (ORM) utilities for the Jetio framework.

This module handles the SQLAlchemy async engine setup and provides the
`JetioModel` base class. It utilizes a metaclass to automatically generate
Pydantic schemas (`CreateSchema` and `ReadSchema`) from model definitions,
reducing boilerplate for API validation and serialization.
"""

import inspect
import sys
from typing import Any, ForwardRef, List, Optional, Union, get_args, get_origin

from pydantic import ConfigDict, create_model
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    Relationship,
    declarative_base,
    relationship as sa_relationship,
    sessionmaker,
)

from .config import settings

# --- Core Database and ORM Setup ---
engine = create_async_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()
_model_registry = []  # Registry for OpenAPI generation.


def relationship(*args, **kwargs) -> Relationship:
    """Wrapper around SQLAlchemy's relationship for consistent API exposure."""
    return sa_relationship(*args, **kwargs)


class ModelMetaclass(type(Base)):
    """
    Metaclass that automatically generates Pydantic models from SQLAlchemy models.

    It introspects columns and relationships to create:
    - `ModelNameRead`: For serializing data (API responses).
    - `ModelNameCreate`: For validating data (API request bodies).
    """

    def __new__(cls, name, bases, attrs):
        # Auto-generate table name if not provided (e.g., 'User' -> 'users').
        if '__tablename__' not in attrs and not attrs.get('__abstract__', False):
            attrs['__tablename__'] = name.lower() + 's'
        return super().__new__(cls, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

        if attrs.get('__abstract__', False):
            return

        # Collect annotations from class hierarchy
        all_annotations = {}
        for base in cls.__mro__:
            if base is Base:
                break
            all_annotations = {**getattr(base, '__annotations__', {}), **all_annotations}

        pydantic_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
        api_config = attrs.get('API')
        exclude_from_read = getattr(api_config, 'exclude_from_read', [])

        def get_python_type_from_mapped(mapped_type):
            """Extracts Python type from SQLAlchemy `Mapped` annotation."""
            if get_origin(mapped_type) is Mapped:
                return get_args(mapped_type)[0]
            return mapped_type

        def resolve_pydantic_type(typ):
            """Resolves SQLAlchemy types to Pydantic-compatible types for schemas."""
            typ = get_python_type_from_mapped(typ)
            origin = get_origin(typ)

            # Handle Optional[T] / Union[T, None]
            if origin is Union:
                args = get_args(typ)
                non_none_args = [t for t in args if t is not type(None)]
                if len(non_none_args) == 1:
                    inner_type = non_none_args[0]
                    # Check for relationships needing forward reference resolution
                    is_relationship = (
                        isinstance(inner_type, ForwardRef) or
                        (inspect.isclass(inner_type) and issubclass(inner_type, JetioModel))
                    )
                    if is_relationship:
                        resolved_inner_type = resolve_pydantic_type(inner_type)
                        return Optional[ForwardRef(str(resolved_inner_type))]
                    return typ

            if isinstance(typ, ForwardRef):
                return f'{typ.__forward_arg__}Read'
            if isinstance(typ, str):
                return f'{typ}Read'
            if inspect.isclass(typ) and issubclass(typ, JetioModel):
                return f'{typ.__name__}Read'
            return typ

        # --- Generate Read Schema ---
        read_fields = {}
        for field_name, field_type in all_annotations.items():
            if field_name.startswith('_') or field_name in exclude_from_read:
                continue

            python_type = get_python_type_from_mapped(field_type)
            origin = get_origin(python_type)

            # Exclude "to-many" relationships (lists) to prevent circular recursion overhead.
            if origin is list or origin is List:
                continue

            final_type = resolve_pydantic_type(python_type)
            read_fields[field_name] = (final_type, None)

        # --- Generate Create Schema ---
        create_fields = {}
        server_side_fields = {'id', 'created_at', 'updated_at', 'hashed_password', 'password_hash', 'url_slug'}
        
        for k, v in all_annotations.items():
            attr_value = None
            for base in cls.__mro__:
                if k in base.__dict__:
                    attr_value = base.__dict__[k]
                    break
            
            has_server_default = hasattr(attr_value, 'default') and attr_value.default is not None

            # Determine if field is a relationship
            is_relationship = False
            py_type_for_check = get_python_type_from_mapped(v)
            type_origin = get_origin(py_type_for_check)
            type_args = get_args(py_type_for_check)

            core_type = None
            if type_origin in (list, List) and type_args:
                core_type = type_args[0]
            elif type_origin is Union and type_args:
                non_none_args = [t for t in type_args if t is not type(None)]
                if len(non_none_args) == 1:
                    core_type = non_none_args[0]
            else:
                core_type = py_type_for_check

            if core_type and (isinstance(core_type, ForwardRef) or (inspect.isclass(core_type) and issubclass(core_type, JetioModel))):
                is_relationship = True

            # Filter fields for creation: exclude server-side fields and relationships.
            if not k.startswith('_') and k not in server_side_fields and not has_server_default and not is_relationship:
                python_type = get_python_type_from_mapped(v)
                is_optional = get_origin(python_type) is Union and type(None) in get_args(python_type)
                
                if is_optional:
                    create_fields[k] = (python_type, None)
                else:
                    create_fields[k] = (python_type, ...)

        # Create Pydantic models
        module = sys.modules[cls.__module__]
        pydantic_read_model = create_model(
            f"{name}Read", 
            **read_fields, 
            __config__=pydantic_config,
            __module__=module.__name__
        )
        pydantic_create_model = create_model(
            f"{name}Create", 
            **create_fields, 
            __config__=pydantic_config,
            __module__=module.__name__
        )
        
        # Attach models to module and class
        setattr(module, pydantic_read_model.__name__, pydantic_read_model)
        setattr(module, pydantic_create_model.__name__, pydantic_create_model)
        setattr(cls, '__pydantic_read_model__', pydantic_read_model)
        setattr(cls, '__pydantic_create_model__', pydantic_create_model)

        if cls not in _model_registry:
            _model_registry.append(cls)


class JetioModel(Base, metaclass=ModelMetaclass):
    """
    The base model for all database tables in a Jetio application.

    Inheritance enables automatic Pydantic schema generation for API
    validation and serialization.
    """
    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True)

    def to_dict(self):
        """Serializes the model to a dictionary using the auto-generated Read schema."""
        return self.__pydantic_read_model__.model_validate(self).model_dump()
