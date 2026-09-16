#!/usr/bin/env python3
"""Read-only independent verifier for the Calloway FactPacket projection oracle."""

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
sys.path.insert(0, str(SKILL / "scripts"))

from product_listing.evidence import canonical_json_bytes  # noqa: E402
from product_listing.listing_plan_validation import ALLOWED_TRANSFORM_IDS  # noqa: E402
from product_listing.replay import replay_bundle  # noqa: E402


MANIFEST = HERE / "nobodys-child-calloway.fact-packet-projection-v2.expected.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha(value: Any, newline: bool = False) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if newline:
        payload += b"\n"
    return hashlib.sha256(payload).hexdigest()


def verify_pinned_inputs(manifest: dict[str, Any]) -> None:
    expected = {
        "bundle": "a6cb0e6f49ad3d356009ffdddb0c64d91523189508603e4b95d342899065f23e",
        "bundle_hash_index": "fce96ae6399342d1fc5c8ab26f663b520bd94a8dc908ffbb38ee91f1a6823679",
        "source_oracle": "46dddf7976e96ccd3fe2a29b5f47a7e5423c05f984b02917b82d3225e6153646",
        "source_evidence_lock": "0bf1135a067f07363b6eacb0e0e942a8e5e6a45f96b6347a3f56b7c453cccc9b",
        "implementation_lock": "3fa869ca05a3b9bd44337eea6b075452d1111f7e01fe2e6d179db6bcad64ec09",
        "v4_stage_a_profile": "e55ce269d910795d4ceff98e897ec5e879632bb4b2f9c41b4a2c863dcf07da59",
        "v4_stage_a_contract": "efff932806984b6c32628c7965633e9fa18b01067edcd3779df0cec309d981b2",
        "v4_stage_a_example": "d7197501e8d40aba48ea3dce91a972195767a4054f41268ca60d550de1aaac63",
    }
    for key, expected_hash in expected.items():
        record = manifest["fixture"][key]
        path = WORKSPACE / record["path"]
        assert record["sha256"] == expected_hash
        assert sha(path) == expected_hash, key


def expected_values() -> dict[str, Any]:
    structured = load(FIXTURE / "structured-product.json")
    sections = load(FIXTURE / "sections.json")
    product = load(FIXTURE / "raw" / "product.js.json")
    details = sections["sections"][1]["blocks"]
    description = sections["sections"][0]["blocks"][0]["text"]
    fabric = sections["sections"][2]["blocks"][0]["value"]
    model = structured["source_model"]

    assert "navy midi dress" in description
    assert "double gauze cotton" in description
    assert "sun goddess embroidery" in description and "intricate laddering" in description
    assert [details[index]["text"].replace("\u200b", "").strip() for index in range(2, 11)] == [
        "Round neck",
        "Sleeveless",
        "Shirred bodice",
        "Elasticated waist",
        "Side pockets",
        "Relaxed skirt",
        "Tiered skirt",
        "Ruffle trim",
        "Lightly lined",
    ]
    assert details[13]["label"] == "Country of Manufacture" and details[13]["value"] == "India"
    assert fabric == "Main: 100% Cotton | Lining: 100% Cotton | Embroidery: 100% Polyester | Embroidery 2: 73% Polyester, 27% Metallised Fibre"
    assert sections["sections"][2]["blocks"][1]["value"] == "Machine Wash"
    assert [item["weight"] for item in product["variants"]] == [340] * 16
    assert model["source_line"] == "Model's height is 5'9\" - she wears a UK size 8. Wearing length is: 140cm"
    assert model["target_fit_note_eligible"] is False

    return {
        "fp.canonical_source_url": "https://www.nobodyschild.com/products/calloway-midi-dress-2616171001",
        "fp.source_product_id": "15364155539841",
        "fp.current_customer_paid_price_gbp": "55.00",
        "fp.options.size": structured["options"][0]["values"],
        "fp.options.length": structured["options"][1]["values"],
        "fp.real_variant_combinations": [item["options"] for item in product["variants"]],
        "fp.colour": structured["colour"],
        "fp.product_type": structured["product_type"],
        "fp.end_use": "day",
        "fp.length_class": "midaxi",
        "fp.silhouette_length": "midi",
        "fp.fabric_structure": "double-gauze cotton",
        "fp.embroidery_present": True,
        "fp.laddering_present": True,
        "fp.neckline": "round",
        "fp.sleeve_style": "sleeveless",
        "fp.bodice_construction": "shirred",
        "fp.waist_construction": "elasticated",
        "fp.pockets": "side pockets",
        "fp.skirt_fit": "relaxed",
        "fp.skirt_construction": "tiered",
        "fp.trim": "ruffle",
        "fp.lining_state": "lightly lined",
        "fp.country_of_manufacture": "India",
        "fp.material_main": {"fiber": "Cotton", "percentage": 100},
        "fp.material_lining": {"fiber": "Cotton", "percentage": 100},
        "fp.material_embroidery": {"fiber": "Polyester", "percentage": 100},
        "fp.material_embroidery_secondary": [
            {"fiber": "Polyester", "percentage": 73},
            {"fiber": "Metallised Fibre", "percentage": 27},
        ],
        "fp.care_instruction": "Machine Wash",
        "fp.weight_grams": 340,
        "fp.source_model.height": "5'9\"",
        "fp.source_model.worn_size": "UK size 8",
        "fp.source_model.wearing_length": "140cm",
    }


