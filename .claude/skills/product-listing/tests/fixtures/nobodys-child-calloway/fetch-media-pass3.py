#!/usr/bin/env python3
"""Complete bounded acquisition pass 3 by hashing only enumerated source media."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "raw" / "media-content-hashes.json"

ITEMS = [
    {
        "role": "product_gallery",
        "position": 1,
        "structured_url": "https://cdn.shopify.com/s/files/1/0640/7005/8155/files/NC_WEB_2616171001_164.jpg?v=1776339491",
        "rendered_url": "https://www.nobodyschild.com/cdn/shop/files/NC_WEB_2616171001_164.jpg?v=1776339491&width=800",
    },
    {
        "role": "product_gallery",
        "position": 2,
        "structured_url": "https://cdn.shopify.com/s/files/1/0640/7005/8155/files/NC_WEB_2616171001_182.jpg?v=1776423570",
        "rendered_url": "https://www.nobodyschild.com/cdn/shop/files/NC_WEB_2616171001_182.jpg?v=1776423570&width=800",
    },
    {
        "role": "product_gallery",
        "position": 3,
        "structured_url": "https://cdn.shopify.com/s/files/1/0640/7005/8155/files/NC_WEB_2616171001_230.jpg?v=1776423570",
        "rendered_url": "https://www.nobodyschild.com/cdn/shop/files/NC_WEB_2616171001_230.jpg?v=1776423570&width=800",
    },
    {
        "role": "product_gallery",
        "position": 4,
        "structured_url": "https://cdn.shopify.com/s/files/1/0640/7005/8155/files/NC_WEB_2616171001_207.jpg?v=1776423570",
        "rendered_url": "https://www.nobodyschild.com/cdn/shop/files/NC_WEB_2616171001_207.jpg?v=1776423570&width=800",
    },
    {
        "role": "product_gallery",
        "position": 5,
        "structured_url": "https://cdn.shopify.com/s/files/1/0640/7005/8155/files/NC_WEB_2616171001_220.jpg?v=1776423570",
        "rendered_url": "https://www.nobodyschild.com/cdn/shop/files/NC_WEB_2616171001_220.jpg?v=1776423570&width=800",
    },
    {
        "role": "size_guide_illustration",
        "position": 1,
        "structured_url": "https://cdn.kiwisizing.com/nobodyschild-1772532336733.jpeg",
        "rendered_url": "https://cdn.kiwisizing.com/nobodyschild-1772532336733.jpeg",
    },
]


def fetch(url: str) -> dict[str, object]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; frozen-fixture-acquisition/1.0)",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read()
        content_type = response.headers.get_content_type()
        return {
            "requested_url": url,
            "final_url": response.geturl(),
            "http_status": response.status,
            "content_type": content_type or mimetypes.guess_type(url)[0],
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }


records = []
for item in ITEMS:
    record = {key: value for key, value in item.items() if key not in {"structured_url", "rendered_url"}}
    record["structured"] = fetch(item["structured_url"])
    if item["rendered_url"] == item["structured_url"]:
        record["rendered"] = {**record["structured"], "same_bytes_as_structured": True}
    else:
        record["rendered"] = fetch(item["rendered_url"])
        record["rendered"]["same_bytes_as_structured"] = (
            record["rendered"]["sha256"] == record["structured"]["sha256"]
        )
    records.append(record)

payload = {
    "fixture_id": "nobodys-child-calloway",
    "acquisition_pass": 3,
    "scope": "five enumerated product-gallery assets plus one size-guide illustration only",
    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    "items": records,
}
OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=False))
