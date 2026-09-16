#!/usr/bin/env python3
"""Read-only Gate 0A integrity validator for the frozen SourceCapture bundles."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_bundle(entry: dict) -> tuple[Path, dict, dict]:
    bundle_path = (ROOT / entry["bundle_path"]).resolve()
    index_path = (ROOT / entry["bundle_hash_index_path"]).resolve()
    oracle_path = (ROOT / entry["oracle_path"]).resolve()
    assert digest(bundle_path) == entry["bundle_sha256"]
    assert digest(index_path) == entry["bundle_hash_index_sha256"]
    assert digest(oracle_path) == entry["oracle_sha256"]
    bundle_root = bundle_path.parent
    for line in index_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        assert digest(bundle_root / relative) == expected, relative
    bundle = load(bundle_path)
    oracle = load(oracle_path)
    assert bundle["fixture_id"] == oracle["fixture_id"] == entry["fixture_id"]
    capture = bundle["capture"]
    assert capture["market"] == "GB"
    assert capture["locale"] == "en-GB"
    assert capture["currency"] == "GBP"
    assert all(capture[name].startswith("https://") for name in ("requested_url", "final_url", "canonical_url"))
    assert capture["json_ld"]["status"] == "ACQUISITION_GAP_NOT_FROZEN"
    media = load(bundle_root / bundle["files"]["media"])
    for gallery_name in ("rendered_gallery", "structured_gallery"):
        gallery = media[gallery_name]
        assert [item["order"] for item in gallery] == list(range(1, len(gallery) + 1))
        assert all(re.fullmatch(r"[0-9a-f]{64}", item["content_sha256"]) for item in gallery)
    sections = load(bundle_root / bundle["files"]["sections"])
    assert [section["order"] for section in sections["sections"]] == list(range(1, len(sections["sections"]) + 1))
    rendered = (bundle_root / "rendered.sanitized.html").read_text(encoding="utf-8", errors="replace")
    assert not re.search(r"(?i)(access[_-]?token|client[_-]?secret|api[_-]?key|authorization:\s*bearer)", rendered)
    return bundle_root, bundle, oracle


def main() -> None:
    manifest = load(ROOT / "aggregate-manifest.json")
    assert manifest["canonical_bundle_entrypoint"] == "bundle.json"
    assert manifest["positive_denominators"] == []
    assert manifest["denominator_ready_for_atlas_signature"] is False
    entries = manifest["expected_blocker_fixtures"] + manifest["incomplete_acquisition_denominators"]
    checked = {entry["fixture_id"]: verify_bundle(entry) for entry in entries}

    phase_root, phase, _ = checked["phase-eight-avenly"]
    assert {item["code"] for item in phase["conflicts"]} == {"MARKET_CURRENCY_RESPONSE_CONFLICT", "COMPOSITION_TOTAL_97_PERCENT"}
    assert [len(table["cells"]) for table in load(phase_root / "size-guide.json")["tables"]] == [18, 18, 8]

    nfd_root, nfd, _ = checked["nfd-abstract-tilly"]
    assert "SIZE_GUIDE_INCH_UNIT_NOT_FROZEN" in {item["code"] for item in nfd["acquisition_gaps"]}
    assert len(load(nfd_root / "media-manifest.json")["rendered_gallery"]) == 8
    assert len(load(nfd_root / "media-manifest.json")["structured_gallery"]) == 9
    assert len(load(nfd_root / "structured-product.json")["colour_relations"]) == 6

    omnes_root, omnes, _ = checked["omnes-bridie-sunset-blur"]
    conflict = next(item for item in omnes["conflicts"] if item["code"] == "MATERIAL_POLYESTER_VS_VISCOSE")
    assert conflict["severity"] == "BLOCKING" and len(conflict["claims"]) == 2
    omnes_sections = load(omnes_root / "sections.json")["sections"]
    fit = next(section for section in omnes_sections if section["source_heading"] == "Size & Fit")
    assert [block["occurrence"] for block in fit["blocks"] if block["kind"] == "fit_fact"] == [1, 2]
    assert all(block.get("target_fit_note_eligible") is False for block in fit["blocks"] if block["kind"] == "label_value")
    assert [len(table["cells"]) for table in load(omnes_root / "size-guide.json")["tables"]] == [9, 9]
    relation = load(omnes_root / "structured-product.json")["colour_relations"][0]
    assert relation["relation"] == "LINKED_SIBLING_PDP" and relation["complete"] is False
    evidence = load(omnes_root / "evidence-registry.json")
    assert any("LOGITECH" in item["reason"] for item in evidence["invalid_preserved"])
    assert sum(item["scope"] == "historical_shopify_status_only_not_source_denominator" for item in evidence["accepted"]) == 1

    print(json.dumps({"status": "PASS_FAIL_CLOSED", "bundles_checked": sorted(checked), "positive_denominators": 0, "expected_or_incomplete_blockers": 3}, indent=2))


if __name__ == "__main__":
    main()
