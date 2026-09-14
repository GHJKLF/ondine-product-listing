"""Authoritative RFC 8785 vectors and locked Phase 2 hash regressions."""

import hashlib
import io
import json
import math
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
PROFILE_DIR = SKILL_ROOT / "profiles" / "ondine"
CALLOWAY_BUNDLE = Path(__file__).resolve().parent / "fixtures" / "nobodys-child-calloway"
CALLOWAY_MANIFEST = (
    Path(__file__).resolve().parent
    / "oracles"
    / "fact-packets"
    / "nobodys-child-calloway.fact-packet-projection-v2.expected.json"
)
sys.path.insert(0, str(SCRIPTS_DIR))

from product_listing.listing_plan_canonical_json import (  # noqa: E402
    CanonicalizationError,
    canonical_json_bytes,
)
from product_listing.listing_plan_copy_guard import build_copy_guard_result  # noqa: E402
from product_listing.listing_plan_cli import main as listing_plan_cli_main  # noqa: E402
from product_listing.listing_plan_validation import (  # noqa: E402
    validate_listing_plan_document,
)
from product_listing.replay import replay_bundle  # noqa: E402
from test_listing_plan_contract import committable_document  # noqa: E402


def float_from_hex(value: str) -> float:
    return struct.unpack(">d", bytes.fromhex(value))[0]


def binding(document, fact_id):
    return next(
        item
        for item in document["fact_packet_projection"]["bindings"]
        if item["fact_packet_fact_id"] == fact_id
    )


def invalid_i_json_documents():
    cases = []
    for name, value in (
        ("price_nan", math.nan),
        ("price_positive_infinity", math.inf),
        ("price_negative_infinity", -math.inf),
    ):
        document = committable_document()
        binding(document, "fp.current_customer_paid_price_gbp")["value"] = value
        cases.append((name, document))

    nested = committable_document()
    binding(nested, "fp.fabric_structure")["value"] = {
        "unused": [{"nested": math.nan}]
    }
    cases.append(("unused_nested_any_nan", nested))

    unsafe_integer = committable_document()
    binding(unsafe_integer, "fp.fabric_structure")["value"] = 1 << 53
    cases.append(("unsafe_integer_boundary", unsafe_integer))
    return cases


