"""Read-only CLI for offline ListingPlan validation."""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from product_listing.listing_plan_validation import (
    DEFAULT_PHASE_2_LOCK,
    validate_listing_plan_document,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate-listing-plan",
        description=(
            "Offline ListingPlan validation. FactPacket projection manifests "
            "resolve through the historical registry or an explicitly hash-pinned "
            "product registry. Plans cannot choose registry paths or URLs."
        ),
    )
    parser.add_argument("listing_plan", type=Path)
    parser.add_argument("--product-registry", type=Path,
                        help="run-local registry created by register_projection.py")
    parser.add_argument("--product-registry-sha256",
                        help="registry hash returned by source verification/registration")
    parser.add_argument("--size-mapping-approval", type=Path,
                        help="external record of the user's product-specific size-label approval")
    parser.add_argument("--size-mapping-approval-sha256",
                        help="trusted hash of the external size-label approval record")
    parser.add_argument(
        "--lock",
        type=Path,
        default=DEFAULT_PHASE_2_LOCK,
        help="Atlas Phase 2 composition lock (hash-pinned)",
    )
    parser.add_argument(
        "--source-capture",
        type=Path,
        help="Phase 1 replay-result JSON; required for committable validation",
    )
    parser.add_argument(
        "--source-bundle",
        type=Path,
        help="signed offline bundle root for hash-pinned source audit artifacts",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        document = json.loads(args.listing_plan.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("ListingPlan JSON root must be an object")
        source_capture_evidence = None
        if args.source_capture is not None:
            source_capture_evidence = json.loads(
                args.source_capture.read_text(encoding="utf-8")
            )
        report = validate_listing_plan_document(
            document,
            args.lock,
            source_capture_evidence=source_capture_evidence,
            source_artifact_root=args.source_bundle,
            test_mode=False,
            product_registry_path=args.product_registry,
            product_registry_sha256=args.product_registry_sha256,
            size_mapping_approval_path=args.size_mapping_approval,
            size_mapping_approval_sha256=args.size_mapping_approval_sha256,
        )
        result = report.model_dump(mode="json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "schema_valid": False,
            "committable": False,
            "phase_2_lock_sha256": None,
            "listing_plan_sha256": None,
            "issues": [
                {
                    "code": "LISTING_PLAN_INPUT_INVALID",
                    "field_path": str(args.listing_plan),
                    "message": str(exc),
                    "blocking": True,
                }
            ],
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["schema_valid"] and result["committable"] else 2
