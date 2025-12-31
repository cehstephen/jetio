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
jetio.orm
=========

Async SQLAlchemy integration and model utilities for Jetio.

This module provides:
- the SQLAlchemy async engine and session factory used by Jetio
- a :class:`~jetio.orm.JetioModel` base class for declarative models
- a :class:`~jetio.orm.ModelMetaclass` that auto-generates Pydantic schemas

Auto-generated Pydantic schemas
-------------------------------
For every concrete model that inherits from :class:`~jetio.orm.JetioModel`,
Jetio generates and attaches:

- ``<ModelName>Read`` (``__pydantic_read_model__``):
  Used for serializing ORM instances in API responses.

- ``<ModelName>Create`` (``__pydantic_create_model__``):
  Used for validating request bodies on create/update operations.

Schema generation rules (high level)
------------------------------------
Read schema:
- includes columns and "to-one" relationships
- excludes private fields (names starting with ``_``)
- excludes relationships that are collections (``List[...]``) to avoid recursion
- respects ``API.exclude_from_read`` if defined on the model

Create schema:
- excludes server-managed fields (e.g. ``id``, timestamps, password hashes)
- excludes relationships (foreign relationships are typically set via IDs/logic)
- excludes fields that have a server-side default
- required/optional is inferred from typing (``Optional[...]`` fields are optional)

Notes:
- Models are registered in ``_model_registry`` for OpenAPI generation.
- Forward references and relationships are represented using read-schema names
  (e.g. ``"UserRead"``) to keep schemas consistent and serializable.
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
    """Declare a SQLAlchemy relationship with Jetio's public API surface.

    This is a thin wrapper around :func:`sqlalchemy.orm.relationship` so Jetio can
    expose a consistent import path (``jetio.orm.relationship``) for applications.

    Returns:
        sqlalchemy.orm.Relationship: SQLAlchemy relationship descriptor.
    """

    return sa_relationship(*args, **kwargs)


class ModelMetaclass(type(Base)):
    """Metaclass that generates Pydantic schemas from SQLAlchemy model annotations.

    Jetio uses a metaclass to reduce boilerplate for API validation and output
    serialization. When you define a model by inheriting :class:`~jetio.orm.JetioModel`,
    Jetio inspects the model's type annotations and generates two Pydantic models:

    - ``<ModelName>Read``:
      A schema suitable for API responses (serialization). Includes "to-one"
      relationships and excludes relationship collections (``List[...]``).

    - ``<ModelName>Create``:
      A schema suitable for request validation (create/update). Excludes server-managed
      fields, server defaults, and relationship fields.

    Naming:
        If ``__tablename__`` is not defined, Jetio uses a simple pluralization rule:
        ``User`` -> ``users``.

    Customization:
        A model may define an inner ``API`` class with:

        - ``exclude_from_read``: a list of attribute names to omit from the read schema.

    Notes:
        - Generated schemas are attached to both the module and the model class as:
          ``__pydantic_read_model__`` and ``__pydantic_create_model__``.
        - Each model class is added to ``_model_registry`` for OpenAPI generation.
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
            """Extract the declared Python type from a SQLAlchemy ``Mapped[T]`` annotation.

            Args:
                mapped_type: The annotation value from ``__annotations__``.

            Returns:
                The inner Python type ``T`` if the annotation is ``Mapped[T]``,
                otherwise returns the original annotation.
            """

            if get_origin(mapped_type) is Mapped:
                return get_args(mapped_type)[0]
            return mapped_type

        def resolve_pydantic_type(typ):
            """Resolve ORM/relationship types into Pydantic-friendly schema types.

            This normalizes relationship targets into *read schema* names
            (e.g. ``User`` -> ``"UserRead"``) and handles forward references.

            Args:
                typ: A type annotation (possibly ``Optional``, ``Union``, ``ForwardRef``).

            Returns:
                A type or schema-name string compatible with ``pydantic.create_model``.
            """

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
    """Base class for Jetio SQLAlchemy models.

    Inherit from ``JetioModel`` to get:
    - a default integer primary key ``id``
    - automatic table naming (if ``__tablename__`` is not provided)
    - automatic generation of Pydantic schemas:
      ``__pydantic_read_model__`` and ``__pydantic_create_model__``
    - inclusion in Jetio's model registry for OpenAPI docs

    Example:
        ```python
        class User(JetioModel):
            username: Mapped[str] = mapped_column(unique=True)
            email: Mapped[str]
        ```

    Customizing schema output:
        ```python
        class User(JetioModel):
            class API:
                exclude_from_read = ["hashed_password"]
        ```

    Notes:
        Relationship collections (e.g. ``List[Post]``) are excluded from read schemas
        by default to avoid heavy recursion and circular schemas.
    """

    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True)

    def to_dict(self):
        """Serialize this model instance using its auto-generated read schema.

        Returns:
            dict: JSON-compatible representation of the ORM object.
        """
        
        return self.__pydantic_read_model__.model_validate(self).model_dump()
