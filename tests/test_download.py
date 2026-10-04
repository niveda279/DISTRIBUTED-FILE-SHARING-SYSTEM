"""Download and file access tests."""
import pytest


@pytest.mark.asyncio
async def test_download_nonexistent(client, auth_headers):
    resp = await client.get("/api/files/99999/download", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_requires_auth(client):
    resp = await client.get("/api/files/1/download")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_file_metadata_nonexistent(client, auth_headers):
    resp = await client.get("/api/files/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent(client, auth_headers):
    resp = await client.delete("/api/files/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_endpoint(client, auth_headers):
    resp = await client.get("/api/files/search", headers=auth_headers, params={"q": "test"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
