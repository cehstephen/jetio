import pytest
from httpx import AsyncClient, ASGITransport

from jetio import CORSMiddleware, Jetio, Request

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
def cors_app():
    app = Jetio()
    app.add_middleware(CORSMiddleware, allowed_origins=["http://localhost:5173"])

    @app.route("/ping")
    async def ping(request: Request):
        return {"ok": True}

    return app


async def test_preflight_allows_known_origin(cors_app):
    async with AsyncClient(transport=ASGITransport(app=cors_app), base_url="http://test") as client:
        response = await client.options(
            "/ping",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("vary") == "Origin"
    assert response.headers.get("access-control-allow-methods") == "GET, POST, PUT, DELETE, OPTIONS"
    assert response.headers.get("access-control-allow-headers") == "Authorization, Content-Type"


async def test_get_response_includes_cors_header(cors_app):
    async with AsyncClient(transport=ASGITransport(app=cors_app), base_url="http://test") as client:
        response = await client.get("/ping", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("vary") == "Origin"


async def test_preflight_disallowed_origin_has_no_allow_origin(cors_app):
    async with AsyncClient(transport=ASGITransport(app=cors_app), base_url="http://test") as client:
        response = await client.options(
            "/ping",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None
