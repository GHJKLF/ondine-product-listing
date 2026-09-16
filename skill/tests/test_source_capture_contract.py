"""Focused guard tests for the evidence-only SourceCapture boundary."""

import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from product_listing.cli import main as cli_main  # noqa: E402
from product_listing.models import SourceCapture, ValidationIssue  # noqa: E402


CAPTURED_AT = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
ZERO_SHA = "0" * 64


def minimal_capture():
    return {
        "schema_version": "1.0.0",
        "capture_id": "fixture-minimal",
        "requested_url": "https://example.test/products/dress",
        "final_url": "https://example.test/products/dress",
        "canonical_url": "https://example.test/products/dress",
        "captured_at": CAPTURED_AT,
        "market": "GB",
        "currency": "GBP",
        "consumer_retail_source": True,
        "source_class_evidence": {
            "consumer_retail_source": True,
            "locator": "fixture.json#/source_class_evidence",
            "rationale": "Public consumer retail PDP",
        },
        "artifacts": [
            {
                "artifact_id": "rendered",
                "kind": "rendered_html",
                "relative_path": "rendered.html",
                "media_type": "text/html",
                "sha256": ZERO_SHA,
            }
        ],
        "expected_section_roles": [],
        "expected_role_absences": [],
        "title": "Evidence Dress",
        "current_price": "59.40",
        "facts": [],
        "sections": [],
        "size_guide_table_ids": [],
        "fit_occurrences": [],
        "source_model_evidence": [],
        "options": [],
        "variants": [],
        "rendered_media": [],
        "structured_media": [],
        "colour_relations": [],
        "conflicts": [],
        "acquisition_gaps": [],
        "explicit_absences": [],
    }


def atomic_fact(value):
    return {
        "fact_id": "semantic-key-guard",
        "field_path": "source.note",
        "value": value,
        "fact_kind": "COMMERCE",
        "source": "MANIFEST",
        "locator": "fixture.json#/semantic-key-guard",
        "captured_at": CAPTURED_AT,
        "scope": "source_product",
        "allowed_transform_ids": [],
    }