class ListingPlanCanonicalJsonTest(unittest.TestCase):
    def test_rfc_8785_appendix_b_ieee_754_vectors(self):
        vectors = (
            ("0000000000000000", "0"),
            ("8000000000000000", "0"),
            ("0000000000000001", "5e-324"),
            ("8000000000000001", "-5e-324"),
            ("7fefffffffffffff", "1.7976931348623157e+308"),
            ("ffefffffffffffff", "-1.7976931348623157e+308"),
            ("4340000000000000", "9007199254740992"),
            ("c340000000000000", "-9007199254740992"),
            ("4430000000000000", "295147905179352830000"),
            ("44b52d02c7e14af5", "9.999999999999997e+22"),
            ("44b52d02c7e14af6", "1e+23"),
            ("44b52d02c7e14af7", "1.0000000000000001e+23"),
            ("444b1ae4d6e2ef4e", "999999999999999700000"),
            ("444b1ae4d6e2ef4f", "999999999999999900000"),
            ("444b1ae4d6e2ef50", "1e+21"),
            ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
            ("3eb0c6f7a0b5ed8d", "0.000001"),
            ("41b3de4355555553", "333333333.3333332"),
            ("41b3de4355555554", "333333333.33333325"),
            ("41b3de4355555555", "333333333.3333333"),
            ("41b3de4355555556", "333333333.3333334"),
            ("41b3de4355555557", "333333333.33333343"),
            ("becbf647612f3696", "-0.0000033333333333333333"),
            ("43143ff3c1cb0959", "1424953923781206.2"),
        )
        for encoded, expected in vectors:
            with self.subTest(ieee_754=encoded):
                self.assertEqual(
                    canonical_json_bytes(float_from_hex(encoded)),
                    expected.encode("ascii"),
                )

    def test_required_number_boundaries_and_non_finite_rejection(self):
        self.assertEqual(
            canonical_json_bytes({"x": 1e20, "y": 1e-7, "z": -0.0}),
            b'{"x":100000000000000000000,"y":1e-7,"z":0}',
        )
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(CanonicalizationError):
                    canonical_json_bytes(value)

    def test_rfc_8785_string_literals_and_utf16_key_order(self):
        sample = {
            "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27],
            "string": "€$\x0f\nA'B\"\\\"/",
            "literals": [None, True, False],
        }
        expected = (
            '{"literals":[null,true,false],'
            '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
            '"string":"€$\\u000f\\nA\'B\\\"\\\\\\\"/"}'
        ).encode("utf-8")
        self.assertEqual(canonical_json_bytes(sample), expected)

        keys = {
            "€": "Euro Sign",
            "\r": "Carriage Return",
            "דּ": "Hebrew Letter Dalet With Dagesh",
            "1": "One",
            "😀": "Emoji: Grinning Face",
            "\u0080": "Control",
            "ö": "Latin Small Letter O With Diaeresis",
        }
        expected_order = ["\r", "1", "\u0080", "ö", "€", "😀", "דּ"]
        encoded = canonical_json_bytes(keys).decode("utf-8")
        self.assertEqual(list(json.loads(encoded)), expected_order)
        with self.assertRaises(CanonicalizationError):
            canonical_json_bytes("\ud800")

    def test_current_calloway_binding_copy_guard_policy_and_plan_hashes_do_not_move(self):
        manifest = json.loads(CALLOWAY_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(canonical_json_bytes(manifest["bindings"])).hexdigest(),
            "7b89952844b9de29083fe5ec943adff7ed1fb23ab19a52a3987e0340bf95ce95",
        )

        document = json.loads(
            (PROFILE_DIR / "listing-plan.example.json").read_text(encoding="utf-8")
        )
        replay = replay_bundle(CALLOWAY_BUNDLE)
        declared = document["originality"]["copy_guard_result"]
        recomputed = build_copy_guard_result(
            document,
            replay.source_capture,
            document["evidence"]["source_capture_sha256"],
            CALLOWAY_BUNDLE,
            declared["exemptions"],
        )
        self.assertEqual(recomputed, declared)
        self.assertEqual(
            recomputed["source_corpus_sha256"],
            "c4de75e35e90c49e4bbd790b8b984b62e6f0b6535ee22d47d37523a6e15bb61f",
        )
        self.assertEqual(
            recomputed["target_corpus_sha256"],
            "1a77d4833f8143385d84de919d2341fb87db2a6e7b2667854c3e62e91324d936",
        )
        self.assertEqual(
            recomputed["report_sha256"],
            "70541a38a223ed420ae878360f15950171cd4ad4674317d6d061995a9f1d177f",
        )
        self.assertEqual(
            hashlib.sha256(canonical_json_bytes(document)).hexdigest(),
            "411e4b26d22991ed5ae698fdd9aaba074e6f8401de5239fcb3d5705922dc77a4",
        )

        synthetic = committable_document()
        snapshot = synthetic["store_policy_snapshot"]
        self.assertEqual(
            snapshot["delivery"]["content_sha256"],
            "ce20fdd257a7276e7729a5311cc9e0a6c9c980e9accbb621c801b97dc227befd",
        )
        self.assertEqual(
            snapshot["returns_and_refunds"]["content_sha256"],
            "8edac5aef8102825c024b744da47c33fb1a44ebeaa18db82d51a46e51ef855eb",
        )
        snapshot_payload = dict(snapshot)
        snapshot_payload.pop("canonical_sha256")
        self.assertEqual(
            snapshot["canonical_sha256"],
            "c884707a1483f252e69b92a447f59a30f62541662e2165cf42905d0f06f5610f",
        )
        self.assertEqual(
            hashlib.sha256(canonical_json_bytes(snapshot_payload)).hexdigest(),
            snapshot["canonical_sha256"],
        )

    def test_validator_stops_before_semantic_validation_for_non_i_json(self):
        with patch(
            "product_listing.listing_plan_validation._price_issues",
            side_effect=AssertionError("price validation must not run"),
        ) as price_issues, patch(
            "product_listing.listing_plan_validation._transform_application_issues",
            side_effect=AssertionError("transform validation must not run"),
        ) as transform_issues:
            for name, document in invalid_i_json_documents():
                with self.subTest(case=name):
                    report = validate_listing_plan_document(document)
                    self.assertFalse(report.schema_valid)
                    self.assertFalse(report.committable)
                    self.assertIsNone(report.listing_plan_sha256)
                    self.assertEqual(
                        [issue.code for issue in report.issues],
                        ["LISTING_PLAN_CANONICALIZATION_INVALID"],
                    )
            price_issues.assert_not_called()
            transform_issues.assert_not_called()

    def test_normal_cli_stops_cleanly_and_deterministically_for_non_i_json(self):
        with patch(
            "product_listing.listing_plan_validation._price_issues",
            side_effect=AssertionError("price validation must not run"),
        ) as price_issues, patch(
            "product_listing.listing_plan_validation._transform_application_issues",
            side_effect=AssertionError("transform validation must not run"),
        ) as transform_issues, tempfile.TemporaryDirectory() as directory:
            for name, document in invalid_i_json_documents():
                with self.subTest(case=name):
                    path = Path(directory) / (name + ".json")
                    path.write_text(
                        json.dumps(
                            document,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=True,
                        ),
                        encoding="utf-8",
                    )
                    outputs = []
                    for _ in range(2):
                        output = io.StringIO()
                        with redirect_stdout(output):
                            exit_code = listing_plan_cli_main([str(path)])
                        self.assertEqual(exit_code, 2)
                        result = json.loads(output.getvalue())
                        self.assertFalse(result["schema_valid"])
                        self.assertFalse(result["committable"])
                        self.assertIsNone(result["listing_plan_sha256"])
                        self.assertEqual(
                            [issue["code"] for issue in result["issues"]],
                            ["LISTING_PLAN_CANONICALIZATION_INVALID"],
                        )
                        outputs.append(output.getvalue())
                    self.assertEqual(outputs[0], outputs[1])
            price_issues.assert_not_called()
            transform_issues.assert_not_called()


if __name__ == "__main__":
    unittest.main()
