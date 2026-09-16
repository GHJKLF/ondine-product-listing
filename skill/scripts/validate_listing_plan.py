#!/usr/bin/env python3
"""Standalone Phase 2 validator; intentionally separate from Phase 1 CLI."""

from product_listing.listing_plan_cli import main


if __name__ == "__main__":
    raise SystemExit(main())

