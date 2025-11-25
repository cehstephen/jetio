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
Tests for secure, authentication-protected CRUD endpoints.

This module verifies that when a `CrudRouter` is configured with `secure=True`,
its endpoints correctly reject unauthorized requests and grant access to
requests with valid authentication credentials (e.g., a JWT).
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from jetio import (
    Jetio,
    CrudRouter,
    Base,
    engine,
    create_access_token,
    decode_access_token,
    Request,
)

pytestmark = pytest.mark.asyncio

from .models import Report, User

async def get_current_user(request: Request):
    """
    Mock dependency to simulate user authentication.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or payload.get("sub") != "testuser":
        return None
    return User(id=1, username="testuser")


@pytest.fixture
def secure_app():
    """Creates a Jetio app instance with a secure CrudRouter."""
    app = Jetio()

    CrudRouter(
        model=Report,
        secure=True,
        auth_dependency=get_current_user
    ).register_routes(app)
    return app


@pytest_asyncio.fixture
async def secure_client(secure_app):
    """
    Creates an async test client for the secure app.
    Also handles the setup and teardown of the database tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(transport=ASGITransport(app=secure_app), base_url="http://test") as ac:
        yield ac
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_secure_endpoint_unauthorized(secure_client):
    """
    Verifies that a secure endpoint correctly returns a 401 Unauthorized error
    when no authentication token is provided.
    """
    response = await secure_client.get("/reports")
    assert response.status_code == 401
    assert response.json() == {"error": "Authentication required"}


async def test_secure_endpoint_authorized(secure_client):
    """
    Verifies that a secure endpoint can be accessed with a valid token.
    """
    token = create_access_token(data={"sub": "testuser"})
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await secure_client.post("/reports", json={"title": "Secret Report"}, headers=headers)
    assert create_response.status_code == 200

    get_response = await secure_client.get("/reports", headers=headers)
    assert get_response.status_code == 200
    assert len(get_response.json()) == 1
    assert get_response.json()[0]["title"] == "Secret Report"
