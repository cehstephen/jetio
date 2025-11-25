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
Automated CRUD route generation for Jetio models.

This module provides a `CrudRouter` class that can be used to quickly
generate a full set of Create, Read, Update, and Delete (CRUD) API
endpoints for any given SQLAlchemy model that inherits from `JetioModel`.
It supports relationship loading, method exclusion, and optional security
via dependency injection.
"""

from typing import List, Optional, Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, create_model

from .framework import JsonResponse, Response, Depends
from .orm import JetioModel


class CrudRouter:
    """
    A class that takes a JetioModel and automatically generates async CRUD API routes for it.

    This router inspects a `JetioModel` and its associated Pydantic schemas
    to create standard RESTful endpoints. It can be secured by passing `secure=True`
    and providing an `auth_dependency`.
    """
    def __init__(
        self, 
        model: JetioModel, 
        load_relationships: Optional[List[str]] = None, 
        exclude_methods: Optional[List[str]] = None,
        secure: bool = False,
        auth_dependency: Optional[Callable] = None
    ):
        """
        Initializes the CrudRouter.

        Args:
            model: The `JetioModel` class to build CRUD routes for.
            load_relationships: A list of relationship names to eager-load
                on 'GET' requests to prevent N+1 query problems.
            exclude_methods: A list of HTTP methods (e.g., ['DELETE', 'POST'])
                to exclude from route generation.
            secure: If True, all generated routes will be protected by the
                `auth_dependency`.
            auth_dependency: A dependency function (like `get_current_user`) that
                provides the authenticated user. Required if `secure` is True.

        Raises:
            ValueError: If `secure` is True but no `auth_dependency` is provided.
        """
        self.model = model
        self.ReadSchema = model.__pydantic_read_model__
        self.load_relationships = load_relationships or []
        self.exclude_methods = [m.upper() for m in exclude_methods] if exclude_methods else []
        self.secure = secure
        self.auth_dependency = auth_dependency

        if self.secure and not self.auth_dependency:
            raise ValueError("When 'secure' is True, an 'auth_dependency' function must be provided.")

        # Dynamic Pydantic Model Generation for Create/Update
        # If secure, exclude '_id' fields to prevent manual foreign key manipulation.
        base_create_schema = model.__pydantic_create_model__
        
        if self.secure:
            fields = {
                name: (field.annotation, field.default)
                for name, field in base_create_schema.model_fields.items()
                if not name.endswith('_id')
            }
            self.CreateSchema = create_model(
                f'{self.model.__name__}SecureCreate',
                **fields,
                __config__=base_create_schema.model_config
            )
        else:
            self.CreateSchema = base_create_schema
        
        self.UpdateSchema = self.CreateSchema

    # --- Internal CRUD Logic ---

    async def _get_all(self, db: AsyncSession) -> JsonResponse:
        """Fetches all records of the model."""
        query = select(self.model)
        if self.load_relationships:
            options = [selectinload(getattr(self.model, rel)) for rel in self.load_relationships]
            query = query.options(*options)
            
        result = await db.execute(query)
        items = result.unique().scalars().all()
        data = [self.ReadSchema.model_validate(item, from_attributes=True).model_dump(mode='json') for item in items]
        return JsonResponse(data)

    async def _create(self, data: BaseModel, db: AsyncSession, user: Optional[Any] = None) -> JetioModel:
        """Creates a new record in the database."""
        item_data = data.model_dump()
        
        # Automatically assign ownership if user context is available
        if user:
            if hasattr(self.model, 'creator_id'):
                item_data['creator_id'] = user.id
            elif hasattr(self.model, 'author_id'):
                item_data['author_id'] = user.id
        
        new_item = self.model(**item_data)
        db.add(new_item)
        await db.flush()
        new_item_id = new_item.id
        await db.commit()
        
        return await self._get_one(new_item_id, db)

    async def _get_one(self, item_id: int, db: AsyncSession) -> Optional[JetioModel]:
        """Fetches a single record by its ID."""
        query = select(self.model).where(self.model.id == item_id)
        if self.load_relationships:
            options = [selectinload(getattr(self.model, rel)) for rel in self.load_relationships]
            query = query.options(*options)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _update(self, item_id: int, data: BaseModel, db: AsyncSession) -> Optional[JetioModel]:
        """Updates an existing record by its ID."""
        item = await db.get(self.model, item_id)
        if not item:
            return None
        
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        
        await db.commit()
        return await self._get_one(item_id, db)
    
    async def _delete(self, item_id: int, db: AsyncSession) -> JsonResponse:
        """Deletes a record by its ID."""
        item = await db.get(self.model, item_id)
        if not item:
            return JsonResponse({"error": f"{self.model.__name__} not found"}, status_code=404)
        await db.delete(item)
        await db.commit()
        return Response(status_code=204)

    # --- Route Registration Logic ---

    def register_routes(self, app, prefix: str = ""):
        """
        Generates and registers the CRUD routes with the main Jetio application.

        Handlers are defined inside this method to capture `self` and ensure 
        the correct dynamic Pydantic schemas are used for validation.
        """
        model_name_plural = self.model.__tablename__
        base_path = f"{prefix}/{model_name_plural}"

        # --- Public Handlers ---

        async def get_all(db: AsyncSession):
            return await self._get_all(db)

        async def create(data: self.CreateSchema, db: AsyncSession, user: Optional[Any] = None):
            created_item = await self._create(data, db, user=user)
            return self.ReadSchema.model_validate(created_item, from_attributes=True)

        async def get_one(item_id: int, db: AsyncSession):
            orm_item = await self._get_one(item_id, db)
            if not orm_item:
                return JsonResponse({"error": f"{self.model.__name__} not found"}, status_code=404)
            return self.ReadSchema.model_validate(orm_item, from_attributes=True)

        async def update(item_id: int, data: self.UpdateSchema, db: AsyncSession):
            updated_item = await self._update(item_id, data, db)
            if not updated_item:
                return JsonResponse({"error": f"{self.model.__name__} not found"}, status_code=404)
            return self.ReadSchema.model_validate(updated_item, from_attributes=True)

        async def delete(item_id: int, db: AsyncSession):
            return await self._delete(item_id, db)

        # --- Secure Wrappers ---

        async def secure_get_all(db: AsyncSession, user: Any = Depends(self.auth_dependency)):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await get_all(db)

        async def secure_create(data: self.CreateSchema, db: AsyncSession, user: Any = Depends(self.auth_dependency)):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await create(data, db, user=user)

        async def secure_get_one(item_id: int, db: AsyncSession, user: Any = Depends(self.auth_dependency)):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await get_one(item_id, db)

        async def secure_update(item_id: int, data: self.UpdateSchema, db: AsyncSession, user: Any = Depends(self.auth_dependency)):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await update(item_id, data, db)

        async def secure_delete(item_id: int, db: AsyncSession, user: Any = Depends(self.auth_dependency)):
            if not user:
                return JsonResponse({"error": "Authentication required"}, status_code=401)
            return await delete(item_id, db)

        # --- Select and Register Handlers ---

        get_all_handler = secure_get_all if self.secure else get_all
        create_handler = secure_create if self.secure else create
        get_one_handler = secure_get_one if self.secure else get_one
        update_handler = secure_update if self.secure else update
        delete_handler = secure_delete if self.secure else delete

        if "GET" not in self.exclude_methods:
            app.route(base_path, methods=['GET'])(get_all_handler)
            app.route(f"{base_path}/{{item_id:int}}", methods=['GET'])(get_one_handler)
        if "POST" not in self.exclude_methods:
            app.route(base_path, methods=['POST'])(create_handler)
        if "PUT" not in self.exclude_methods:
            app.route(f"{base_path}/{{item_id:int}}", methods=['PUT'])(update_handler)
        if "DELETE" not in self.exclude_methods:
            app.route(f"{base_path}/{{item_id:int}}", methods=['DELETE'])(delete_handler)
