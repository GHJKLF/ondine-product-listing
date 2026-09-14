#!/usr/bin/env python3
"""Capture public Shopify source evidence using Python's standard library.

Only GETs. One cookie session. No login, Shopify Admin, or listing write.
This saves source material for review; it does not certify facts or market state.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from http.cookiejar import CookieJar
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import build_opener, HTTPCookieProcessor, Request


def source_urls(url):
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc or parts.username or parts.password:
        raise ValueError("provide a public HTTP(S) product URL without credentials")
    path = parts.path.rstrip("/")
    if "/products/" not in path or path.endswith((".js", ".json")):
        raise ValueError("this helper supports Shopify product pages; use a browser for other sources")
    locale_prefix = path.split("/products/", 1)[0]
    # Collection URLs are not locale prefixes.
    if "/collections/" in locale_prefix:
        locale_prefix = locale_prefix.split("/collections/", 1)[0]
    return {
        "page": urlunsplit((parts.scheme, parts.netloc, path, parts.query, "")),
        "product": urlunsplit((parts.scheme, parts.netloc, path + ".js", parts.query, "")),
        "cart_currency": urlunsplit((parts.scheme, parts.netloc, locale_prefix + "/cart.js", parts.query, "")),
    }


def capture(url, output, opener=None):
    urls = source_urls(url)
    opener = opener or build_opener(HTTPCookieProcessor(CookieJar()))
    output.mkdir(parents=True, exist_ok=False)
    result = {"captured_at": datetime.now(timezone.utc).isoformat(),
              "method": "HTTP_GET_SAME_COOKIE_SESSION", "browser_rendered": False,
              "facts_verified": False, "shopify_written": False,
              "requested_market": "GB", "requested_language": "en-GB",
              "artifacts": {}, "errors": []}
    for kind, address in urls.items():
        try:
            request = Request(address, headers={"User-Agent": "Mozilla/5.0",
                              "Accept-Language": "en-GB,en;q=0.9", "Cache-Control": "no-cache"})
            with opener.open(request, timeout=40) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise ValueError("response exceeded 8 MiB; use the browser")
                final_url = response.geturl()
                content_type = response.headers.get("Content-Type", "")
            if kind == "page":
                if "html" not in content_type:
                    raise ValueError("product page did not return HTML")
                filename = "page.html"
            else:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("structured response must be an object")
                if kind == "product" and (not data.get("id") or not isinstance(data.get("variants"), list)):
                    raise ValueError("response is not a Shopify product")
                if kind == "cart_currency":
                    if not isinstance(data.get("currency"), str):
                        raise ValueError("cart currency missing")
                    # Keep market evidence only, never cart/session tokens or items.
                    raw = json.dumps({"currency": data["currency"]}).encode() + b"\n"
                    result["observed_cart_currency"] = data["currency"]
                filename = kind + ".json"
            (output / filename).write_bytes(raw)
            result["artifacts"][kind] = {
                "requested_url": address, "final_url": final_url,
                "redirected": final_url != address,
                "path": filename, "sha256": hashlib.sha256(raw).hexdigest(),
                "content_type": content_type,
                "currency_only_projection": kind == "cart_currency",
            }
        except (OSError, ValueError) as exc:
            result["errors"].append({"source": kind, "error": str(exc)})
    result["capture_complete"] = len(result["artifacts"]) == 3
    (output / "capture-report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = capture(args.url, args.output)
    except (OSError, ValueError) as exc:
        report = {"capture_complete": False, "error": str(exc), "facts_verified": False}
    print(json.dumps(report, indent=2))
    return 0 if report["capture_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
