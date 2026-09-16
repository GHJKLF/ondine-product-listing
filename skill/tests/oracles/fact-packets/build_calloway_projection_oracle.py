#!/usr/bin/env python3
"""Offline-only builder for Scout's reviewer-owned Calloway FactPacket oracle."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[2]
WORKSPACE = SKILL.parents[2]
FIXTURE = SKILL / "tests" / "fixtures" / "nobodys-child-calloway"
ORACLES = SKILL / "tests" / "oracles"
PROFILE = SKILL / "profiles" / "ondine"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

from product_listing.evidence import canonical_json_bytes  # noqa: E402
from product_listing.listing_plan_validation import ALLOWED_TRANSFORM_IDS  # noqa: E402
from product_listing.replay import replay_bundle  # noqa: E402


OUTPUT = HERE / "nobodys-child-calloway.fact-packet-projection.expected.json"
CAPTURED_AT = "2026-09-01T11:35:24Z"
REVIEWED_AT = "2026-09-01T20:28:00+01:00"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: Any, newline: bool = False) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if newline:
        payload += b"\n"
    return hashlib.sha256(payload).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact(path: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(WORKSPACE)),
        "sha256": sha(path),
    }


bundle_path = FIXTURE / "bundle.json"
index_path = FIXTURE / "bundle-files.sha256"
oracle_path = ORACLES / "nobodys-child-calloway.expected.json"
aggregate_lock_path = ORACLES / "aggregate-manifest-v2.atlas-lock.json"
implementation_lock_path = ORACLES / "gate-0b-implementation-v3.atlas-lock.json"
phase2_lock_path = PROFILE / "phase-2-composition-v3.atlas-lock.json"
example_path = PROFILE / "listing-plan.example.json"
structured_path = FIXTURE / "structured-product.json"
sections_path = FIXTURE / "sections.json"
product_ajax_path = FIXTURE / "raw" / "product.js.json"
jsonld_path = FIXTURE / "product.jsonld.json"

PINNED = {
    bundle_path: "a6cb0e6f49ad3d356009ffdddb0c64d91523189508603e4b95d342899065f23e",
    index_path: "fce96ae6399342d1fc5c8ab26f663b520bd94a8dc908ffbb38ee91f1a6823679",
    oracle_path: "46dddf7976e96ccd3fe2a29b5f47a7e5423c05f984b02917b82d3225e6153646",
    aggregate_lock_path: "0bf1135a067f07363b6eacb0e0e942a8e5e6a45f96b6347a3f56b7c453cccc9b",
    implementation_lock_path: "3fa869ca05a3b9bd44337eea6b075452d1111f7e01fe2e6d179db6bcad64ec09",
    phase2_lock_path: "45d24cfc430b44fcd8dd68c62d36686344cedddb5a9c99f113685921d70bab3e",
    example_path: "12eb0cac47a50ae653d2dec164178e876bdb91f95f139541810681ac2b12664b",
}
for path, expected in PINNED.items():
    assert sha(path) == expected, f"locked input hash drift: {path}"

bundle = load(bundle_path)
structured = load(structured_path)
sections = load(sections_path)
product_ajax = load(product_ajax_path)
jsonld = load(jsonld_path)
example = load(example_path)
candidate = example["fact_packet_projection"]
bindings = candidate["bindings"]
assert len(bindings) == 33

first = replay_bundle(FIXTURE)
second = replay_bundle(FIXTURE)
assert first.valid and second.valid and first.issues == second.issues == []
assert canonical_json_bytes(first) == canonical_json_bytes(second)
assert first.determinism_sha256 == second.determinism_sha256 == "b39a7394ac9f66f2189b82acb121da8f2c878313a9bf63f1ac5a05723a3f7535"
replay_json = first.model_dump(mode="json", exclude_none=False)
output_sha256 = canonical_sha(replay_json, newline=True)
assert output_sha256 == "279d3d4170cf62c02a140bd190aefe1fc1cded754041ad92ca0c2f88c802b660"
capture = first.source_capture
facts = {item.fact_id: item.model_dump(mode="json") for item in capture.facts}


def source(path: Path, locator: str, raw_value: Any) -> dict[str, Any]:
    return {
        "artifact_path": str(path.relative_to(WORKSPACE)),
        "artifact_sha256": sha(path),
        "locator": locator,
        "raw_value": raw_value,
        "raw_value_canonical_sha256": canonical_sha(raw_value),
    }


def typed(value: Any, fact_id: str, binding: dict[str, Any]) -> dict[str, Any]:
    if fact_id == "fp.current_customer_paid_price_gbp":
        return {"type": "decimal_string", "value": value, "currency": "GBP", "unit": "GBP"}
    if fact_id == "fp.weight_grams":
        return {"type": "integer", "value": value, "unit": "g"}
    if fact_id == "fp.source_model.height":
        return {"type": "string", "value": value, "unit": "ft_in_literal"}
    if fact_id == "fp.source_model.wearing_length":
        return {"type": "string", "value": value, "unit": "cm"}
    if fact_id.startswith("fp.material_"):
        return {
            "type": "array<object>" if isinstance(value, list) else "object",
            "value": value,
            "component_units": {"percentage": "percent", "fiber": "source_literal"},
        }
    if isinstance(value, bool):
        value_type = "boolean"
    elif isinstance(value, int):
        value_type = "integer"
    elif isinstance(value, str):
        value_type = "string"
    elif isinstance(value, list):
        value_type = "array"
    elif isinstance(value, dict):
        value_type = "object"
    else:
        raise AssertionError(f"unsupported type for {fact_id}")
    result = {"type": value_type, "value": value, "unit": binding.get("unit")}
    if binding.get("currency"):
        result["currency"] = binding["currency"]
    return result


def evidence_for(fact_id: str, value: Any) -> tuple[list[dict[str, Any]], str, bool, bool, str]:
    """Return sources, mapping kind, normalized/parsed, physical, verification note."""
    description = sections["sections"][0]["blocks"][0]["text"]
    detail_blocks = sections["sections"][1]["blocks"]
    fabric_value = sections["sections"][2]["blocks"][0]["value"]
    model = structured["source_model"]
    if fact_id == "fp.canonical_source_url":
        return [source(bundle_path, "/capture/canonical_url", bundle["capture"]["canonical_url"])], "EXACT_IDENTITY", False, False, "Exact canonical URL matches replay fact fact-8446ef8f5e55a83a."
    if fact_id == "fp.source_product_id":
        return [
            source(structured_path, "/product_id", structured["product_id"]),
            source(product_ajax_path, "/id", product_ajax["id"]),
        ], "STRINGIFY_INTEGER_ID", True, False, "Raw integer ID and signed structured string identify the same product."
    if fact_id == "fp.current_customer_paid_price_gbp":
        return [
            source(structured_path, "/price/current", structured["price"]["current"]),
            source(jsonld_path, "/offers/price", jsonld["offers"]["price"]),
            source(product_ajax_path, "/price", product_ajax["price"]),
        ], "GBP_MINOR_UNITS_TO_TWO_DECIMAL", True, False, "5500 GBP minor units and both independent decimal representations resolve exactly to 55.00 GBP."
    if fact_id == "fp.options.size":
        return [
            source(structured_path, "/options/0/values", structured["options"][0]["values"]),
            source(product_ajax_path, "/options/0/values", product_ajax["options"][0]["values"]),
        ], "ORDERED_ARRAY_IDENTITY", False, False, "All eight source sizes are preserved in source order."
    if fact_id == "fp.options.length":
        return [
            source(structured_path, "/options/1/values", structured["options"][1]["values"]),
            source(product_ajax_path, "/options/1/values", product_ajax["options"][1]["values"]),
        ], "ORDERED_ARRAY_IDENTITY", False, False, "Regular and Petite are preserved in source order; source option name remains lowercase length."
    if fact_id == "fp.real_variant_combinations":
        return [
            source(structured_path, "/real_variant_combinations", structured["real_variant_combinations"]),
            source(product_ajax_path, "/variants/*/options", [item["options"] for item in product_ajax["variants"]]),
        ], "ORDERED_REAL_COMBINATION_IDENTITY", False, False, "All and only the 16 signed Size × length combinations match the replay."
    if fact_id == "fp.colour":
        return [source(structured_path, "/colour", structured["colour"])], "EXACT_IDENTITY", False, False, "Exact signed colour field."
    if fact_id == "fp.product_type":
        return [
            source(structured_path, "/product_type", structured["product_type"]),
            source(product_ajax_path, "/type", product_ajax["type"]),
        ], "EXACT_IDENTITY", False, False, "Exact signed product type in both structured sources."
    if fact_id == "fp.end_use":
        return [source(structured_path, "/tags", "end-use:day")], "TAG_PREFIX_VALUE", True, False, "Exact suffix extracted from signed tag end-use:day."
    if fact_id == "fp.length_class":
        return [source(structured_path, "/tags", "length:midaxi")], "TAG_PREFIX_VALUE", True, False, "Exact suffix extracted from signed tag length:midaxi."
    if fact_id == "fp.silhouette_length":
        return [source(sections_path, "/sections/0/blocks/0/text", description)], "PHRASE_TOKEN_EXTRACTION", True, True, "Reviewer verified the exact phrase ‘navy midi dress’; only the literal length token is projected."
    if fact_id == "fp.fabric_structure":
        return [source(sections_path, "/sections/0/blocks/0/text", description)], "SOURCE_PHRASE_HYPHEN_NORMALIZATION", True, True, "Reviewer verified exact raw phrase ‘double gauze cotton’; projection adds only deterministic compound hyphenation."
    if fact_id == "fp.embroidery_present":
        return [
            source(sections_path, "/sections/0/blocks/0/text", description),
            source(sections_path, "/sections/1/blocks/1/text", detail_blocks[1]["text"]),
        ], "EXPLICIT_PHRASE_TO_BOOLEAN", True, True, "Both description and first detail bullet explicitly state embroidery; presence=true is supported."
    if fact_id == "fp.laddering_present":
        return [source(sections_path, "/sections/0/blocks/0/text", description)], "EXPLICIT_PHRASE_TO_BOOLEAN", True, True, "Description explicitly states intricate laddering; presence=true is supported."
    direct_detail = {
        "fp.neckline": (2, "ROUND_NECK_TO_NECKLINE", "Exact bullet ‘Round neck’ deterministically maps to round."),
        "fp.sleeve_style": (3, "EXACT_TERM_CASEFOLD", "Exact bullet ‘Sleeveless’ casefolds to sleeveless."),
        "fp.bodice_construction": (4, "HEAD_NOUN_REMOVAL", "Exact bullet ‘Shirred bodice’ maps to construction value shirred."),
        "fp.waist_construction": (5, "HEAD_NOUN_REMOVAL", "Exact bullet ‘Elasticated waist’ maps to construction value elasticated."),
        "fp.pockets": (6, "EXACT_TERM_CASEFOLD", "Exact bullet ‘Side pockets’ casefolds without semantic change."),
        "fp.skirt_fit": (7, "HEAD_NOUN_REMOVAL", "Exact bullet ‘Relaxed skirt’ maps to fit value relaxed."),
        "fp.skirt_construction": (8, "HEAD_NOUN_REMOVAL", "Exact bullet ‘Tiered skirt’ maps to construction value tiered."),
        "fp.trim": (9, "HEAD_NOUN_REMOVAL", "Exact bullet ‘Ruffle trim’ maps to trim value ruffle."),
        "fp.lining_state": (10, "EXACT_TERM_WHITESPACE_NORMALIZATION", "Exact bullet ‘Lightly lined’ is preserved after zero-width/space normalization."),
    }
    if fact_id in direct_detail:
        index, kind, note = direct_detail[fact_id]
        return [source(sections_path, f"/sections/1/blocks/{index}/text", detail_blocks[index]["text"])], kind, True, True, note
    if fact_id == "fp.country_of_manufacture":
        return [source(sections_path, "/sections/1/blocks/13/value", detail_blocks[13]["value"])], "EXACT_IDENTITY", False, True, "Exact Country of Manufacture label-value block."
    material_values = {
        "fp.material_main": ({"fiber": "Cotton", "percentage": 100}, "Main: 100% Cotton"),
        "fp.material_lining": ({"fiber": "Cotton", "percentage": 100}, "Lining: 100% Cotton"),
        "fp.material_embroidery": ({"fiber": "Polyester", "percentage": 100}, "Embroidery: 100% Polyester"),
        "fp.material_embroidery_secondary": ([{"fiber": "Polyester", "percentage": 73}, {"fiber": "Metallised Fibre", "percentage": 27}], "Embroidery 2: 73% Polyester, 27% Metallised Fibre"),
    }
    if fact_id in material_values:
        expected, segment = material_values[fact_id]
        assert value == expected and segment in fabric_value
        return [source(sections_path, "/sections/2/blocks/0/value", fabric_value)], "LABELED_COMPOSITION_SEGMENT_PARSE", True, True, f"Reviewer verified exact labeled segment ‘{segment}’; numeric percentages and fibre literals are copied without inference."
    if fact_id == "fp.care_instruction":
        return [source(sections_path, "/sections/2/blocks/1/value", sections["sections"][2]["blocks"][1]["value"])], "EXACT_IDENTITY", False, True, "Exact Washcare label-value block."
    if fact_id == "fp.weight_grams":
        weights = [item["weight"] for item in product_ajax["variants"]]
        signed_weights = [item["weight_grams"] for item in structured["variants"]]
        assert weights == signed_weights == [340] * 16
        return [
            source(product_ajax_path, "/variants/*/weight", weights),
            source(structured_path, "/variants/*/weight_grams", signed_weights),
        ], "ALL_VARIANTS_EQUAL_GRAM_CONSENSUS", True, True, "Reviewer verified every one of 16 variants carries numeric weight 340 grams; no averaging or defaulting."
    if fact_id == "fp.source_model.height":
        return [source(structured_path, "/source_model/source_line", model["source_line"])], "MODEL_LINE_HEIGHT_PARSE", True, True, "Reviewer verified literal 5'9\" inside the exact signed model line; competitor-only and claim-ineligible."
    if fact_id == "fp.source_model.worn_size":
        return [source(structured_path, "/source_model/source_line", model["source_line"])], "MODEL_LINE_WORN_SIZE_PARSE", True, True, "Reviewer verified literal UK size 8 inside the exact signed model line; competitor-only and claim-ineligible."
    if fact_id == "fp.source_model.wearing_length":
        return [source(structured_path, "/source_model/source_line", model["source_line"])], "MODEL_LINE_WEARING_LENGTH_PARSE", True, True, "Reviewer verified literal 140cm inside the exact signed model line; unit cm is explicit and competitor-only."
    raise AssertionError(f"no evidence mapping for {fact_id}")


records = []
for order, binding in enumerate(bindings, 1):
    fact_id = binding["fact_packet_fact_id"]
    sources, mapping_kind, parsed, physical, note = evidence_for(fact_id, binding["value"])
    referenced_ids = re.findall(r"fact-[0-9a-f]{16}", binding["source_fact_or_path"])
    for referenced_id in referenced_ids:
        assert referenced_id in facts, f"missing replay fact {referenced_id}"
    rule_suffix = re.sub(r"[^a-z0-9]+", "_", fact_id.lower()).strip("_")
    unsupported_transform_ids = sorted(set(binding["allowed_transform_ids"]) - ALLOWED_TRANSFORM_IDS)
    projection_status = "BLOCK" if unsupported_transform_ids else "ALLOW"
    records.append(
        {
            "order": order,
            "fact_packet_fact_id": fact_id,
            "projection_status": projection_status,
            "block_reason": (
                {
                    "code": "UNREGISTERED_ALLOWED_TRANSFORM_ID",
                    "unsupported_transform_ids": unsupported_transform_ids,
                    "detail": "The value is evidenced, but this candidate binding may not project until every allowed transform ID is present in the locked v3 transform registry.",
                }
                if unsupported_transform_ids
                else None
            ),
            "typed_value": typed(binding["value"], fact_id, binding),
            "source_fact_or_path": binding["source_fact_or_path"],
            "evidence_locator": binding["evidence_locator"],
            "captured_at": binding["captured_at"],
            "market": binding["market"],
            "locale": binding["locale"],
            "currency": binding.get("currency"),
            "unit": binding.get("unit"),
            "projection_rule": {
                "id": f"calloway_{rule_suffix}_projection_v1",
                "version": "1.0.0",
                "mapping_kind": mapping_kind,
            },
            "scope": binding["scope"],
            "conflict_state": binding["conflict_state"],
            "claim_eligibility": {"publishable_as_claim": binding["publishable_as_claim"]},
            "policy_eligibility": {"usable_as_policy_input": binding["usable_as_policy_input"]},
            "allowed_transform_ids": binding["allowed_transform_ids"],
            "reviewer_verification": {
                "status": "VERIFIED_AGAINST_LOCKED_RAW_AND_REPLAY",
                "reviewer_role": "Scout",
                "normalized_or_parsed": parsed,
                "physical_value": physical,
                "reviewer_verified": True,
                "note": note,
                "evidence_sources": sources,
            },
        }
    )

assert [record["order"] for record in records] == list(range(1, 34))
assert len({record["fact_packet_fact_id"] for record in records}) == 33
assert [record["fact_packet_fact_id"] for record in records if record["projection_status"] == "BLOCK"] == ["fp.length_class"]
assert all(
    record["reviewer_verification"]["reviewer_verified"] is True
    for record in records
    if record["reviewer_verification"]["normalized_or_parsed"] or record["reviewer_verification"]["physical_value"]
)

manifest = {
    "manifest_id": "nobodys-child-calloway-fact-packet-projection-oracle-v1",
    "schema_version": "1.0.0",
    "artifact_role": "REVIEWER_OWNED_PRODUCT_SPECIFIC_FACT_PACKET_PROJECTION_DENOMINATOR",
    "status": "AWAITING_ATLAS_SIGNATURE",
    "reviewer": {"role": "Scout", "reviewed_at": REVIEWED_AT, "signature": None},
    "fixture": {
        "fixture_id": "nobodys-child-calloway",
        "bundle": artifact(bundle_path),
        "bundle_hash_index": artifact(index_path),
        "source_oracle": artifact(oracle_path),
        "source_evidence_lock": artifact(aggregate_lock_path),
        "implementation_lock": artifact(implementation_lock_path),
        "phase_2_contract_lock": artifact(phase2_lock_path),
        "v3_candidate_example": artifact(example_path),
    },
    "source_capture": {
        "output_sha256": output_sha256,
        "determinism_sha256": first.determinism_sha256,
        "offline_replay_runs": 2,
        "canonical_replay_bytes_equal": True,
        "valid": True,
        "issues": [],
    },
    "capture_context": {
        "market": "GB",
        "locale": "en-GB",
        "currency": "GBP",
        "captured_at": CAPTURED_AT,
    },
    "global_projection_rule": {
        "id": "ondine_fact_packet_projection_v1",
        "version": "1.0.0",
        "source_capture_immutable": True,
        "policy": "Only reviewer-verified values traceable to signed SourceCapture evidence may be projected; unsupported or conflicting values must be BLOCK.",
    },
    "candidate_projection_pins": {
        "source_capture_sha256": candidate["source_capture_sha256"],
        "source_capture_determinism_sha256": candidate["source_capture_determinism_sha256"],
        "ondine_profile_sha256": candidate["ondine_profile_sha256"],
    },
    "summary": {
        "candidate_binding_count": 33,
        "ordered_record_count": len(records),
        "allowed_count": sum(record["projection_status"] == "ALLOW" for record in records),
        "blocked_count": sum(record["projection_status"] == "BLOCK" for record in records),
        "blocked_fact_ids": [record["fact_packet_fact_id"] for record in records if record["projection_status"] == "BLOCK"],
        "unsupported_values_invented": 0,
        "decision": "LOCK_READY_WITH_EXPECTED_BLOCK_AWAITING_ATLAS_SIGNATURE",
    },
    "records": records,
}

OUTPUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({
    "manifest": str(OUTPUT.relative_to(WORKSPACE)),
    "sha256": sha(OUTPUT),
    "records": len(records),
    "allowed": manifest["summary"]["allowed_count"],
    "blocked": manifest["summary"]["blocked_count"],
    "status": manifest["status"],
}, indent=2))
