import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from jetio import Jetio, Request
from jetio.framework import JsonResponse, _print_startup_banner


@pytest_asyncio.fixture
async def fixes_client():
    app = Jetio()

    @app.route("/rate-limited")
    def rate_limited_handler():
        from starlette.exceptions import HTTPException

        raise HTTPException(status_code=429, detail="slow down", headers={"Retry-After": "42"})

    @app.route("/no-headers")
    def no_headers_handler():
        from starlette.exceptions import HTTPException

        raise HTTPException(status_code=404, detail="not found")

    @app.route("/whoami")
    async def whoami_handler(request: Request):
        return JsonResponse({"client": list(request.client) if request.client else None})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHTTPExceptionHeaders:
    """A raised starlette.exceptions.HTTPException with `headers=` should
    have those headers reach the actual HTTP response -- previously
    silently dropped, since the framework's exception handler only read
    `.detail`/`.status_code`. Real-world impact: any dependency raising
    HTTPException(429, headers={"Retry-After": ...}) -- e.g. a rate
    limiter -- lost that header on the way out."""

    @pytest.mark.asyncio
    async def test_headers_reach_the_response(self, fixes_client):
        response = await fixes_client.get("/rate-limited")
        assert response.status_code == 429
        assert response.headers.get("retry-after") == "42"
        assert response.json()["detail"] == "slow down"

    @pytest.mark.asyncio
    async def test_no_headers_still_works(self, fixes_client):
        # HTTPException.headers defaults to None -- must not crash when
        # there's nothing to propagate.
        response = await fixes_client.get("/no-headers")
        assert response.status_code == 404
        assert response.json()["detail"] == "not found"


class TestRequestClient:
    """Request had no public way to read the connecting client's address
    -- only the private, underscore-prefixed `_scope`. Any code needing the
    caller's IP (rate limiting, audit logging) had to reach into framework
    internals to get it."""

    @pytest.mark.asyncio
    async def test_client_is_exposed_publicly(self, fixes_client):
        response = await fixes_client.get("/whoami")
        assert response.status_code == 200
        # httpx's ASGITransport supplies a client address in the scope by
        # default; assert it's a 2-element [host, port] shape rather than a
        # specific value, since that's what varies across transports.
        client = response.json()["client"]
        assert client is not None
        assert len(client) == 2


class TestStartupBannerEncoding:
    """run() printed an emoji unconditionally; on a terminal that can't
    encode it (the default Windows console, cp1252, unless
    PYTHONIOENCODING=utf-8 is set), print() raised UnicodeEncodeError and
    crashed the server before it ever started listening."""

    def test_falls_back_when_stdout_cannot_encode_emoji(self, monkeypatch, capsys):
        calls = []
        real_print = print

        def fake_print(*args, **kwargs):
            text = args[0] if args else ""
            if "🚀" in text:
                calls.append(text)
                raise UnicodeEncodeError("cp1252", text, 0, 1, "character maps to <undefined>")
            calls.append(text)
            real_print(*args, **kwargs)

        monkeypatch.setattr("builtins.print", fake_print)

        _print_startup_banner("127.0.0.1", 8000)  # must not raise

        assert len(calls) == 2, "expected one failed emoji attempt, then a plain-text fallback"
        assert "🚀" not in calls[-1]
        assert "127.0.0.1:8000" in calls[-1]

    def test_prints_normally_when_stdout_supports_it(self, capsys):
        _print_startup_banner("0.0.0.0", 9000)
        out = capsys.readouterr().out
        assert "0.0.0.0:9000" in out
