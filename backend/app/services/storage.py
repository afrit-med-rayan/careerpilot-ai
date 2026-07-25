"""
Storage abstraction layer.

Currently implements local filesystem storage.
To swap in S3/R2, implement the StorageBackend protocol and update get_storage_backend().
"""

import os
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings

settings = get_settings()


class StorageBackend(Protocol):
    async def save(self, filename: str, content: bytes) -> str:
        """Save content and return a URL/path that can retrieve it."""
        ...

    async def read(self, file_url: str) -> bytes:
        """Read and return file content by its URL/path."""
        ...

    async def delete(self, file_url: str) -> None:
        """Delete a stored file."""
        ...


class LocalStorage:
    """Stores files on the local filesystem under `upload_dir`."""

    def __init__(self, upload_dir: str):
        self.base = Path(upload_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    async def save(self, filename: str, content: bytes) -> str:
        # Prefix with a UUID to avoid collisions
        safe_name = f"{uuid.uuid4().hex}_{filename}"
        dest = self.base / safe_name
        dest.write_bytes(content)
        return str(dest)

    async def read(self, file_url: str) -> bytes:
        return Path(file_url).read_bytes()

    async def delete(self, file_url: str) -> None:
        path = Path(file_url)
        if path.exists():
            path.unlink()


def get_storage_backend() -> LocalStorage:
    """FastAPI dependency — returns the configured storage backend."""
    if settings.storage_backend == "local":
        return LocalStorage(upload_dir=settings.local_upload_dir)
    raise NotImplementedError(f"Storage backend '{settings.storage_backend}' not implemented yet.")
