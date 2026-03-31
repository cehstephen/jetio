import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from pydantic import BaseModel as PydanticModel

from jetio import Jetio, Request
from jetio.framework import BaseMiddleware, Depends, JsonResponse, Response
from .models import Widget


@pytest_asyncio.fixture
async def branch_client():
    app = Jetio()

    class Body(BaseModel):
        value: int

    @app.route("/sync")
    def sync_handler():
        return {"ok": True}

    @app.route("/starlette")
    def starlette_handler():
        from starlette.exceptions import HTTPException

        raise HTTPException(status_code=418, detail="teapot")

    @app.route("/auth")
    def auth_handler():
        from jetio.framework import AuthenticationError

        raise AuthenticationError()

    @app.route("/err")
    def err_handler():
        raise RuntimeError("boom")

    @app.route("/typed/{item_id:int}")
    def typed_handler(item_id: int):
        return {"item_id": item_id}

    @app.route("/validate", methods=["POST"])
    def validate_handler(data: Body):
        return {"value": data.value}

    async def dep_value(**kwargs):
        return kwargs.get("item_id")

    @app.route("/dep/{item_id:int}")
    async def dep_handler(dep=Depends(dep_value)):
        return {"dep": dep}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield app, client


def _lifespan_io(messages):
    queue = asyncio.Queue()
    for item in messages:
        queue.put_nowait(item)

    sent = []

    async def receive():
        return await queue.get()

    async def send(msg):
        sent.append(msg)

    return receive, send, sent


@pytest.mark.asyncio
async def test_framework_handles_error_branches_and_dependency_path_injection(branch_client):
    app, client = branch_client

    r_sync = await client.get("/sync")
    assert r_sync.status_code == 200

    r_auth = await client.get("/auth")
    assert r_auth.status_code == 401

    r_st = await client.get("/starlette")
    assert r_st.status_code == 418
    assert r_st.json()["detail"] == "teapot"

    r_404 = await client.get("/missing")
    assert r_404.status_code == 404

    r_405 = await client.post("/sync")
    assert r_405.status_code == 405

    r_422 = await client.post("/validate", json={"value": "x"})
    assert r_422.status_code == 422

    r_dep = await client.get("/dep/not-an-int")
    assert r_dep.status_code == 200
    assert r_dep.json()["dep"] == "not-an-int"

    r_500 = await client.get("/err")
    assert r_500.status_code == 500

    # direct call branch for invalid scopes
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_msg):
        return None

    with pytest.raises(TypeError):
        await app("not-a-scope", receive, send)

    with pytest.raises(TypeError):
        await app({"wsgi.version": (1, 0)}, receive, send)


@pytest.mark.asyncio
async def test_lifespan_startup_shutdown_success_and_failure():
    app = Jetio()

    events = []

    @app.on_event("startup")
    async def startup():
        events.append("startup")

    @app.on_event("shutdown")
    async def shutdown():
        events.append("shutdown")

    receive, send, sent = _lifespan_io([
        {"type": "lifespan.startup"},
        {"type": "lifespan.shutdown"},
    ])

    await app({"type": "lifespan"}, receive, send)
    assert events == ["startup", "shutdown"]
    assert sent[0]["type"] == "lifespan.startup.complete"
    assert sent[1]["type"] == "lifespan.shutdown.complete"

    failing = Jetio()

    @failing.on_event("startup")
    async def bad_startup():
        raise RuntimeError("startup-fail")

    @failing.on_event("shutdown")
    async def bad_shutdown():
        raise RuntimeError("shutdown-fail")

    receive2, send2, sent2 = _lifespan_io([
        {"type": "lifespan.startup"},
        {"type": "lifespan.shutdown"},
    ])
    await failing({"type": "lifespan"}, receive2, send2)

    assert sent2[0]["type"] == "lifespan.startup.failed"
    assert "startup-fail" in sent2[0]["message"]
    assert sent2[1]["type"] == "lifespan.shutdown.failed"
    assert "shutdown-fail" in sent2[1]["message"]


def test_request_json_and_stream_caching_behavior():
    messages = [
        {"type": "http.request", "body": b"{\"a\":1}", "more_body": False},
    ]

    async def receive():
        if messages:
            return messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    req = Request({"method": "POST", "path": "/x", "headers": []}, receive)
    first = asyncio.run(req.json())
    second = asyncio.run(req.json())
    assert first == {"a": 1}
    assert second == first

    invalid_messages = [
        {"type": "http.request", "body": b"{", "more_body": False},
    ]

    async def receive_invalid():
        if invalid_messages:
            return invalid_messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    req2 = Request({"method": "POST", "path": "/x", "headers": []}, receive_invalid)
    assert asyncio.run(req2.json()) == {}


async def _collect_stream(stream):
    items = []
    async for chunk in stream:
        items.append(chunk)
    return items


def test_framework_request_response_helpers_additional_paths(tmp_path):
    scope = {"method": "GET", "path": "/api/items", "root_path": "/api", "headers": []}

    async def recv_once():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, recv_once)
    assert request.path == "/items"

    async def recv_stream():
        return {"type": "http.request", "body": b"abc", "more_body": False}

    stream_request = Request({"method": "POST", "path": "/x", "headers": []}, recv_stream)
    first = list(asyncio.run(_collect_stream(stream_request.stream())))
    second = list(asyncio.run(_collect_stream(stream_request.stream())))
    assert first[0] == b"abc"
    assert second[0] == b""

    class EchoMiddleware(BaseMiddleware):
        async def __call__(self, scope, receive, send):
            response = Response(body=b"bytes", content_type="text/plain")
            await response(scope, receive, send)

    sent = []

    async def send(msg):
        sent.append(msg)

    asyncio.run(EchoMiddleware(lambda *_: None)({"type": "http"}, recv_once, send))
    assert sent[0]["status"] == 200

    class MiniModel(PydanticModel):
        x: int

    model_payload = JsonResponse(MiniModel(x=3)).body.decode("utf-8")
    assert '"x": 3' in model_payload

    widget_payload = JsonResponse(Widget(id=1, name="w", part_number=1)).body.decode("utf-8")
    assert '"name": "w"' in widget_payload


def test_run_calls_uvicorn_and_rebuilds_models(monkeypatch):
    app = Jetio()
    called = {}

    def fake_run(instance, host, port):
        called["instance"] = instance
        called["host"] = host
        called["port"] = port

    monkeypatch.setattr("jetio.framework.uvicorn.run", fake_run)

    app.run(host="0.0.0.0", port=9999)

    assert called["instance"] is app
    assert called["host"] == "0.0.0.0"
    assert called["port"] == 9999
