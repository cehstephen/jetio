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
jetio.framework
===============

Core primitives for the Jetio web framework.

This module contains the main :class:`~jetio.framework.Jetio` application class,
plus foundational HTTP types (:class:`~jetio.framework.Request`,
:class:`~jetio.framework.Response`, :class:`~jetio.framework.JsonResponse`)
and a lightweight dependency injection marker (:class:`~jetio.framework.Depends`).

Jetio is an ASGI application:
- Define routes with :meth:`~jetio.framework.Jetio.route`
- Resolve dependencies via :class:`~jetio.framework.Depends`
- Return either :class:`~jetio.framework.Response` (manual) or any JSON-serializable
  object (auto-wrapped into :class:`~jetio.framework.JsonResponse`)

Notes:
- Request body parsing supports JSON and multipart form data.
- A database session (SQLAlchemy :class:`~sqlalchemy.ext.asyncio.AsyncSession`) is
  created per request and closed automatically.
"""

import json
import inspect
import asyncio
import uvicorn
import logging
import re
from jinja2 import Environment, FileSystemLoader
from http.cookies import SimpleCookie
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from starlette.formparsers import MultiPartParser
from starlette.datastructures import UploadFile, Headers
from starlette.exceptions import HTTPException as StarletteHTTPException

from .orm import SessionLocal, JetioModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class Depends:
    """Dependency injection marker for Jetio route handlers.

    Use :class:`Depends` as a default value for a route handler parameter to
    indicate that the framework should call the given dependency and inject its
    return value.

    Dependencies may declare any of the following parameters and Jetio will pass
    them if available:
    - ``request``: :class:`~jetio.framework.Request`
    - ``db``: :class:`~sqlalchemy.ext.asyncio.AsyncSession`
    - any path parameters **if** the dependency function accepts them (either via
      named parameters or ``**kwargs``)

    Examples:
        A basic dependency:

        ```python
        async def get_current_user(request: Request):
            ...
            return user
        ```

        Inject it into a handler:

        ```python
        @app.route("/profile")
        async def profile(user = Depends(get_current_user)):
            return {"username": user.username}
        ```

    Args:
        dependency: The callable to resolve (sync or async).
    """

    def __init__(self, dependency: callable):
        self.dependency = dependency


class Request:
    """"Incoming HTTP request wrapper.

    Provides convenient access to method, path, headers, cookies and body
    parsing utilities.

    Attributes:
        method: HTTP method (e.g. ``"GET"``).
        path: URL path adjusted for ``root_path`` when deployed under a sub-path.
        headers: Parsed ASGI headers (:class:`starlette.datastructures.Headers`).
        cookies: Parsed cookies (:class:`http.cookies.SimpleCookie`).
        user: Optional user context (framework/userland can set this).
        client: ``(host, port)`` tuple of the connecting client, or ``None``
            if the ASGI server didn't provide one. This is the direct TCP
            peer -- behind a reverse proxy it's the proxy's address, not the
            original client's; consult an ``X-Forwarded-For``-style header
            for that instead.

    Notes:
        - :meth:`json` is tolerant and returns ``{}`` on invalid JSON.
        - :meth:`form` parses multipart form data via Starlette's parser.
    """

    def __init__(self, scope, receive):
        self._scope = scope
        self._receive = receive
        self._stream_consumed = False
        self._form = None
        self._json = None
        self.method = scope['method']

        # Handle root_path for deployments in a sub-directory (e.g., cPanel).
        root_path = scope.get("root_path", "")
        path = scope.get("path", "/")
        if root_path and path.startswith(root_path):
            self.path = path[len(root_path):] or "/"
        else:
            self.path = path

        self.headers = Headers(scope=scope)
        self.cookies = SimpleCookie(self.headers.get('cookie', ''))
        self.user = None
        self.client = scope.get("client")

    async def stream(self):
        """Yield request body chunks as bytes.

        Returns:
            An async iterator of ``bytes`` chunks.
        """
        if self._stream_consumed:
            yield b''
            return
        self._stream_consumed = True
        while True:
            message = await self._receive()
            if message['type'] == 'http.request':
                yield message.get('body', b'')
                if not message.get('more_body', False):
                    break
        yield b''

    async def body(self) -> bytes:
        """Return the full request body as bytes (cached)."""
        if hasattr(self, '_body'):
            return self._body
        chunks = [chunk async for chunk in self.stream()]
        self._body = b"".join(chunks)
        return self._body

    async def json(self):
        """Parse and return the request body as JSON (cached).

        Returns:
            dict: Parsed JSON object. Returns ``{}`` if empty or invalid.
        """
        if self._json is None:
            body_bytes = await self.body()
            try:
                self._json = json.loads(body_bytes) if body_bytes else {}
            except (json.JSONDecodeError, TypeError):
                self._json = {}
        return self._json

    async def form(self):
        """Parse and return multipart form data (cached)."""
        if self._form is not None:
            return self._form
        parser = MultiPartParser(headers=self.headers, stream=self.stream())
        self._form = await parser.parse()
        return self._form


class Response:
    """Outgoing HTTP response.

    Args:
        body: Response body (``str`` or ``bytes``).
        status_code: HTTP status code.
        content_type: MIME type for Content-Type header.
        headers: Optional headers dict.

    Notes:
        - Strings are UTF-8 encoded automatically.
        - Content-Length is set automatically.
    """

    def __init__(self, body='', status_code=200, content_type='text/html', headers=None):
        if isinstance(body, str):
            self.body = body.encode('utf-8')
        else:
            self.body = body  # Assume bytes

        self.status_code = status_code
        self.headers = headers or {}
        self.headers.setdefault('Content-Type', content_type)
        self.headers.setdefault('Content-Length', str(len(self.body)))

    async def __call__(self, scope, receive, send):
        """The ASGI callable interface."""
        await send({
            'type': 'http.response.start',
            'status': self.status_code,
            'headers': [[k.encode(), v.encode()] for k, v in self.headers.items()]
        })
        await send({'type': 'http.response.body', 'body': self.body})


class JsonResponse(Response):
    """JSON response helper.

    Serializes Python objects to JSON and sets ``Content-Type: application/json``.

    Supports:
    - Pydantic models (serialized via ``model_dump(mode="json")``)
    - Jetio ORM models (:class:`~jetio.orm.JetioModel`) serialized via their
      auto-generated read schema (``__pydantic_read_model__``)

    Args:
        data: Any JSON-serializable object.
        status_code: HTTP status code (default 200).
    """

    def __init__(self, data, status_code=200, **kwargs):
        def pydantic_encoder(obj):
            if isinstance(obj, BaseModel):
                return obj.model_dump(mode='json')
            # Serialize SQLAlchemy models via their auto-generated Pydantic schemas
            if isinstance(obj, JetioModel):
                return obj.__pydantic_read_model__.model_validate(obj, from_attributes=True).model_dump(mode='json')
            return str(obj)
        
        json_body = json.dumps(data, indent=2, default=pydantic_encoder)
        super().__init__(body=json_body, status_code=status_code, content_type='application/json', **kwargs)


class BaseMiddleware:
    """Base class for creating custom middleware."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)


