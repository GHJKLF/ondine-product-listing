"""Offline Phase 2 FactPacket and ListingPlan contract tests."""

import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from functools import lru_cache
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
SCHEMA_DIR = SKILL_ROOT / "schemas"
PROFILE_DIR = SKILL_ROOT / "profiles" / "ondine"
LOCK_PATH = PROFILE_DIR / "phase-2-composition-v5.ilias-lock.json"
EXAMPLE_PATH = PROFILE_DIR / "listing-plan.example.json"
CALLOWAY_BUNDLE = Path(__file__).resolve().parent / "fixtures" / "nobodys-child-calloway"
TEST_PROJECTION_DIR = Path(__file__).resolve().parent / "projection_registry"
LOCK_SHA256 = "6756399bf2afaed3258be318411951a1bf7fc61a9659c9a0ec08362a8445602b"
TEST_PROJECTION_PINS = {
    "size-only": {
        "manifest_id": "synthetic-size-only-fact-packet-projection-test-v1",
        "manifest_path": "tests/projection_registry/synthetic-size-only.fact-packet-projection.expected.json",
        "manifest_sha256": "dccca597fb1b80a8d0284c05bb51cba43a0d033ac4bede73634702fb9ec4fbbf",
        "atlas_lock_path": "tests/projection_registry/synthetic-size-only.fact-packet-projection.atlas-lock.json",
        "atlas_lock_sha256": "d2380df6e544c3d3feb818aad31a71dc946bcc9183f6cdeb97e6cd6c6bd8a1c2",
        "author_actor_id": "Scout-Test-Fixture",
        "reviewer_actor_id": "Atlas-Test-Fixture",
        "ordered_binding_count": 29,
        "ordered_bindings_canonical_sha256": "b8747c5d662a47df831312a8fe145943208f3fd865544f079035a131117ca438",
        "fixture_only": True,
    },
    "size-fit": {
        "manifest_id": "synthetic-size-fit-fact-packet-projection-test-v1",
        "manifest_path": "tests/projection_registry/synthetic-size-fit.fact-packet-projection.expected.json",
        "manifest_sha256": "b3b22bcc60110811ded19127bd3d081bee6f2679f5e01e0433105323d3ab3f8a",
        "atlas_lock_path": "tests/projection_registry/synthetic-size-fit.fact-packet-projection.atlas-lock.json",
        "atlas_lock_sha256": "ccc7e3fc7d2fdabc9c7c17bac5713af5e6ed7434ff6cb19daaf84f2410e859af",
        "author_actor_id": "Scout-Test-Fixture",
        "reviewer_actor_id": "Atlas-Test-Fixture",
        "ordered_binding_count": 30,
        "ordered_bindings_canonical_sha256": "a24496aa0331b6f027a4b8074f2795ebe9e8d7357eabb8abefa26e16b8f1eed7",
        "fixture_only": True,
    },
}
sys.path.insert(0, str(SCRIPTS_DIR))

from product_listing.listing_plan_copy_guard import (  # noqa: E402
    build_copy_guard_result,
)
from product_listing.evidence import (  # noqa: E402
    canonical_json_bytes as phase_1_canonical_json_bytes,
)
from product_listing.listing_plan_canonical_json import canonical_json_bytes  # noqa: E402
from product_listing.listing_plan_models import FactPacket, ListingPlan  # noqa: E402
from product_listing.listing_plan_cli import main as listing_plan_cli_main  # noqa: E402
from product_listing.listing_plan_validation import validate_listing_plan_document  # noqa: E402
from product_listing.models import SourceCapture  # noqa: E402
from product_listing.replay import replay_bundle  # noqa: E402


def load_example():
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def issue_codes(report):
    return [issue.code for issue in report.issues]


@lru_cache(maxsize=1)
def golden_replay():
    return replay_bundle(CALLOWAY_BUNDLE)


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_projection_registry(kind):
    entry = copy.deepcopy(TEST_PROJECTION_PINS[kind])
    return {entry["manifest_id"]: entry}


def bind_test_projection(document, kind):
    entry = TEST_PROJECTION_PINS[kind]
    manifest = json.loads(
        (SKILL_ROOT / entry["manifest_path"]).read_text(encoding="utf-8")
    )
    document["evidence"]["fact_packet_projection_manifest_id"] = entry["manifest_id"]
    document["evidence"]["fact_packet_projection_manifest_sha256"] = entry[
        "manifest_sha256"
    ]
    packet = document["fact_packet_projection"]
    packet["manifest_id"] = entry["manifest_id"]
    packet["manifest_sha256"] = entry["manifest_sha256"]
    packet["bindings"] = copy.deepcopy(manifest["bindings"])


