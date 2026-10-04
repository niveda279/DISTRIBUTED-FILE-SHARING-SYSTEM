"""SHA-256 integrity verification utilities."""
import hashlib


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def verify_integrity(data: bytes, expected_checksum: str) -> bool:
    """Return True if SHA-256(data) matches expected_checksum."""
    actual = compute_sha256(data)
    return actual == expected_checksum
