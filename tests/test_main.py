import pytest
from jetio import Jetio, CrudRouter, add_swagger_ui
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.asyncio


async def test_create_widget(client):
    """Test creating a new widget via POST request."""
    response = await client.post("/widgets", json={"name": "Test Widget", "part_number": 12345})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Widget"
    assert data["part_number"] == 12345
    assert "id" in data


async def test_get_all_widgets(client):
    """Test retrieving all widgets."""
    await client.post("/widgets", json={"name": "Widget A", "part_number": 100})
    await client.post("/widgets", json={"name": "Widget B", "part_number": 200})

    response = await client.get("/widgets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Widget A"
    assert data[1]["name"] == "Widget B"


async def test_get_one_widget(client):
    """Test retrieving a single widget by its ID."""
    create_response = await client.post("/widgets", json={"name": "Specific Widget", "part_number": 999})
    widget_id = create_response.json()["id"]

    response = await client.get(f"/widgets/{widget_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == widget_id
    assert data["name"] == "Specific Widget"

    response_404 = await client.get("/widgets/9999")
    assert response_404.status_code == 404


async def test_update_widget(client):
    """Test updating a widget's data."""
    create_response = await client.post("/widgets", json={"name": "Original Name", "part_number": 111})
    widget_id = create_response.json()["id"]

    update_response = await client.put(f"/widgets/{widget_id}", json={"name": "Updated Name", "part_number": 222})
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "Updated Name"
    assert data["part_number"] == 222


async def test_delete_widget(client):
    """Test deleting a widget."""
    create_response = await client.post("/widgets", json={"name": "To Be Deleted", "part_number": 555})
    widget_id = create_response.json()["id"]

    delete_response = await client.delete(f"/widgets/{widget_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/widgets/{widget_id}")
    assert get_response.status_code == 404


async def test_swagger_docs_ui(client):
    """Test that the Swagger UI documentation endpoint is available."""
    response = await client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text


@pytest.mark.parametrize(
    "payload, expected_error_loc",
    [
        ({"name": "Incomplete Widget"}, ("part_number",)),  # Missing part_number
        ({"part_number": 9876}, ("name",)),  # Missing name
        ({"name": "Wrong Type", "part_number": "not-an-int"}, ("part_number",)),  # Wrong type
    ],
)
async def test_create_widget_validation_error(client, payload, expected_error_loc):
    """Test creating a widget with invalid or missing data results in a 422 error."""
    response = await client.post("/widgets", json=payload)

    assert response.status_code == 422
    error_data = response.json()
    assert "detail" in error_data
    assert error_data["detail"][0]["loc"] == list(expected_error_loc)


async def test_update_widget_validation_error(client):
    """Test updating a widget with invalid data results in a 422 error."""
    create_response = await client.post("/widgets", json={"name": "Valid Widget", "part_number": 123})
    assert create_response.status_code == 200
    widget_id = create_response.json()["id"]

    invalid_payload = {"name": "Updated Name", "part_number": "not-a-valid-number"}
    response = await client.put(f"/widgets/{widget_id}", json=invalid_payload)

    assert response.status_code == 422
    error_data = response.json()
    assert "detail" in error_data
    assert error_data["detail"][0]["loc"] == ["part_number"]


async def test_exclude_methods(client):
    """
    Verifies that the `exclude_methods` parameter in CrudRouter works.

    This test configures a router to exclude the 'DELETE' method and then
    asserts that trying to call the DELETE endpoint results in a
    405 Method Not Allowed error.
    """
    from .models import Report
    app = Jetio()
    CrudRouter(model=Report, exclude_methods=['DELETE']).register_routes(app)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as local_client:
        delete_response = await local_client.delete("/reports/1")
        assert delete_response.status_code == 405
