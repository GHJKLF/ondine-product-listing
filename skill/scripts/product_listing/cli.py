"""Offline-only Phase 1 command line interface."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from pydantic import ValidationError

from product_listing.errors import PipelineStop
from product_listing.models import SourceCapture
from product_listing.live_capture import prepare_live_capture, finalize_live_capture, write_new_json
from product_listing.replay import replay_bundle
from product_listing.validation import validate_source_capture


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="listing.py",
        description="Prepare and validate source evidence offline. These commands never write to Shopify.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    replay = subcommands.add_parser("replay", help="replay a signed Scout fixture bundle")
    replay.add_argument("bundle", type=Path, help="directory containing bundle.json")
    replay.add_argument("--pretty", action="store_true", help="indent JSON output")

    validate = subcommands.add_parser("validate", help="validate a SourceCapture JSON file")
    validate.add_argument("capture", type=Path)
    validate.add_argument("--pretty", action="store_true", help="indent JSON output")
    prepare = subcommands.add_parser("prepare-live", help="build review candidates from a real fetch_source report")
    prepare.add_argument("report", type=Path)
    prepare.add_argument("--source-bundle", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    finalize = subcommands.add_parser("finalize-live", help="validate reviewed live evidence and create its envelope")
    finalize.add_argument("capture", type=Path)
    finalize.add_argument("--source-bundle", type=Path, required=True)
    finalize.add_argument("--output", type=Path, required=True)
    return parser


def _dump(value, pretty: bool) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare-live":
            capture = prepare_live_capture(args.report, args.source_bundle)
            write_new_json(args.output, capture)
            _dump({"candidate_created": True, "listing_ready": False, "output": str(args.output),
                   "issues": [item.model_dump(mode="json") for item in validate_source_capture(capture)]}, True)
            return 0
        if args.command == "finalize-live":
            result = finalize_live_capture(args.capture, args.source_bundle)
            write_new_json(args.output, result)
            _dump({"valid": True, "output": str(args.output),
                   "determinism_sha256": result.determinism_sha256, "shopify_written": False}, True)
            return 0
        if args.command == "replay":
            result = replay_bundle(args.bundle)
            _dump(result.model_dump(mode="json", exclude_none=False), args.pretty)
            return 0 if result.valid else 2
        if args.command == "validate":
            payload = json.loads(args.capture.read_text(encoding="utf-8"))
            capture = SourceCapture.model_validate(payload)
            issues = validate_source_capture(capture)
            has_blocking_issues = any(issue.blocking for issue in issues)
            _dump(
                {
                    "valid": not has_blocking_issues,
                    "issues": [issue.model_dump(mode="json") for issue in issues],
                },
                args.pretty,
            )
            return 2 if has_blocking_issues else 0
    except PipelineStop as exc:
        _dump({"valid": False, "stop": exc.as_dict()}, True)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        _dump(
            {
                "valid": False,
                "stop": {
                    "code": "CONTRACT_VALIDATION_ERROR",
                    "message": str(exc),
                    "details": {},
                },
            },
            True,
        )
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
