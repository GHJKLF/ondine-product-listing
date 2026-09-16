#!/usr/bin/env python3
"""Regenerate the checked-in Phase 2 schemas deterministically."""

import json
from pathlib import Path

from product_listing.listing_plan_models import FactPacket, ListingPlan


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


def _write(path: Path, schema: dict) -> None:
    path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        SCHEMA_DIR / "fact-packet.schema.json": FactPacket.model_json_schema(),
        SCHEMA_DIR / "listing-plan.schema.json": ListingPlan.model_json_schema(by_alias=True),
    }
    for path, schema in outputs.items():
        _write(path, schema)
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
