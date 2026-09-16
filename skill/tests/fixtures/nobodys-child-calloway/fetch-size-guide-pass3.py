#!/usr/bin/env python3
"""One-use, read-only public KiwiSizing acquisition for the frozen fixture."""

from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json


ROOT = Path(__file__).resolve().parent
product = json.loads((ROOT / "raw" / "product.js.json").read_text(encoding="utf-8"))
params = {
    "shop": "nobodyschild.myshopify.com",
    "product": str(product["id"]),
    "title": product["title"],
    "tags": ",".join(product["tags"]),
    "metafields": "[]",
    "categories": "",
    "brand": "",
    "type": product["type"],
    "vendor": product["vendor"],
    "collections": "302774747307,680284094849,691584369025,674360525185,680543420801,676529930625,302668447915,691909034369,303045607595",
}
url = "https://app.kiwisizing.com/api/getSizingChart?" + urlencode(params)
request = Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 EvidenceCapture/1.0",
        "Accept": "application/json",
        "Referer": "https://www.nobodyschild.com/products/calloway-midi-dress-2616171001?country=GB",
    },
)
with urlopen(request, timeout=90) as response:
    body = response.read()
    status = response.status
    final_url = response.url
    content_type = response.headers.get("Content-Type")
(ROOT / "raw" / "size-guide.api.json").write_bytes(body)
parsed = json.loads(body)
print(
    json.dumps(
        {
            "status": status,
            "final_url": final_url,
            "content_type": content_type,
            "bytes": len(body),
            "sha256": sha256(body).hexdigest(),
            "keys": list(parsed),
            "sizing_count": len(parsed.get("sizings", [])),
            "sizing_ids": [item.get("id") for item in parsed.get("sizings", [])],
        },
        ensure_ascii=False,
        indent=2,
    )
)
