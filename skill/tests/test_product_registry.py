"""Run-local registration regression tests. All approvals here are synthetic test data."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from product_listing.listing_plan_projection_registry import verify_projection_manifest, sha256_bytes, _binding_from_record
from product_listing.listing_plan_models import ListingPlan
from product_listing.listing_plan_validation import DEFAULT_PHASE_2_LOCK
from product_listing.listing_plan_cli import main as validate_cli
from product_listing.listing_plan_validation import _source_capture_evidence_issues
from product_listing.evidence import canonical_json_bytes as source_json
from product_listing.product_registry_cli import register_product
from product_listing.artifact_paths import locked_skill_file
from test_listing_plan_contract import golden_replay, load_example


class ProductRegistryTests(unittest.TestCase):
    def test_source_option_metadata_survives_reviewed_record_reconstruction(self):
        manifest = json.loads((ROOT / "tests/oracles/fact-packets/nobodys-child-calloway.fact-packet-projection-v2.expected.json").read_text())
        record = next(record for record in manifest["records"] if record["fact_packet_fact_id"] == "fp.options.size")
        record.update(source_option_name="Size", source_option_position=1)
        binding = _binding_from_record(record)
        self.assertEqual(binding["source_option_name"], "Size")
        self.assertEqual(binding["source_option_position"], 1)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lock = json.loads(DEFAULT_PHASE_2_LOCK.read_text())
        old = self.lock["fact_packet_projection_dependency"]
        self.manifest = json.loads(locked_skill_file(old["manifest_path"]).read_text())
        self.review = json.loads(locked_skill_file(old["atlas_lock_path"]).read_text())
        self.manifest["manifest_id"] = "TEST-ONLY-new-registration"
        self.manifest["actors"]["author_auditor"]["actor_id"] = "TEST-ONLY-author"
        self.manifest["actors"]["required_reviewer_signatory"]["actor_id"] = "TEST-ONLY-reviewer"
        self.review["reviewer_signatory"].update(actor_id="TEST-ONLY-reviewer",
            distinct_from_author_actor_id="TEST-ONLY-author")
        self.review["manifest"].update(manifest_id=self.manifest["manifest_id"],
            author_actor_id="TEST-ONLY-author", reviewer_actor_id="TEST-ONLY-reviewer")
        self.capture = golden_replay()
        self.capture_path = self.root / "capture.json"
        self.capture_path.write_text(self.capture.model_dump_json())
        self.manifest_path = self.root / "candidate.json"
        self.review_path = self.root / "review.json"
        self.write_pair()

    def write_pair(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.review["manifest"]["sha256"] = sha256_bytes(self.manifest_path.read_bytes())
        self.review_path.write_text(json.dumps(self.review))

    def register(self):
        return register_product(self.manifest_path, self.review_path, self.capture_path,
                                self.root / "registered", "TEST-ONLY-reviewer")

    def verify(self, receipt, mutate=None, sha=None):
        doc = load_example()
        for section in (doc["evidence"], doc["fact_packet_projection"]):
            if section is doc["evidence"]:
                section["fact_packet_projection_manifest_id"] = receipt["manifest_id"]
                section["fact_packet_projection_manifest_sha256"] = receipt["manifest_sha256"]
            else:
                section["manifest_id"] = receipt["manifest_id"]
                section["manifest_sha256"] = receipt["manifest_sha256"]
        if mutate:
            mutate(doc)
        return verify_projection_manifest(ListingPlan.model_validate(doc), doc,
            self.lock, ROOT, self.capture.source_capture,
            product_registry_path=Path(receipt["registry"]),
            product_registry_sha256=sha or receipt["registry_sha256"])

    def test_new_id_accepted_in_normal_mode_without_lock_edits(self):
        receipt = self.register()
        self.assertEqual([], self.verify(receipt))
        self.assertFalse(receipt["listing_validated"])
        self.assertFalse(receipt["shopify_written"])
        with self.assertRaises(FileExistsError):
            self.register()

    def test_self_review_rejected_before_output(self):
        self.manifest["actors"]["author_auditor"]["actor_id"] = "TEST-ONLY-reviewer"
        self.write_pair()
        with self.assertRaisesRegex(ValueError, "independent"):
            self.register()
        self.assertFalse((self.root / "registered").exists())

    def test_unapproved_review_rejected(self):
        self.review["reviewer_signatory"]["approval_status"] = "PENDING"
        self.write_pair()
        with self.assertRaisesRegex(ValueError, "independent"):
            self.register()

    def test_changed_source_pins_rejected(self):
        self.manifest["source_capture"]["output_sha256"] = "0" * 64
        self.write_pair()
        with self.assertRaisesRegex(ValueError, "SourceCapture"):
            self.register()

    def test_changed_registry_rejected(self):
        receipt = self.register()
        path = Path(receipt["registry"])
        path.write_bytes(path.read_bytes() + b" ")
        self.assertIn("hash mismatch", self.verify(receipt)[0].message)

    def test_reordered_binding_rejected(self):
        receipt = self.register()
        issues = self.verify(receipt, lambda doc: doc["fact_packet_projection"]["bindings"].reverse())
        self.assertIn("FACT_PACKET_PROJECTION_BINDINGS_MISMATCH", [i.code for i in issues])

    def test_changed_review_rejected(self):
        receipt = self.register()
        (Path(receipt["registry"]).parent / "review.json").write_text("{}")
        self.assertIn("hash mismatch", self.verify(receipt)[0].message)

    def test_malformed_review_returns_blocking_issue(self):
        receipt = self.register()
        registry_path = Path(receipt["registry"])
        review_path = registry_path.parent / "review.json"
        value = json.loads(review_path.read_text())
        value["reviewer_signatory"] = ["invalid"]
        review_path.write_text(json.dumps(value))
        registry = json.loads(registry_path.read_text())
        registry["fact_packet_projection_registry"][0]["atlas_lock_sha256"] = sha256_bytes(review_path.read_bytes())
        registry_path.write_text(json.dumps(registry))
        issues = self.verify(receipt, sha=sha256_bytes(registry_path.read_bytes()))
        self.assertTrue(issues)
        self.assertTrue(all(issue.blocking for issue in issues))

    def test_rehashed_invalid_capture_cannot_self_declare_valid(self):
        payload = self.capture.model_dump(mode="json", exclude_none=False)
        payload["source_capture"]["consumer_retail_source"] = False
        payload["determinism_sha256"] = sha256_bytes(source_json(payload["source_capture"]))
        doc = load_example()
        doc["evidence"]["source_capture_sha256"] = sha256_bytes(source_json(payload) + b"\n")
        doc["evidence"]["source_capture_determinism_sha256"] = payload["determinism_sha256"]
        _, issues = _source_capture_evidence_issues(ListingPlan.model_validate(doc), payload, False)
        self.assertTrue(any("INVALID_SOURCE_CLASS" in issue.message for issue in issues))

    def test_registry_path_escape_rejected_even_with_new_pin(self):
        receipt = self.register()
        path = Path(receipt["registry"])
        value = json.loads(path.read_text())
        value["fact_packet_projection_registry"][0]["manifest_path"] = "../candidate.json"
        path.write_text(json.dumps(value))
        self.assertIn("escapes", self.verify(receipt, sha=sha256_bytes(path.read_bytes()))[0].message)

    def test_cli_wires_registry_and_preserves_other_stops(self):
        receipt = self.register()
        doc = load_example()
        doc["evidence"].update(fact_packet_projection_manifest_id=receipt["manifest_id"],
                              fact_packet_projection_manifest_sha256=receipt["manifest_sha256"])
        doc["fact_packet_projection"].update(manifest_id=receipt["manifest_id"],
                                             manifest_sha256=receipt["manifest_sha256"])
        path = self.root / "plan.json"
        path.write_text(json.dumps(doc))
        output = io.StringIO()
        with redirect_stdout(output):
            result = validate_cli([str(path), "--source-capture", str(self.capture_path),
                "--product-registry", receipt["registry"],
                "--product-registry-sha256", receipt["registry_sha256"]])
        report = json.loads(output.getvalue())
        self.assertEqual(2, result)  # Historical composition still cannot commit.
        codes = {issue["code"] for issue in report["issues"]}
        self.assertNotIn("FACT_PACKET_PROJECTION_MANIFEST_INVALID", codes)
        self.assertIn("PROFILE_HASH_MISMATCH", codes)
