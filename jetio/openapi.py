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
jetio.openapi
=============

OpenAPI (Swagger) schema generation for Jetio.

Jetio generates an OpenAPI 3.0 schema by inspecting:
- registered routes (path + methods)
- route handler signatures (path parameters, request body models)
- return annotations (to infer response schemas)
- handler docstrings (first line used as operation summary)

Use :func:`add_swagger_ui` to mount:
- ``/openapi.json``: schema document
- ``/docs``: Swagger UI pointing to the schema
"""

import inspect
import re
from typing import List, get_args, get_origin

from pydantic import BaseModel
from pydantic.json_schema import model_json_schema

from .framework import Jetio, JsonResponse, Request, Response
from .orm import _model_registry


def _generate_and_add_schema(model, schema_store):
    """Generate JSON schema for a Pydantic model and store it in components.

    Args:
        model: A Pydantic BaseModel subclass.
        schema_store: Dict that becomes ``#/components/schemas``.

    Returns:
        Optional[str]: The schema name added/used, or ``None`` if not applicable.

    Notes:
        Pydantic v2 may emit nested ``$defs``. This function flattens those into
        the main schema store for easier referencing.
    """
    if not model or not inspect.isclass(model) or not issubclass(model, BaseModel):
        return None
        
    schema_name = model.__name__
    if schema_name not in schema_store:
        model_schema = model_json_schema(model, ref_template="#/components/schemas/{model}")
        
        # Flatten Pydantic v2 nested '$defs' into the main schema store.
        if '$defs' in model_schema:
            for def_name, def_schema in model_schema['$defs'].items():
                if def_name not in schema_store:
                    schema_store[def_name] = def_schema
            del model_schema['$defs']

        schema_store[schema_name] = model_schema
    
    return schema_name


def generate_openapi_schema(app: Jetio):
    """Generate an OpenAPI 3.0 schema for a Jetio application.

    The generator inspects:
    - all registered Jetio models (from the ORM registry) to pre-register schemas
    - all routes and handler signatures to build the ``paths`` section

    Path conversion:
        Jetio allows typed path params like ``/users/{id:int}``.
        OpenAPI uses ``/users/{id}``; Jetio types are removed for schema output.

    Request bodies:
        If a handler parameter is annotated with a Pydantic model, it is treated
        as a JSON request body.

    Responses:
        If the handler has a return annotation, Jetio attempts to generate a
        matching JSON schema for 200/201 responses.

    Args:
        app: Jetio application instance.

    Returns:
        dict: OpenAPI specification document.
    """
    schema = {
        "openapi": "3.0.0",
        "info": {
            "title": app.title,
            "version": app.version,
            "description": "Auto-generated API documentation by the Jetio Framework."
        },
        "paths": {},
        "components": {"schemas": {}}
    }
    schema_store = schema['components']['schemas']

    # Generate schemas for all registered JetioModels
    for model in _model_registry:
        if hasattr(model, '__pydantic_read_model__'):
            _generate_and_add_schema(model.__pydantic_read_model__, schema_store)
        if hasattr(model, '__pydantic_create_model__'):
            _generate_and_add_schema(model.__pydantic_create_model__, schema_store)
        
    # Build 'paths' section from registered routes
    for route in app.routes:
        handler = route.handler
        sig = inspect.signature(handler)
        
        # Convert custom path params (e.g., /users/{id:int}) to standard OpenAPI format (/users/{id})
        openapi_path = re.sub(r':\w+}', '}', route.path)

        if openapi_path not in schema['paths']:
            schema['paths'][openapi_path] = {}

        for method in route.methods:
            method_lower = method.lower()
            operation = {
                "summary": (inspect.getdoc(handler) or "No summary").split('\n')[0],
                "tags": [openapi_path.strip('/').split('/')[0].title()],
                "responses": {"200": {"description": "Successful Response"}}
            }

            # --- Parameters (Path and Body) ---
            path_param_names = re.findall(r'{(\w+)', openapi_path)
            operation['parameters'] = []

            for name, param in sig.parameters.items():
                if name in path_param_names:
                    operation['parameters'].append({
                        "name": name, 
                        "in": "path", 
                        "required": True,
                        "schema": {"type": "integer" if param.annotation is int else "string"}
                    })
                elif isinstance(param.annotation, type) and issubclass(param.annotation, BaseModel):
                    schema_name = _generate_and_add_schema(param.annotation, schema_store)
                    if schema_name:
                        operation['requestBody'] = {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}}
                        }
            
            # --- Responses ---
            if sig.return_annotation != inspect.Signature.empty:
                response_model = sig.return_annotation
                status_code = "201" if method == "POST" else "200"
                response_schema = {}

                origin = get_origin(response_model)
                if origin is list or origin is List:
                    item_model = get_args(response_model)[0]
                    if hasattr(item_model, '__pydantic_read_model__'):
                        item_model = item_model.__pydantic_read_model__
                    
                    item_schema_name = _generate_and_add_schema(item_model, schema_store)
                    if item_schema_name:
                        response_schema = { "type": "array", "items": {"$ref": f"#/components/schemas/{item_schema_name}"} }
                else:
                    if hasattr(response_model, '__pydantic_read_model__'):
                        response_model = response_model.__pydantic_read_model__
                    
                    schema_name = _generate_and_add_schema(response_model, schema_store)
                    if schema_name:
                        response_schema = {"$ref": f"#/components/schemas/{schema_name}"}

                if response_schema:
                    operation['responses'][status_code] = { 
                        "description": "Successful Response", 
                        "content": {"application/json": {"schema": response_schema}} 
                    }
            
            schema['paths'][openapi_path][method_lower] = operation
    return schema


def add_swagger_ui(app):
    """Mount Swagger UI and OpenAPI schema routes.

    Adds:
        - ``GET /docs``: Swagger UI HTML
        - ``GET /openapi.json``: OpenAPI schema JSON

    Notes:
        Supports sub-path deployments (reverse proxies) by reading ASGI
        ``root_path`` and setting:
        - Swagger UI's schema URL
        - ``servers`` field in the OpenAPI document
    """
    
    @app.route('/docs')
    def swagger_ui(request: Request):
        """Swagger UI page."""
        # Handle sub-directory deployments (e.g., behind reverse proxies)
        root_path = request._scope.get("root_path", "")
        openapi_url = f"{root_path}/openapi.json"

        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>{app.title} - Docs</title>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
            </head>
            <body>
                <div id="swagger-ui"></div>
                <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
                <script>
                    SwaggerUIBundle({{
                        url: "{openapi_url}",
                        dom_id: '#swagger-ui'
                    }})
                </script>
            </body>
        </html>
        """
        return Response(html_content)

    @app.route('/openapi.json')
    def openapi_spec(request: Request):
        """OpenAPI schema JSON."""
        schema = generate_openapi_schema(app)

        # Inject server URL for correct execution behind proxies
        root_path = request._scope.get("root_path", "")
        if root_path:
            schema["servers"] = [{"url": root_path}]

        return JsonResponse(schema)
