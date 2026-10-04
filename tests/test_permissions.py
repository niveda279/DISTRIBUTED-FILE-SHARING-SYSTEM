"""Permission and sharing tests."""
import pytest


@pytest.mark.asyncio
async def test_share_nonexistent_file(client, auth_headers):
    resp = await client.post("/api/files/99999/share", headers=auth_headers, json={
        "shared_with_email": "other@test.com",
        "permission": "VIEW",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_permissions_nonexistent_file(client, auth_headers):
    resp = await client.get("/api/files/99999/permissions", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_revoke_nonexistent_permission(client, auth_headers):
    resp = await client.delete("/api/files/99999/permissions/1", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_share_requires_auth(client):
    resp = await client.post("/api/files/1/share", json={
        "shared_with_email": "x@test.com", "permission": "VIEW"
    })
    assert resp.status_code == 401
