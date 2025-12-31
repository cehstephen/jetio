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
jetio.crud
==========

Automated CRUD route generation for Jetio models.

This module provides :class:`~jetio.crud.CrudRouter`, which generates a complete
set of async Create/Read/Update/Delete endpoints for a SQLAlchemy model that
inherits from :class:`~jetio.orm.JetioModel`.

Generated routes
----------------
By default, the router registers the following endpoints under
``/{prefix}/{model.__tablename__}``:

- ``GET    /resource``           List all items
- ``POST   /resource``           Create an item
- ``GET    /resource/{item_id}`` Retrieve a single item
- ``PUT    /resource/{item_id}`` Update an item (partial updates supported)
- ``DELETE /resource/{item_id}`` Delete an item

Key features
------------
- **Relationship eager-loading** for GET routes via ``selectinload``.
- **Method exclusion** (e.g. disable DELETE) via ``exclude_methods``.
- **Optional security** via dependency injection (``secure=True``).
- **Policy-based security** allowing method-specific dependencies
  (e.g. PUT/DELETE ownership checks).
- **Audit / ownership field auto-fill** when secure, using
  :func:`~jetio.security.resolve_audit_field` and ``DEFAULT_AUDIT_FIELDS``.

Notes
-----
- When ``secure=True``, create payloads automatically exclude audit/ownership
  fields so clients cannot set them; the server sets the resolved field to
  ``user.id``.
- Error responses are returned as :class:`~jetio.framework.JsonResponse` with
  appropriate HTTP status codes.