class SourceCaptureContractTest(unittest.TestCase):
    def test_minimal_evidence_contract_parses(self):
        capture = SourceCapture.model_validate(minimal_capture())
        self.assertEqual(capture.currency, "GBP")

    def test_target_and_inventory_keys_are_rejected_recursively(self):
        payload = minimal_capture()
        payload["facts"] = [atomic_fact({"inventory_quantity": 12})]
        with self.assertRaisesRegex(ValidationError, "forbidden target/inventory key"):
            SourceCapture.model_validate(payload)

    def test_semantic_key_spellings_are_rejected_at_nested_dict_list_depth(self):
        forbidden_keys = (
            "inventoryQuantity",
            "inventory-quantity",
            "targetAvailability",
            "MediaPlan",
            "media-plan",
            "higgsfield",
            "higgsfieldJob",
            "composedTargetModel",
        )
        for key in forbidden_keys:
            with self.subTest(key=key):
                payload = minimal_capture()
                payload["facts"] = [atomic_fact({"safe": [{"nested": {key: "forbidden"}}]})]
                with self.assertRaisesRegex(ValidationError, "forbidden target/inventory key"):
                    SourceCapture.model_validate(payload)

    def test_separator_free_prefix_and_ancestor_split_target_state_is_rejected(self):
        forbidden_values = (
            ("mediaPlanState", {"mediaPlanState": "forbidden"}),
            ("media_plan_state", {"media_plan_state": "forbidden"}),
            ("mediaplan", {"mediaplan": "forbidden"}),
            ("targetavailability", {"targetavailability": False}),
            ("inventoryquantity", {"inventoryquantity": 12}),
            ("higgsfieldjob", {"higgsfieldjob": "forbidden"}),
            ("composedtargetmodel", {"composedtargetmodel": "forbidden"}),
            ("shopifyTargetStatePayload", {"shopifyTargetStatePayload": {}}),
            ("target/availability", {"target": {"availability": False}}),
            ("inventory/quantity", {"inventory": {"quantity": 12}}),
        )
        for case, value in forbidden_values:
            with self.subTest(case=case):
                payload = minimal_capture()
                payload["facts"] = [atomic_fact({"safe": [{"nested": value}]})]
                with self.assertRaisesRegex(ValidationError, "forbidden target/inventory key"):
                    SourceCapture.model_validate(payload)

    def test_namespace_prefix_and_terminal_family_state_is_rejected(self):
        forbidden_values = (
            ("productTargetAvailability", {"productTargetAvailability": False}),
            ("shopifyInventoryQuantity", {"shopifyInventoryQuantity": 12}),
            ("draftMediaPlanState", {"draftMediaPlanState": "draft"}),
            ("shopifyHiggsfieldJob", {"shopifyHiggsfieldJob": "job-1"}),
            ("listingComposedTargetModel", {"listingComposedTargetModel": "forbidden"}),
            ("ondineMediaPlanState", {"ondineMediaPlanState": "draft"}),
            ("shopifyTarget/availability", {"shopifyTarget": {"availability": False}}),
            ("terminal target object", {"target": {}}),
            ("terminal target scalar", {"target": "draft"}),
            ("terminal inventory object", {"inventory": {}}),
            ("terminal inventory scalar", {"inventory": 12}),
        )
        for case, value in forbidden_values:
            with self.subTest(case=case):
                payload = minimal_capture()
                payload["facts"] = [
                    atomic_fact({"safe": [{"deeper": [{"nested": value}]}]})
                ]
                with self.assertRaisesRegex(ValidationError, "forbidden target/inventory key"):
                    SourceCapture.model_validate(payload)

    def test_source_evidence_positive_controls_remain_allowed(self):
        allowed_values = (
            ("source_available", {"source_available": True}),
            ("sourceAvailable", {"sourceAvailable": True}),
            ("source/available", {"source": {"available": True}}),
        )
        for case, value in allowed_values:
            with self.subTest(case=case):
                payload = minimal_capture()
                payload["facts"] = [atomic_fact({"safe": [{"nested": value}]})]
                capture = SourceCapture.model_validate(payload)
                self.assertEqual(capture.facts[0].value["safe"][0]["nested"], value)

    def test_source_model_evidence_cannot_be_target_eligible(self):
        payload = minimal_capture()
        payload["source_model_evidence"] = [
            {
                "evidence_id": "model-1",
                "occurrence_ids": ["fit-1", "fit-2"],
                "model_height": "176 cm",
                "size_worn": "UK 8",
                "scope": "COMPETITOR_ONLY",
                "target_fit_note_eligible": True,
            }
        ]
        with self.assertRaises(ValidationError):
            SourceCapture.model_validate(payload)

    def test_checked_in_json_schema_matches_typed_contract(self):
        schema_path = SCRIPTS_DIR.parent / "schemas" / "source-capture.schema.json"
        self.assertEqual(
            json.loads(schema_path.read_text(encoding="utf-8")),
            SourceCapture.model_json_schema(),
        )

    def test_validate_cli_returns_zero_for_warning_only_result(self):
        capture = SourceCapture.model_validate(minimal_capture())
        warning = ValidationIssue(
            code="NONBLOCKING_WARNING",
            field_path="facts",
            message="review recommended",
            blocking=False,
        )
        with tempfile.TemporaryDirectory() as temporary:
            capture_path = Path(temporary) / "source-capture.json"
            capture_path.write_text(capture.model_dump_json(), encoding="utf-8")
            output = io.StringIO()
            with patch("product_listing.cli.validate_source_capture", return_value=[warning]):
                with redirect_stdout(output):
                    exit_code = cli_main(["validate", str(capture_path)])

        self.assertEqual(exit_code, 0)
        result = json.loads(output.getvalue())
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"][0]["code"], "NONBLOCKING_WARNING")


if __name__ == "__main__":
    unittest.main()
