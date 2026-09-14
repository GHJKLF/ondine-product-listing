#!/usr/bin/env python3
"""Regenerate the checked-in SourceCapture JSON Schema deterministically."""

import json
from pathlib import Path

from product_listing.models import SourceCapture


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "source-capture.schema.json"


def main() -> int:
    schema = SourceCapture.model_json_schema()
    serialized = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(serialized, encoding="utf-8")
    print(SCHEMA_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
