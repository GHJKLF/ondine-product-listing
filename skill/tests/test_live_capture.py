"""The live bridge uses actual run files, not a historical replay fixture."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from product_listing.cli import main
from product_listing.evidence import model_sha256, sha256_file, sha256_text
from product_listing.live_capture import prepare_live_capture, finalize_live_capture, write_new_json
from product_listing.models import SourceMedia


class LiveCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.url = "https://example.test/products/synthetic-dress"
        product = {"id": 123, "title": "Synthetic Dress", "price": 5900,
                   "options": [{"name": "Size", "position": 1, "values": ["UK 8"]}],
                   "variants": [{"id": 456, "options": ["UK 8"], "price": 5900}]}
        inputs = {"page": ("page.html", "<html><main><h1>Synthetic Dress</h1></main></html>"),
                  "product": ("product.json", json.dumps(product)),
                  "cart_currency": ("cart_currency.json", '{"currency":"GBP"}')}
        artifacts = {}
        for role, (name, content) in inputs.items():
            path = self.source / name
            path.write_text(content)
            url = self.url + (".js" if role == "product" else "")
            if role == "cart_currency":
                url = "https://example.test/cart.js"
            artifacts[role] = {"path": name, "sha256": sha256_file(path),
                               "requested_url": url, "final_url": url, "redirected": False}
        self.report = {"capture_complete": True, "errors": [],
                       "method": "SCRAPLING_GET_SAME_COOKIE_SESSION", "browser_rendered": False,
                       "captured_at": "2026-09-16T10:00:00+00:00", "requested_market": "GB",
                       "requested_language": "en-GB", "observed_cart_currency": "GBP",
                       "artifacts": artifacts}
        self.report_path = self.source / "capture-report.json"
        self.save_report()

    def save_report(self):
        self.report_path.write_text(json.dumps(self.report))

    def reviewed_synthetic_capture(self):
        capture = prepare_live_capture(self.report_path, self.root)
        capture.consumer_retail_source = True
        capture.source_class_evidence.consumer_retail_source = True
        capture.source_class_evidence.rationale = "Synthetic test review only."
        capture.acquisition_gaps = []
        (self.source / "image.jpg").write_bytes(b"synthetic image bytes for integrity tests")
        digest = sha256_file(self.source / "image.jpg")
        url = "https://example.test/synthetic.jpg"
        common = dict(media_id="synthetic-media", position=1, url=url,
                      url_sha256=sha256_text(url), content_sha256=digest, exclusion_group_ids=[])
        capture.rendered_media = [SourceMedia(order_kind="RENDERED", **common)]
        capture.structured_media = [SourceMedia(order_kind="STRUCTURED", **common)]
        capture.media_manifest_evidence = {"content_files": [
            {"url": url, "relative_path": "source/image.jpg", "sha256": digest}]}
        path = self.root / "reviewed.json"
        path.write_text(capture.model_dump_json())
        return capture, path

    def test_raw_capture_builds_complete_but_unapproved_candidate(self):
        capture = prepare_live_capture(self.report_path, self.root)
        self.assertEqual(str(capture.current_price), "59")
        self.assertEqual(capture.variants[0].option_values[0].value, "UK 8")
        self.assertEqual(capture.artifacts[1].relative_path, "source/page.html")
        self.assertIsNone(capture.rendered_capture)
        self.assertFalse(capture.consumer_retail_source)
        self.assertEqual(capture.acquisition_gaps[0].code, "LIVE_SOURCE_REVIEW_PENDING")
        self.assertFalse(capture.same_session_commerce["browser_rendered"])
        path = self.root / "unreviewed.json"
        path.write_text(capture.model_dump_json())
        with self.assertRaisesRegex(ValueError, "review is incomplete"):
            finalize_live_capture(path, self.root)

    def test_finalizer_matches_registration_envelope_and_hash(self):
        capture, path = self.reviewed_synthetic_capture()
        result = finalize_live_capture(path, self.root)
        self.assertTrue(result.valid)
        self.assertEqual(result.issues, [])
        self.assertEqual(result.determinism_sha256, model_sha256(capture))
        self.assertEqual(result, finalize_live_capture(path, self.root))

    def test_tampered_capture_artifact_rejected(self):
        (self.source / "product.json").write_text('{"id":999}')
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            prepare_live_capture(self.report_path, self.root)

    def test_shopify_zero_compare_at_means_no_struck_price(self):
        path = self.source / "product.json"
        product = json.loads(path.read_text())
        product["compare_at_price"] = 0
        product["variants"][0]["compare_at_price"] = 0
        path.write_text(json.dumps(product))
        self.report["artifacts"]["product"]["sha256"] = sha256_file(path)
        self.save_report()
        capture = prepare_live_capture(self.report_path, self.root)
        self.assertIsNone(capture.compare_at_price)
        self.assertIsNone(capture.variants[0].compare_at_price)
        self.assertEqual(capture.current_price, 59)

    def test_wrong_market_and_incomplete_capture_rejected(self):
        for field, value in [("requested_market", "MA"), ("capture_complete", False),
                             ("observed_cart_currency", "MAD")]:
            with self.subTest(field=field):
                previous = self.report[field]
                self.report[field] = value
                self.save_report()
                with self.assertRaises(ValueError):
                    prepare_live_capture(self.report_path, self.root)
                self.report[field] = previous

    def test_escaping_and_symlink_artifact_paths_rejected(self):
        self.report["artifacts"]["page"]["path"] = "../../outside.html"
        self.save_report()
        with self.assertRaisesRegex(ValueError, "outside source bundle"):
            prepare_live_capture(self.report_path, self.root)
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "outside.html"
            outside.write_text("unrelated")
            (self.source / "link.html").symlink_to(outside)
            self.report["artifacts"]["page"].update(path="link.html", sha256=sha256_file(outside))
            self.save_report()
            with self.assertRaisesRegex(ValueError, "outside source bundle"):
                prepare_live_capture(self.report_path, self.root)

    def test_redirect_remains_explicitly_unresolved(self):
        self.report["artifacts"]["page"].update(final_url=self.url + "?country=MA", redirected=True)
        self.save_report()
        capture = prepare_live_capture(self.report_path, self.root)
        self.assertIn("LIVE_REDIRECT_REVIEW_PENDING", [gap.code for gap in capture.acquisition_gaps])

    def test_finalizer_rechecks_raw_and_media_files(self):
        _, path = self.reviewed_synthetic_capture()
        (self.source / "image.jpg").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            finalize_live_capture(path, self.root)
        (self.source / "page.html").write_text("changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            finalize_live_capture(path, self.root)

    def test_missing_media_evidence_rejected(self):
        capture, path = self.reviewed_synthetic_capture()
        capture.media_manifest_evidence = {"content_files": []}
        path.write_text(capture.model_dump_json())
        with self.assertRaisesRegex(ValueError, "verified local file"):
            finalize_live_capture(path, self.root)

    def test_deleting_a_parser_conflict_does_not_count_as_resolving_it(self):
        page = self.source / "page.html"
        page.write_text('<html><main><h1>Different title</h1></main></html>')
        self.report["artifacts"]["page"]["sha256"] = sha256_file(page)
        self.save_report()
        capture, path = self.reviewed_synthetic_capture()
        self.assertTrue(capture.conflicts)
        conflicts = list(capture.conflicts)
        capture.conflicts = []
        path.write_text(capture.model_dump_json())
        with self.assertRaisesRegex(ValueError, "preserve original conflict evidence"):
            finalize_live_capture(path, self.root)
        capture.conflicts = conflicts
        for conflict in capture.conflicts:
            conflict.state = "RESOLVED"
            conflict.rationale = "Synthetic resolution test: both original values remain in the record."
        path.write_text(capture.model_dump_json())
        self.assertTrue(finalize_live_capture(path, self.root).valid)

    def test_cli_and_overwrite_protection(self):
        output = self.root / "candidate.json"
        with redirect_stdout(io.StringIO()):
            code = main(["prepare-live", str(self.report_path), "--source-bundle", str(self.root),
                         "--output", str(output)])
        self.assertEqual(code, 0)
        before = output.read_bytes()
        with self.assertRaises(FileExistsError):
            write_new_json(output, {"replacement": True})
        self.assertEqual(before, output.read_bytes())
        with redirect_stdout(io.StringIO()):
            code = main(["finalize-live", str(output), "--source-bundle", str(self.root),
                         "--output", str(self.root / "not-ready.json")])
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "not-ready.json").exists())


if __name__ == "__main__":
    unittest.main()