def verify_records(manifest: dict[str, Any]) -> None:
    example = load(PROFILE / "listing-plan.example.json")
    candidates = example["fact_packet_projection"]["bindings"]
    records = manifest["records"]
    assert manifest["bindings"] == candidates
    assert canonical_sha(manifest["bindings"]) == "7b89952844b9de29083fe5ec943adff7ed1fb23ab19a52a3987e0340bf95ce95"
    expected = expected_values()
    assert len(candidates) == len(records) == len(expected) == 33
    assert [record["order"] for record in records] == list(range(1, 34))
    assert [record["fact_packet_fact_id"] for record in records] == list(expected)
    assert len({record["projection_rule"]["id"] for record in records}) == 33

    for candidate, record in zip(candidates, records):
        fact_id = record["fact_packet_fact_id"]
        assert candidate["fact_packet_fact_id"] == fact_id
        assert record["typed_value"]["value"] == expected[fact_id] == candidate["value"], fact_id
        assert record["source_fact_or_path"] == candidate["source_fact_or_path"]
        assert record["evidence_locator"] == candidate["evidence_locator"]
        assert record["captured_at"] == candidate["captured_at"] == "2026-09-01T11:35:24Z"
        assert record["market"] == candidate["market"] == "GB"
        assert record["locale"] == candidate["locale"] == "en-GB"
        assert record["currency"] == candidate.get("currency")
        assert record["unit"] == candidate.get("unit")
        assert record["scope"] == candidate["scope"]
        assert record["conflict_state"] == candidate["conflict_state"] == "NONE"
        assert record["claim_eligibility"]["publishable_as_claim"] == candidate["publishable_as_claim"]
        assert record["policy_eligibility"]["usable_as_policy_input"] == candidate["usable_as_policy_input"]
        assert record["allowed_transform_ids"] == candidate["allowed_transform_ids"]
        unsupported_transform_ids = sorted(set(record["allowed_transform_ids"]) - ALLOWED_TRANSFORM_IDS)
        assert record["projection_status"] == "ALLOW"
        assert unsupported_transform_ids == []
        assert record["block_reason"] is None
        assert record["projection_rule"]["version"] == "1.0.0"
        assert re.fullmatch(r"calloway_fp_[a-z0-9_]+_projection_v1", record["projection_rule"]["id"])
        verification = record["reviewer_verification"]
        assert verification["status"] == "VERIFIED_AGAINST_LOCKED_RAW_AND_REPLAY"
        assert verification["reviewer_role"] == "Scout" and verification["reviewer_verified"] is True
        assert verification["evidence_sources"]
        for evidence in verification["evidence_sources"]:
            evidence_path = WORKSPACE / evidence["artifact_path"]
            assert sha(evidence_path) == evidence["artifact_sha256"]
            assert canonical_sha(evidence["raw_value"]) == evidence["raw_value_canonical_sha256"]

    typed_by_id = {record["fact_packet_fact_id"]: record["typed_value"] for record in records}
    record_by_id = {record["fact_packet_fact_id"]: record for record in records}
    assert record_by_id["fp.length_class"]["allowed_transform_ids"] == ["ondine_tags_v1"]
    assert typed_by_id["fp.current_customer_paid_price_gbp"] == {"type": "decimal_string", "value": "55.00", "currency": "GBP", "unit": "GBP"}
    assert typed_by_id["fp.weight_grams"] == {"type": "integer", "value": 340, "unit": "g"}
    assert typed_by_id["fp.source_model.height"] == {"type": "string", "value": "5'9\"", "unit": "ft_in_literal"}
    assert typed_by_id["fp.source_model.wearing_length"] == {"type": "string", "value": "140cm", "unit": "cm"}
    for fact_id in (
        "fp.silhouette_length",
        "fp.fabric_structure",
        "fp.material_main",
        "fp.material_lining",
        "fp.material_embroidery",
        "fp.material_embroidery_secondary",
        "fp.weight_grams",
        "fp.source_model.height",
        "fp.source_model.worn_size",
        "fp.source_model.wearing_length",
    ):
        verification = next(item for item in records if item["fact_packet_fact_id"] == fact_id)["reviewer_verification"]
        assert verification["reviewer_verified"] is True and verification["physical_value"] is True

    for fact_id in ("fp.source_model.height", "fp.source_model.worn_size", "fp.source_model.wearing_length"):
        record = next(item for item in records if item["fact_packet_fact_id"] == fact_id)
        assert record["scope"] == "competitor_only_model_record"
        assert record["claim_eligibility"]["publishable_as_claim"] is False
        assert record["policy_eligibility"]["usable_as_policy_input"] is False
        assert record["allowed_transform_ids"] == []


