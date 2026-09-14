"""Register already-reviewed product evidence; never create reviewer approvals.

The output hash must be supplied by the operator outside the ListingPlan. Hashes
provide integrity, not authentication: real independent review is still required.
"""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, Sequence

from product_listing.evidence import canonical_json_bytes as source_json
from product_listing.listing_plan_canonical_json import canonical_json_bytes
from product_listing.listing_plan_projection_registry import (
    _manifest_structure_errors, _registry_artifact_errors, _separation_errors,
    sha256_bytes,
)
from product_listing.models import ReplayResult
from product_listing.validation import validate_source_capture


def register_product(manifest_path: Path, review_path: Path, capture_path: Path,
                     output: Path, reviewer_id: str) -> dict:
    manifest_bytes = manifest_path.read_bytes()
    review_bytes = review_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    review = json.loads(review_bytes)
    capture = ReplayResult.model_validate_json(capture_path.read_text(encoding="utf-8"))
    if not capture.valid or capture.issues or validate_source_capture(capture.source_capture):
        raise ValueError("source capture must validate with no issues before registration")
    source_hash = sha256_bytes(source_json(capture.model_dump(mode="json", exclude_none=False)) + b"\n")
    determinism_hash = sha256_bytes(source_json(capture.source_capture.model_dump(mode="json", exclude_none=False)))
    if capture.determinism_sha256 != determinism_hash:
        raise ValueError("source capture determinism hash mismatch")
    bindings = manifest["bindings"]
    actor_id = manifest["actors"]["author_auditor"]["actor_id"]
    actual_reviewer = review["reviewer_signatory"]["actor_id"]
    if not reviewer_id.strip() or actual_reviewer != reviewer_id:
        raise ValueError("reviewer identity does not match the operator-supplied reviewer")
    manifest_sha = sha256_bytes(manifest_bytes)
    entry = {
        "manifest_id": manifest["manifest_id"],
        "manifest_path": "manifest.json", "manifest_sha256": manifest_sha,
        "atlas_lock_path": "review.json", "atlas_lock_sha256": sha256_bytes(review_bytes),
        "author_actor_id": actor_id, "reviewer_actor_id": reviewer_id,
        "ordered_binding_count": len(bindings),
        "ordered_bindings_canonical_sha256": sha256_bytes(canonical_json_bytes(bindings)),
        "fixture_only": False,
    }
    errors = _manifest_structure_errors(manifest, entry)
    errors += _separation_errors(manifest, review, entry, manifest_sha)
    evidence_pins = SimpleNamespace(source_capture_sha256=source_hash,
                                   source_capture_determinism_sha256=determinism_hash)
    errors += _registry_artifact_errors(SimpleNamespace(evidence=evidence_pins),
                                       capture.source_capture, manifest, review, entry)
    if errors:
        raise ValueError("; ".join(errors))
    registry = {"schema_version": 1, "fact_packet_projection_registry": [entry]}
    registry_bytes = canonical_json_bytes(registry) + b"\n"
    # Refuse to overwrite any previous run or silently replace its approved facts.
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_bytes(manifest_bytes)
    (output / "review.json").write_bytes(review_bytes)
    (output / "source-capture.json").write_text(
        source_json(capture.model_dump(mode="json", exclude_none=False)).decode() + "\n",
        encoding="utf-8")
    (output / "registry.json").write_bytes(registry_bytes)
    return {"registered": True, "manifest_id": manifest["manifest_id"],
            "manifest_sha256": manifest_sha, "registry": str(output / "registry.json"),
            "registry_sha256": sha256_bytes(registry_bytes),
            "listing_validated": False, "shopify_written": False}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Register independently reviewed product facts; no Shopify writes.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("source_capture", type=Path)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = register_product(args.manifest, args.review, args.source_capture,
                                  args.output, args.reviewer_id)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = {"registered": False, "error": str(exc), "shopify_written": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["registered"] else 2
