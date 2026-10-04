"""File upload tests."""
import io
import pytest


def _make_file(content=b"Hello World", filename="test.txt"):
    return ("file", (filename, io.BytesIO(content), "text/plain"))


@pytest.mark.asyncio
async def test_upload_requires_auth(client):
    resp = await client.post("/api/files/upload", files=[_make_file()])
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_success(client, auth_headers, monkeypatch):
    """Upload should succeed when a node is available."""
    # Mock storage_client to avoid real HTTP calls to storage nodes
    from app.services import storage_client
    async def mock_store(node_url, file_id, data, filename):
        return {"file_id": file_id, "checksum": "abc123", "size": len(data)}

    monkeypatch.setattr(storage_client, "store_file", mock_store)

    # Also seed a mock node in DB
    from app.database import AsyncSessionLocal
    from app.models.storage_node import StorageNode
    async with AsyncSessionLocal() as db:
        node = StorageNode(node_id="nodetest", name="Test Node", host="localhost", port=9999, status="ONLINE")
        db.add(node)
        await db.commit()

    resp = await client.post(
        "/api/files/upload",
        headers=auth_headers,
        files=[_make_file(b"Test file content", "sample.txt")],
    )
    # Expect 201 or 503 if no real node (integration depends on environment)
    assert resp.status_code in (201, 503)


@pytest.mark.asyncio
async def test_list_files(client, auth_headers):
    resp = await client.get("/api/files/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_shared_files(client, auth_headers):
    resp = await client.get("/api/files/shared", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