def committable_document():
    document = load_example()
    document["example_status"] = "SYNTHETIC_TEST_ONLY_NOT_LIVE"
    document["flags"] = [
        flag
        for flag in document["flags"]
        if flag["code"] != "STORE_POLICY_SNAPSHOT_REQUIRED_AT_COMPOSE"
    ]
    document["store_policy_snapshot"] = {
        "snapshot_id": "test-only-current-policy-2026-09-01",
        "profile_id": "ondine-live-policy-v1",
        "provenance": "SYNTHETIC_TEST_ONLY",
        "test_only": True,
        "status": "CURRENT_AT_COMPOSE",
        "verified_at": "2026-09-01T15:00:00+01:00",
        "delivery": {
            "requested_url": "https://ondinelondon.co.uk/pages/shipping-policy",
            "final_url": "https://ondinelondon.co.uk/pages/shipping-policy",
            "captured_at": "2026-09-01T14:59:00+01:00",
            "heading": "Delivery",
            "content": (
                "Synthetic test-only delivery content for validator coverage. "
                "This is not live store policy."
            ),
            "content_sha256": "",
            "policy_binding": "ondine.delivery.current",
        },
        "returns_and_refunds": {
            "requested_url": "https://ondinelondon.co.uk/pages/returns-refund-policy",
            "final_url": "https://ondinelondon.co.uk/pages/returns-refund-policy",
            "captured_at": "2026-09-01T14:59:00+01:00",
            "heading": "Returns and Refunds",
            "content": (
                "Synthetic test-only returns content for validator coverage. "
                "This is not live store policy."
            ),
            "content_sha256": "",
            "policy_binding": "ondine.returns_and_refunds.current",
        },
        "canonical_sha256": "",
    }
    snapshot = document["store_policy_snapshot"]
    snapshot["delivery"]["content_sha256"] = sha256_text(snapshot["delivery"]["content"])
    snapshot["returns_and_refunds"]["content_sha256"] = sha256_text(
        snapshot["returns_and_refunds"]["content"]
    )
    snapshot_payload = copy.deepcopy(snapshot)
    snapshot_payload.pop("canonical_sha256")
    snapshot["canonical_sha256"] = hashlib.sha256(
        canonical_json_bytes(snapshot_payload)
    ).hexdigest()
    declared = document["originality"]["copy_guard_result"]
    document["originality"]["copy_guard_result"] = build_copy_guard_result(
        document,
        golden_replay().source_capture,
        document["evidence"]["source_capture_sha256"],
        CALLOWAY_BUNDLE,
        declared["exemptions"],
    )
    return document


