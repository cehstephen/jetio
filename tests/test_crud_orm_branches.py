import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Mapped, mapped_column

from jetio import Base, CrudRouter, Jetio, JetioModel, Request, engine


class OwnerRecord(JetioModel):
    __tablename__ = "owner_records_cov"
    title: Mapped[str]
    owner_id: Mapped[int]


class OptionalModel(JetioModel):
    __tablename__ = "optional_cov"
    username: Mapped[str]
    nickname: Mapped[str | None]
    age: Mapped[int] = mapped_column(default=10)


class SecretModel(JetioModel):
    __tablename__ = "secrets_cov"
    username: Mapped[str]
    hashed_password: Mapped[str]

    class API:
        exclude_from_read = ["hashed_password"]


@pytest_asyncio.fixture
async def coverage_client():
    app = Jetio()

    async def auth_dep(request: Request):
        token = request.headers.get("Authorization")
        if token == "Bearer ok":
            return type("User", (), {"id": 99})()
        return None

    CrudRouter(
        model=OwnerRecord,
        secure=True,
        auth_dependency=auth_dep,
    ).register_routes(app, prefix="api")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def test_secure_router_requires_auth_dependency_or_full_policy():
    with pytest.raises(ValueError):
        CrudRouter(model=OwnerRecord, secure=True)


@pytest.mark.asyncio
async def test_secure_create_assigns_owner_and_prefix_normalization(coverage_client):
    unauthorized = await coverage_client.post("/api/owner_records_cov", json={"title": "x", "owner_id": 1})
    assert unauthorized.status_code == 401

    authorized = await coverage_client.post(
        "/api/owner_records_cov",
        json={"title": "from-client", "owner_id": 1},
        headers={"Authorization": "Bearer ok"},
    )
    assert authorized.status_code == 200
    body = authorized.json()
    assert body["owner_id"] == 99
    assert body["title"] == "from-client"

    fetched = await coverage_client.get("/api/owner_records_cov", headers={"Authorization": "Bearer ok"})
    assert fetched.status_code == 200
    assert len(fetched.json()) == 1

    not_found_get = await coverage_client.get("/api/owner_records_cov/999", headers={"Authorization": "Bearer ok"})
    assert not_found_get.status_code == 404

    not_found_update = await coverage_client.put(
        "/api/owner_records_cov/999",
        json={"title": "none"},
        headers={"Authorization": "Bearer ok"},
    )
    assert not_found_update.status_code == 404

    item_id = body["id"]
    update = await coverage_client.put(
        f"/api/owner_records_cov/{item_id}",
        json={"title": "updated"},
        headers={"Authorization": "Bearer ok"},
    )
    assert update.status_code == 200
    assert update.json()["title"] == "updated"

    delete_unauthorized = await coverage_client.delete(f"/api/owner_records_cov/{item_id}")
    assert delete_unauthorized.status_code == 401

    delete_authorized = await coverage_client.delete(
        f"/api/owner_records_cov/{item_id}",
        headers={"Authorization": "Bearer ok"},
    )
    assert delete_authorized.status_code == 204

    delete_not_found = await coverage_client.delete(
        f"/api/owner_records_cov/{item_id}",
        headers={"Authorization": "Bearer ok"},
    )
    assert delete_not_found.status_code == 404


@pytest.mark.asyncio
async def test_dep_for_prefers_policy_over_fallback():
    async def fallback(request: Request):
        return object()

    async def get_policy(request: Request):
        return object()

    router = CrudRouter(
        model=OwnerRecord,
        secure=True,
        auth_dependency=fallback,
        policy={"get": get_policy},
    )

    assert router._dep_for("GET") is get_policy
    assert router._dep_for("POST") is fallback


def test_orm_metaclass_relationship_and_exclude_behavior():
    read_fields = SecretModel.__pydantic_read_model__.model_fields
    create_fields = SecretModel.__pydantic_create_model__.model_fields

    assert "hashed_password" not in read_fields
    assert "hashed_password" not in create_fields

    optional_create = OptionalModel.__pydantic_create_model__.model_fields
    assert "age" not in optional_create  # excluded because it has server default
    assert "nickname" in optional_create
    assert optional_create["nickname"].annotation in (str | None, OptionalModel.__annotations__["nickname"])

    instance = SecretModel(id=1, username="alpha", hashed_password="hash")
    data = instance.to_dict()
    assert data["id"] == 1
    assert data["username"] == "alpha"
