"""Thin Phase 3 CLI; no live Shopify transport is bundled."""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from product_listing.listing_plan_models import ListingPlanValidationReport
from product_listing.shopify_draft_sender import (
    DraftSendBlocked,
    OndineStoreContract,
    ShopifyDraftTransport,
    send_shopify_draft,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="send-shopify-draft")
    parser.add_argument("listing_plan", type=Path)
    parser.add_argument("validation_report", type=Path)
    parser.add_argument("store_contract", type=Path)
    parser.add_argument(
        "--commit",
        action="store_true",
        help="create or resume one owned Shopify DRAFT; default is dry-run",
    )
    return parser


def main(
    argv: Optional[Sequence[str]] = None,
    transport: Optional[ShopifyDraftTransport] = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        if transport is None:
            raise DraftSendBlocked(
                "SHOPIFY_CONNECTOR_UNAVAILABLE",
                "use the existing Shopify connector; no second API transport is bundled",
            )
        document = json.loads(args.listing_plan.read_text(encoding="utf-8"))
        report = ListingPlanValidationReport.model_validate_json(
            args.validation_report.read_text(encoding="utf-8")
        )
        contract = OndineStoreContract.from_dict(
            json.loads(args.store_contract.read_text(encoding="utf-8"))
        )
        result = send_shopify_draft(
            document,
            report,
            contract,
            transport,
            commit=args.commit,
        ).as_dict()
        result["ok"] = True
    except (OSError, ValueError, json.JSONDecodeError, DraftSendBlocked) as exc:
        result = {
            "ok": False,
            "code": getattr(exc, "code", "DRAFT_SENDER_INPUT_INVALID"),
            "message": str(exc),
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["ok"] else 2
