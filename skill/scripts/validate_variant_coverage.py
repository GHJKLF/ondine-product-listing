#!/usr/bin/env python3
"""Validate a planned or read-back target against a pinned PDP colour family."""
import argparse
import json
from pathlib import Path
import sys

from product_listing.variant_coverage import validate_variant_coverage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="hash-pinned colour-family manifest")
    parser.add_argument("target", type=Path, help="planned target or normalized Shopify read-back JSON")
    args = parser.parse_args(argv)
    report = validate_variant_coverage(args.manifest, args.target)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
