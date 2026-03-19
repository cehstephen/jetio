import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from jetio import Jetio, add_swagger_ui
from jetio.openapi import _generate_and_add_schema, generate_openapi_schema
from .models import Widget


class Payload(BaseModel):
    name: str


def test_generate_and_add_schema_rejects_non_pydantic_input():
    schema_store = {}
    assert _generate_and_add_schema(None, schema_store) is None
    assert _generate_and_add_schema(dict, schema_store) is None
    assert schema_store == {}


def test_generate_openapi_schema_includes_path_params_body_and_response_models():
    app = Jetio(title="Spec Test", version="9.9.9")

    @app.route("/widgets/{item_id:int}", methods=["GET"])
    def get_widget(item_id: int) -> Widget:
        """Get widget."""
        return Widget(id=item_id, name="x", part_number=1)

    @app.route("/widgets", methods=["POST"])
    def create_widget(data: Payload) -> Widget:
        """Create widget."""
        return Widget(id=1, name=data.name, part_number=1)

    @app.route("/widgets/list", methods=["GET"])
    def list_widgets() -> list[Widget]:
        """List widgets."""
        return []

    schema = generate_openapi_schema(app)

    get_op = schema["paths"]["/widgets/{item_id}"]["get"]
    assert get_op["summary"] == "Get widget."
    assert get_op["parameters"][0]["name"] == "item_id"
    assert get_op["parameters"][0]["schema"]["type"] == "integer"

    post_op = schema["paths"]["/widgets"]["post"]
    assert post_op["requestBody"]["required"] is True
    assert post_op["responses"]["201"]["content"]["application/json"]["schema"]["$ref"].endswith("WidgetRead")

    list_op = schema["paths"]["/widgets/list"]["get"]
    assert list_op["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "array"


@pytest.mark.asyncio
async def test_swagger_ui_and_openapi_respect_root_path():
    app = Jetio()
    add_swagger_ui(app)

    transport = ASGITransport(app=app, root_path="/api")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        docs = await client.get("/docs")
        spec = await client.get("/openapi.json")

    assert docs.status_code == 200
    assert '/api/openapi.json' in docs.text
    assert spec.status_code == 200
    assert spec.json()["servers"] == [{"url": "/api"}]
