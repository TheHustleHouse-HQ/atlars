import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from main import app
from app.core.database import get_users_collection, get_entries_collection
from app.models.user import UserInDB
from app.core.security import create_access_token


@pytest.fixture
async def async_client():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


@pytest.fixture(autouse=True)
async def clear_db(async_client):
    await get_users_collection().delete_many({})
    await get_entries_collection().delete_many({})


@pytest.fixture(autouse=True)
def mock_celery_task():
    with patch("app.services.capture.entry_service.embed_entry.delay") as mock_delay:
        yield mock_delay


@pytest.fixture
async def auth_headers():
    users = get_users_collection()
    user = UserInDB.new(email="test@example.com", hashed_password="pw", display_name="Test User")
    await users.insert_one(user.model_dump())
    
    token = create_access_token(user.user_id)
    return {"Authorization": f"Bearer {token}"}


async def test_create_entry(async_client: AsyncClient, auth_headers: dict, mock_celery_task):
    response = await async_client.post(
        "/entries/",
        json={"raw_text": "Hello world", "modality": "text"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["raw_text"] == "Hello world"
    assert data["modality"] == "text"
    assert data["embedding_generated_at"] is None
    assert data["compression_tier"] == "hot"
    assert "entry_id" in data
    
    # Verify task was enqueued
    mock_celery_task.assert_called_once_with(data["entry_id"])


async def test_get_entries_pagination(async_client: AsyncClient, auth_headers: dict):
    # Create 3 entries sequentially
    for i in range(3):
        await async_client.post(
            "/entries/",
            json={"raw_text": f"Entry {i}", "modality": "text"},
            headers=auth_headers
        )

    # Get first page (limit=2)
    response = await async_client.get("/entries/?limit=2", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) == 2
    assert data["entries"][0]["raw_text"] == "Entry 2"
    assert data["entries"][1]["raw_text"] == "Entry 1"
    
    next_cursor = data["next_cursor"]
    assert next_cursor is not None
    
    # Get second page
    response2 = await async_client.get(f"/entries/?limit=2&cursor={next_cursor}", headers=auth_headers)
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["entries"]) == 1
    assert data2["entries"][0]["raw_text"] == "Entry 0"
    assert data2["next_cursor"] is None


async def test_get_single_entry(async_client: AsyncClient, auth_headers: dict):
    create_resp = await async_client.post(
        "/entries/",
        json={"raw_text": "Single entry"},
        headers=auth_headers
    )
    entry_id = create_resp.json()["entry_id"]

    get_resp = await async_client.get(f"/entries/{entry_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["raw_text"] == "Single entry"


async def test_update_entry(async_client: AsyncClient, auth_headers: dict, mock_celery_task):
    create_resp = await async_client.post(
        "/entries/",
        json={"raw_text": "Original text"},
        headers=auth_headers
    )
    entry_id = create_resp.json()["entry_id"]
    
    # reset mock to check call count specifically for update
    mock_celery_task.reset_mock()

    patch_resp = await async_client.patch(
        f"/entries/{entry_id}",
        json={"raw_text": "Updated text"},
        headers=auth_headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["raw_text"] == "Updated text"
    assert patch_resp.json()["embedding_generated_at"] is None
    
    # verify task enqueued again
    mock_celery_task.assert_called_once_with(entry_id)


async def test_delete_entry(async_client: AsyncClient, auth_headers: dict):
    create_resp = await async_client.post(
        "/entries/",
        json={"raw_text": "Delete me"},
        headers=auth_headers
    )
    entry_id = create_resp.json()["entry_id"]

    del_resp = await async_client.delete(f"/entries/{entry_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Verify it's gone
    get_resp = await async_client.get(f"/entries/{entry_id}", headers=auth_headers)
    assert get_resp.status_code == 404