"""

from typing import List, Optional, Any, Callable, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, create_model

from .framework import JsonResponse, Response, Depends
from .orm import JetioModel
from .security import resolve_audit_field, DEFAULT_AUDIT_FIELDS


class CrudRouter:
    """Generate and register CRUD routes for a :class:`~jetio.orm.JetioModel`.

    ``CrudRouter`` builds standard REST endpoints for a given model and attaches
    them to a Jetio application via :meth:`register_routes`.

    The router is designed to be **low-boilerplate** while still supporting:
    relationship eager-loading, optional authentication/authorization, and
    server-controlled audit/ownership fields.

    Examples:
        Basic usage:

        ```python
        app = Jetio()
        CrudRouter(User).register_routes(app)
        ```

        Load relationships on GET routes:

        ```python
        CrudRouter(User, load_relationships=["posts", "profile"]).register_routes(app)
        ```

        Secure all routes with a single dependency:

        ```python
        CrudRouter(
            User,
            secure=True,
            auth_dependency=get_current_user,
        ).register_routes(app)
        ```

        Method-specific security (policy):

        ```python
        CrudRouter(
            User,
            secure=True,
            policy={
                "GET": get_current_user,
                "POST": get_current_user,
                "PUT": owner_or_admin,
                "DELETE": owner_or_admin,
            },
        ).register_routes(app)
        ```

    See Also:
        - :class:`~jetio.orm.JetioModel`
        - :func:`~jetio.security.resolve_audit_field`
    """

    def __init__(
        self,
        model: JetioModel,
        load_relationships: Optional[List[str]] = None,
        exclude_methods: Optional[List[str]] = None,
        secure: bool = False,
        auth_dependency: Optional[Callable] = None,
        audit_fields: Optional[List[str]] = None,
        policy: Optional[Dict[str, Callable]] = None,
    ):
        """Create a CRUD router for a model.

        Args:
            model:
                A model class inheriting from :class:`~jetio.orm.JetioModel`.
                The model must expose Pydantic schema attributes
                (e.g. ``__pydantic_read_model__`` and ``__pydantic_create_model__``)
                as expected by Jetio.
            load_relationships:
                Relationship attribute names to eager-load on GET routes using
                SQLAlchemy ``selectinload``.
            exclude_methods:
                HTTP methods to skip, e.g. ``["DELETE"]`` or ``["POST", "PUT"]``.
                Values are normalized to uppercase.
            secure:
                If ``True``, the registered routes will require authentication via
                dependency injection.
            auth_dependency:
                Base dependency used when ``secure=True`` and no method-level
                ``policy`` exists for a request method (e.g. ``get_current_user``).
            audit_fields:
                Ordered list of field names to treat as audit/ownership fields.
                When secure, these fields are removed from the create schema and
                set server-side to ``user.id`` for the resolved audit field.
                Defaults to :data:`~jetio.security.DEFAULT_AUDIT_FIELDS`.
            policy:
                Optional mapping of HTTP method -> dependency callable.
                This overrides ``auth_dependency`` on a per-method basis.
                Example: ``{"PUT": owner_check, "DELETE": owner_check}``.

        Raises:
            ValueError:
                If ``secure=True`` and neither ``auth_dependency`` is provided nor
                the ``policy`` covers all enabled methods (after ``exclude_methods``).
        """

        self.model = model
        self.ReadSchema = model.__pydantic_read_model__
        self.load_relationships = load_relationships or []
        self.exclude_methods = [m.upper() for m in exclude_methods] if exclude_methods else []
        self.secure = secure
        self.auth_dependency = auth_dependency

        # Normalize policy keys to uppercase
        self.policy: Dict[str, Callable] = {}
        if policy:
            for k, v in policy.items():
                self.policy[str(k).upper()] = v

        # If secure, require a base auth_dependency OR policy covering all enabled methods.
        if self.secure:
            enabled_methods = set(["GET", "POST", "PUT", "DELETE"]) - set(self.exclude_methods)
            covered_by_policy = enabled_methods.issubset(set(self.policy.keys()))
            if not self.auth_dependency and not covered_by_policy:
                raise ValueError(
                    "When 'secure' is True, provide 'auth_dependency' or a 'policy' that covers "
                    "all enabled methods (after exclude_methods)."
                )

        # Audit fields: developer override or framework defaults
        self.audit_fields = audit_fields if audit_fields is not None else list(DEFAULT_AUDIT_FIELDS)

        # Dynamic schema generation
        base_create_schema = model.__pydantic_create_model__

        if self.secure:
            # Exclude only intended audit fields (auto-filled server-side).
            fields = {
                name: (field.annotation, field.default)
                for name, field in base_create_schema.model_fields.items()
                if name not in self.audit_fields
            }
            self.CreateSchema = create_model(
                "%sSecureCreate" % self.model.__name__,
                **fields,
                __config__=base_create_schema.model_config,
            )
        else:
            self.CreateSchema = base_create_schema

        self.UpdateSchema = self.CreateSchema

        # Resolve once for speed/consistency
        self._audit_field = resolve_audit_field(self.model, self.audit_fields)

    # --- Helpers ---

    def _dep_for(self, method: str) -> Optional[Callable]:
        """
        Returns the dependency for a given HTTP method:
        - if `policy` provides one, use it
        - else fall back to `auth_dependency`
        """
        method = str(method).upper()
        if method in self.policy:
            return self.policy[method]
        return self.auth_dependency

    # --- Internal CRUD Logic ---

    async def _get_all(self, db: AsyncSession) -> JsonResponse:
        query = select(self.model)
        if self.load_relationships:
            options = [selectinload(getattr(self.model, rel)) for rel in self.load_relationships]
            query = query.options(*options)

        result = await db.execute(query)
        items = result.unique().scalars().all()
        data = [
            self.ReadSchema.model_validate(item, from_attributes=True).model_dump(mode="json")
            for item in items
        ]
        return JsonResponse(data)

    async def _create(self, data: BaseModel, db: AsyncSession, user: Optional[Any] = None) -> JetioModel:
        item_data = data.model_dump()

        # Automatic ownership assignment (secure overwrite)
        if user and self._audit_field:
            item_data[self._audit_field] = user.id

        new_item = self.model(**item_data)
        db.add(new_item)
        await db.flush()

        new_item_id = new_item.id
        await db.commit()

        return await self._get_one(new_item_id, db)

    async def _get_one(self, item_id: int, db: AsyncSession) -> Optional[JetioModel]:
        query = select(self.model).where(self.model.id == item_id)
        if self.load_relationships:
            options = [selectinload(getattr(self.model, rel)) for rel in self.load_relationships]
            query = query.options(*options)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _update(self, item_id: int, data: BaseModel, db: AsyncSession) -> Optional[JetioModel]:
        item = await db.get(self.model, item_id)
        if not item:
            return None

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)

        await db.commit()
        return await self._get_one(item_id, db)

    async def _delete(self, item_id: int, db: AsyncSession) -> JsonResponse:
        item = await db.get(self.model, item_id)
        if not item:
            return JsonResponse({"error": "%s not found" % self.model.__name__}, status_code=404)
        await db.delete(item)
        await db.commit()
        return Response(status_code=204)

    # --- Route Registration Logic ---

    def register_routes(self, app, prefix: str = ""):
        model_name_plural = self.model.__tablename__

        # Ensure exactly one leading slash, and correct joining with prefix
        base_path = (prefix.rstrip("/") + "/" + model_name_plural).strip()
        if not base_path.startswith("/"):
            base_path = "/" + base_path

        # --- Public Handlers ---

        async def get_all(db: AsyncSession):
            return await self._get_all(db)

        async def create(data: self.CreateSchema, db: AsyncSession, user: Optional[Any] = None):
            created_item = await self._create(data, db, user=user)
            return self.ReadSchema.model_validate(created_item, from_attributes=True)

        async def get_one(item_id: int, db: AsyncSession):
            orm_item = await self._get_one(item_id, db)
            if not orm_item:
                return JsonResponse({"error": "%s not found" % self.model.__name__}, status_code=404)
            return self.ReadSchema.model_validate(orm_item, from_attributes=True)

        async def update(item_id: int, data: self.UpdateSchema, db: AsyncSession):
            updated_item = await self._update(item_id, data, db)
            if not updated_item:
                return JsonResponse({"error": "%s not found" % self.model.__name__}, status_code=404)
            return self.ReadSchema.model_validate(updated_item, from_attributes=True)

        async def delete(item_id: int, db: AsyncSession):
            return await self._delete(item_id, db)

        # --- Secure Wrappers (policy-aware) ---

        async def secure_get_all(db: AsyncSession, user: Any = Depends(self._dep_for("GET"))):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await get_all(db)

        async def secure_create(data: self.CreateSchema, db: AsyncSession, user: Any = Depends(self._dep_for("POST"))):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await create(data, db, user=user)

        async def secure_get_one(item_id: int, db: AsyncSession, user: Any = Depends(self._dep_for("GET"))):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await get_one(item_id, db)

        async def secure_update(item_id: int, data: self.UpdateSchema, db: AsyncSession, user: Any = Depends(self._dep_for("PUT"))):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await update(item_id, data, db)

        async def secure_delete(item_id: int, db: AsyncSession, user: Any = Depends(self._dep_for("DELETE"))):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await delete(item_id, db)

        # --- Select Handlers ---

        get_all_handler = secure_get_all if self.secure else get_all
        create_handler = secure_create if self.secure else create
        get_one_handler = secure_get_one if self.secure else get_one
        update_handler = secure_update if self.secure else update
        delete_handler = secure_delete if self.secure else delete

        # --- Register Routes ---
        if "GET" not in self.exclude_methods:
            app.route(base_path, methods=["GET"])(get_all_handler)
            app.route("%s/{item_id:int}" % base_path, methods=["GET"])(get_one_handler)

        if "POST" not in self.exclude_methods:
            app.route(base_path, methods=["POST"])(create_handler)

        if "PUT" not in self.exclude_methods:
            app.route("%s/{item_id:int}" % base_path, methods=["PUT"])(update_handler)

        if "DELETE" not in self.exclude_methods:
            app.route("%s/{item_id:int}" % base_path, methods=["DELETE"])(delete_handler)
