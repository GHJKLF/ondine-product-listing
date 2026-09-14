"""GET/HEAD-only Playwright capture interface.

This module has no Shopify Admin client and no mutation method. It uses a fresh
ephemeral browser context, performs no clicks, and aborts every non-read HTTP
method before it leaves the browser.
"""

from typing import Any, Dict, List, Optional, Protocol
from urllib.parse import urlparse, urlunparse

from pydantic import Field

from product_listing.models import StrictModel


class BrowserSnapshot(StrictModel):
    requested_url: str
    final_url: str
    rendered_html: str
    shopify_ajax: Optional[Dict[str, Any]] = None
    blocked_request_methods: List[str] = Field(default_factory=list)


class ReadOnlyPageCapture(Protocol):
    async def capture(self, url: str) -> BrowserSnapshot:
        ...


class PlaywrightReadOnlyCapture:
    """Read a public product page in an isolated browser context."""

    ALLOWED_METHODS = {"GET", "HEAD"}

    def __init__(self, timeout_ms: int = 45_000) -> None:
        self.timeout_ms = timeout_ms

    async def capture(self, url: str) -> BrowserSnapshot:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("capture URL must be absolute HTTP(S)")

        from playwright.async_api import async_playwright

        blocked_methods: List[str] = []
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(service_workers="block")
            page = await context.new_page()

            async def read_only_guard(route, request):
                method = request.method.upper()
                if method not in self.ALLOWED_METHODS:
                    blocked_methods.append(method)
                    await route.abort("blockedbyclient")
                    return
                await route.continue_()

            await page.route("**/*", read_only_guard)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                rendered_html = await page.content()
                final_url = page.url
                ajax_url = self._shopify_ajax_url(final_url)
                shopify_ajax: Optional[Dict[str, Any]] = None
                if ajax_url:
                    shopify_ajax = await page.evaluate(
                        """async (sourceUrl) => {
                          const response = await fetch(sourceUrl, {
                            method: 'GET', credentials: 'same-origin', headers: {'Accept': 'application/json'}
                          });
                          if (!response.ok) return null;
                          const type = response.headers.get('content-type') || '';
                          if (!type.includes('json') && !type.includes('javascript')) return null;
                          try { return await response.json(); } catch (_) { return null; }
                        }""",
                        ajax_url,
                    )
                return BrowserSnapshot(
                    requested_url=url,
                    final_url=final_url,
                    rendered_html=rendered_html,
                    shopify_ajax=shopify_ajax,
                    blocked_request_methods=sorted(set(blocked_methods)),
                )
            finally:
                await context.close()
                await browser.close()

    @staticmethod
    def _shopify_ajax_url(url: str) -> Optional[str]:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if "/products/" not in path or path.endswith((".js", ".json")):
            return None
        return urlunparse((parsed.scheme, parsed.netloc, path + ".js", "", "", ""))