def second_product_case():
    captured_at = "2026-09-01T12:00:00Z"
    source_url = "https://example-retailer.test/products/reference-garment-2002"
    description_text = (
        "A cobalt midi dress in double gauze cotton with decorative embroidery "
        "and laddering through the fabric."
    )
    details_text = (
        "Round neckline. Sleeveless. A shirred bodice meets an elasticated waist. "
        "Side pockets. Ruffle trim. The skirt is tiered and relaxed. Lightly lined. "
        "Country of Manufacture: India."
    )
    composition_text = (
        "Main: 100% Cotton | Lining: 100% Cotton | Embroidery: 100% Polyester | "
        "Embroidery 2: 73% Polyester, 27% Metallised Fibre. Machine Wash."
    )
    capture = SourceCapture.model_validate(
        {
            "capture_id": "synthetic-size-only-2002",
            "requested_url": source_url,
            "final_url": source_url,
            "canonical_url": source_url,
            "captured_at": captured_at,
            "market": "GB",
            "currency": "GBP",
            "locale": "en-GB",
            "consumer_retail_source": True,
            "source_class_evidence": {
                "consumer_retail_source": True,
                "locator": "synthetic:test-only",
                "rationale": "Explicit offline test-only retailer evidence.",
            },
            "artifacts": [
                {
                    "artifact_id": "bundle",
                    "kind": "bundle",
                    "relative_path": "bundle.json",
                    "media_type": "application/json",
                    "sha256": "a" * 64,
                }
            ],
            "expected_section_roles": [],
            "expected_role_absences": [],
            "title": "Reference Garment 2002",
            "vendor": "Example Retailer",
            "current_price": "79.00",
            "facts": [],
            "sections": [
                {
                    "section_id": "description",
                    "order": 1,
                    "role": "DESCRIPTION",
                    "heading": "Source details",
                    "raw_text": description_text,
                    "raw_text_sha256": sha256_text(description_text),
                    "locator": "synthetic:test-only#description",
                    "blocks": [
                        {
                            "order": 1,
                            "kind": "paragraph",
                            "occurrence": 1,
                            "text": description_text,
                        }
                    ],
                    "tables": [],
                },
                {
                    "section_id": "details",
                    "order": 2,
                    "role": "DETAILS",
                    "heading": "Details",
                    "raw_text": details_text,
                    "raw_text_sha256": sha256_text(details_text),
                    "locator": "synthetic:test-only#details",
                    "blocks": [
                        {"order": 1, "kind": "subheading", "occurrence": 1, "text": "Details"},
                        {"order": 2, "kind": "bullet", "occurrence": 1, "text": "Decorative embroidery"},
                        {"order": 3, "kind": "bullet", "occurrence": 2, "text": "Round neck"},
                        {"order": 4, "kind": "bullet", "occurrence": 3, "text": "Sleeveless"},
                        {"order": 5, "kind": "bullet", "occurrence": 4, "text": "Shirred bodice"},
                        {"order": 6, "kind": "bullet", "occurrence": 5, "text": "Elasticated waist"},
                        {"order": 7, "kind": "bullet", "occurrence": 6, "text": "Side pockets"},
                        {"order": 8, "kind": "bullet", "occurrence": 7, "text": "Relaxed skirt"},
                        {"order": 9, "kind": "bullet", "occurrence": 8, "text": "Tiered skirt"},
                        {"order": 10, "kind": "bullet", "occurrence": 9, "text": "Ruffle trim"},
                        {"order": 11, "kind": "bullet", "occurrence": 10, "text": "Lightly lined"},
                        {"order": 12, "kind": "bullet", "occurrence": 11, "text": "UK numeric sizing"},
                        {"order": 13, "kind": "bullet", "occurrence": 12, "text": "Synthetic test record"},
                        {
                            "order": 14,
                            "kind": "label_value",
                            "occurrence": 1,
                            "label": "Country of Manufacture",
                            "value": "India",
                        },
                    ],
                    "tables": [],
                },
                {
                    "section_id": "composition",
                    "order": 3,
                    "role": "COMPOSITION_AND_CARE",
                    "heading": "Fabric & care",
                    "raw_text": composition_text,
                    "raw_text_sha256": sha256_text(composition_text),
                    "locator": "synthetic:test-only#composition",
                    "blocks": [
                        {
                            "order": 1,
                            "kind": "label_value",
                            "occurrence": 1,
                            "label": "Fabric",
                            "value": (
                                "Main: 100% Cotton | Lining: 100% Cotton | "
                                "Embroidery: 100% Polyester | Embroidery 2: "
                                "73% Polyester, 27% Metallised Fibre"
                            ),
                        },
                        {
                            "order": 2,
                            "kind": "label_value",
                            "occurrence": 2,
                            "label": "Washcare",
                            "value": "Machine Wash",
                        },
                    ],
                    "tables": [],
                }
            ],
            "size_guide_table_ids": [],
            "fit_occurrences": [],
            "source_model_evidence": [],
            "options": [{"name": "Size", "position": 1, "values": ["8", "10"]}],
            "variants": [
                {
                    "source_variant_id": "test-2002-8",
                    "option_values": [{"option_name": "Size", "value": "8"}],
                    "current_price": "79.00",
                    "source_available": True,
                    "source_weight_grams": 340,
                },
                {
                    "source_variant_id": "test-2002-10",
                    "option_values": [{"option_name": "Size", "value": "10"}],
                    "current_price": "79.00",
                    "source_available": False,
                    "source_weight_grams": 340,
                },
            ],
            "rendered_media": [],
            "structured_media": [],
            "colour_relations": [],
            "conflicts": [],
            "acquisition_gaps": [],
            "explicit_absences": [],
            "structured_product_evidence": {
                "product_id": "2002",
                "colour": "Cobalt",
                "product_type": "Dresses",
                "tags": ["end-use:day", "length:midaxi"],
                "seo": {
                    "html_title": "Reference Garment 2002 | Example Retailer",
                    "meta_description": "Captured evidence for garment construction and fit.",
                },
            },
        }
    )
    capture_hash = hashlib.sha256(
        phase_1_canonical_json_bytes(
            capture.model_dump(mode="json", exclude_none=False)
        )
    ).hexdigest()
    document = committable_document()
    document["plan_id"] = "synthetic-generic-size-only-2002"
    document["example_status"] = "SYNTHETIC_GENERIC_TEST_ONLY_NOT_LIVE"
    document["evidence"].update(
        {
            "aggregate_lock_sha256": "b" * 64,
            "oracle_sha256": "c" * 64,
            "source_capture_determinism_sha256": capture_hash,
            "fixture_role": "SYNTHETIC_GENERIC_SIZE_ONLY_TEST",
            "captured_at": captured_at,
            "source_capture_sha256": capture_hash,
        }
    )
    packet = document["fact_packet_projection"]
    packet["source_capture_sha256"] = capture_hash
    packet["source_capture_determinism_sha256"] = capture_hash
    removed = {
        "fp.options.length",
        "fp.source_model.height",
        "fp.source_model.worn_size",
        "fp.source_model.wearing_length",
    }
    packet["bindings"] = [
        binding for binding in packet["bindings"]
        if binding["fact_packet_fact_id"] not in removed
    ]
    bindings = {item["fact_packet_fact_id"]: item for item in packet["bindings"]}
    for binding in bindings.values():
        binding["captured_at"] = captured_at
    bindings["fp.canonical_source_url"]["value"] = source_url
    bindings["fp.canonical_source_url"]["source_fact_or_path"] = "source_capture.canonical_url"
    bindings["fp.source_product_id"]["value"] = "2002"
    bindings["fp.current_customer_paid_price_gbp"]["value"] = "79.00"
    bindings["fp.current_customer_paid_price_gbp"]["source_fact_or_path"] = "source_capture.current_price"
    bindings["fp.options.size"]["value"] = ["8", "10"]
    bindings["fp.real_variant_combinations"]["value"] = [["8"], ["10"]]
    bindings["fp.colour"]["value"] = "Cobalt"
    for fact_id in (
        "fp.material_main",
        "fp.material_lining",
        "fp.material_embroidery",
        "fp.material_embroidery_secondary",
    ):
        bindings[fact_id]["source_fact_or_path"] = "sections[2].blocks[0]"
    bindings["fp.weight_grams"]["scope"] = "all_2_source_variants"

    title = "Cobalt Cotton Midi Day Dress"
    style_code = "CCMDD"
    derived = {item["derived_fact_id"]: item for item in document["derived_facts"]}
    derived["df.approved_new_title"]["value"] = title
    derived["df.target_price_gbp_54_95"].update({"value": "78.95", "input_value": "79.00"})
    derived["df.style_code_necmdd"]["value"] = style_code
    derived["df.colour_code_nvy"]["value"] = "COB"
    identity = "example-retailer.test|2002"
    identity_sha = sha256_text(identity)
    derived["df.canonical_source_identity"].update(
        {"value": identity, "sha256": identity_sha}
    )
    derived["df.source_tag"]["value"] = "source:example-retailer.test-2002"

    composition = document["composition"]
    composition["title"].update({"value": title, "character_count": len(title)})
    composition["pdp_order"]["buy_box"] = [
        "title", "colour", "size_module", "price", "add_to_bag"
    ]
    composition["buy_box"]["colour"]["value"] = "Cobalt"
    composition["buy_box"]["size_module"]["values"] = ["8", "10"]
    composition["buy_box"]["price"]["amount"] = "78.95"
    composition["buy_box"].pop("length_selector")
    composition["description"]["slots"][0]["text"] = (
        "A cobalt cotton midi shape with a softly defined bodice. "
        "Light lining supports an easy daytime silhouette."
    )
    size_fit = composition["below_fold_sections"][1]
    size_fit["items"] = [size_fit["items"][0]]
    size_fit["items"][0]["text"] = "UK sizes 8–10"
    size_fit.pop("omitted_claims", None)

    target = document["shopify_target_state"]
    target["title"] = title
    target["handle"] = "cobalt-cotton-midi-day-dress"
    target["options"] = [
        {
            "name": "Size",
            "position": 1,
            "values": ["8", "10"],
            "fact_ref": "fp.options.size",
        }
    ]
    variant_template = copy.deepcopy(target["variants"][0])
    target["variants"] = []
    for size in ("8", "10"):
        variant = copy.deepcopy(variant_template)
        code = "OND-%s-COB-%03d" % (style_code, int(size))
        variant.update(
            {
                "option_values": {"Size": size},
                "price": "78.95",
                "sku": code,
                "mpn": code,
            }
        )
        target["variants"].append(variant)
    target["option_render_order"] = ["Size"]
    target["identifier_generation"].update(
        {
            "style_code": style_code,
            "colour_code": "COB",
            "additional_option_codes": {},
        }
    )
    target["seo"].update(
        {
            "handle": target["handle"],
            "canonical_path": "/products/" + target["handle"],
            "page_title": "Cobalt Cotton Midi Day Dress for Women | Ondine London",
            "meta_description": (
                "A cobalt cotton midi dress with a softly shaped bodice, easy tiered skirt, "
                "side pockets and light lining for composed everyday dressing in UK sizes 8 to 10."
            ),
        }
    )
    target["seo"]["page_title_character_count"] = len(target["seo"]["page_title"])
    target["seo"]["meta_description_character_count"] = len(
        target["seo"]["meta_description"]
    )
    target["seo"]["input_fact_refs"] = [
        item for item in target["seo"]["input_fact_refs"]
        if item != "fp.options.length"
    ]
    target["gmc"].update(
        {"colour": "Cobalt", "link_path": "/products/" + target["handle"]}
    )
    target["gmc"]["fact_refs"].pop("lengths", None)
    target["tags"] = [
        "midi dress", "cobalt dress", "cotton dress", "tiered dress",
        "sleeveless dress", "round neckline", "shirred bodice", "side pockets",
        "daywear", "lightly lined",
    ]
    target["tags_transform"]["input_fact_refs"] = [
        item for item in target["tags_transform"]["input_fact_refs"]
        if item != "fp.options.length"
    ]
    target["metafields"]["size"] = "UK 8–10"
    target["metafield_fact_refs"]["size"] = ["fp.options.size"]
    ownership = target["private_ownership"]
    ownership["canonical_source_identity_sha256"] = identity_sha
    ownership["internal_tags"][0]["value"] = "source:example-retailer.test-2002"
    for slot in document["MediaPlan"]["slots"]:
        slot["filename"] = slot["filename"].replace("navy-embroidered-cotton-midi-day-dress", target["handle"])
        slot["alt_text"] = slot["alt_text"].replace("Navy", "Cobalt")

    composition_exemptions = [
        item
        for item in load_example()["originality"]["copy_guard_result"]["exemptions"]
        if item["whitelist_rule_id"] == "EXACT_CAPTURED_COMPOSITION_VALUE"
    ]
    document["originality"]["copy_guard_result"] = build_copy_guard_result(
        document,
        capture,
        capture_hash,
        exemptions=composition_exemptions,
    )
    bind_test_projection(document, "size-only")
    return document, capture


