"""Deterministic replay tests against Scout's read-only signed bundle."""

import json
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "phase-eight-avenly"
CALLOWAY_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "nobodys-child-calloway"
ORACLE_DIR = Path(__file__).resolve().parent / "oracles"
CALLOWAY_ORACLE = ORACLE_DIR / "nobodys-child-calloway.expected.json"
ATLAS_LOCK = ORACLE_DIR / "aggregate-manifest-v2.atlas-lock.json"
ATLAS_LOCK_SHA256 = "0bf1135a067f07363b6eacb0e0e942a8e5e6a45f96b6347a3f56b7c453cccc9b"
sys.path.insert(0, str(SCRIPTS_DIR))

from product_listing.errors import PipelineStop  # noqa: E402
from product_listing.evidence import canonical_json_bytes  # noqa: E402
from product_listing.replay import replay_bundle  # noqa: E402


def all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key.lower()
            yield from all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_keys(child)


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def locked_blocker_expectations():
    if hashlib.sha256(ATLAS_LOCK.read_bytes()).hexdigest() != ATLAS_LOCK_SHA256:
        raise AssertionError("Atlas lock hash drifted")
    lock = json.loads(ATLAS_LOCK.read_text(encoding="utf-8"))
    aggregate_record = lock["aggregate_manifest"]
    aggregate_path = ORACLE_DIR / aggregate_record["path"]
    if hashlib.sha256(aggregate_path.read_bytes()).hexdigest() != aggregate_record["sha256"]:
        raise AssertionError("Atlas-pinned aggregate hash drifted")
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    expected = {}
    for item in aggregate["expected_blocker_fixtures"]:
        expected[item["fixture_id"]] = set(item["expected_codes"])
    for item in aggregate["incomplete_acquisition_denominators"]:
        expected[item["fixture_id"]] = set(item["blocking_gap_codes"])
    return expected


