import pytest
import asyncio
import pytest_asyncio
from sqlalchemy.orm import Mapped
from httpx import AsyncClient, ASGITransport, Response

from jetio import Jetio, CrudRouter, Base, engine, add_swagger_ui, Request
from .models import Widget, Staff, Report


@pytest.fixture(scope="session")
def event_loop():
    """Creates an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_app():
    """Creates and configures a new Jetio app instance for each test function."""
    app = Jetio()
    add_swagger_ui(app)

    CrudRouter(model=Widget).register_routes(app)

    return app


@pytest.fixture(scope="function")
def multi_model_app():
    """Creates a Jetio app instance with multiple CRUD routers registered."""
    app = Jetio()
    add_swagger_ui(app)
    CrudRouter(model=Staff).register_routes(app)
    CrudRouter(model=Report).register_routes(app)
    return app


@pytest.fixture(scope="function")
def custom_routes_app():
    """Creates a Jetio app with custom decorator-based routes."""
    app = Jetio()

    @app.route("/")
    async def home(request: Request):
        return {"message": "home"}

    @app.route("/custom-post", methods=["POST"])
    async def custom_post(request: Request):
        return {"status": "posted"}

    return app


@pytest_asyncio.fixture(scope="function")
async def client(test_app):
    """
    Creates an async HTTP client for the test app and handles database
    setup and teardown.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def custom_client(custom_routes_app):
    """Creates an async client for the app with custom routes."""
    async with AsyncClient(transport=ASGITransport(app=custom_routes_app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def multi_model_client(multi_model_app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=multi_model_app), base_url="http://test") as ac:
        yield ac

    async with engine.begin() as conn:
        """Teardown: Drop all tables"""
        await conn.run_sync(Base.metadata.drop_all)
