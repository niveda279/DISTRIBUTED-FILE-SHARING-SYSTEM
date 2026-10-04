"""Shared test fixtures."""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import Base, engine


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session")
async def client(create_tables):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def auth_headers(client):
    """Register + login a test user and return auth headers."""
    await client.post("/api/auth/register", json={
        "name": "Test User", "email": "test@example.com", "password": "password123"
    })
    resp = await client.post("/api/auth/login", json={
        "email": "test@example.com", "password": "password123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="session")
async def admin_headers(client):
    """Register + login an ADMIN test user."""
    # Register
    resp = await client.post("/api/auth/register", json={
        "name": "Admin User", "email": "admin@example.com", "password": "admin1234"
    })
    user_id = resp.json().get("id")

    # Promote directly in DB
    from app.database import AsyncSessionLocal
    from app.models.user import User
    from sqlalchemy import select, update
    async with AsyncSessionLocal() as db:
        await db.execute(update(User).where(User.id == user_id).values(role="ADMIN"))
        await db.commit()

    resp = await client.post("/api/auth/login", json={
        "email": "admin@example.com", "password": "admin1234"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