def generic_additional_selector_case():
    document, source_capture = second_product_case()
    capture_data = source_capture.model_dump(mode="json", exclude_none=False)
    capture_data["options"].append(
        {"name": "Fit", "position": 2, "values": ["Slim", "Relaxed"]}
    )
    capture_data["variants"][0]["option_values"].append(
        {"option_name": "Fit", "value": "Slim"}
    )
    capture_data["variants"][1]["option_values"].append(
        {"option_name": "Fit", "value": "Relaxed"}
    )
    source_capture = SourceCapture.model_validate(capture_data)
    capture_hash = hashlib.sha256(
        phase_1_canonical_json_bytes(
            source_capture.model_dump(mode="json", exclude_none=False)
        )
    ).hexdigest()
    document["evidence"]["source_capture_sha256"] = capture_hash
    document["evidence"]["source_capture_determinism_sha256"] = capture_hash
    packet = document["fact_packet_projection"]
    packet["source_capture_sha256"] = capture_hash
    packet["source_capture_determinism_sha256"] = capture_hash
    template = next(
        item for item in load_example()["fact_packet_projection"]["bindings"]
        if item["fact_packet_fact_id"] == "fp.options.length"
    )
    fit_binding = copy.deepcopy(template)
    fit_binding.update(
        {
            "fact_packet_fact_id": "fp.options.fit",
            "value": ["Slim", "Relaxed"],
            "source_fact_or_path": "source_capture.options[1]",
            "evidence_locator": "source_capture.options[1]",
            "captured_at": "2026-09-01T12:00:00Z",
        }
    )
    packet["bindings"].append(fit_binding)
    combinations = [["8", "Slim"], ["10", "Relaxed"]]
    next(
        item for item in packet["bindings"]
        if item["fact_packet_fact_id"] == "fp.real_variant_combinations"
    )["value"] = combinations
    target = document["shopify_target_state"]
    target["options"].append(
        {
            "name": "Fit",
            "position": 2,
            "values": ["Slim", "Relaxed"],
            "fact_ref": "fp.options.fit",
        }
    )
    target["option_render_order"] = ["Size", "Fit"]
    target["identifier_generation"]["additional_option_codes"] = {
        "Slim": "SLM",
        "Relaxed": "RLX",
    }
    for variant, row, suffix in zip(target["variants"], combinations, ("SLM", "RLX")):
        variant["option_values"] = {"Size": row[0], "Fit": row[1]}
        variant["sku"] += "-" + suffix
        variant["mpn"] += "-" + suffix
    document["composition"]["buy_box"]["selectors"] = [
        {
            "pdp_order_id": "fit_selector",
            "option_name": "Fit",
            "values": ["Slim", "Relaxed"],
            "fact_ref": "fp.options.fit",
            "selector_order": 2,
        }
    ]
    document["composition"]["pdp_order"]["buy_box"] = [
        "title", "colour", "size_module", "fit_selector", "price", "add_to_bag"
    ]
    exemptions = document["originality"]["copy_guard_result"]["exemptions"]
    document["originality"]["copy_guard_result"] = build_copy_guard_result(
        document,
        source_capture,
        capture_hash,
        exemptions=exemptions,
    )
    bind_test_projection(document, "size-fit")
    return document, source_capture


