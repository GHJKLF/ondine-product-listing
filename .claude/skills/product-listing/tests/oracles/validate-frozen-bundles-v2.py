#!/usr/bin/env python3
"""Read-only Gate 0A v2 validator: retain v1 blockers and verify one positive denominator."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
V1_EXPECTED_SHA256 = "248cfddbc81e25cc1a6890d008bdccc87efa6f89532573d8ee78e662276505ff"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_index(bundle_root: Path, index_path: Path) -> None:
    seen = set()
    for line in index_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        assert relative not in seen
        seen.add(relative)
        assert re.fullmatch(r"[0-9a-f]{64}", expected)
        assert digest(bundle_root / relative) == expected, relative
    assert {
        "bundle.json",
        "rendered.sanitized.html",
        "product.jsonld.json",
        "structured-product.json",
        "sections.json",
        "size-guide.json",
        "media-manifest.json",
        "evidence-registry.json",
        "raw/product.js.json",
        "raw/cart.currency.json",
        "raw/size-guide.api.json",
        "raw/media-content-hashes.json",
    }.issubset(seen)


def verify_positive(entry: dict) -> None:
    bundle_path = (ROOT / entry["bundle_path"]).resolve()
    bundle_root = bundle_path.parent
    index_path = (ROOT / entry["bundle_hash_index_path"]).resolve()
    oracle_path = (ROOT / entry["oracle_path"]).resolve()
    assert digest(bundle_path) == entry["bundle_sha256"]
    assert digest(index_path) == entry["bundle_hash_index_sha256"]
    assert digest(oracle_path) == entry["oracle_sha256"]
    verify_index(bundle_root, index_path)

    bundle = load(bundle_path)
    oracle = load(oracle_path)
    assert bundle["fixture_id"] == oracle["fixture_id"] == entry["fixture_id"] == "nobodys-child-calloway"
    assert bundle["status"] == "POSITIVE_DENOMINATOR_COMPLETE"
    assert bundle["conflicts"] == bundle["acquisition_gaps"] == []
    assert oracle["expected"]["status"] == "POSITIVE_DENOMINATOR_COMPLETE"
    assert oracle["reviewer_lock"] == {"status": "AWAITING_ATLAS_SIGNATURE", "locked_hash": None}

    capture = bundle["capture"]
    assert capture["market"] == "GB" and capture["locale"] == "en-GB" and capture["currency"] == "GBP"
    assert capture["json_ld"]["status"] == "FROZEN"
    assert capture["same_session_commerce_json"] == {
        "status": "FROZEN",
        "product_path": "raw/product.js.json",
        "cart_currency_path": "raw/cart.currency.json",
        "currency": "GBP",
    }
    assert not (bundle_root / "raw/response.html").exists()
    rendered = (bundle_root / "rendered.sanitized.html").read_text(encoding="utf-8", errors="replace")
    assert not re.search(r"(?i)(access[_-]?token|client[_-]?secret|api[_-]?key|authorization:\s*bearer|credential[_-]?secret)", rendered)

    product = load(bundle_root / "structured-product.json")
    assert product["price"] == {"current": "55.00", "compare_at": "139.00"}
    assert product["promotion"]["text"] == "60% off" and product["promotion"]["displayed_exactly"] is True
    assert [item["name"] for item in product["options"]] == ["Size", "length"]
    assert product["options"][0]["values"] == ["4", "6", "8", "10", "12", "14", "16", "18"]
    assert product["options"][1]["values"] == ["Regular", "Petite"]
    expected_combinations = [[size, length] for size in product["options"][0]["values"] for length in product["options"][1]["values"]]
    assert product["real_variant_combinations"] == expected_combinations
    assert len(product["variants"]) == 16
    assert all(item["price"] == "55.00" and item["compare_at"] == "139.00" for item in product["variants"])
    assert product["source_model"]["namespace"] == "competitor_only"
    assert product["source_model"]["target_fit_note_eligible"] is False
    assert product["source_model"]["source_line"] == "Model's height is 5'9\" - she wears a UK size 8. Wearing length is: 140cm"
    assert product["colour_relations"] == [
        {
            "relation": "SELF_ONLY_SINGLE_COLOUR",
            "title": "Navy Embroidered Tiered Calloway Midi Dress",
            "url": "https://www.nobodyschild.com/products/calloway-midi-dress-2616171001",
            "aria_current": "page",
            "complete": True,
            "note": "The rendered selector states 1 Colours available and contains only the canonical PDP itself; no sibling PDP is represented.",
        }
    ]

    jsonld = load(bundle_root / "product.jsonld.json")
    cart = load(bundle_root / "raw/cart.currency.json")
    assert jsonld["offers"]["price"] == "55.00" and jsonld["offers"]["priceCurrency"] == "GBP"
    assert jsonld["aggregateRating"]["ratingValue"] == "4.6" and jsonld["aggregateRating"]["reviewCount"] == "25"
    assert cart["currency"] == "GBP"

    sections = load(bundle_root / "sections.json")
    assert [section["order"] for section in sections["sections"]] == [1, 2, 3, 4]
    assert [section["source_heading"] for section in sections["sections"]] == ["Product description", "Details", "Fabric & care", "Delivery & returns"]
    details = sections["sections"][1]
    assert len([item for item in details["blocks"] if item["kind"] == "bullet"]) == 12
    assert sections["sections"][3]["target_composer_eligible"] is False
    assert {item["section"] for item in sections["expected_section_absences"]} == {"separate Size & Fit PDP accordion", "separate Sustainability PDP accordion"}

    size_guide = load(bundle_root / "size-guide.json")
    assert size_guide["status"] == "COMPLETE" and size_guide["measurement_basis"] == "BODY"
    table = size_guide["tables"][0]
    assert table["dimensions"] == {"rows": 5, "columns": 12}
    expected_rows = [
        ["UK Size", "4", "6", "8", "10", "12", "14", "16", "18", "20", "22", "24"],
        ["Dual Sizing", "XS", "", "S", "", "M", "", "L", "", "XL", "", "XXL"],
        ["Bust", "78", "82", "86", "90", "95", "100", "107", "114", "119", "124", "129"],
        ["Waist", "60", "64", "68", "72", "77", "82", "89", "96", "101", "106", "111"],
        ["Hips", "85", "89", "93", "97", "102", "107", "114", "121", "126", "131", "136"],
    ]
    assert [[cell["value"] for cell in row] for row in table["rows"]] == expected_rows
    assert all(cell["unitType"] == "cm" for row in table["rows"][2:] for cell in row[1:])
    assert table["authored_inch_table_status"] == table["footnote_status"] == "PROVEN_ABSENT"
    assert size_guide["complete_content_checks"] == {
        "how_to_measure_paragraphs": 6,
        "petite_intro_paragraphs": 3,
        "petite_adjustment_bullets": 11,
        "illustration_hashed": True,
        "hidden_select_size_control_excluded": True,
    }

    media = load(bundle_root / "media-manifest.json")
    assert media["orders_match"] is True and media["gallery_count"] == 5
    for gallery in (media["rendered_gallery"], media["structured_gallery"]):
        assert [item["order"] for item in gallery] == [1, 2, 3, 4, 5]
        assert all(re.fullmatch(r"[0-9a-f]{64}", item["content_sha256"]) for item in gallery)
        assert all(item["colour_association"] == "Navy" and item["excluded"] is False for item in gallery)
    assert len(media["explicit_exclusions"]) == 5

    evidence = load(bundle_root / "evidence-registry.json")
    assert evidence["acquisition"]["bounded_passes_used"] == 3
    assert evidence["acquisition"]["pass_3"]["further_live_acquisition_permitted"] is False
    assert evidence["acquisition_gaps"] == []
    assert evidence["reviews_evidence_only"]["target_composer_eligible"] is False
    claims = evidence["retailer_sustainability_and_trust_evidence_only"]
    assert claims["target_composer_eligible"] is False
    assert any("£15,000 to Blue Marine Foundation" in item for item in claims["editorial_blocks"])
    assert len(claims["transparency_claims"]) == 2

    assert oracle["expected"]["structured_product"] == product
    assert oracle["expected"]["sections"] == sections["sections"]
    assert oracle["expected"]["media"] == media
    assert oracle["expected"]["size_guide"] == size_guide


def main() -> None:
    v1_path = ROOT / "aggregate-manifest.json"
    v2_path = ROOT / "aggregate-manifest-v2.json"
    assert digest(v1_path) == V1_EXPECTED_SHA256
    v1 = load(v1_path)
    v2 = load(v2_path)
    assert v2["predecessor"] == {"path": "aggregate-manifest.json", "sha256": V1_EXPECTED_SHA256, "atlas_verdict": "DO_NOT_SIGN_ZERO_POSITIVE_DENOMINATORS"}
    assert v2["expected_blocker_fixtures"] == v1["expected_blocker_fixtures"]
    assert v2["incomplete_acquisition_denominators"] == v1["incomplete_acquisition_denominators"]
    assert len(v2["positive_denominators"]) == 1
    assert v2["denominator_ready_for_atlas_signature"] is True
    assert v2["reviewer_lock"] == {"status": "AWAITING_ATLAS_AGGREGATE_REVIEW", "signed_hash": None}
    verify_positive(v2["positive_denominators"][0])
    print(json.dumps({
        "status": "PASS_GATE_0A_UNSIGNED",
        "positive_denominators": 1,
        "positive_fixture": "nobodys-child-calloway",
        "retained_expected_or_incomplete_blockers": 3,
        "atlas_signature_status": "AWAITING_ATLAS_AGGREGATE_REVIEW",
    }, indent=2))


if __name__ == "__main__":
    main()
