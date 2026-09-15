"""Customer copy in the current prose and rich-text layout remains audited."""
import sys
import unittest
import hashlib
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from product_listing.listing_plan_copy_guard import build_target_field_records, build_source_field_records, build_copy_guard_result, CopyGuardEvidenceError
from product_listing.listing_plan_validation import validate_listing_plan_document
from test_listing_plan_contract import committable_document, golden_replay, CALLOWAY_BUNDLE
from test_current_composition import current_document


class CurrentCopyGuardTest(unittest.TestCase):
    def test_responsive_shopify_alias_keeps_every_alt_and_reports_count(self):
        capture = golden_replay().source_capture.model_copy(deep=True)
        capture.canonical_url = "https://source.example/products/dress"
        capture.rendered_media = capture.rendered_media[:1]
        capture.rendered_media[0].url = "https://cdn.shopify.com/s/files/1/0000/1111/files/dress.webp?v=123"
        raw = (b'<img src="https://source.example/cdn/shop/files/dress.webp?v=123&width=1200" alt="Front garment">'
               b'<img src="https://source.example/cdn/shop/files/dress.webp?width=100&v=123" alt="Pocket detail">')
        artifact = next(a for a in capture.artifacts if a.artifact_id == "rendered-sanitized")
        artifact.artifact_id = "source-page"
        artifact.relative_path = "source.html"
        artifact.sha256 = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.html").write_bytes(raw)
            fields = build_source_field_records(capture, root)
            alts = [f["normalized"] for f in fields if "#/product_gallery_media_alt/" in f["path"]]
            self.assertEqual(alts, ["front garment", "pocket detail"])
            report = build_copy_guard_result(committable_document(), capture, "0" * 64, root, [])
            self.assertEqual(report["source_media_alt_field_count"], 2)

    def test_alias_cannot_hide_wrong_host_version_or_missing_alt(self):
        capture = golden_replay().source_capture.model_copy(deep=True)
        capture.canonical_url = "https://source.example/products/dress"
        capture.rendered_media = capture.rendered_media[:1]
        capture.rendered_media[0].url = "https://cdn.shopify.com/s/files/1/0000/1111/files/dress.webp?v=123"
        artifact = next(a for a in capture.artifacts if a.artifact_id == "rendered-sanitized")
        artifact.relative_path = "source.html"
        for raw in (
            b'<img src="https://other.example/cdn/shop/files/dress.webp?v=123" alt="Wrong host">',
            b'<img src="https://source.example/cdn/shop/files/dress.webp?v=124" alt="Wrong version">',
            b'<img src="https://source.example/cdn/shop/files/dress.webp?v=123">',
        ):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                artifact.sha256 = hashlib.sha256(raw).hexdigest()
                (root / "source.html").write_bytes(raw)
                with self.assertRaises(CopyGuardEvidenceError):
                    build_source_field_records(capture, root)

    def test_malformed_rich_text_returns_blocking_report_with_source_present(self):
        for children in (None, 42, ["not a node"]):
            with self.subTest(children=children):
                document = current_document()
                document["shopify_target_state"]["rich_text_metafields"]["fit_details"]["children"] = children
                report = validate_listing_plan_document(document,
                    source_capture_evidence=golden_replay().model_dump(mode="json"),
                    source_artifact_root=CALLOWAY_BUNDLE)
                self.assertFalse(report.committable)
                self.assertIn("RICH_TEXT_METAFIELD_INVALID", {issue.code for issue in report.issues})

    def test_source_page_full_image_link_alt_is_checked_and_hash_pinned(self):
        capture = golden_replay().source_capture.model_copy(deep=True)
        capture.rendered_media = capture.rendered_media[:1]
        capture.rendered_media[0].url = "https://example.com/garment.jpg"
        raw = b'<a href="https://example.com/garment.jpg"><img src="https://example.com/garment.jpg?width=100" alt="Floral garment front"></a>'
        artifact = next(a for a in capture.artifacts if a.artifact_id == "rendered-sanitized")
        artifact.artifact_id = "source-page"
        artifact.relative_path = "source.html"
        artifact.sha256 = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.html").write_bytes(raw)
            fields = {item["path"]: item["normalized"] for item in build_source_field_records(capture, root)}
            self.assertEqual(fields["artifact:source-page#/product_gallery_media_alt/0"], "floral garment front")
            (root / "source.html").write_bytes(raw + b'changed')
            with self.assertRaises(CopyGuardEvidenceError):
                build_source_field_records(capture, root)

    def test_collects_benefits_prose_and_nested_rich_text(self):
        document = committable_document()
        benefits = document["composition"]["description"]["slots"][2]
        benefits.pop("items", None)
        benefits["text"] = "Exclusive benefits that must be checked."
        document["shopify_target_state"]["rich_text_metafields"] = {
            "fit_details": {"type": "root", "children": [{"type": "list", "listType": "unordered", "children": [
                {"type": "list-item", "children": [{"type": "text", "value": "Luxury fabric must not escape review."}]}
            ]}]}
        }
        document["shopify_target_state"]["metafields"]["neckline"] = "Exclusive trim"
        records = {r["path"]: r["normalized"] for r in build_target_field_records(document)}
        self.assertIn("exclusive", records["/composition/description/slots/2/text"])
        path = "/shopify_target_state/rich_text_metafields/fit_details/children/0/children/0/children/0/value"
        self.assertIn("luxury", records[path])
        self.assertEqual(records["/shopify_target_state/metafields/neckline"], "exclusive trim")


if __name__ == "__main__":
    unittest.main()
