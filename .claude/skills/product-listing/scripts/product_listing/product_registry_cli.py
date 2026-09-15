"""Register assistant-verified facts, or an existing genuine independent review.

Per-fact source checks must already be recorded. The normal path records them as
an assistant self-check, never as independent or human approval. Hashes provide
integrity, not authentication or a substitute for examining the evidence.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, Sequence

from product_listing.evidence import canonical_json_bytes as source_json
from product_listing.listing_plan_canonical_json import canonical_json_bytes
from product_listing.listing_plan_projection_registry import (
    _manifest_structure_errors, _registry_artifact_errors, _separation_errors,
    sha256_bytes, SELF_CHECK,
)
from product_listing.listing_plan_models import FactBinding
from product_listing.listing_plan_validation import source_fact_issues
from product_listing.models import ReplayResult
from product_listing.validation import validate_source_capture


def register_product(manifest_path: Path, review_path: Optional[Path], capture_path: Path,
                     output: Path, reviewer_id: Optional[str] = None) -> dict:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    capture = ReplayResult.model_validate_json(capture_path.read_text(encoding="utf-8"))
    if not capture.valid or capture.issues or validate_source_capture(capture.source_capture):
        raise ValueError("source capture must validate with no issues before registration")
    source_hash = sha256_bytes(source_json(capture.model_dump(mode="json", exclude_none=False)) + b"\n")
    determinism_hash = sha256_bytes(source_json(capture.source_capture.model_dump(mode="json", exclude_none=False)))
    if capture.determinism_sha256 != determinism_hash:
        raise ValueError("source capture determinism hash mismatch")
    bindings = manifest["bindings"]
    actor_id = manifest["actors"]["author_auditor"]["actor_id"]
    manifest_sha = sha256_bytes(manifest_bytes)
    binding_hash = sha256_bytes(canonical_json_bytes(bindings))
    self_check = review_path is None
    if self_check:
        if reviewer_id is not None or manifest.get("verification_method") != SELF_CHECK:
            raise ValueError("normal registration requires ASSISTANT_SELF_CHECK evidence, not a reviewer")
        review = {
            "verification_method": SELF_CHECK,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "assistant_verifier": {"actor_id": actor_id, "verification_status": "COMPLETE"},
            "manifest": {"manifest_id": manifest["manifest_id"], "sha256": manifest_sha,
                         "author_actor_id": actor_id, "verification_actor_id": actor_id,
                         "verification_status": "ASSISTANT_SELF_CHECK_COMPLETE"},
            "accepted_projection": {
                "source_capture_output_sha256": source_hash,
                "source_capture_determinism_sha256": determinism_hash,
                "ordered_binding_count": len(bindings),
                "ordered_bindings_canonical_sha256": binding_hash,
                "allowed_count": len(bindings), "blocked_count": 0,
            },
        }
        review_bytes = canonical_json_bytes(review) + b"\n"
    else:
        review_bytes = review_path.read_bytes()
        review = json.loads(review_bytes)
        actual_reviewer = review["reviewer_signatory"]["actor_id"]
        if not reviewer_id or not reviewer_id.strip() or actual_reviewer != reviewer_id:
            raise ValueError("reviewer identity does not match the operator-supplied reviewer")
    entry = {
        "manifest_id": manifest["manifest_id"],
        "manifest_path": "manifest.json", "manifest_sha256": manifest_sha,
        "author_actor_id": actor_id,
        "ordered_binding_count": len(bindings),
        "ordered_bindings_canonical_sha256": binding_hash,
        "fixture_only": False,
    }
    if self_check:
        entry.update(verification_method=SELF_CHECK, verification_actor_id=actor_id,
                     verification_path="verification.json", verification_sha256=sha256_bytes(review_bytes))
    else:
        entry.update(atlas_lock_path="review.json", atlas_lock_sha256=sha256_bytes(review_bytes),
                     reviewer_actor_id=reviewer_id)
    errors = _manifest_structure_errors(manifest, entry)
    errors += _separation_errors(manifest, review, entry, manifest_sha)
    evidence_pins = SimpleNamespace(source_capture_sha256=source_hash,
                                   source_capture_determinism_sha256=determinism_hash)
    errors += _registry_artifact_errors(SimpleNamespace(evidence=evidence_pins),
                                       capture.source_capture, manifest, review, entry)
    if self_check:
        packet = SimpleNamespace(bindings=[FactBinding.model_validate(binding) for binding in bindings])
        errors += [issue.message for issue in source_fact_issues(
            SimpleNamespace(fact_packet_projection=packet), capture.source_capture)]
    if errors:
        raise ValueError("; ".join(errors))
    registry = {"schema_version": 1, "fact_packet_projection_registry": [entry]}
    registry_bytes = canonical_json_bytes(registry) + b"\n"
    # Refuse to overwrite any previous run or silently replace its approved facts.
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_bytes(manifest_bytes)
    (output / ("verification.json" if self_check else "review.json")).write_bytes(review_bytes)
    (output / "source-capture.json").write_text(
        source_json(capture.model_dump(mode="json", exclude_none=False)).decode() + "\n",
        encoding="utf-8")
    (output / "registry.json").write_bytes(registry_bytes)
    return {"registered": True, "manifest_id": manifest["manifest_id"],
            "manifest_sha256": manifest_sha, "registry": str(output / "registry.json"),
            "registry_sha256": sha256_bytes(registry_bytes),
            "verification_method": SELF_CHECK if self_check else "INDEPENDENT_REVIEW",
            "listing_validated": False, "shopify_written": False}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Register assistant-verified product facts; no separate reviewer or Shopify writes.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("capture_or_review", type=Path, help="SourceCapture; or existing detached review for the legacy three-file form")
    parser.add_argument("source_capture", type=Path, nargs="?", help="Only for an existing independent review")
    parser.add_argument("--reviewer-id", help="Only for an existing genuine independent review")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = register_product(args.manifest,
                                  args.capture_or_review if args.source_capture else None,
                                  args.source_capture or args.capture_or_review,
                                  args.output, args.reviewer_id)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = {"registered": False, "error": str(exc), "shopify_written": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["registered"] else 2
