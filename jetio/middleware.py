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

from .framework import Response
from typing import Optional

class CORSMiddleware:
    """
    Handles Cross-Origin Resource Sharing (CORS) for the application.
    Allows frontends from different origins to communicate with the API.
    """
    def __init__(self, app, allowed_origins: list = None):
        self.app = app
        self.allowed_origins = allowed_origins or ["*"]

    @staticmethod
    def _get_header(scope, header_name: bytes):
        for key, value in scope.get("headers", []):
            if key.lower() == header_name:
                return value.decode("latin-1")
        return None

    def _resolve_allow_origin(self, request_origin: Optional[str]):
        if "*" in self.allowed_origins:
            return "*"
        if request_origin and request_origin in self.allowed_origins:
            return request_origin
        return None

    def _build_cors_headers(self, scope):
        request_origin = self._get_header(scope, b"origin")
        allow_origin = self._resolve_allow_origin(request_origin)

        request_allow_headers = self._get_header(scope, b"access-control-request-headers")
        allow_headers = request_allow_headers or "Authorization, Content-Type"

        headers = {
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": allow_headers,
        }

        if allow_origin:
            headers["Access-Control-Allow-Origin"] = allow_origin
            if allow_origin != "*":
                headers["Vary"] = "Origin"

        return headers

    @staticmethod
    def _merge_headers(asgi_headers, extra_headers):
        header_map = {name.lower(): [name, value] for name, value in asgi_headers}
        for name, value in extra_headers.items():
            encoded_name = name.encode("latin-1")
            header_map[encoded_name.lower()] = [encoded_name, value.encode("latin-1")]
        return [tuple(pair) for pair in header_map.values()]

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        cors_headers = self._build_cors_headers(scope)

        if scope['method'] == 'OPTIONS':
            response = Response(
                status_code=200,
                content_type="text/plain",
                headers=cors_headers
            )
            await response(scope, receive, send)
            return

        async def send_with_cors_headers(message):
            if message['type'] == 'http.response.start':
                message['headers'] = self._merge_headers(message.get('headers', []), cors_headers)
            await send(message)

        await self.app(scope, receive, send_with_cors_headers)
