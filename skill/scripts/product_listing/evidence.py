"""Canonical serialization and SHA-256 evidence helpers."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON-compatible data identically across clean replays."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=False)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def model_sha256(model: BaseModel) -> str:
    return sha256_bytes(canonical_json_bytes(model))


def hashed_json(value: Any) -> Dict[str, Any]:
    """Return an auditable envelope without embedding mutable runtime state."""

    return {
        "sha256": sha256_bytes(canonical_json_bytes(value)),
        "value": value,
    }