# --- Exceptions ---

class MethodNotAllowedError(Exception):
    """Raised when a request is made to a valid path with an invalid HTTP method."""
    pass

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class HttpValidationError(Exception):
    """Raised when request body validation fails.

    This is thrown internally when Pydantic validation fails for a handler
    parameter annotated with a Pydantic model. Jetio converts it to a 422 JSON
    response in :meth:`Jetio.handle_request`.
    """

    def __init__(self, errors):
        self.errors = errors


def _print_startup_banner(host, port):
    """Print the run() startup message, tolerating terminals that can't
    encode the emoji.

    Some terminals -- notably the default Windows console, which decodes
    stdout as cp1252 unless ``PYTHONIOENCODING=utf-8`` is set -- raise
    ``UnicodeEncodeError`` on the emoji, which would otherwise crash
    :meth:`Jetio.run` before the server even starts.
    """
    try:
        print(f"🚀 Jetio server running on http://{host}:{port}")
    except UnicodeEncodeError:
        print(f"Jetio server running on http://{host}:{port}")


class Jetio:
    """Jetio application object (ASGI).

    ``Jetio`` registers routes, resolves dependencies, manages a per-request
    database session, and returns ASGI responses.

    Examples:
        Minimal app:

        ```python
        app = Jetio()

        @app.route("/")
        async def home():
            return {"hello": "world"}
        ```

        Run with Uvicorn:

        ```python
        if __name__ == "__main__":
            app.run(host="127.0.0.1", port=8000)
        ```

    Attributes:
        title: OpenAPI title (also used by Swagger UI).
        version: OpenAPI version.
        routes: Registered routes.
    """

    def __init__(self, title: str = "Jetio API", version: str = "1.0.0", template_folder='templates'):
        self.routes = []
        self.title = title
        self.version = version
        self.template_env = Environment(loader=FileSystemLoader(template_folder), autoescape=True)
        self.error_handlers = {}
        self.startup_handlers = []
        self.shutdown_handlers = []
        self.app = self.handle_request

    def add_middleware(self, middleware_cls, **kwargs):
        """
        Adds a middleware to the application stack.
        Middleware is processed in reverse order of addition.
        """
        self.app = middleware_cls(self.app, **kwargs)

    def add_error_page(self, status_code: int, template_name: str):
        """Registers a custom HTML template for a specific HTTP error status code."""
        self.error_handlers[status_code] = template_name

    def route(self, path, methods=None):
        """Register a route handler.

        Args:
            path: URL path pattern. Supports placeholders like ``{user_id:int}``.
            methods: Allowed HTTP methods. Defaults to ``["GET"]``.

        Returns:
            A decorator that registers the handler and returns it.

        Notes:
            The handler docstring's *first line* is used as the OpenAPI summary
            in :func:`jetio.openapi.generate_openapi_schema`.
        """

        def wrapper(handler):
            self.routes.append(Route(path, handler, methods or ['GET']))
            return handler
        return wrapper

    def on_event(self, event_type: str):
        """A decorator to register a startup or shutdown event handler."""
        def wrapper(handler):
            if event_type == "startup":
                self.startup_handlers.append(handler)
            elif event_type == "shutdown":
                self.shutdown_handlers.append(handler)
            return handler
        return wrapper

    async def __call__(self, scope, receive, send):
        """The main ASGI entry point for the application."""
        # Guard against WSGI server execution without an adapter
        if not isinstance(scope, dict) or 'type' not in scope:
            if isinstance(scope, dict) and 'wsgi.version' in scope:
                raise TypeError(
                    "This is an ASGI application, but it was called by a WSGI server.\n"
                    "Please check your server's entry point (e.g., passenger_wsgi.py) "
                    "and ensure you are using an ASGI-to-WSGI adapter like 'a2wsgi'."
                )
            raise TypeError("Invalid ASGI scope provided to application. Expected a dictionary with a 'type' key.")

        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    try:
                        for handler in self.startup_handlers:
                            await handler()
                        await send({'type': 'lifespan.startup.complete'})
                    except Exception as e:
                        log.exception("Error during startup.")
                        await send({'type': 'lifespan.startup.failed', 'message': str(e)})
                elif message['type'] == 'lifespan.shutdown':
                    try:
                        for handler in self.shutdown_handlers:
                            await handler()
                        await send({'type': 'lifespan.shutdown.complete'})
                    except Exception as e:
                        log.exception("Error during shutdown.")
                        await send({'type': 'lifespan.shutdown.failed', 'message': str(e)})
                    return
        elif scope['type'] == 'http':
            await self.app(scope, receive, send)

    async def handle_request(self, scope, receive, send):
        """Handle an incoming HTTP request.

        Flow:
        1) Create a per-request database session
        2) Match a route by path + method
        3) Resolve handler arguments (path params, Request, db session, Pydantic body)
        4) Resolve dependencies declared via :class:`Depends`
        5) Call the handler (async or sync)
        6) Convert result to :class:`Response` / :class:`JsonResponse`
        7) Handle exceptions and close the DB session

        Returns:
            None. Sends an ASGI response via ``send``.
        """

        db_session = SessionLocal()
        try:
            request = Request(scope, receive)
            handler, path_kwargs = self.find_handler(request.path, request.method)

            # --- Dependency Injection and Argument Resolution ---
            sig = inspect.signature(handler)
            handler_kwargs = {}
            for name, param in sig.parameters.items():
                if name in path_kwargs:
                    param_type = param.annotation
                    if param_type is not inspect.Parameter.empty:
                        handler_kwargs[name] = param_type(path_kwargs[name])
                    else:
                        handler_kwargs[name] = path_kwargs[name]
                elif param.annotation is Request:
                    handler_kwargs[name] = request
                elif param.annotation is AsyncSession:
                    handler_kwargs[name] = db_session
                elif isinstance(param.annotation, type) and issubclass(param.annotation, BaseModel):
                    try:
                        request_json = await request.json()
                        handler_kwargs[name] = param.annotation(**request_json)
                    except ValidationError as e:
                        raise HttpValidationError(e.errors())
                elif isinstance(param.default, Depends):
                    dep_func = param.default.dependency
                    dep_sig = inspect.signature(dep_func)
                    sub_dep_kwargs = {}

                    # Pass request/db if requested (existing behavior)
                    if 'request' in dep_sig.parameters:
                        sub_dep_kwargs['request'] = request
                    if 'db' in dep_sig.parameters:
                        sub_dep_kwargs['db'] = db_session

                    # Now supports path param - pass path params if the dependency accepts them
                    dep_params = dep_sig.parameters

                    accepts_kwargs = any(
                        p.kind == inspect.Parameter.VAR_KEYWORD
                        for p in dep_params.values()
                    )

                    if accepts_kwargs:
                        # If dependency has **kwargs, give it all path params
                        sub_dep_kwargs.update(path_kwargs)
                    else:
                        # Otherwise only pass named matches (safe / backwards compatible)
                        for k, v in path_kwargs.items():
                            if k in dep_params:
                                ann = dep_params[k].annotation
                                if ann is not inspect._empty:
                                    try:
                                        sub_dep_kwargs[k] = ann(v)
                                    except Exception:
                                        sub_dep_kwargs[k] = v
                                else:
                                    sub_dep_kwargs[k] = v

                    handler_kwargs[name] = await dep_func(**sub_dep_kwargs)


            # --- Call the Handler ---
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**handler_kwargs)
            else:
                result = handler(**handler_kwargs)

            # --- Prepare the Response ---
            if isinstance(result, Response):
                response = result
            else:
                response = JsonResponse(result)

        # --- Exception Handling ---
        except HttpValidationError as e:
            response = JsonResponse({"detail": e.errors}, status_code=422)

        except StarletteHTTPException as e:
            response = JsonResponse({"detail": e.detail}, status_code=e.status_code, headers=e.headers)

        except AuthenticationError:
            response = JsonResponse({"error": "Authentication required"}, status_code=401)

        except FileNotFoundError:
            if 404 in self.error_handlers:
                template = self.template_env.get_template(self.error_handlers[404])
                html_content = template.render(path=scope.get("path", "unknown"))
                response = Response(html_content, status_code=404)
            else:
                response = Response("<h1>404 Not Found</h1>", status_code=404)

        except MethodNotAllowedError:
            if 405 in self.error_handlers:
                template = self.template_env.get_template(self.error_handlers[405])
                html_content = template.render(path=scope.get("path", "unknown"), method=scope.get("method"))
                response = Response(html_content, status_code=405)
            else:
                response = Response("<h1>405 Method Not Allowed</h1>", status_code=405)

        except Exception as e:
            log.exception(f"Unhandled exception on path {scope.get('path')}")
            if 500 in self.error_handlers:
                template = self.template_env.get_template(self.error_handlers[500])
                html_content = template.render(path=scope.get("path", "unknown"), error=e)
                response = Response(html_content, status_code=500)
            else:
                response = Response("<h1>500 Internal Server Error</h1>", status_code=500)

        finally:
            await db_session.close()

        await response(scope, receive, send)

    def find_handler(self, path, method):
        """Find a matching handler for a path and HTTP method.

        Args:
            path: Request path (already adjusted for ``root_path``).
            method: HTTP method (e.g. ``"GET"``).

        Returns:
            Tuple[callable, dict]: ``(handler, path_kwargs)``.

        Raises:
            FileNotFoundError: If no route matches the path.
            MethodNotAllowedError: If path matches but method is not allowed.
        """

        path_found = False
        for route in self.routes:
            # Convert path format like "/users/{id:int}" to a regex
            pattern = "^" + re.sub(r'\{(\w+)(?::\w+)?\}', r'(?P<\1>[^/]+)', route.path) + "$"
            match = re.match(pattern, path)

            if match:
                path_found = True
                if method in route.methods:
                    return route.handler, match.groupdict()

        if path_found:
            raise MethodNotAllowedError()
        raise FileNotFoundError()

    def run(self, host='127.0.0.1', port=8000):
        """Run the app with Uvicorn.

        This rebuilds forward references for any registered Jetio models' Pydantic
        schemas before starting.

        Args:
            host: Bind host.
            port: Bind port.
        """

        # Import here to avoid circular dependency issues at module load time.
        from .orm import _model_registry
        for model in _model_registry:
            if hasattr(model, '__pydantic_read_model__'):
                model.__pydantic_read_model__.model_rebuild()
            if hasattr(model, '__pydantic_create_model__'):
                model.__pydantic_create_model__.model_rebuild()

        _print_startup_banner(host, port)
        uvicorn.run(self, host=host, port=port)


class Route:
    """A registered application route.

    Attributes:
        path: Route path template (Jetio syntax, e.g. ``"/users/{id:int}"``).
        handler: Callable invoked when the route matches.
        methods: Allowed HTTP methods (e.g. ``["GET", "POST"]``).
    """
    
    def __init__(self, path, handler, methods):
        self.path, self.handler, self.methods = path, handler, methods
