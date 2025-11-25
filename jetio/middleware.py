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

class CORSMiddleware:
    """
    Handles Cross-Origin Resource Sharing (CORS) for the application.
    Allows frontends from different origins to communicate with the API.
    """
    def __init__(self, app, allowed_origins: list = None):
        self.app = app
        self.allowed_origins = allowed_origins or ["*"]

    async def __call__(self, scope, receive, send):
        if scope['method'] == 'OPTIONS':
            response = Response(
                status_code=200,
                content_type="text/plain",
                headers={
                    "Access-Control-Allow-Origin": ", ".join(self.allowed_origins),
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type",
                }
            )
            await response(scope, receive, send)
            return

        async def send_with_cors_headers(message):
            if message['type'] == 'http.response.start':
                headers = dict(message['headers'])
                headers[b"Access-Control-Allow-Origin"] = b", ".join(o.encode() for o in self.allowed_origins)
                message['headers'] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_with_cors_headers)
