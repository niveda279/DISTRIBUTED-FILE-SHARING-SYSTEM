"""Authentication endpoint tests."""
import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/api/auth/register", json={
        "name": "Alice", "email": "alice@test.com", "password": "alice1234"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@test.com"
    assert data["role"] == "USER"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    body = {"name": "Bob", "email": "bob@test.com", "password": "bob12345"}
    await client.post("/api/auth/register", json=body)
    resp = await client.post("/api/auth/register", json=body)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/auth/register", json={
        "name": "Carol", "email": "carol@test.com", "password": "carol123"
    })
    resp = await client.post("/api/auth/login", json={
        "email": "carol@test.com", "password": "carol123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["email"] == "carol@test.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={
        "name": "Dave", "email": "dave@test.com", "password": "dave1234"
    })
    resp = await client.post("/api/auth/login", json={
        "email": "dave@test.com", "password": "wrongpassword"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client, auth_headers):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_protected_without_token(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
