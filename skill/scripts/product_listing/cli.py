"""Offline-only Phase 1 command line interface."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from pydantic import ValidationError

from product_listing.errors import PipelineStop
from product_listing.models import SourceCapture
from product_listing.replay import replay_bundle
from product_listing.validation import validate_source_capture


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="listing.py",
        description="Offline product source capture replay. No Shopify writer exists in Phase 1.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    replay = subcommands.add_parser("replay", help="replay a signed Scout fixture bundle")
    replay.add_argument("bundle", type=Path, help="directory containing bundle.json")
    replay.add_argument("--pretty", action="store_true", help="indent JSON output")

    validate = subcommands.add_parser("validate", help="validate a SourceCapture JSON file")
    validate.add_argument("capture", type=Path)
    validate.add_argument("--pretty", action="store_true", help="indent JSON output")
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
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
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
