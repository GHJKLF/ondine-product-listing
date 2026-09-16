"""Portable raw capture must not masquerade as verified or expose cart tokens."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fetch_source import capture, capture_scrapling, source_urls


class Response(io.BytesIO):
    def __init__(self, url, data, content_type):
        super().__init__(data)
        self.url = url
        self.headers = {"Content-Type": content_type}
    def geturl(self):
        return self.url


class Opener:
    def open(self, request, timeout):
        url = request.full_url
        if "cart.js" in url:
            return Response(url, b'{"currency":"GBP","token":"DO-NOT-SAVE","items":[]}', "application/json")
        if ".js" in url:
            return Response(url, b'{"id":123,"variants":[{"id":456}]}', "text/javascript")
        return Response(url, b'<html><body>Example product</body></html>', "text/html")


class PortableSourceTests(unittest.TestCase):
    def test_scrapling_reuses_session_preserves_market_and_drops_tokens(self):
        sessions, requests = [], []
        class Session:
            def __init__(self, **kwargs):
                sessions.append(kwargs)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def get(self, url, headers, timeout):
                requests.append((url, headers, timeout))
                response = Opener().open(SimpleNamespace(full_url=url), timeout)
                return SimpleNamespace(status=200, body=response.read(), url=url,
                    headers={'content-type': response.headers['Content-Type']})
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'source'
            report = capture_scrapling('https://retailer.test/en-gb/products/example?variant=123', output, Session)
            self.assertTrue(report['capture_complete'])
            self.assertEqual('SCRAPLING_GET_SAME_COOKIE_SESSION', report['method'])
            self.assertEqual(1, len(sessions))
            self.assertEqual(3, len(requests))
            self.assertEqual('safe', sessions[0]['follow_redirects'])
            self.assertTrue(all('variant=123' in url and headers['Accept-language'].startswith('en-GB') for url, headers, _ in requests))
            self.assertFalse(report['facts_verified'])
            self.assertFalse(report['browser_rendered'])
            self.assertEqual({'currency':'GBP'}, json.loads((output/'cart_currency.json').read_text()))

    def test_scrapling_http_error_is_not_saved_as_a_valid_page(self):
        class BlockedSession:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def get(self, *args, **kwargs):
                return SimpleNamespace(status=403, body=b'<html>Blocked</html>', url=args[0], headers={})
        with tempfile.TemporaryDirectory() as folder:
            report = capture_scrapling('https://retailer.test/products/example', Path(folder)/'source', BlockedSession)
            self.assertFalse(report['capture_complete'])
            self.assertEqual({}, report['artifacts'])
            self.assertEqual(3, len(report['errors']))

    def test_locale_and_variant_query_preserved(self):
        urls = source_urls("https://retailer.test/en-gb/products/example?variant=123")
        self.assertEqual("https://retailer.test/en-gb/cart.js?variant=123", urls["cart_currency"])
        self.assertTrue(urls["product"].endswith("example.js?variant=123"))

    def test_capture_is_evidence_only_and_drops_session_token(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "source"
            report = capture("https://retailer.test/products/example", output, Opener())
            self.assertTrue(report["capture_complete"])
            self.assertFalse(report["facts_verified"])
            self.assertFalse(report["browser_rendered"])
            self.assertEqual({"currency": "GBP"}, json.loads((output / "cart_currency.json").read_text()))
            for path in output.iterdir():
                self.assertNotIn("DO-NOT-SAVE", path.read_text())

    def test_inaccessible_source_is_not_success(self):
        class Blocked:
            def open(self, request, timeout):
                raise OSError("access unavailable")
        with tempfile.TemporaryDirectory() as folder:
            report = capture("https://retailer.test/products/example", Path(folder)/"source", Blocked())
            self.assertFalse(report["capture_complete"])
            self.assertEqual(3, len(report["errors"]))

    def test_reject_non_product_and_credentials(self):
        for url in ("file:///tmp/page", "https://a:b@retailer.test/products/example", "https://retailer.test/"):
            with self.assertRaises(ValueError):
                source_urls(url)