def build_positive_bundle(root):
    bundle = {
        "schema": "source-capture-fixture-v1",
        "capture": {
            "requested_url": "https://example.test/products/calloway",
            "final_url": "https://example.test/products/calloway",
            "canonical_url": "https://example.test/products/calloway",
            "market": "GB",
            "currency": "GBP",
            "captured_at": "2026-09-01T10:00:00Z",
        },
        "files": {
            "structured_product": "structured-product.json",
            "sections": "sections.json",
            "size_guide": "size-guide.json",
            "media": "media-manifest.json",
            "evidence": "evidence-registry.json",
        },
        "conflicts": [],
        "acquisition_gaps": [],
        "absences": [],
        "verdict": "POSITIVE_DENOMINATOR",
    }
    payloads = {
        "bundle.json": bundle,
        "structured-product.json": {
            "source_class": "CONSUMER_RETAILER",
            "title": "Calloway Dress",
            "vendor": "Example Retailer",
            "currency": "GBP",
            "price": {"current": "79.00", "compare_at": None},
            "options": [{"name": "Size", "values": ["8", "10"]}],
            "real_variant_combinations": [["8"], ["10"]],
        },
        "sections.json": {
            "sections": [
                {
                    "order": 1,
                    "source_heading": "Description",
                    "blocks": [{"kind": "paragraph", "occurrence": 1, "text": "Source evidence."}],
                }
            ],
            "expected_section_absences": [],
        },
        "size-guide.json": {"basis": "UNSTATED", "tables": [], "footnotes": []},
        "media-manifest.json": {
            "colour_association": "Green",
            "rendered_gallery": [
                {
                    "order": 1,
                    "url": "https://cdn.example.test/rendered.jpg",
                    "content_sha256": "1" * 64,
                    "excluded": False,
                }
            ],
            "structured_gallery": [
                {
                    "order": 1,
                    "url": "https://cdn.example.test/structured.jpg",
                    "content_sha256": "2" * 64,
                    "excluded": False,
                }
            ],
        },
        "evidence-registry.json": {},
    }
    for filename, payload in payloads.items():
        write_json(root / filename, payload)
    (root / "rendered.sanitized.html").write_text("<html></html>", encoding="utf-8")
    signed_names = sorted(list(payloads) + ["rendered.sanitized.html"])
    lines = []
    for filename in signed_names:
        digest = hashlib.sha256((root / filename).read_bytes()).hexdigest()
        lines.append("%s  %s" % (digest, filename))
    (root / "bundle-files.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


class OfflineReplayTest(unittest.TestCase):
    def test_atlas_locked_calloway_positive_denominator_exact_parity(self):
        self.assertEqual(hashlib.sha256(ATLAS_LOCK.read_bytes()).hexdigest(), ATLAS_LOCK_SHA256)
        lock = json.loads(ATLAS_LOCK.read_text(encoding="utf-8"))
        positive = lock["positive_denominator"]
        pinned = {
            ORACLE_DIR / lock["aggregate_manifest"]["path"]: lock["aggregate_manifest"]["sha256"],
            (ORACLE_DIR / positive["bundle_path"]).resolve(): positive["bundle_sha256"],
            (ORACLE_DIR / positive["bundle_hash_index_path"]).resolve(): positive["bundle_hash_index_sha256"],
            ORACLE_DIR / positive["oracle_path"]: positive["oracle_sha256"],
            ORACLE_DIR / lock["predecessor"]["path"]: lock["predecessor"]["sha256"],
            ORACLE_DIR / lock["validator"]["path"]: lock["validator"]["sha256"],
        }
        for path, expected in pinned.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected, str(path))

        first = replay_bundle(CALLOWAY_FIXTURE_DIR)
        second = replay_bundle(CALLOWAY_FIXTURE_DIR)
        oracle = json.loads(CALLOWAY_ORACLE.read_text(encoding="utf-8"))["expected"]

        self.assertTrue(first.valid)
        self.assertEqual(first.issues, [])
        self.assertEqual(first.determinism_sha256, second.determinism_sha256)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertEqual(
            first.source_capture.locked_denominator.model_dump(mode="json"),
            oracle,
        )

        capture = first.source_capture
        self.assertEqual(capture.locale, oracle["capture"]["locale"])
        self.assertEqual(capture.capture_attempt, oracle["capture"]["attempt"])
        self.assertEqual(capture.rendered_capture, oracle["capture"]["rendered_html"])
        self.assertEqual(capture.json_ld_capture, oracle["capture"]["json_ld"])
        self.assertEqual(capture.same_session_commerce, oracle["capture"]["same_session_commerce_json"])
        self.assertEqual(capture.structured_product_evidence, oracle["structured_product"])
        self.assertEqual(capture.size_guide_evidence, oracle["size_guide"])
        self.assertEqual(capture.media_manifest_evidence, oracle["media"])
        self.assertEqual(capture.evidence_only_exclusions, oracle["evidence_only_exclusions"])
        self.assertEqual([section.role.value for section in capture.sections[:4]], [
            "DESCRIPTION", "DETAILS", "COMPOSITION_AND_CARE", "RETAILER_POLICY_EVIDENCE_ONLY"
        ])
        self.assertEqual(
            [block.kind for block in capture.sections[1].blocks].count("bullet"),
            12,
        )
        self.assertEqual(len(capture.variants), 16)
        self.assertEqual(capture.variants[0].source_variant_id, oracle["structured_product"]["variants"][0]["id"])
        self.assertEqual(capture.variants[0].source_sku, oracle["structured_product"]["variants"][0]["sku"])
        self.assertEqual(capture.variants[0].source_barcode, oracle["structured_product"]["variants"][0]["barcode"])
        self.assertEqual(capture.variants[0].source_available, oracle["structured_product"]["variants"][0]["available"])
        self.assertEqual(capture.variants[0].source_weight_grams, oracle["structured_product"]["variants"][0]["weight_grams"])
        self.assertEqual(capture.source_model_evidence[0].source_line, oracle["structured_product"]["source_model"]["source_line"])
        self.assertEqual(capture.source_model_evidence[0].wearing_length, oracle["structured_product"]["source_model"]["wearing_length"])
        self.assertEqual(len(capture.media_exclusions), 5)
        self.assertEqual(len(capture.explicit_absences), 5)
        forbidden = {
            "shopify_target_state",
            "target_availability",
            "target_inventory",
            "inventory_quantity",
            "inventory_policy",
            "inventory_management",
            "media_plan",
            "higgsfield_target",
            "ondine_model_sentence",
            "composed_model_sentence",
        }
        self.assertTrue(forbidden.isdisjoint(set(all_keys(capture.model_dump(mode="json")))))

    def test_phase_eight_replays_fail_closed_and_deterministically(self):
        first = replay_bundle(FIXTURE_DIR)
        second = replay_bundle(FIXTURE_DIR)

        self.assertFalse(first.valid)
        self.assertEqual(first.determinism_sha256, second.determinism_sha256)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertEqual(
            {issue.code for issue in first.issues},
            locked_blocker_expectations()["phase-eight-avenly"],
        )

        capture = first.source_capture
        self.assertEqual([option.name for option in capture.options], ["Size"])
        self.assertEqual(len(capture.variants), 9)
        self.assertEqual(len(capture.rendered_media), 8)
        self.assertEqual(len(capture.structured_media), 8)
        self.assertEqual(len(capture.size_guide_table_ids), 3)

        forbidden = {
            "target_availability",
            "target_inventory",
            "inventory_quantity",
            "inventory_policy",
            "inventory_management",
            "media_plan",
            "higgsfield_target",
            "ondine_model_sentence",
        }
        self.assertTrue(forbidden.isdisjoint(set(all_keys(capture.model_dump(mode="json")))))

    def test_all_current_denominators_replay_fail_closed_twice(self):
        for fixture_name, expected_codes in locked_blocker_expectations().items():
            with self.subTest(fixture=fixture_name):
                fixture = FIXTURE_DIR.parent / fixture_name
                first = replay_bundle(fixture)
                second = replay_bundle(fixture)
                self.assertFalse(first.valid)
                self.assertEqual(first.determinism_sha256, second.determinism_sha256)
                self.assertEqual({issue.code for issue in first.issues}, expected_codes)
                if fixture_name == "omnes-bridie-sunset-blur":
                    conflict = next(
                        item for item in first.source_capture.conflicts
                        if item.code == "MATERIAL_POLYESTER_VS_VISCOSE"
                    )
                    self.assertEqual(conflict.field_path, "material_composition")
                    self.assertEqual(len(conflict.values), 2)
                    self.assertEqual(
                        conflict.blocked_output_ids,
                        ["listing.claim.material_composition", "listing.metafield.fabric"],
                    )
                if fixture_name == "nfd-abstract-tilly":
                    relations = first.source_capture.colour_relations
                    self.assertEqual(len(relations), 6)
                    self.assertTrue(all(item.capture_status.value == "UNOPENED" for item in relations))

    def test_same_bundle_interface_can_replay_a_positive_denominator(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            build_positive_bundle(fixture)
            first = replay_bundle(fixture)
            second = replay_bundle(fixture)
            self.assertTrue(first.valid)
            self.assertEqual(first.issues, [])
            self.assertEqual(first.determinism_sha256, second.determinism_sha256)

    def test_hash_mismatch_stops_before_parsing(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "phase-eight-avenly"
            shutil.copytree(FIXTURE_DIR, copied)
            structured = copied / "structured-product.json"
            payload = json.loads(structured.read_text(encoding="utf-8"))
            payload["title"] = "tampered"
            structured.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PipelineStop, "signed artifact hash does not match"):
                replay_bundle(copied)

    def test_bundle_json_is_the_only_entrypoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            (fixture / "fixture.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(PipelineStop, "bundle.json is required"):
                replay_bundle(fixture)


if __name__ == "__main__":
    unittest.main()