def verify_replay(manifest: dict[str, Any]) -> None:
    first = replay_bundle(FIXTURE)
    second = replay_bundle(FIXTURE)
    assert first.valid and second.valid and first.issues == second.issues == []
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert first.determinism_sha256 == "b39a7394ac9f66f2189b82acb121da8f2c878313a9bf63f1ac5a05723a3f7535"
    output_hash = canonical_sha(first.model_dump(mode="json", exclude_none=False), newline=True)
    assert output_hash == "279d3d4170cf62c02a140bd190aefe1fc1cded754041ad92ca0c2f88c802b660"
    assert manifest["source_capture"] == {
        "output_sha256": output_hash,
        "determinism_sha256": first.determinism_sha256,
        "offline_replay_runs": 2,
        "canonical_replay_bytes_equal": True,
        "valid": True,
        "issues": [],
    }


def main() -> None:
    manifest = load(MANIFEST)
    assert manifest["manifest_id"] == "nobodys-child-calloway-fact-packet-projection-oracle-v2"
    assert manifest["schema_version"] == "2.0.0"
    assert manifest["artifact_role"] == "SCOUT_AUTHORED_AUDITED_PRODUCT_SPECIFIC_PROJECTION_PENDING_DISTINCT_ATLAS_REVIEW"
    assert manifest["status"] == "AWAITING_ATLAS_SIGNATURE"
    assert manifest["supersedes"] == {
        "manifest_path": ".claude/skills/product-listing/tests/oracles/fact-packets/nobodys-child-calloway.fact-packet-projection.expected.json",
        "manifest_sha256": "da5e192235690688e156e67f8b7112a25b586c51626e81fbdc163ad239626fa3",
        "prior_status": "AWAITING_ATLAS_SIGNATURE",
        "prior_disposition": "NOT_SIGNED_EXPECTED_BLOCK",
        "reason": "Mira v4 stage A removed the unused unregistered transform from fp.length_class; the blocked v1 artifact remains immutable audit history.",
    }
    assert sha(HERE / "nobodys-child-calloway.fact-packet-projection.expected.json") == manifest["supersedes"]["manifest_sha256"]
    author = manifest["actors"]["author_auditor"]
    reviewer = manifest["actors"]["required_reviewer_signatory"]
    assert author == {
        "actor_id": "Scout",
        "role": "AUTHOR_AUDITOR",
        "attestation_status": "AUTHOR_AUDIT_COMPLETE",
        "attested_at": "2026-09-01T20:32:00+01:00",
        "review_or_signature_authority": False,
    }
    assert reviewer == {
        "actor_id": "Atlas",
        "role": "REVIEWER_SIGNATORY",
        "required_state": "PENDING_DETACHED_ATLAS_LOCK",
        "approval_status": "PENDING",
        "signature": None,
        "must_be_distinct_from_author_auditor": True,
        "attestation_mechanism": "DETACHED_IMMUTABLE_ATLAS_LOCK_OVER_FINAL_MANIFEST_SHA256",
    }
    assert author["actor_id"] != reviewer["actor_id"]
    assert manifest["attestation_policy"] == {
        "author_and_reviewer_actor_ids_must_differ": True,
        "self_review_forbidden": True,
        "unsigned_manifest_approval_state": "PENDING_REVIEWER_SIGNATURE",
        "accepted_state_requires": "A detached immutable Atlas lock naming this manifest ID and exact final manifest SHA-256.",
    }
    assert manifest["capture_context"] == {
        "market": "GB",
        "locale": "en-GB",
        "currency": "GBP",
        "captured_at": "2026-09-01T11:35:24Z",
    }
    assert manifest["global_projection_rule"]["id"] == "ondine_fact_packet_projection_v1"
    assert manifest["global_projection_rule"]["version"] == "1.0.0"
    assert manifest["summary"] == {
        "candidate_binding_count": 33,
        "ordered_record_count": 33,
        "allowed_count": 33,
        "blocked_count": 0,
        "blocked_fact_ids": [],
        "unsupported_values_invented": 0,
        "decision": "AUTHOR_AUDIT_COMPLETE_AWAITING_DETACHED_ATLAS_LOCK",
    }
    verify_pinned_inputs(manifest)
    verify_replay(manifest)
    verify_records(manifest)
    print(json.dumps({
        "status": "PASS_FACT_PACKET_PROJECTION_ORACLE_UNSIGNED",
        "manifest_sha256": sha(MANIFEST),
        "records_verified": 33,
        "allow": 33,
        "block": 0,
        "source_capture_output_sha256": manifest["source_capture"]["output_sha256"],
        "source_capture_determinism_sha256": manifest["source_capture"]["determinism_sha256"],
        "signature_status": manifest["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
