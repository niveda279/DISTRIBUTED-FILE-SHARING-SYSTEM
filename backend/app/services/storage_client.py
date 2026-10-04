"""HTTP client for communicating with storage nodes."""
import hashlib
import io
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()

# Global async client (reused across requests)
_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=60.0)
    return _client


async def close_client():
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def node_url(node_id: str) -> str:
    urls = settings.node_urls
    if node_id not in urls:
        raise ValueError(f"Unknown node_id: {node_id}")
    return urls[node_id]


async def store_file_on_node(node_id: str, file_id: str, file_bytes: bytes, filename: str) -> dict:
    """Upload a file to a storage node."""
    url = f"{node_url(node_id)}/store"
    client = get_client()
    response = await client.post(
        url,
        params={"file_id": file_id},
        files={"file": (filename, io.BytesIO(file_bytes), "application/octet-stream")},
    )
    response.raise_for_status()
    return response.json()


async def retrieve_file_from_node(node_id: str, file_id: str) -> bytes:
    """Download file bytes from a storage node."""
    url = f"{node_url(node_id)}/files/{file_id}"
    client = get_client()
    response = await client.get(url)
    response.raise_for_status()
    return response.content


async def delete_file_from_node(node_id: str, file_id: str) -> dict:
    """Delete a file from a storage node."""
    url = f"{node_url(node_id)}/files/{file_id}"
    client = get_client()
    response = await client.delete(url)
    response.raise_for_status()
    return response.json()


async def check_node_health(node_id: str) -> Optional[dict]:
    """Poll /health on a storage node. Returns None on failure."""
    try:
        url = f"{node_url(node_id)}/health"
        client = get_client()
        response = await client.get(url, timeout=10.0)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None
