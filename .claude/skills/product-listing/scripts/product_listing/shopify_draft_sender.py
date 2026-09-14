"""Minimal, transport-neutral Shopify DRAFT sender for Phase 3.

The module contains no HTTP, credentials, publication, stock quantities, media,
deletion, or rollback capability.  A caller must inject a narrowly scoped
transport whose implementation is outside this offline slice.
"""

from dataclasses import dataclass
from html import escape
import hashlib
import re
from typing import Any, Dict, List, Optional, Protocol, Sequence

from product_listing.listing_plan_canonical_json import canonical_json_bytes
from product_listing.listing_plan_models import (
    ListingPlan,
    ListingPlanValidationReport,
)


ONDINE_MYSHOPIFY_DOMAIN = "zfrbm1-y6.myshopify.com"
ONDINE_PRIMARY_DOMAIN_HOST = "ondinelondon.co.uk"
ONDINE_APPROVED_SHOP_NAME = "Ondine London"
MANAGED_BY = "product-listing-v2"
SHOP_GID_PATTERN = re.compile(r"^gid://shopify/Shop/[1-9][0-9]*$")


class DraftSendBlocked(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class UnknownWriteOutcome(RuntimeError):
    """Transport could not determine whether Shopify accepted a write."""


@dataclass(frozen=True)
class OndineStoreContract:
    contract_id: str
    myshopify_domain: str
    primary_domain_host: str
    approved_shop_name: str
    expected_shop_gid: str

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "OndineStoreContract":
        expected_keys = {
            "contract_id",
            "myshopify_domain",
            "primary_domain_host",
            "approved_shop_name",
            "expected_shop_gid",
        }
        if not isinstance(value, dict) or set(value) != expected_keys:
            raise DraftSendBlocked(
                "STORE_CONTRACT_INVALID",
                "store contract must contain exactly the five approved identity fields",
            )
        contract = cls(**value)
        if (
            not contract.contract_id
            or contract.myshopify_domain != ONDINE_MYSHOPIFY_DOMAIN
            or contract.primary_domain_host != ONDINE_PRIMARY_DOMAIN_HOST
            or contract.approved_shop_name != ONDINE_APPROVED_SHOP_NAME
            or not SHOP_GID_PATTERN.fullmatch(contract.expected_shop_gid)
        ):
            raise DraftSendBlocked(
                "STORE_CONTRACT_INVALID",
                "store contract does not identify the approved Ondine store",
            )
        return contract


@dataclass(frozen=True)
class ShopIdentity:
    shop_gid: str
    myshopify_domain: str
    primary_domain_host: str
    shop_name: str


@dataclass(frozen=True)
class ProductSnapshot:
    product_id: str
    shop_gid: str
    status: str
    publication_ids: Sequence[str]
    state: Dict[str, Any]


class ShopifyDraftTransport(Protocol):
    def read_shop_identity(self) -> ShopIdentity:
        ...

    def find_candidates(
        self,
        source_key: str,
        title: str,
        handle: str,
    ) -> Sequence[ProductSnapshot]:
        ...

    def create_draft(self, desired_state: Dict[str, Any]) -> str:
        ...

    def update_draft(self, product_id: str, desired_state: Dict[str, Any]) -> None:
        ...

    def read_product(self, product_id: str) -> ProductSnapshot:
        ...


@dataclass(frozen=True)
class DraftSendResult:
    action: str
    committed: bool
    product_id: Optional[str]
    source_key: str
    desired_state_sha256: str
    current_state_sha256: Optional[str]
    diff: List[Dict[str, Any]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "committed": self.committed,
            "product_id": self.product_id,
            "source_key": self.source_key,
            "desired_state_sha256": self.desired_state_sha256,
            "current_state_sha256": self.current_state_sha256,
            "diff": self.diff,
        }


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fact_value(plan: ListingPlan, fact_id: str) -> Any:
    matches = [
        binding.value
        for binding in plan.fact_packet_projection.bindings
        if binding.fact_packet_fact_id == fact_id
    ]
    if len(matches) != 1:
        raise DraftSendBlocked(
            "LISTING_PLAN_OWNERSHIP_INVALID",
            "required FactPacket binding is missing or duplicated: %s" % fact_id,
        )
    return matches[0]


def _derived_value(plan: ListingPlan, fact_id: str) -> Any:
    matches = [
        fact.value for fact in plan.derived_facts if fact.derived_fact_id == fact_id
    ]
    if len(matches) != 1:
        raise DraftSendBlocked(
            "LISTING_PLAN_OWNERSHIP_INVALID",
            "required derived fact is missing or duplicated: %s" % fact_id,
        )
    return matches[0]


def _validated_plan(
    document: Dict[str, Any],
    report: ListingPlanValidationReport,
) -> ListingPlan:
    document_sha256 = _sha256(canonical_json_bytes(document))
    if (
        not report.schema_valid
        or not report.committable
        or any(issue.blocking for issue in report.issues)
        or report.listing_plan_sha256 != document_sha256
    ):
        raise DraftSendBlocked(
            "LISTING_PLAN_NOT_COMMITTABLE",
            "sender requires an exact, committable validation receipt",
        )
    return ListingPlan.model_validate(document)


def _assert_shop(
    identity: ShopIdentity,
    contract: OndineStoreContract,
) -> None:
    if (
        identity.shop_gid != contract.expected_shop_gid
        or identity.myshopify_domain != contract.myshopify_domain
        or identity.primary_domain_host != contract.primary_domain_host
        or identity.shop_name != contract.approved_shop_name
    ):
        raise DraftSendBlocked(
            "WRONG_SHOP",
            "Shop query does not exactly match the expected Ondine store contract",
        )


def build_desired_state(
    plan: ListingPlan,
    contract: OndineStoreContract,
) -> Dict[str, Any]:
    target = plan.shopify_target_state
    canonical_identity = _derived_value(plan, "df.canonical_source_identity")
    canonical_source_url = _fact_value(plan, "fp.canonical_source_url")
    source_tag = _derived_value(plan, "df.source_tag")
    if not all(
        isinstance(value, str) and value
        for value in (canonical_identity, canonical_source_url, source_tag)
    ):
        raise DraftSendBlocked(
            "LISTING_PLAN_OWNERSHIP_INVALID",
            "source ownership values must be non-empty strings",
        )
    source_key = _sha256(
        (contract.expected_shop_gid + canonical_identity).encode("utf-8")
    )
    public_tags = list(target.tags)
    if source_tag in public_tags:
        raise DraftSendBlocked(
            "LISTING_PLAN_OWNERSHIP_INVALID",
            "private source tag must not already exist in public tags",
        )
    description_parts: List[str] = []
    for slot in plan.composition.description.slots:
        paragraph_parts = []
        text = slot.get("text")
        if isinstance(text, str) and text:
            paragraph_parts.append(text)
        items = slot.get("items")
        if isinstance(items, list) and items:
            # Historical unit fixtures used a benefits list. Render its text
            # as prose too; current-mode validation requires five prose slots.
            paragraph_parts.extend(
                str(item["text"]) for item in items
                if isinstance(item, dict) and item.get("text")
            )
        if paragraph_parts:
            description_parts.append("<p>%s</p>" % escape(" ".join(paragraph_parts)))

    return {
        "status": "DRAFT",
        "title": target.title,
        "handle": target.handle,
        "vendor": target.vendor,
        "product_type": target.product_type,
        "category_path": target.gmc.google_product_category,
        "gmc": target.gmc.model_dump(exclude={"fact_refs", "feed_image_binding"}),
        "description_html": "".join(description_parts),
        "options": [
            {
                "name": option.name,
                "position": option.position,
                "values": list(option.values),
            }
            for option in target.options
        ],
        "variants": [
            {
                "option_values": dict(variant.option_values),
                "price": variant.price,
                "sku": variant.sku,
                "mpn": variant.mpn,
                "taxable": False,
                "inventoryItem": {"tracked": False},
                **({"weight_grams": variant.weight_grams}
                   if variant.weight_grams is not None else {}),
            }
            for variant in target.variants
        ],
        "collections": sorted(target.collections),
        "tags": sorted(public_tags),
        "metafields": dict(target.metafields),
        "rich_text_metafields": dict(target.rich_text_metafields),
        "seo": {
            "page_title": target.seo.page_title,
            "meta_description": target.seo.meta_description,
        },
        "ownership": {
            "managed_by": MANAGED_BY,
            "source_key": source_key,
            "source_url": canonical_source_url,
            "source_tag": source_tag,
        },
    }


def _diff(before: Dict[str, Any], after: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"path": "/" + key, "before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before).union(after))
        if before.get(key) != after.get(key)
    ]


def _state_sha256(state: Dict[str, Any]) -> str:
    return _sha256(canonical_json_bytes(state))


def _assert_owned_draft(
    snapshot: ProductSnapshot,
    contract: OndineStoreContract,
    expected_ownership: Dict[str, Any],
) -> None:
    if snapshot.shop_gid != contract.expected_shop_gid:
        raise DraftSendBlocked("WRONG_SHOP", "product belongs to another shop")
    if snapshot.status != "DRAFT":
        raise DraftSendBlocked(
            "MATCH_NOT_DRAFT",
            "matching product is ACTIVE, ARCHIVED, or otherwise not DRAFT",
        )
    if list(snapshot.publication_ids):
        raise DraftSendBlocked(
            "PRODUCT_HAS_PUBLICATIONS",
            "matching DRAFT has one or more publications",
        )
    if snapshot.state.get("ownership") != expected_ownership:
        raise DraftSendBlocked(
            "MATCH_NOT_OWNED",
            "matching product is not exactly owned by product-listing-v2",
        )


def _read_back(
    transport: ShopifyDraftTransport,
    product_id: str,
    desired_state: Dict[str, Any],
    contract: OndineStoreContract,
) -> ProductSnapshot:
    snapshot = transport.read_product(product_id)
    if snapshot.product_id != product_id:
        raise DraftSendBlocked("READ_BACK_MISMATCH", "read-back product ID changed")
    _assert_owned_draft(snapshot, contract, desired_state["ownership"])
    if canonical_json_bytes(snapshot.state) != canonical_json_bytes(desired_state):
        raise DraftSendBlocked(
            "READ_BACK_MISMATCH",
            "canonical Shopify read-back does not equal desired DRAFT state",
        )
    return snapshot


def send_shopify_draft(
    document: Dict[str, Any],
    validation_report: ListingPlanValidationReport,
    contract: OndineStoreContract,
    transport: ShopifyDraftTransport,
    commit: bool = False,
) -> DraftSendResult:
    plan = _validated_plan(document, validation_report)
    identity = transport.read_shop_identity()
    _assert_shop(identity, contract)
    desired = build_desired_state(plan, contract)
    desired_hash = _state_sha256(desired)
    source_key = desired["ownership"]["source_key"]
    candidates = list(
        transport.find_candidates(source_key, desired["title"], desired["handle"])
    )
    if len(candidates) > 1:
        raise DraftSendBlocked(
            "MULTIPLE_PRODUCT_MATCHES",
            "preflight found more than one source/title/handle candidate",
        )

    current = candidates[0] if candidates else None
    if current is not None:
        _assert_owned_draft(current, contract, desired["ownership"])
    current_state = current.state if current is not None else {}
    current_hash = _state_sha256(current_state) if current is not None else None
    diff = _diff(current_state, desired)
    action = "CREATE" if current is None else ("UPDATE" if diff else "NOOP")
    if not commit:
        return DraftSendResult(
            action=action,
            committed=False,
            product_id=current.product_id if current is not None else None,
            source_key=source_key,
            desired_state_sha256=desired_hash,
            current_state_sha256=current_hash,
            diff=diff,
        )

    if current is None:
        try:
            product_id = transport.create_draft(desired)
        except UnknownWriteOutcome as exc:
            recovered = list(
                transport.find_candidates(source_key, desired["title"], desired["handle"])
            )
            if len(recovered) != 1:
                raise DraftSendBlocked(
                    "WRITE_OUTCOME_UNKNOWN",
                    "read-after-unknown did not find exactly one owned product",
                ) from exc
            _assert_owned_draft(recovered[0], contract, desired["ownership"])
            product_id = recovered[0].product_id
            action = "RECOVERED_CREATE"
    elif diff:
        product_id = current.product_id
        try:
            transport.update_draft(product_id, desired)
        except UnknownWriteOutcome as exc:
            recovered = list(
                transport.find_candidates(source_key, desired["title"], desired["handle"])
            )
            if len(recovered) != 1 or recovered[0].product_id != product_id:
                raise DraftSendBlocked(
                    "WRITE_OUTCOME_UNKNOWN",
                    "read-after-unknown could not prove the same owned product",
                ) from exc
            _assert_owned_draft(recovered[0], contract, desired["ownership"])
            action = "RECOVERED_UPDATE"
    else:
        product_id = current.product_id

    verified = _read_back(transport, product_id, desired, contract)
    return DraftSendResult(
        action=action,
        committed=True,
        product_id=product_id,
        source_key=source_key,
        desired_state_sha256=desired_hash,
        current_state_sha256=_state_sha256(verified.state),
        diff=diff,
    )