class ListingPlanContractTest(unittest.TestCase):
    def assert_blocks(self, document, *expected_codes):
        report = validate_listing_plan_document(
            document,
            source_capture_evidence=golden_replay(),
            source_artifact_root=CALLOWAY_BUNDLE,
            test_mode=True,
        )
        self.assertFalse(report.committable)
        for code in expected_codes:
            self.assertIn(code, issue_codes(report))
        return report

    def test_locked_example_is_schema_valid_with_exact_policy_blocker(self):
        self.assertEqual(hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest(), LOCK_SHA256)
        document = load_example()
        ListingPlan.model_validate(document)
        report = validate_listing_plan_document(
            document,
            source_capture_evidence=golden_replay(),
            source_artifact_root=CALLOWAY_BUNDLE,
        )
        self.assertTrue(report.schema_valid)
        self.assertFalse(report.committable)
        self.assertEqual(issue_codes(report), ["STORE_POLICY_SNAPSHOT_REQUIRED_AT_COMPOSE"])

    def test_checked_in_phase_2_schemas_match_typed_contracts(self):
        expected = {
            "fact-packet.schema.json": FactPacket.model_json_schema(),
            "listing-plan.schema.json": ListingPlan.model_json_schema(by_alias=True),
        }
        for filename, schema in expected.items():
            with self.subTest(schema=filename):
                actual = json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))
                self.assertEqual(actual, schema)

    def test_static_generic_projection_registry_pairs_are_hash_pinned(self):
        for kind, entry in TEST_PROJECTION_PINS.items():
            with self.subTest(kind=kind):
                manifest_path = SKILL_ROOT / entry["manifest_path"]
                review_path = SKILL_ROOT / entry["atlas_lock_path"]
                self.assertEqual(
                    hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                    entry["manifest_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256(review_path.read_bytes()).hexdigest(),
                    entry["atlas_lock_sha256"],
                )
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                self.assertEqual(manifest["manifest_id"], entry["manifest_id"])
                self.assertEqual(
                    hashlib.sha256(
                        canonical_json_bytes(manifest["bindings"])
                    ).hexdigest(),
                    entry["ordered_bindings_canonical_sha256"],
                )
                self.assertEqual(len(manifest["bindings"]), entry["ordered_binding_count"])

    def test_synthetic_current_policy_snapshot_is_committable_and_test_only(self):
        document = committable_document()
        report = validate_listing_plan_document(
            document,
            source_capture_evidence=golden_replay(),
            source_artifact_root=CALLOWAY_BUNDLE,
            test_mode=True,
        )
        self.assertTrue(report.schema_valid)
        self.assertTrue(report.committable)
        self.assertEqual(issue_codes(report), [])
        self.assertEqual(
            document["store_policy_snapshot"]["provenance"],
            "SYNTHETIC_TEST_ONLY",
        )
        self.assertTrue(document["store_policy_snapshot"]["test_only"])

    def test_second_product_size_only_plan_is_generic_and_committable_in_test_mode(self):
        document, source_capture = second_product_case()
        self.assertNotEqual(len(document["fact_packet_projection"]["bindings"]), 33)
        self.assertEqual(len(document["shopify_target_state"]["variants"]), 2)
        self.assertEqual(document["shopify_target_state"]["option_render_order"], ["Size"])
        self.assertNotIn("length_selector", document["composition"]["buy_box"])
        report = validate_listing_plan_document(
            document,
            source_capture_evidence=source_capture,
            test_mode=True,
            test_projection_registry=test_projection_registry("size-only"),
            test_projection_registry_root=SKILL_ROOT,
        )
        self.assertTrue(report.schema_valid)
        self.assertTrue(report.committable, [item.model_dump() for item in report.issues])
        self.assertEqual(issue_codes(report), [])

    def test_generic_non_length_selector_preserves_sparse_real_matrix(self):
        document, source_capture = generic_additional_selector_case()
        report = validate_listing_plan_document(
            document,
            source_capture_evidence=source_capture,
            test_mode=True,
            test_projection_registry=test_projection_registry("size-fit"),
            test_projection_registry_root=SKILL_ROOT,
        )
        self.assertTrue(report.committable, [item.model_dump() for item in report.issues])
        self.assertEqual(
            document["composition"]["pdp_order"]["buy_box"],
            ["title", "colour", "size_module", "fit_selector", "price", "add_to_bag"],
        )
        self.assertEqual(
            [item["option_values"] for item in document["shopify_target_state"]["variants"]],
            [{"Size": "8", "Fit": "Slim"}, {"Size": "10", "Fit": "Relaxed"}],
        )

    def test_raw_source_reference_cannot_bypass_fact_packet(self):
        document = committable_document()
        document["derived_facts"][0]["input_fact_ref"] = "source_capture.title"
        self.assert_blocks(document, "RAW_SOURCE_REFERENCE_BYPASS")

    def test_unauthorized_transform_is_rejected(self):
        cases = (
            (
                "derived fact",
                lambda document: next(
                    fact
                    for fact in document["derived_facts"]
                    if fact["transform_id"] == "ondine_price_nearest_95_below_v1"
                ).update({"transform_id": "ondine_seo_copy_v1"}),
            ),
            (
                "direct SEO transform",
                lambda document: document["shopify_target_state"]["seo"].update(
                    {"transform_id": "ondine_tags_v1"}
                ),
            ),
        )
        for name, mutate in cases:
            with self.subTest(case=name):
                document = committable_document()
                mutate(document)
                self.assert_blocks(document, "UNAUTHORIZED_TRANSFORM")

    def test_price_point_95_equality_is_not_strictly_below(self):
        document = committable_document()
        vectors = document["transform_contracts"]["ondine_price_nearest_95_below_v1"]["test_vectors"]
        vectors[2]["output"] = "59.95"
        self.assert_blocks(document, "PRICE_BOUNDARY_VECTOR_INVALID")

    def test_size_above_current_chart_and_more_than_three_dimensions_block(self):
        document = committable_document()
        size_binding = next(
            item for item in document["fact_packet_projection"]["bindings"]
            if item["fact_packet_fact_id"] == "fp.options.size"
        )
        size_binding["value"].append("20")
        self.assert_blocks(document, "SIZE_OUTSIDE_CURRENT_CHART")

        document = committable_document()
        template = next(
            item for item in document["fact_packet_projection"]["bindings"]
            if item["fact_packet_fact_id"] == "fp.options.length"
        )
        for index, name in enumerate(("fit", "sleeve"), start=2):
            binding = copy.deepcopy(template)
            binding["fact_packet_fact_id"] = "fp.options.%s" % name
            binding["source_fact_or_path"] = "source_capture.options[%s]" % index
            binding["evidence_locator"] = binding["source_fact_or_path"]
            binding["value"] = ["A", "B"]
            document["fact_packet_projection"]["bindings"].append(binding)
        self.assert_blocks(document, "OPTION_DIMENSION_LIMIT_EXCEEDED")

    def test_invented_cartesian_variant_is_rejected(self):
        document = committable_document()
        invented = copy.deepcopy(document["shopify_target_state"]["variants"][-1])
        invented["option_values"]["Size"] = "20"
        invented["sku"] = "OND-NECMDD-NVY-020-REG"
        invented["mpn"] = "OND-NECMDD-NVY-020-REG"
        document["shopify_target_state"]["variants"].append(invented)
        self.assert_blocks(document, "INVENTED_OR_MISSING_VARIANT_COMBINATION")

    def test_duplicate_sku_and_mpn_are_rejected(self):
        document = committable_document()
        first = document["shopify_target_state"]["variants"][0]
        second = document["shopify_target_state"]["variants"][1]
        second["sku"] = first["sku"]
        second["mpn"] = first["mpn"]
        self.assert_blocks(document, "DUPLICATE_SKU", "DUPLICATE_MPN")

    def test_customer_source_url_and_tag_leakage_are_rejected(self):
        cases = (
            ("source tag", lambda doc: doc["shopify_target_state"]["tags"].append("source:www.nobodyschild.com-15364155539841")),
            (
                "source URL",
                lambda doc: doc["composition"]["description"]["slots"][0].update(
                    {"text": doc["fact_packet_projection"]["bindings"][1]["value"]}
                ),
            ),
        )
        for name, mutate in cases:
            with self.subTest(case=name):
                document = committable_document()
                mutate(document)
                self.assert_blocks(document, "CUSTOMER_SOURCE_LEAKAGE")

    def test_target_inventory_and_availability_are_rejected_recursively(self):
        for key, code in (
            ("inventoryQuantity", "TARGET_INVENTORY_FORBIDDEN"),
            ("targetAvailability", "TARGET_AVAILABILITY_FORBIDDEN"),
        ):
            with self.subTest(key=key):
                document = committable_document()
                document["shopify_target_state"]["variants"][0][key] = 10
                self.assert_blocks(document, code)

    def test_bad_pdp_order_is_rejected(self):
        document = committable_document()
        order = document["composition"]["pdp_order"]["buy_box"]
        order[-2], order[-1] = order[-1], order[-2]
        self.assert_blocks(document, "PDP_ORDER_INVALID")

    def test_non_draft_and_non_pending_media_states_are_rejected(self):
        cases = (
            ("status", "ACTIVE", "TARGET_STATE_NOT_DRAFT"),
            ("target_media", [{"id": "not-allowed"}], "TARGET_MEDIA_NOT_EMPTY"),
            ("media_status", "READY", "MEDIA_STATUS_INVALID"),
        )
        for key, value, code in cases:
            with self.subTest(key=key):
                document = committable_document()
                document["shopify_target_state"][key] = value
                self.assert_blocks(document, code)

    def test_private_ownership_is_required(self):
        document = committable_document()
        del document["shopify_target_state"]["private_ownership"]
        self.assert_blocks(document, "PRIVATE_OWNERSHIP_INVALID")

    def test_model_text_requires_approved_target_record(self):
        document = committable_document()
        line = document["composition"]["buy_box"]["size_module"]["live_model_line"]
        line.update(
            {
                "render": True,
                "text": "Model is 175 cm and wears UK 8",
                "target_model_record_ref": "target_model.unapproved",
            }
        )
        self.assert_blocks(document, "MODEL_TEXT_REQUIRES_APPROVED_TARGET_RECORD")

    def test_policy_url_content_hash_and_capture_time_are_verified(self):
        cases = (
            (
                "wrong final URL",
                lambda snapshot: snapshot["delivery"].update(
                    {"final_url": "https://example.test/pages/shipping-policy"}
                ),
            ),
            (
                "wrong content hash",
                lambda snapshot: snapshot["returns_and_refunds"].update(
                    {"content_sha256": "0" * 64}
                ),
            ),
            (
                "future capture",
                lambda snapshot: snapshot["delivery"].update(
                    {"captured_at": "2026-09-02T15:00:00+01:00"}
                ),
            ),
        )
        for name, mutate in cases:
            with self.subTest(case=name):
                document = committable_document()
                mutate(document["store_policy_snapshot"])
                self.assert_blocks(document, "STORE_POLICY_SNAPSHOT_INVALID")

    def test_copy_guard_is_recomputed_and_enforces_customer_voice(self):
        document = committable_document()
        document["originality"]["copy_guard_result"]["report_sha256"] = "0" * 64
        self.assert_blocks(document, "COPY_GUARD_RECOMPUTATION_MISMATCH")

        for text in ("A luxury choice!", "Shop now for this dress"):
            with self.subTest(text=text):
                document = committable_document()
                document["composition"]["description"]["slots"][4]["text"] = text
                self.assert_blocks(
                    document,
                    "COPY_GUARD_RECOMPUTATION_MISMATCH",
                    "COPY_GUARD_FAILED",
                )

    def test_projection_manifest_missing_unknown_and_wrong_hash_block(self):
        missing = committable_document()
        del missing["evidence"]["fact_packet_projection_manifest_id"]
        report = validate_listing_plan_document(
            missing,
            source_capture_evidence=golden_replay(),
            source_artifact_root=CALLOWAY_BUNDLE,
            test_mode=True,
        )
        self.assertIn("FACT_PACKET_PROJECTION_MANIFEST_REQUIRED", issue_codes(report))

        unknown = committable_document()
        unknown["evidence"]["fact_packet_projection_manifest_id"] = "unknown-product-manifest"
        unknown["fact_packet_projection"]["manifest_id"] = "unknown-product-manifest"
        report = validate_listing_plan_document(
            unknown,
            source_capture_evidence=golden_replay(),
            source_artifact_root=CALLOWAY_BUNDLE,
            test_mode=True,
        )
        self.assertIn("FACT_PACKET_PROJECTION_MANIFEST_INVALID", issue_codes(report))

        wrong_hash = committable_document()
        wrong_hash["evidence"]["fact_packet_projection_manifest_sha256"] = "0" * 64
        wrong_hash["fact_packet_projection"]["manifest_sha256"] = "0" * 64
        report = validate_listing_plan_document(
            wrong_hash,
            source_capture_evidence=golden_replay(),
            source_artifact_root=CALLOWAY_BUNDLE,
            test_mode=True,
        )
        self.assertIn("FACT_PACKET_PROJECTION_MANIFEST_INVALID", issue_codes(report))

        for injected_key, injected_value in (
            ("manifest_path", "/tmp/forbidden-projection.json"),
            ("manifest_url", "https://example.test/forbidden-projection.json"),
        ):
            with self.subTest(injected_key=injected_key):
                injected = committable_document()
                injected["fact_packet_projection"][injected_key] = injected_value
                report = validate_listing_plan_document(
                    injected,
                    source_capture_evidence=golden_replay(),
                    source_artifact_root=CALLOWAY_BUNDLE,
                    test_mode=True,
                )
                self.assertIn(
                    "FACT_PACKET_PROJECTION_MANIFEST_INVALID",
                    issue_codes(report),
                )

    def test_projection_manifest_wrong_source_and_cross_product_reuse_block(self):
        _, other_capture = second_product_case()
        wrong_source = committable_document()
        report = validate_listing_plan_document(
            wrong_source,
            source_capture_evidence=other_capture,
            test_mode=True,
        )
        self.assertIn("FACT_PACKET_PROJECTION_MANIFEST_INVALID", issue_codes(report))

        reused, reused_capture = second_product_case()
        calloway = load_example()
        reused["evidence"]["fact_packet_projection_manifest_id"] = calloway["evidence"][
            "fact_packet_projection_manifest_id"
        ]
        reused["evidence"]["fact_packet_projection_manifest_sha256"] = calloway[
            "evidence"
        ]["fact_packet_projection_manifest_sha256"]
        reused["fact_packet_projection"]["manifest_id"] = calloway[
            "fact_packet_projection"
        ]["manifest_id"]
        reused["fact_packet_projection"]["manifest_sha256"] = calloway[
            "fact_packet_projection"
        ]["manifest_sha256"]
        report = validate_listing_plan_document(
            reused,
            source_capture_evidence=reused_capture,
            test_mode=True,
        )
        self.assertIn("FACT_PACKET_PROJECTION_MANIFEST_INVALID", issue_codes(report))

    def test_projection_binding_array_is_exact_and_ordered(self):
        def binding(document, fact_id):
            return next(
                item
                for item in document["fact_packet_projection"]["bindings"]
                if item["fact_packet_fact_id"] == fact_id
            )

        cases = {
            "added": lambda document: document["fact_packet_projection"]["bindings"].append(
                {
                    **copy.deepcopy(document["fact_packet_projection"]["bindings"][-1]),
                    "fact_packet_fact_id": "fp.test_only_added_fact",
                }
            ),
            "removed": lambda document: document["fact_packet_projection"]["bindings"].pop(11),
            "reordered": lambda document: document["fact_packet_projection"]["bindings"].__setitem__(
                slice(0, 2),
                list(reversed(document["fact_packet_projection"]["bindings"][0:2])),
            ),
            "typed value": lambda document: binding(document, "fp.weight_grams").update(
                {"value": "340"}
            ),
            "claim eligibility": lambda document: binding(
                document, "fp.fabric_structure"
            ).update({"publishable_as_claim": False}),
            "policy eligibility": lambda document: binding(
                document, "fp.fabric_structure"
            ).update({"usable_as_policy_input": False}),
            "transform allowlist": lambda document: binding(
                document, "fp.fabric_structure"
            )["allowed_transform_ids"].reverse(),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                document = committable_document()
                mutate(document)
                report = validate_listing_plan_document(
                    document,
                    source_capture_evidence=golden_replay(),
                    source_artifact_root=CALLOWAY_BUNDLE,
                    test_mode=True,
                )
                self.assertIn(
                    "FACT_PACKET_PROJECTION_BINDINGS_MISMATCH",
                    issue_codes(report),
                )

    def test_projection_reviewer_must_be_distinct_from_author(self):
        document, source_capture = second_product_case()
        base_entry = copy.deepcopy(TEST_PROJECTION_PINS["size-only"])
        manifest = json.loads(
            (SKILL_ROOT / base_entry["manifest_path"]).read_text(encoding="utf-8")
        )
        review = json.loads(
            (SKILL_ROOT / base_entry["atlas_lock_path"]).read_text(encoding="utf-8")
        )
        actor = "Self-Reviewer-Test-Fixture"
        manifest["actors"]["author_auditor"]["actor_id"] = actor
        manifest["actors"]["required_reviewer_signatory"]["actor_id"] = actor
        manifest_bytes = json.dumps(
            manifest, ensure_ascii=False, sort_keys=True, indent=2
        ).encode("utf-8") + b"\n"
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        review["reviewer_signatory"]["actor_id"] = actor
        review["reviewer_signatory"]["distinct_from_author_actor_id"] = actor
        review["manifest"].update(
            {
                "sha256": manifest_sha,
                "author_actor_id": actor,
                "reviewer_actor_id": actor,
            }
        )
        review_bytes = json.dumps(
            review, ensure_ascii=False, sort_keys=True, indent=2
        ).encode("utf-8") + b"\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            review_path = root / "review-lock.json"
            manifest_path.write_bytes(manifest_bytes)
            review_path.write_bytes(review_bytes)
            entry = {
                **base_entry,
                "manifest_path": manifest_path.name,
                "manifest_sha256": manifest_sha,
                "atlas_lock_path": review_path.name,
                "atlas_lock_sha256": hashlib.sha256(review_bytes).hexdigest(),
                "author_actor_id": actor,
                "reviewer_actor_id": actor,
            }
            document["evidence"]["fact_packet_projection_manifest_sha256"] = manifest_sha
            document["fact_packet_projection"]["manifest_sha256"] = manifest_sha
            report = validate_listing_plan_document(
                document,
                source_capture_evidence=source_capture,
                test_mode=True,
                test_projection_registry={entry["manifest_id"]: entry},
                test_projection_registry_root=root,
            )
        self.assertIn(
            "FACT_PACKET_PROJECTION_REVIEW_SEPARATION_INVALID",
            issue_codes(report),
        )

    def test_invented_unused_fabric_binding_blocks(self):
        document = committable_document()
        next(
            item
            for item in document["fact_packet_projection"]["bindings"]
            if item["fact_packet_fact_id"] == "fp.fabric_structure"
        )["value"] = "cashmere"
        report = validate_listing_plan_document(
            document,
            source_capture_evidence=golden_replay(),
            source_artifact_root=CALLOWAY_BUNDLE,
            test_mode=True,
        )
        self.assertIn("FACT_PACKET_PROJECTION_BINDINGS_MISMATCH", issue_codes(report))

    def test_invented_customer_fabric_blocks_even_when_copy_guard_passes(self):
        document = committable_document()
        next(
            item
            for item in document["fact_packet_projection"]["bindings"]
            if item["fact_packet_fact_id"] == "fp.fabric_structure"
        )["value"] = "cashmere"
        opening = document["composition"]["description"]["slots"][0]
        opening["text"] = opening["text"].replace("double-gauze cotton", "cashmere wool")
        seo = document["shopify_target_state"]["seo"]
        seo["meta_description"] = seo["meta_description"].replace(
            "double-gauze cotton", "cashmere wool"
        )
        seo["meta_description_character_count"] = len(seo["meta_description"])
        exemptions = [
            item
            for item in document["originality"]["copy_guard_result"]["exemptions"]
            if item["normalized_span"] != "double gauze cotton"
        ]
        document["originality"]["copy_guard_result"] = build_copy_guard_result(
            document,
            golden_replay().source_capture,
            document["evidence"]["source_capture_sha256"],
            CALLOWAY_BUNDLE,
            exemptions,
        )
        self.assertEqual(document["originality"]["copy_guard_result"]["result"], "PASS")
        report = validate_listing_plan_document(
            document,
            source_capture_evidence=golden_replay(),
            source_artifact_root=CALLOWAY_BUNDLE,
            test_mode=True,
        )
        self.assertIn("FACT_PACKET_PROJECTION_BINDINGS_MISMATCH", issue_codes(report))
        self.assertNotIn("COPY_GUARD_FAILED", issue_codes(report))
        self.assertNotIn("COPY_GUARD_RECOMPUTATION_MISMATCH", issue_codes(report))

    def test_standalone_cli_exit_matches_committability(self):
        for name, document, expected_exit, expected_code in (
            ("locked", load_example(), 2, "STORE_POLICY_SNAPSHOT_REQUIRED_AT_COMPOSE"),
            ("synthetic", committable_document(), 2, "SYNTHETIC_POLICY_FORBIDDEN"),
        ):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "listing-plan.json"
                path.write_text(json.dumps(document), encoding="utf-8")
                source_path = Path(directory) / "source-capture.json"
                source_path.write_text(
                    json.dumps(
                        golden_replay().model_dump(mode="json", exclude_none=False),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ) + "\n",
                    encoding="utf-8",
                )
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = listing_plan_cli_main(
                        [
                            str(path),
                            "--source-capture",
                            str(source_path),
                            "--source-bundle",
                            str(CALLOWAY_BUNDLE),
                        ]
                    )
                result = json.loads(output.getvalue())
                self.assertEqual(exit_code, expected_exit)
                self.assertFalse(result["committable"])
                self.assertIn(expected_code, [item["code"] for item in result["issues"]])

    def test_normal_cli_fails_without_source_capture_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "listing-plan.json"
            path.write_text(json.dumps(load_example()), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = listing_plan_cli_main([str(path)])
            result = json.loads(output.getvalue())
            self.assertEqual(exit_code, 2)
            self.assertIn(
                "SOURCE_CAPTURE_EVIDENCE_REQUIRED",
                [item["code"] for item in result["issues"]],
            )


if __name__ == "__main__":
    unittest.main()
