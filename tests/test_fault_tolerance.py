"""Fault tolerance tests – node status and admin controls."""
import pytest


@pytest.mark.asyncio
async def test_nodes_list_requires_auth(client):
    resp = await client.get("/api/nodes/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_nodes_list(client, auth_headers):
    resp = await client.get("/api/nodes/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_disable_node_requires_admin(client, auth_headers):
    resp = await client.post("/api/nodes/node1/disable", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats(client, admin_headers):
    resp = await client.get("/api/admin/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "online_nodes" in data


@pytest.mark.asyncio
async def test_admin_users_list(client, admin_headers):
    resp = await client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_requires_admin_role(client, auth_headers):
    resp = await client.get("/api/admin/users", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs(client, admin_headers):
    resp = await client.get("/api/admin/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_ping_nonexistent_node(client, auth_headers):
    resp = await client.post("/api/nodes/nonexistent_node/ping", headers=auth_headers)
    assert resp.status_code == 404
