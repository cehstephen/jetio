import pytest
from httpx import ASGITransport, AsyncClient

from jetio import Jetio

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_custom_error_templates_for_404_405_500(tmp_path):
    (tmp_path / "404.html").write_text("Missing: {{ path }}", encoding="utf-8")
    (tmp_path / "405.html").write_text("No method {{ method }}", encoding="utf-8")
    (tmp_path / "500.html").write_text("Oops at {{ path }}", encoding="utf-8")

    app = Jetio(template_folder=str(tmp_path))
    app.add_error_page(404, "404.html")
    app.add_error_page(405, "405.html")
    app.add_error_page(500, "500.html")

    @app.route("/ok", methods=["GET"])
    def ok_route():
        return {"ok": True}

    @app.route("/boom", methods=["GET"])
    def boom_route():
        raise RuntimeError("fail")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        miss = await client.get("/missing")
        wrong = await client.post("/ok")
        boom = await client.get("/boom")

    assert miss.status_code == 404
    assert "Missing: /missing" in miss.text

    assert wrong.status_code == 405
    assert "No method POST" in wrong.text

    assert boom.status_code == 500
    assert "Oops at /boom" in boom.text
