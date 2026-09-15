"""Offline validation for FactPacket -> ListingPlan composition."""

import hashlib
import json
import re
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from pydantic import ValidationError

from product_listing.evidence import canonical_json_bytes as phase_1_canonical_json_bytes
from product_listing.listing_plan_canonical_json import (
    CanonicalizationError,
    canonical_json_bytes,
)
from product_listing.listing_plan_models import (
    ListingPlan,
    ListingPlanIssue,
    ListingPlanValidationReport,
    SizeMappingApprovalRecord,
)
from product_listing.listing_plan_copy_guard import (
    CopyGuardEvidenceError,
    build_copy_guard_result,
)
from product_listing.listing_plan_projection_registry import (
    projection_manifest_raw_issues,
    verify_projection_manifest,
)
from product_listing.models import ReplayResult, SourceCapture
from product_listing.validation import validate_source_capture


PHASE_2_LOCK_SHA256 = "6756399bf2afaed3258be318411951a1bf7fc61a9659c9a0ec08362a8445602b"
SKILL_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PHASE_2_LOCK = (
    SKILL_ROOT / "profiles" / "ondine" / "phase-2-composition-v5.ilias-lock.json"
)
MAINTENANCE_SHA256 = "ed18947bf4e0e6c8fc53943527b54283a09e199ae96c313ee808c3523f27dc26"
MAINTENANCE_PATH = SKILL_ROOT / "profiles/ondine/maintenance-2026-09-15.json"

EXPECTED_BELOW_FOLD_ORDER = [
    "description",
    "details_and_care",
    "size_and_fit",
    "materials_and_provenance",
    "delivery",
    "returns_and_refunds",
]
EXPECTED_SLOT_IDS = ["opening", "occasion", "benefits", "styling", "close"]
EXPECTED_MEDIA_ROLES = [
    "FRONT_GMC",
    "BACK",
    "SIDE_MOVEMENT",
    "DETAIL",
    "LIFESTYLE",
    "GHOST_FLAT",
]
REQUIRED_METAFIELDS = {"size", "fabric", "occasion", "neckline", "age_group"}
POLICY_URLS = {
    "delivery": "https://ondinelondon.co.uk/pages/shipping-policy",
    "returns_and_refunds": "https://ondinelondon.co.uk/pages/returns-refund-policy",
}
ALLOWED_TRANSFORM_IDS = {
    "ondine_original_title_v1",
    "ondine_original_five_slot_copy_v1",
    "ondine_price_nearest_95_below_v1",
    "ondine_uk_numeric_size_identity_v1",
    "ondine_approved_source_size_label_v1",
    "ondine_option_identity_v1",
    "ondine_variant_matrix_preserve_real_v1",
    "ondine_style_code_v1",
    "ondine_colour_code_v1",
    "ondine_sku_mpn_v3",
    "ondine_occasion_from_end_use_v1",
    "ondine_adult_womenswear_defaults_v1",
    "ondine_dress_taxonomy_v1",
    "ondine_handle_slug_v1",
    "ondine_seo_copy_v1",
    "ondine_tags_v1",
    "ondine_media_plan_v1",
    "ondine_weight_identity_v1",
    "ondine_canonical_source_identity_v1",
    "ondine_source_tag_v1",
    "ondine_source_key_v1",
}
RAW_SOURCE_PREFIXES = (
    "source_capture.",
    "sections.",
    "structured_product.",
    "structured_product_evidence.",
)
REFERENCE_KEYS = {
    "fact_ref",
    "fact_refs",
    "input_fact_ref",
    "input_fact_refs",
    "combination_fact_ref",
    "price_fact_ref",
    "weight_fact_ref",
    "product_type_fact_ref",
    "colour_fact_ref",
    "garment_fact_refs",
    "derived_fact_ref",
    "title_ref",
    "style_code_ref",
    "colour_code_ref",
    "canonical_source_identity_ref",
    "canonical_source_url_ref",
    "value_ref",
    "source_key_ref",
    "source_url_ref",
    "expected_ref",
    "input_refs",
    "size_guide_ref",
    "policy_binding",
    "target_model_record_ref",
    "pdp_order_ref",
    "buy_box_ref",
    "description_ref",
    "below_fold_sections_ref",
}
ALLOWED_REFERENCE_PREFIXES = (
    "fp.",
    "df.",
    "profile.",
    "policy_snapshot.",
    "target_model.",
    "store_contract.",
    "run_state.",
    "composition.",
    "ondine.",
)
ALLOWED_REFERENCE_LITERALS = {"ondine-size-chart-current"}


class ContractLoadError(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _phase_2_document_sha256(value: Any) -> Optional[str]:
    try:
        return _sha256_bytes(canonical_json_bytes(value))
    except CanonicalizationError:
        return None


def _safe_workspace_path(workspace_root: Path, relative_path: str) -> Path:
    candidate = (workspace_root / relative_path).resolve()
    try:
        candidate.relative_to(workspace_root)
    except ValueError as exc:
        raise ContractLoadError("locked path escapes workspace: %s" % relative_path) from exc
    if not candidate.is_file():
        raise ContractLoadError("locked artifact is missing: %s" % relative_path)
    return candidate


def _load_locked_contract(lock_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    lock_path = lock_path.resolve()
    actual_lock_hash = _sha256_bytes(lock_path.read_bytes())
    if actual_lock_hash != PHASE_2_LOCK_SHA256:
        raise ContractLoadError(
            "Phase 2 lock hash mismatch: expected %s, got %s"
            % (PHASE_2_LOCK_SHA256, actual_lock_hash)
        )
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    workspace_root = lock_path.parents[5]
    # Reconcile mutable operational documents through a separately pinned maintenance
    # revision. Never rewrite historical approval records or trust unpinned edits.
    if _sha256_bytes(MAINTENANCE_PATH.read_bytes()) != MAINTENANCE_SHA256:
        raise ContractLoadError("maintenance revision hash mismatch")
    maintenance = json.loads(MAINTENANCE_PATH.read_text(encoding="utf-8"))
    revisions = {item["path"]: item for item in maintenance["artifacts"]}
    for historical_record in list(lock.get("artifacts") or []) + list(lock.get("phase_1_dependencies") or []):
        record = revisions.get(historical_record["path"], historical_record)
        path = _safe_workspace_path(workspace_root, str(record["path"]))
        actual = _sha256_bytes(path.read_bytes())
        if actual != record["sha256"]:
            raise ContractLoadError(
                "locked artifact hash mismatch for %s: expected %s, got %s"
                % (record["path"], record["sha256"], actual)
            )
    example_record = next(
        record for record in lock["artifacts"]
        if record["path"].endswith("listing-plan.example.json")
    )
    example_path = _safe_workspace_path(workspace_root, example_record["path"])
    example = json.loads(example_path.read_text(encoding="utf-8"))
    return lock, example


def _profile_and_evidence_issues(
    plan: ListingPlan,
    lock: Dict[str, Any],
) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    profile_record = next(
        item for item in lock["artifacts"] if item["path"].endswith("profiles/ondine.md")
    )
    if plan.profile.model_dump(mode="json") != {
        "brand": "Ondine London",
        "profile_id": "ondine",
        "inventory_scope": "OUT_OF_SCOPE",
    }:
        issues.append(_issue("PROFILE_CONTRACT_MISMATCH", "$.profile", "Ondine profile contract required"))
    if (
        plan.evidence.market != "GB"
        or plan.evidence.locale != "en-GB"
        or plan.evidence.currency != "GBP"
    ):
        issues.append(_issue("MARKET_LOCALE_CURRENCY_INVALID", "$.evidence", "GB/en-GB/GBP required"))
    if (
        plan.evidence.ondine_profile_sha256 != profile_record["sha256"]
        or plan.fact_packet_projection.ondine_profile_sha256 != profile_record["sha256"]
    ):
        issues.append(_issue("PROFILE_HASH_MISMATCH", "$.evidence.ondine_profile_sha256", "current release-pinned Ondine profile required"))
    if (
        plan.fact_packet_projection.source_capture_sha256 != plan.evidence.source_capture_sha256
        or plan.fact_packet_projection.source_capture_determinism_sha256
        != plan.evidence.source_capture_determinism_sha256
    ):
        issues.append(_issue("FACT_PACKET_PIN_MISMATCH", "$.fact_packet_projection", "projection pins must match evidence"))
    for index, binding in enumerate(plan.fact_packet_projection.bindings):
        if binding.market != "GB" or binding.locale != "en-GB":
            issues.append(_issue("FACT_MARKET_LOCALE_INVALID", "$.fact_packet_projection.bindings[%s]" % index, "GB/en-GB required"))
        if binding.currency is not None and binding.currency != "GBP":
            issues.append(_issue("FACT_CURRENCY_INVALID", "$.fact_packet_projection.bindings[%s].currency" % index, "GBP required"))
    return issues


def _source_capture_evidence_issues(
    plan: ListingPlan,
    evidence: Any,
    test_mode: bool,
    legacy: bool = False,
) -> Tuple[Optional[SourceCapture], List[ListingPlanIssue]]:
    issues: List[ListingPlanIssue] = []
    if evidence is None:
        return None, [
            _issue(
                "SOURCE_CAPTURE_EVIDENCE_REQUIRED",
                "$.evidence.source_capture_sha256",
                "a valid Phase 1 replay result is required",
            )
        ]
    if isinstance(evidence, (ReplayResult, SourceCapture)):
        raw_evidence = evidence.model_dump(mode="json", exclude_none=False)
    elif isinstance(evidence, dict):
        raw_evidence = evidence
    else:
        return None, [_issue("SOURCE_CAPTURE_EVIDENCE_INVALID", "$.evidence", "unsupported source evidence input")]
    replay: Optional[ReplayResult] = None
    capture: Optional[SourceCapture] = None
    output_hash: Optional[str] = None
    try:
        if isinstance(evidence, ReplayResult) or "source_capture" in raw_evidence:
            replay = evidence if isinstance(evidence, ReplayResult) else ReplayResult.model_validate(raw_evidence)
            capture = replay.source_capture
            canonical_replay = replay.model_dump(mode="json", exclude_none=False)
            output_hash = _sha256_bytes(
                phase_1_canonical_json_bytes(canonical_replay) + b"\n"
            )
            if not replay.valid or replay.issues:
                issues.append(_issue("SOURCE_CAPTURE_EVIDENCE_INVALID", "$.source_capture", "Phase 1 replay must be valid with no issues"))
        elif test_mode:
            capture = evidence if isinstance(evidence, SourceCapture) else SourceCapture.model_validate(raw_evidence)
            output_hash = _sha256_bytes(
                phase_1_canonical_json_bytes(
                    capture.model_dump(mode="json", exclude_none=False)
                )
            )
        else:
            issues.append(_issue("SOURCE_CAPTURE_REPLAY_ENVELOPE_REQUIRED", "$.source_capture", "normal validation requires the Phase 1 replay envelope"))
            return None, issues
    except ValidationError as exc:
        return None, [_issue("SOURCE_CAPTURE_EVIDENCE_INVALID", "$.source_capture", str(exc))]
    assert capture is not None and output_hash is not None
    if not test_mode:
        # A caller-supplied envelope is evidence, not authority to self-declare valid.
        for source_issue in validate_source_capture(capture):
            issues.append(_issue("SOURCE_CAPTURE_EVIDENCE_INVALID", "$.source_capture",
                                 "%s: %s" % (source_issue.code, source_issue.message)))
    determinism_hash = _sha256_bytes(
        phase_1_canonical_json_bytes(
            capture.model_dump(mode="json", exclude_none=False)
        )
    )
    if replay is not None and replay.determinism_sha256 != determinism_hash:
        issues.append(_issue("SOURCE_CAPTURE_DETERMINISM_MISMATCH", "$.source_capture.determinism_sha256", determinism_hash))
    if output_hash != plan.evidence.source_capture_sha256:
        issues.append(_issue("SOURCE_CAPTURE_HASH_MISMATCH", "$.evidence.source_capture_sha256", output_hash))
    if determinism_hash != plan.evidence.source_capture_determinism_sha256:
        issues.append(_issue("SOURCE_CAPTURE_DETERMINISM_MISMATCH", "$.evidence.source_capture_determinism_sha256", determinism_hash))
    if (
        capture.market != plan.evidence.market
        or capture.locale != plan.evidence.locale
        or capture.currency != plan.evidence.currency
        or capture.captured_at != plan.evidence.captured_at
    ):
        issues.append(_issue("SOURCE_CAPTURE_CONTEXT_MISMATCH", "$.evidence", "capture market/locale/currency/time must match"))
    issues.extend(source_fact_issues(plan, capture, legacy=legacy))
    return capture, issues


def source_fact_issues(plan: ListingPlan, capture: SourceCapture,
                       legacy: bool = False) -> List[ListingPlanIssue]:
    """Use the same source comparisons at registration and listing validation."""
    issues: List[ListingPlanIssue] = []
    bindings = {item.fact_packet_fact_id: item for item in plan.fact_packet_projection.bindings}
    core_expected = {
        "fp.canonical_source_url": capture.canonical_url,
        "fp.current_customer_paid_price_gbp": (
            str(capture.current_price.quantize(Decimal("0.01")))
            if capture.current_price is not None else None
        ),
    }
    product_id = (capture.structured_product_evidence or {}).get("product_id")
    if product_id is not None:
        core_expected["fp.source_product_id"] = str(product_id)
    for fact_id, expected in core_expected.items():
        binding = bindings.get(fact_id)
        if binding is None or str(binding.value) != str(expected):
            issues.append(_issue("FACT_PACKET_SOURCE_MISMATCH", "$.fact_packet_projection.%s" % fact_id, "incoming SourceCapture fact mismatch"))
    capture_options = [
        (item.name.title() if legacy else item.name, item.position, list(item.values)) for item in capture.options
    ]
    packet_options = [
        (name, position, list(binding.value) if isinstance(binding.value, list) else [])
        for name, binding, position in _ordered_option_bindings(plan, legacy=legacy)
    ]
    if packet_options != capture_options:
        issues.append(_issue("FACT_PACKET_SOURCE_MISMATCH", "$.fact_packet_projection.bindings", "option facts must match SourceCapture"))
    source_combinations = [
        [value.value for value in variant.option_values]
        for variant in capture.variants
    ]
    combination_binding = bindings.get("fp.real_variant_combinations")
    if combination_binding is None or combination_binding.value != source_combinations:
        issues.append(_issue("FACT_PACKET_SOURCE_MISMATCH", "$.fact_packet_projection.fp.real_variant_combinations", "real combinations must match SourceCapture"))
    return issues


def _issue(code: str, path: str, message: str) -> ListingPlanIssue:
    return ListingPlanIssue(code=code, field_path=path, message=message, blocking=True)


def _walk(value: Any, path: str = "$") -> Iterable[Tuple[str, Optional[str], Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = "%s.%s" % (path, key)
            yield child_path, str(key), child
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = "%s[%s]" % (path, index)
            yield child_path, None, child
            yield from _walk(child, child_path)


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _flatten_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _flatten_strings(child)


def _canonical_key(value: str) -> str:
    separated = re.sub(r"[^0-9A-Za-z]+", "_", value.strip())
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", separated)
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return re.sub(r"_+", "_", separated).strip("_").lower()


def _forbidden_target_state_issues(document: Dict[str, Any]) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []

    def visit(value: Any, path: str, ancestors: Sequence[str]) -> None:
        if isinstance(value, dict):
            for raw_key, child in value.items():
                key = _canonical_key(str(raw_key))
                compact = key.replace("_", "")
                semantic_path = tuple(ancestors) + (compact,)
                joined = "".join(semantic_path)
                child_path = "%s.%s" % (path, raw_key)
                inventory_scope_metadata = child_path == "$.profile.inventory_scope"
                if "inventory" in joined and not inventory_scope_metadata:
                    issues.append(
                        _issue(
                            "TARGET_INVENTORY_FORBIDDEN",
                            child_path,
                            "inventory state is outside ListingPlan target scope",
                        )
                    )
                source_availability = compact in {"sourceavailable", "sourceavailability"}
                if not source_availability and (
                    "targetavailability" in joined
                    or (compact in {"availability", "available"} and "shopifytargetstate" in joined)
                ):
                    issues.append(
                        _issue(
                            "TARGET_AVAILABILITY_FORBIDDEN",
                            child_path,
                            "target availability is outside ListingPlan scope",
                        )
                    )
                visit(child, child_path, semantic_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, "%s[%s]" % (path, index), ancestors)

    visit(document, "$", ())
    return issues


def _reference_issues(plan_data: Dict[str, Any], fp_ids: set, df_ids: set) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    for path, key, value in _walk(plan_data):
        if path.startswith("$.fact_packet_projection.bindings"):
            continue
        if isinstance(value, str) and value.startswith(RAW_SOURCE_PREFIXES):
            issues.append(
                _issue(
                    "RAW_SOURCE_REFERENCE_BYPASS",
                    path,
                    "ListingPlan references must not bypass FactPacket: %s" % value,
                )
            )
        if key not in REFERENCE_KEYS:
            continue
        for reference in _flatten_strings(value):
            if reference.startswith(RAW_SOURCE_PREFIXES):
                issues.append(
                    _issue(
                        "RAW_SOURCE_REFERENCE_BYPASS",
                        path,
                        "ListingPlan references must not bypass FactPacket: %s" % reference,
                    )
                )
            elif reference.startswith("fp.") and reference not in fp_ids:
                issues.append(_issue("UNKNOWN_FACT_REFERENCE", path, reference))
            elif reference.startswith("df.") and reference not in df_ids:
                issues.append(_issue("UNKNOWN_DERIVED_FACT_REFERENCE", path, reference))
            elif not reference.startswith(ALLOWED_REFERENCE_PREFIXES) and reference not in ALLOWED_REFERENCE_LITERALS:
                issues.append(
                    _issue(
                        "REFERENCE_NAMESPACE_FORBIDDEN",
                        path,
                        "reference is outside approved namespaces: %s" % reference,
                    )
                )
    return issues


def _raw_source_bypass_issues(document: Dict[str, Any]) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    for path, _, value in _walk(document):
        if path.startswith("$.fact_packet_projection.bindings"):
            continue
        if isinstance(value, str) and value.startswith(RAW_SOURCE_PREFIXES):
            issues.append(
                _issue(
                    "RAW_SOURCE_REFERENCE_BYPASS",
                    path,
                    "ListingPlan references must not bypass FactPacket: %s" % value,
                )
            )
    return issues


def _raw_target_safety_issues(document: Dict[str, Any]) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    state = document.get("shopify_target_state")
    if not isinstance(state, dict):
        return [_issue("TARGET_STATE_INVALID", "$.shopify_target_state", "target state object is required")]
    if state.get("status") != "DRAFT" or state.get("target_kind") != "DATA_READY_DRAFT":
        issues.append(_issue("TARGET_STATE_NOT_DRAFT", "$.shopify_target_state.status", "DRAFT only"))
    if state.get("target_media") != []:
        issues.append(_issue("TARGET_MEDIA_NOT_EMPTY", "$.shopify_target_state.target_media", "target media must remain empty"))
    if state.get("media_status") != "PENDING_APPROVAL":
        issues.append(_issue("MEDIA_STATUS_INVALID", "$.shopify_target_state.media_status", "PENDING_APPROVAL required"))
    ownership = state.get("private_ownership")
    read_back = state.get("read_back_contract")
    if not isinstance(ownership, dict) or not isinstance(read_back, dict):
        issues.append(_issue("PRIVATE_OWNERSHIP_INVALID", "$.shopify_target_state", "private ownership and read-back are required"))
    return issues


def _derived_fact_issues(plan: ListingPlan) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    bindings = {
        binding.fact_packet_fact_id: binding
        for binding in plan.fact_packet_projection.bindings
    }
    derived_ids = {fact.derived_fact_id for fact in plan.derived_facts}
    for index, fact in enumerate(plan.derived_facts):
        path = "$.derived_facts[%s]" % index
        if fact.transform_id not in ALLOWED_TRANSFORM_IDS:
            issues.append(_issue("UNKNOWN_TRANSFORM", path + ".transform_id", fact.transform_id))
        references = fact.input_fact_refs or [fact.input_fact_ref]
        for reference in references:
            if reference is None:
                continue
            if reference.startswith(RAW_SOURCE_PREFIXES):
                issues.append(_issue("RAW_SOURCE_REFERENCE_BYPASS", path, reference))
            elif reference.startswith("fp."):
                binding = bindings.get(reference)
                if binding is None:
                    issues.append(_issue("UNKNOWN_FACT_REFERENCE", path, reference))
                elif fact.transform_id not in binding.allowed_transform_ids:
                    issues.append(
                        _issue(
                            "UNAUTHORIZED_TRANSFORM",
                            path + ".transform_id",
                            "%s is not authorized by %s" % (fact.transform_id, reference),
                        )
                    )
            elif reference.startswith("df.") and reference not in derived_ids:
                issues.append(_issue("UNKNOWN_DERIVED_FACT_REFERENCE", path, reference))
            elif not reference.startswith(("df.", "profile.", "policy_snapshot.", "store_contract.")):
                issues.append(_issue("REFERENCE_NAMESPACE_FORBIDDEN", path, reference))
    return issues


def _ordered_option_bindings(plan: ListingPlan, legacy: bool = False) -> List[Tuple[str, Any, int]]:
    result = []
    for fallback_position, binding in enumerate(plan.fact_packet_projection.bindings, start=1):
        prefix = "fp.options."
        if not binding.fact_packet_fact_id.startswith(prefix):
            continue
        raw_name = binding.fact_packet_fact_id[len(prefix):].replace("_", " ")
        name = raw_name.title() if legacy else (binding.source_option_name or raw_name.title())
        match = re.search(r"(?:^|\.)options\[(\d+)\]", binding.source_fact_or_path)
        position = (binding.source_option_position if not legacy else None) or (int(match.group(1)) + 1 if match else fallback_position)
        result.append((name, binding, position))
    return sorted(result, key=lambda item: item[2])


def _transform_application_issues(plan: ListingPlan) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    bindings = {
        binding.fact_packet_fact_id: binding
        for binding in plan.fact_packet_projection.bindings
    }

    def check(transform_id: Any, expected: str, references: Iterable[str], path: str) -> None:
        if transform_id != expected:
            issues.append(
                _issue(
                    "UNAUTHORIZED_TRANSFORM",
                    path,
                    "expected %s, got %s" % (expected, transform_id),
                )
            )
            return
        for reference in references:
            if not reference.startswith("fp."):
                continue
            binding = bindings.get(reference)
            if binding is None or expected not in binding.allowed_transform_ids:
                issues.append(
                    _issue(
                        "UNAUTHORIZED_TRANSFORM",
                        path,
                        "%s is not authorized by %s" % (expected, reference),
                    )
                )

    derived_by_id = {fact.derived_fact_id: fact for fact in plan.derived_facts}
    title = plan.composition.title
    title_fact = derived_by_id.get(title.derived_fact_ref)
    if (
        title_fact is None
        or title.authorship_rule_id != "ondine_original_title_v1"
        or title_fact.transform_id != title.authorship_rule_id
        or title_fact.value != title.value
    ):
        issues.append(
            _issue(
                "UNAUTHORIZED_TRANSFORM",
                "$.composition.title.authorship_rule_id",
                "title must resolve through df.* and ondine_original_title_v1",
            )
        )

    description_refs = [
        reference
        for _, key, value in _walk(plan.composition.description.slots)
        if key in {"fact_ref", "fact_refs"}
        for reference in _flatten_strings(value)
    ]
    check(
        plan.composition.description.authorship_rule_id,
        "ondine_original_five_slot_copy_v1",
        description_refs,
        "$.composition.description.authorship_rule_id",
    )

    size_module = plan.composition.buy_box.size_module
    check(
        size_module.get("transform_id"),
        "ondine_approved_source_size_label_v1" if plan.approved_size_mapping else "ondine_uk_numeric_size_identity_v1",
        ["fp.options.size"],
        "$.composition.buy_box.size_module.transform_id",
    )
    for index, section in enumerate(plan.composition.below_fold_sections):
        for item_index, item in enumerate(section.get("items") or []):
            transform_id = item.get("transform_id")
            if transform_id is None:
                continue
            references = list(
                _flatten_strings(item.get("fact_refs", item.get("fact_ref", [])))
            )
            check(
                transform_id,
                "ondine_uk_numeric_size_identity_v1",
                references,
                "$.composition.below_fold_sections[%s].items[%s].transform_id"
                % (index, item_index),
            )

    check(
        plan.shopify_target_state.seo.transform_id,
        "ondine_seo_copy_v1",
        plan.shopify_target_state.seo.input_fact_refs,
        "$.shopify_target_state.seo.transform_id",
    )
    tags_transform = plan.shopify_target_state.tags_transform
    check(
        tags_transform.get("transform_id"),
        "ondine_tags_v1",
        list(_flatten_strings(tags_transform.get("input_fact_refs") or [])),
        "$.shopify_target_state.tags_transform.transform_id",
    )
    identifier = plan.shopify_target_state.identifier_generation
    identifier_refs = [
        binding.fact_packet_fact_id
        for _, binding, _ in _ordered_option_bindings(plan)
    ] + ["fp.real_variant_combinations"]
    check(
        identifier.get("transform_id"),
        "ondine_sku_mpn_v3",
        identifier_refs,
        "$.shopify_target_state.identifier_generation.transform_id",
    )
    for index, variant in enumerate(plan.shopify_target_state.variants):
        check(
            variant.sku_mpn_transform_id,
            "ondine_sku_mpn_v3",
            identifier_refs,
            "$.shopify_target_state.variants[%s].sku_mpn_transform_id" % index,
        )
    return issues


def nearest_95_strictly_below(value: Decimal) -> Decimal:
    whole = int(value)
    candidate = Decimal(whole) + Decimal("0.95")
    if candidate >= value:
        candidate -= Decimal("1.00")
    return candidate.quantize(Decimal("0.01"))


def _price_issues(plan: ListingPlan) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    bindings = {b.fact_packet_fact_id: b for b in plan.fact_packet_projection.bindings}
    price_binding = bindings.get("fp.current_customer_paid_price_gbp")
    price_facts = [
        fact for fact in plan.derived_facts
        if fact.transform_id == "ondine_price_nearest_95_below_v1"
    ]
    if price_binding is None or len(price_facts) != 1:
        return [_issue("PRICE_INPUT_OR_DERIVATION_MISSING", "$.derived_facts", "one price derivation is required")]
    source_price = Decimal(str(price_binding.value))
    expected_price = nearest_95_strictly_below(source_price)
    derived = price_facts[0]
    if Decimal(str(derived.value)) != expected_price or Decimal(str(derived.value)) >= source_price:
        issues.append(
            _issue(
                "PRICE_STRICT_BELOW_VIOLATION",
                "$.derived_facts.%s" % derived.derived_fact_id,
                "expected %s strictly below %s" % (expected_price, source_price),
            )
        )
    price_contract = plan.transform_contracts.get("ondine_price_nearest_95_below_v1") or {}
    vectors = price_contract.get("test_vectors") or []
    required_inputs = ["59.00", "59.40", "59.95", "59.96"]
    if [str(vector.get("input")) for vector in vectors] != required_inputs:
        issues.append(_issue("PRICE_BOUNDARY_VECTORS_INVALID", "$.transform_contracts", "locked vectors are required"))
    for index, vector in enumerate(vectors):
        try:
            actual = Decimal(str(vector["output"]))
            expected = nearest_95_strictly_below(Decimal(str(vector["input"])))
        except (KeyError, ValueError):
            issues.append(_issue("PRICE_BOUNDARY_VECTOR_INVALID", "$.transform_contracts.test_vectors[%s]" % index, "invalid vector"))
            continue
        if actual != expected or actual >= Decimal(str(vector["input"])):
            issues.append(
                _issue(
                    "PRICE_BOUNDARY_VECTOR_INVALID",
                    "$.transform_contracts.test_vectors[%s]" % index,
                    "output must be the nearest .95 strictly below input",
                )
            )
    target_price = str(expected_price)
    if str(plan.composition.buy_box.price.get("amount")) != target_price:
        issues.append(_issue("TARGET_PRICE_MISMATCH", "$.composition.buy_box.price", target_price))
    for index, variant in enumerate(plan.shopify_target_state.variants):
        if variant.price != target_price:
            issues.append(_issue("TARGET_PRICE_MISMATCH", "$.shopify_target_state.variants[%s].price" % index, target_price))
    return issues


def _ascii_initial_code(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    tokens = re.findall(r"[A-Za-z0-9]+", ascii_value)
    return "".join(token[0].upper() for token in tokens)


def _approved_size_mapping(
    plan: ListingPlan,
    approval_path: Optional[Path],
    approval_sha256: Optional[str],
    test_mode: bool = False,
) -> Tuple[Dict[str, str], List[ListingPlanIssue]]:
    """A plan cannot grant its own exception: approval pins come from the caller."""
    declared = plan.approved_size_mapping
    if declared is None:
        return {}, []
    path = "$.approved_size_mapping"
    try:
        if approval_path is None or approval_sha256 is None:
            raise ValueError("an independently supplied approval record and hash are required")
        raw = approval_path.read_bytes()
        if _sha256_bytes(raw) != approval_sha256 or declared.approval_record_sha256 != approval_sha256:
            raise ValueError("approval record hash does not match the trusted pin")
        record = SizeMappingApprovalRecord.model_validate_json(raw)
        if record.provenance != "USER_MESSAGE" and not test_mode:
            raise ValueError("synthetic size approvals are forbidden in normal validation")
        expected = declared.model_dump(exclude={"approval_record_sha256"})
        actual = record.model_dump(include=set(expected))
        if actual != expected:
            raise ValueError("approval must match the exact product, capture and label mapping")
        bindings = {b.fact_packet_fact_id: b for b in plan.fact_packet_projection.bindings}
        source_url = bindings.get("fp.canonical_source_url")
        sizes = bindings.get("fp.options.size")
        if (source_url is None or declared.canonical_source_url != source_url.value
                or declared.source_capture_sha256 != plan.evidence.source_capture_sha256):
            raise ValueError("approval is bound to a different source product or capture")
        if sizes is None or not isinstance(sizes.value, list) or set(declared.labels) != set(sizes.value):
            raise ValueError("approval must cover exactly every original source size")
        codes = []
        for source_label, target_label in declared.labels.items():
            match = re.fullmatch(re.escape(source_label) + r" \(UK ([0-9]+)[–-]([0-9]+)\)", target_label)
            if match is None or int(match[1]) > int(match[2]):
                raise ValueError("approved labels must preserve the source label and one explicit UK range")
            code = _source_size_code(source_label)
            if not code:
                raise ValueError("original size label cannot produce a SKU code")
            codes.append(code)
        if len(set(codes)) != len(codes) or len(set(declared.labels.values())) != len(declared.labels):
            raise ValueError("approved size labels and original-label SKU codes must be unique")
        return dict(declared.labels), []
    except (OSError, ValueError, TypeError, ValidationError) as exc:
        return {}, [_issue("SIZE_MAPPING_APPROVAL_INVALID", path, str(exc))]


def _source_size_code(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]", "", ascii_value.upper())


def _explicit_uk_size_labels(plan: ListingPlan, legacy: bool = False) -> Dict[str, str]:
    """Normalize an explicit single UK number; never infer a letter/range conversion."""
    if legacy:
        return {}
    size = next((binding for name, binding, _ in _ordered_option_bindings(plan)
                 if name == "Size"), None)
    if size is None or not isinstance(size.value, list):
        return {}
    labels = {}
    for value in size.value:
        match = re.fullmatch(r"UK\s+([1-9][0-9]?)(?:\s*\((?:[2-9]?X{0,3}[SML])\))?", str(value), re.I)
        if match and int(match[1]) % 2 == 0:
            labels[str(value)] = str(int(match[1]))
    return labels


def _variant_issues(
    plan: ListingPlan,
    legacy: bool = False,
    approved_size_labels: Optional[Dict[str, str]] = None,
) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    bindings = {b.fact_packet_fact_id: b for b in plan.fact_packet_projection.bindings}
    option_bindings = _ordered_option_bindings(plan, legacy=legacy)
    size_labels = _explicit_uk_size_labels(plan, legacy)
    size_labels.update(approved_size_labels or {})
    if not option_bindings or not any(name == "Size" for name, _, _ in option_bindings):
        return [_issue("SIZE_DIMENSION_REQUIRED", "$.fact_packet_projection.bindings", "Ondine requires Size")]
    if len(option_bindings) > 3:
        issues.append(
            _issue(
                "OPTION_DIMENSION_LIMIT_EXCEEDED",
                "$.fact_packet_projection.bindings",
                "at most three captured source option dimensions are supported",
            )
        )
    positions = [position for _, _, position in option_bindings]
    if positions != list(range(1, len(positions) + 1)):
        issues.append(
            _issue(
                "OPTION_STRUCTURE_MISMATCH",
                "$.fact_packet_projection.bindings",
                "source option positions must be unique and contiguous",
            )
        )
    selection = plan.seasonal_colour_selection
    selected_colours = None
    if selection is not None:
        source_colour = next((binding for name, binding, _ in option_bindings if name == "Colour"), None)
        values = source_colour.value if source_colour is not None else None
        selected = selection.selected_colours
        if (legacy or not isinstance(values, list) or not selection.reason.strip()
                or len(selected) != len(set(selected))
                or selected != [value for value in values if value in selected]):
            issues.append(_issue("SEASONAL_COLOUR_SELECTION_INVALID", "$.seasonal_colour_selection",
                                 "select existing source colours once, in source order, with a seasonal reason"))
        else:
            selected_colours = selected
    expected_options = []
    option_values: Dict[str, List[str]] = {}
    for name, binding, position in option_bindings:
        if not legacy and (binding.source_option_name is None or binding.source_option_position is None):
            issues.append(_issue("SOURCE_OPTION_METADATA_REQUIRED", binding.fact_packet_fact_id, "current options require exact source names and positions"))
        if not isinstance(binding.value, list) or not binding.value:
            issues.append(_issue("OPTION_STRUCTURE_MISMATCH", binding.fact_packet_fact_id, "option values are required"))
            values = []
        else:
            values = [str(value) for value in binding.value]
        option_values[name] = values
        target_values = [size_labels.get(value, value) for value in values] if name == "Size" else values
        if name == "Size" and len(target_values) != len(set(target_values)):
            issues.append(_issue("SIZE_MAPPING_COLLISION", "$.shopify_target_state.options", "distinct source sizes cannot collapse into one target size"))
        if name == "Colour" and selected_colours is not None:
            target_values = selected_colours
        expected_options.append((name, position, target_values, binding.fact_packet_fact_id))
    colour_binding = bindings.get("fp.colour")
    colour = str(colour_binding.value) if colour_binding is not None else ""
    if not legacy:
        colour_options = [option for option in expected_options if option[0] == "Colour"]
        if not colour_options:
            if not colour or colour_binding is None or not colour_binding.publishable_as_claim:
                issues.append(_issue("COLOUR_FACT_REQUIRED", "$.fact_packet_projection", "singleton Colour requires a publishable fp.colour"))
            colour_options = [("Colour", 1, [colour], "fp.colour")]
        expected_options = colour_options + [option for option in expected_options if option[0] != "Colour"]
        expected_options = [(name, index, values, fact_ref) for index, (name, _, values, fact_ref) in enumerate(expected_options, 1)]
        if len(expected_options) > 3:
            issues.append(_issue("OPTION_DIMENSION_LIMIT_EXCEEDED", "$.shopify_target_state.options", "Colour insertion must not exceed three dimensions"))
    actual_options = [
        (option.name, option.position, option.values, option.fact_ref)
        for option in plan.shopify_target_state.options
    ]
    non_colour_names = [name for name, _, _ in option_bindings if name.lower() != "colour"]
    if (
        actual_options != expected_options
        or plan.shopify_target_state.option_render_order != non_colour_names
    ):
        issues.append(
            _issue(
                "OPTION_STRUCTURE_MISMATCH",
                "$.shopify_target_state.options",
                "target options must preserve source dimensions, verified UK sizes and recorded seasonal colours, with Colour first",
            )
        )
    for value in option_values.get("Size", []):
        if value in size_labels:
            continue
        try:
            numeric_size = int(value)
        except ValueError:
            issues.append(_issue("SIZE_MAPPING_REQUIRED", "$.shopify_target_state.options", value))
            continue
        if legacy and numeric_size > 18:
            issues.append(
                _issue(
                    "SIZE_OUTSIDE_CURRENT_CHART",
                    "$.shopify_target_state.options",
                    "UK size %s exceeds the current chart maximum 18" % value,
                )
            )
    combination_binding = bindings.get("fp.real_variant_combinations")
    if combination_binding is None or not isinstance(combination_binding.value, list):
        return issues + [
            _issue(
                "REAL_VARIANT_COMBINATIONS_REQUIRED",
                "$.fact_packet_projection.bindings",
                "fp.real_variant_combinations is required",
            )
        ]
    combinations = [list(value) if isinstance(value, list) else [] for value in combination_binding.value]
    if len({tuple(value) for value in combinations}) != len(combinations):
        issues.append(_issue("DUPLICATE_REAL_COMBINATION", "$.fact_packet_projection.bindings", "real combinations must be unique"))
    for row_index, combination in enumerate(combinations):
        if len(combination) != len(option_bindings):
            issues.append(_issue("VARIANT_COMBINATION_SHAPE_INVALID", "$.fact_packet_projection.bindings[%s]" % row_index, "combination arity must match source dimensions"))
            continue
        for (name, _, _), value in zip(option_bindings, combination):
            if str(value) not in option_values.get(name, []):
                issues.append(_issue("VARIANT_COMBINATION_VALUE_INVALID", "$.fact_packet_projection.bindings[%s]" % row_index, "%s=%s" % (name, value)))
    expected_variant_values = []
    for combination in combinations:
        values = {name: str(value) for (name, _, _), value in zip(option_bindings, combination)}
        if selected_colours is not None and values.get("Colour") not in selected_colours:
            continue
        if "Size" in values:
            values["Size"] = size_labels.get(values["Size"], values["Size"])
        if not legacy and "Colour" not in values:
            values["Colour"] = colour
        expected_variant_values.append(values)
    actual_variant_values = [variant.option_values for variant in plan.shopify_target_state.variants]
    if actual_variant_values != expected_variant_values:
        issues.append(
            _issue(
                "INVENTED_OR_MISSING_VARIANT_COMBINATION",
                "$.shopify_target_state.variants",
                "target variants must equal every incoming real combination for retained colours, in source order",
            )
        )
    title = plan.shopify_target_state.title
    style_code = _ascii_initial_code(title)
    identifier = plan.shopify_target_state.identifier_generation
    if identifier.get("style_code") != style_code:
        issues.append(_issue("STYLE_CODE_NOT_DETERMINISTIC", "$.shopify_target_state.identifier_generation", style_code))
    colour_mapping = plan.transform_contracts.get("ondine_colour_code_v1", {}).get("profile_mapping", {})
    colour_codes = dict(identifier.get("colour_codes") or {})
    if identifier.get("colour_code") is not None:
        colour_codes.setdefault(colour, identifier.get("colour_code"))
    option_codes = identifier.get("additional_option_codes") or {}
    additional_names = [
        name for name, _, _ in option_bindings
        if name not in {"Size", "Colour"}
    ]
    derived = {fact.derived_fact_id: fact for fact in plan.derived_facts}
    skus = []
    mpns = []
    for index, variant in enumerate(plan.shopify_target_state.variants):
        if variant.combination_fact_ref != "fp.real_variant_combinations":
            issues.append(_issue("VARIANT_COMBINATION_BINDING_INVALID", "$.shopify_target_state.variants[%s].combination_fact_ref" % index, "each row must bind the captured real combination matrix"))
        try:
            original_sizes = {target: source for source, target in (approved_size_labels or {}).items()}
            size_code = (_source_size_code(original_sizes[variant.option_values["Size"]])
                         if variant.option_values["Size"] in original_sizes
                         else "%03d" % int(variant.option_values["Size"]))
            variant_colour = variant.option_values.get("Colour", colour)
            colour_code = colour_codes.get(variant_colour) or colour_mapping[variant_colour]
            suffix = [option_codes[variant.option_values[name]] for name in additional_names]
            expected_code = "-".join(["OND", style_code, colour_code, size_code] + suffix)
        except (KeyError, TypeError, ValueError):
            expected_code = "<invalid>"
        if variant.sku != expected_code or variant.mpn != expected_code:
            issues.append(_issue("SKU_MPN_NOT_DETERMINISTIC", "$.shopify_target_state.variants[%s]" % index, expected_code))
        skus.append(variant.sku)
        mpns.append(variant.mpn)
        style_fact = derived.get(variant.style_code_ref)
        colour_fact = derived.get(variant.colour_code_ref)
        if style_fact is None or style_fact.value != style_code:
            issues.append(_issue("STYLE_CODE_NOT_DETERMINISTIC", "$.shopify_target_state.variants[%s].style_code_ref" % index, style_code))
        if colour_fact is None or colour_fact.value != colour_codes.get(variant.option_values.get("Colour", colour), colour_mapping.get(variant.option_values.get("Colour", colour))):
            issues.append(_issue("COLOUR_CODE_NOT_MAPPED", "$.shopify_target_state.variants[%s].colour_code_ref" % index, "approved colour mapping required"))
        weight_binding = bindings.get(variant.weight_fact_ref or "")
        if variant.weight_fact_ref is not None and (
            weight_binding is None
            or "ondine_weight_identity_v1" not in weight_binding.allowed_transform_ids
            or variant.weight_grams != weight_binding.value
        ):
            issues.append(
                _issue(
                    "VARIANT_WEIGHT_MISMATCH",
                    "$.shopify_target_state.variants[%s].weight_grams" % index,
                    "variant weight must preserve its authorized fp.* value",
                )
            )
        if variant.weight_fact_ref is None and variant.weight_grams is not None:
            issues.append(_issue("VARIANT_WEIGHT_MISMATCH", "$.shopify_target_state.variants[%s].weight_grams" % index, "weight requires an eligible fp.* binding"))
    if len(skus) != len(set(skus)):
        issues.append(_issue("DUPLICATE_SKU", "$.shopify_target_state.variants", "SKUs must be unique"))
    if len(mpns) != len(set(mpns)):
        issues.append(_issue("DUPLICATE_MPN", "$.shopify_target_state.variants", "MPNs must be unique"))
    return issues


def _structure_issues(
    plan: ListingPlan,
    legacy: bool = False,
    approved_size_labels: Optional[Dict[str, str]] = None,
) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    option_bindings = _ordered_option_bindings(plan, legacy=legacy)
    non_colour = [item for item in option_bindings if item[0].lower() != "colour"]
    if not non_colour or non_colour[0][0] != "Size":
        issues.append(
            _issue(
                "SIZE_SELECTOR_ORDER_INVALID",
                "$.fact_packet_projection.bindings",
                "Size must be the first non-colour selector",
            )
        )
    buy_box = plan.composition.buy_box
    size_values = list(non_colour[0][1].value) if non_colour and isinstance(non_colour[0][1].value, list) else []
    size_labels = _explicit_uk_size_labels(plan, legacy)
    size_labels.update(approved_size_labels or {})
    size_values = [size_labels.get(value, value) for value in size_values]
    if (
        buy_box.size_module.get("option_name") != "Size"
        or buy_box.size_module.get("values") != size_values
        or buy_box.size_module.get("selector_order") != 1
    ):
        issues.append(_issue("SIZE_MODULE_INVALID", "$.composition.buy_box.size_module", "Size module must bind the incoming Size option"))
    expected_selector_ids: List[str] = []
    additional = non_colour[1:]
    generic_selectors = buy_box.selectors or []
    if buy_box.length_selector is not None and generic_selectors:
        issues.append(_issue("SELECTOR_REPRESENTATION_INVALID", "$.composition.buy_box", "use legacy Length or generic selectors, not both"))
    if buy_box.length_selector is not None:
        if len(additional) != 1 or additional[0][0] != "Length":
            issues.append(_issue("SELECTOR_REPRESENTATION_INVALID", "$.composition.buy_box.length_selector", "legacy selector is valid only for one Length dimension"))
        else:
            name, binding, _ = additional[0]
            selector = buy_box.length_selector
            if (
                selector.get("option_name") != name
                or selector.get("values") != list(binding.value)
                or selector.get("fact_ref") != binding.fact_packet_fact_id
                or selector.get("selector_order") != 2
            ):
                issues.append(_issue("SELECTOR_REPRESENTATION_INVALID", "$.composition.buy_box.length_selector", "Length selector must preserve its binding"))
            expected_selector_ids.append("length_selector")
    elif additional:
        if len(generic_selectors) != len(additional):
            issues.append(_issue("SELECTOR_REPRESENTATION_INVALID", "$.composition.buy_box.selectors", "every additional source option requires one selector"))
        for index, ((name, binding, _), selector) in enumerate(zip(additional, generic_selectors), start=2):
            if (
                selector.option_name != name
                or selector.values != list(binding.value)
                or selector.fact_ref != binding.fact_packet_fact_id
                or selector.selector_order != index
            ):
                issues.append(_issue("SELECTOR_REPRESENTATION_INVALID", "$.composition.buy_box.selectors[%s]" % (index - 2), "selector must preserve the incoming option"))
            expected_selector_ids.append(selector.pdp_order_id)
    elif generic_selectors:
        issues.append(_issue("SELECTOR_REPRESENTATION_INVALID", "$.composition.buy_box.selectors", "unexpected selector"))
    expected_buy_box_order = ["title", "colour", "size_module"] + expected_selector_ids + ["price", "add_to_bag"]
    below_fold_order = EXPECTED_BELOW_FOLD_ORDER if legacy else ["description", "fit_details", "fabric_care", "delivery", "returns_and_refunds"]
    if plan.composition.pdp_order.buy_box != expected_buy_box_order or plan.composition.pdp_order.below_fold != below_fold_order:
        issues.append(_issue("PDP_ORDER_INVALID", "$.composition.pdp_order", "fixed buy-box and below-fold order required"))
    slots = plan.composition.description.slots
    if [slot.get("id") for slot in slots] != EXPECTED_SLOT_IDS or [slot.get("slot") for slot in slots] != [1, 2, 3, 4, 5]:
        issues.append(_issue("DESCRIPTION_SLOT_ORDER_INVALID", "$.composition.description.slots", "exact five-slot order required"))
    if legacy:
        benefits = slots[2].get("items") if len(slots) >= 3 else []
        if not isinstance(benefits, list) or len(benefits) != 3:
            issues.append(_issue("DESCRIPTION_BENEFITS_INVALID", "$.composition.description.slots[2]", "exactly three benefits required"))
    else:
        for index, slot in enumerate(slots):
            text = slot.get("text")
            if (not isinstance(text, str) or not text.strip() or "items" in slot
                    or re.search(r"<[^>]*>|(?:^|\n)\s*(?:[-*•]|\d+\.)\s|[✓✔☑]|https?://", text)):
                issues.append(_issue("DESCRIPTION_PROSE_REQUIRED", "$.composition.description.slots[%s]" % index, "each of the five slots requires plain prose without lists, links or markup"))
    section_ids = [section.get("id") for section in plan.composition.below_fold_sections]
    if section_ids != (EXPECTED_BELOW_FOLD_ORDER[1:] if legacy else []):
        issues.append(_issue("BELOW_FOLD_SECTION_ORDER_INVALID", "$.composition.below_fold_sections", "fixed section order required"))
    if plan.composition.title.character_count != len(plan.composition.title.value) or plan.composition.title.value != plan.shopify_target_state.title:
        issues.append(_issue("TITLE_BINDING_INVALID", "$.composition.title", "title value/count must match target title"))
    if not legacy:
        issues.extend(_rich_text_issues(plan))
    return issues


def _rich_text_issues(plan: ListingPlan) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    fields = plan.shopify_target_state.rich_text_metafields
    path = "$.shopify_target_state.rich_text_metafields"
    if set(fields) != {"fit_details", "fabric_care"}:
        return [_issue("RICH_TEXT_METAFIELDS_REQUIRED", path, "Fit and fabric rich-text fields are required; unknown content may be an empty root")]
    bindings = {b.fact_packet_fact_id: b for b in plan.fact_packet_projection.bindings}

    def valid_node(node: Any, allowed: set) -> bool:
        if not isinstance(node, dict) or node.get("type") not in allowed:
            return False
        kind = node["type"]
        if kind == "text":
            return (set(node) <= {"type", "value", "bold", "italic"}
                    and isinstance(node.get("value"), str) and bool(node["value"].strip())
                    and all(isinstance(node[key], bool) for key in {"bold", "italic"} & set(node)))
        children = node.get("children")
        keys = {"type", "children", "listType"} if kind == "list" else {"type", "children"}
        if set(node) != keys or not isinstance(children, list) or (kind != "root" and not children):
            return False
        if kind == "list" and node.get("listType") != "unordered":
            return False
        next_types = {"paragraph", "list"} if kind == "root" else {"list-item"} if kind == "list" else {"text"}
        return all(valid_node(child, next_types) for child in children)

    for name, value in fields.items():
        if not valid_node(value, {"root"}):
            issues.append(_issue("RICH_TEXT_METAFIELD_INVALID", path + "." + name, "only root, paragraph, unordered list, list-item and text nodes are supported"))
        refs = plan.shopify_target_state.metafield_fact_refs.get(name, [])
        if value.get("children") and not refs:
            issues.append(_issue("RICH_TEXT_FACT_BINDING_REQUIRED", path + "." + name, "customer facts require eligible source bindings"))
        for ref in refs:
            binding = bindings.get(ref)
            if binding is None or not binding.publishable_as_claim or "ondine_original_five_slot_copy_v1" not in binding.allowed_transform_ids:
                issues.append(_issue("UNAUTHORIZED_TRANSFORM", path + "." + name, "rich-text copy requires an authorized publishable fact: " + ref))
        if plan.approved_target_model_record is None:
            for _, key, text in _walk(value):
                if key == "value" and isinstance(text, str) and re.search(r"\bmodel\b", text, re.I):
                    issues.append(_issue("MODEL_TEXT_REQUIRES_APPROVED_TARGET_RECORD", path + "." + name, "model text must be omitted without an approved target record"))
    return issues


def _seo_organisation_issues(plan: ListingPlan, legacy: bool = False) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    state = plan.shopify_target_state
    seo = state.seo
    if len(state.title) > 70:
        issues.append(_issue("TITLE_LENGTH_INVALID", "$.shopify_target_state.title", "target title must be at most 70 characters"))
    handle_words = state.handle.split("-")
    if len(handle_words) not in {5, 6} or seo.handle != state.handle:
        issues.append(_issue("HANDLE_INVALID", "$.shopify_target_state.handle", "own 5-6 word handle required"))
    if seo.page_title_character_count != len(seo.page_title) or not 50 <= len(seo.page_title) <= 60:
        issues.append(_issue("SEO_PAGE_TITLE_INVALID", "$.shopify_target_state.seo.page_title", "50-60 characters required"))
    if seo.meta_description_character_count != len(seo.meta_description) or not 150 <= len(seo.meta_description) <= 160:
        issues.append(_issue("SEO_META_DESCRIPTION_INVALID", "$.shopify_target_state.seo.meta_description", "150-160 characters required"))
    if not 10 <= len(state.tags) <= 15 or any(tag != tag.lower() for tag in state.tags):
        issues.append(_issue("TAGS_INVALID", "$.shopify_target_state.tags", "10-15 lowercase descriptive tags required"))
    if not state.collections or any(not collection.strip() for collection in state.collections):
        issues.append(_issue("COLLECTION_REQUIRED", "$.shopify_target_state.collections", "a real collection is required"))
    if set(state.metafields) != REQUIRED_METAFIELDS or any(
        not value.strip() for name, value in state.metafields.items()
        if legacy or name in {"size", "age_group"}
    ):
        issues.append(_issue("METAFIELDS_INCOMPLETE", "$.shopify_target_state.metafields", "all five metafields are required"))
    if not legacy:
        for name in {"fabric", "occasion", "neckline"}:
            if not state.metafields.get(name, "").strip() and state.metafield_fact_refs.get(name):
                issues.append(_issue("UNKNOWN_METAFIELD_BINDING_INVALID", "$.shopify_target_state.metafield_fact_refs." + name, "unknown blank fields must not claim source references"))
    if state.vendor != "Ondine London" or state.gmc.brand != "Ondine London" or state.gmc.vendor != "Ondine London":
        issues.append(_issue("BRAND_VENDOR_INVALID", "$.shopify_target_state", "Ondine London brand/vendor required"))
    if not state.gmc.google_product_category.strip():
        issues.append(_issue("CATEGORY_UNBOUND", "$.shopify_target_state.gmc.google_product_category", "category binding required"))
    return issues


def _state_media_model_issues(plan: ListingPlan, legacy: bool = False) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    state = plan.shopify_target_state
    if state.status != "DRAFT" or state.target_kind != "DATA_READY_DRAFT":
        issues.append(_issue("TARGET_STATE_NOT_DRAFT", "$.shopify_target_state.status", "DRAFT only"))
    if state.target_media or state.read_back_contract.target_media:
        issues.append(_issue("TARGET_MEDIA_NOT_EMPTY", "$.shopify_target_state.target_media", "target media must remain empty"))
    if state.media_status != "PENDING_APPROVAL" or state.read_back_contract.media_status != "PENDING_APPROVAL":
        issues.append(_issue("MEDIA_STATUS_INVALID", "$.shopify_target_state.media_status", "PENDING_APPROVAL required"))
    media = plan.media_plan
    expected_ids = ["01", "02", "03", "04", "05", "06"] if legacy else ["01", "01b", "02", "03", "04", "05", "06"]
    expected_roles = EXPECTED_MEDIA_ROLES if legacy else ["FRONT_GMC", "SECOND_MODEL_FRONT", *EXPECTED_MEDIA_ROLES[1:]]
    if [slot.slot for slot in media.slots] != expected_ids or [slot.role for slot in media.slots] != expected_roles:
        issues.append(_issue("MEDIA_PLAN_INVALID", "$.MediaPlan.slots", "exact ordered gallery required: " + ", ".join(expected_ids)))
    if not legacy and media.generation_gate != "LEAD_INTERNAL_QA_THEN_SECOND_MODEL_GALLERY_UPLOAD_REVIEW":
        issues.append(_issue("MEDIA_GENERATION_GATE_INVALID", "$.MediaPlan.generation_gate", "lead internal QA and subsequent review gates required"))
    if len({slot.filename for slot in media.slots}) != len(media.slots):
        issues.append(_issue("MEDIA_PLAN_FILENAME_DUPLICATE", "$.MediaPlan.slots", "filenames must be unique"))
    binding_map = {b.fact_packet_fact_id: b for b in plan.fact_packet_projection.bindings}
    for index, slot in enumerate(media.slots):
        for reference in slot.garment_fact_refs:
            binding = binding_map.get(reference)
            if binding is None or "ondine_media_plan_v1" not in binding.allowed_transform_ids:
                issues.append(_issue("UNAUTHORIZED_TRANSFORM", "$.MediaPlan.slots[%s].garment_fact_refs" % index, reference))
        if not any("zero" in criterion.lower() and "text" in criterion.lower() for criterion in slot.acceptance):
            issues.append(_issue("MEDIA_TEXT_FREE_GATE_MISSING", "$.MediaPlan.slots[%s].acceptance" % index, "zero-text acceptance required"))
    model_line = plan.composition.buy_box.size_module.get("live_model_line") or {}
    record = plan.approved_target_model_record
    if record is None:
        if model_line.get("render") is not False or model_line.get("text") is not None or model_line.get("target_model_record_ref") is not None:
            issues.append(_issue("MODEL_TEXT_REQUIRES_APPROVED_TARGET_RECORD", "$.composition.buy_box.size_module.live_model_line", "model text must be omitted"))
    else:
        expected_text = "Model is %s and wears UK %s" % (record.height, record.uk_worn_size)
        if model_line.get("render") is not True or model_line.get("text") != expected_text or model_line.get("target_model_record_ref") != record.record_id:
            issues.append(_issue("APPROVED_TARGET_MODEL_BINDING_INVALID", "$.composition.buy_box.size_module.live_model_line", expected_text))
    return issues


def _ownership_issues(plan: ListingPlan) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    bindings = {item.fact_packet_fact_id: item for item in plan.fact_packet_projection.bindings}
    url_binding = bindings.get("fp.canonical_source_url")
    if url_binding is None:
        return [_issue("PRIVATE_OWNERSHIP_INVALID", "$.fact_packet_projection", "canonical source URL fact is required")]
    source_url = str(url_binding.value)
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    product_binding = bindings.get("fp.source_product_id")
    source_identifier = str(product_binding.value).strip() if product_binding is not None else ""
    if not source_identifier:
        source_identifier = parsed.path.rstrip("/").split("/")[-1].lower()
    canonical_identity = "%s|%s" % (host, source_identifier)
    canonical_hash = _sha256_bytes(canonical_identity.encode("utf-8"))
    source_tag = "source:%s-%s" % (host, source_identifier)
    derived = {item.derived_fact_id: item for item in plan.derived_facts}
    identity_fact = derived.get("df.canonical_source_identity")
    tag_fact = derived.get("df.source_tag")
    ownership = plan.shopify_target_state.private_ownership
    if (
        not host
        or not source_identifier
        or identity_fact is None
        or identity_fact.value != canonical_identity
        or identity_fact.sha256 != canonical_hash
        or identity_fact.transform_id != "ondine_canonical_source_identity_v1"
        or tag_fact is None
        or tag_fact.value != source_tag
        or tag_fact.transform_id != "ondine_source_tag_v1"
        or ownership.canonical_source_identity_sha256 != canonical_hash
        or len(ownership.internal_tags) != 1
        or ownership.internal_tags[0].value != source_tag
    ):
        issues.append(_issue("PRIVATE_OWNERSHIP_INVALID", "$.shopify_target_state.private_ownership", "ownership must derive from the incoming canonical URL and product ID"))
    expected_read_back = {
        "source_key": {"expected_ref": "run_state.source_key_sha256", "match": "EXACT"},
        "source_tag": {"expected_ref": "df.source_tag", "match": "EXACT"},
        "managed_by": {"expected_value": "product-listing-v2", "match": "EXACT"},
        "canonical_source_url": {"expected_ref": "fp.canonical_source_url", "match": "EXACT_PRIVATE"},
    }
    if plan.shopify_target_state.read_back_contract.private_ownership != expected_read_back:
        issues.append(_issue("PRIVATE_OWNERSHIP_INVALID", "$.shopify_target_state.read_back_contract", "exact private read-back markers required"))
    return issues


def _public_customer_values(plan: ListingPlan) -> Dict[str, Any]:
    state = plan.shopify_target_state.model_dump(mode="json")
    return {
        "composition": plan.composition.model_dump(mode="json"),
        "title": state["title"],
        "handle": state["handle"],
        "collections": state["collections"],
        "tags": state["tags"],
        "metafields": state["metafields"],
        "rich_text_metafields": state["rich_text_metafields"],
        "seo": state["seo"],
        "gmc": state["gmc"],
        "MediaPlan": plan.media_plan.model_dump(mode="json"),
        "store_policy_snapshot": (
            {
                "delivery": {
                    "heading": plan.store_policy_snapshot.delivery.heading,
                    "content": plan.store_policy_snapshot.delivery.content,
                },
                "returns_and_refunds": {
                    "heading": plan.store_policy_snapshot.returns_and_refunds.heading,
                    "content": plan.store_policy_snapshot.returns_and_refunds.content,
                },
            }
            if plan.store_policy_snapshot else None
        ),
    }


def _customer_leakage_issues(plan: ListingPlan) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    bindings = {b.fact_packet_fact_id: b for b in plan.fact_packet_projection.bindings}
    url_binding = bindings.get("fp.canonical_source_url")
    if url_binding is None:
        return [_issue("CUSTOMER_SOURCE_LEAKAGE", "$.fact_packet_projection", "canonical source URL fact is required")]
    source_url = str(url_binding.value)
    product_binding = bindings.get("fp.source_product_id")
    source_product_id = str(product_binding.value) if product_binding is not None else ""
    parsed = urlparse(source_url)
    host_compact = re.sub(r"[^a-z0-9]", "", parsed.hostname or "").removeprefix("www")
    slug = parsed.path.rstrip("/").split("/")[-1].lower()
    slug_tokens = {
        token for token in re.split(r"[^a-z0-9]+", slug)
        if len(token) >= 5
        and token not in {
            "clothing",
            "dress",
            "garment",
            "midi",
            "product",
            "products",
            "reference",
        }
        and not token.isdigit()
    }
    for path, _, value in _walk(_public_customer_values(plan)):
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        compact = re.sub(r"[^a-z0-9]", "", lowered)
        leaked = (
            "http://" in lowered
            or "https://" in lowered
            or "www." in lowered
            or "source:" in lowered
            or (
                source_product_id
                and re.search(
                    r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(source_product_id.lower()),
                    lowered,
                )
            )
            or (host_compact and host_compact in compact)
            or any(token in lowered for token in slug_tokens)
        )
        if leaked:
            issues.append(_issue("CUSTOMER_SOURCE_LEAKAGE", path, "source identity is private-only"))
    return issues


def _policy_issues(plan: ListingPlan, test_mode: bool, legacy: bool = False) -> List[ListingPlanIssue]:
    issues: List[ListingPlanIssue] = []
    snapshot = plan.store_policy_snapshot
    if snapshot is None and not legacy and not plan.composition.below_fold_sections:
        return []
    if snapshot is None:
        return [
            _issue(
                "STORE_POLICY_SNAPSHOT_REQUIRED_AT_COMPOSE",
                "$.store_policy_snapshot",
                "Delivery and Returns require a current StorePolicySnapshot",
            )
        ]
    if snapshot.status != "CURRENT_AT_COMPOSE":
        issues.append(_issue("STORE_POLICY_SNAPSHOT_INVALID", "$.store_policy_snapshot", "current policy snapshot required"))
    if snapshot.test_only != (snapshot.provenance == "SYNTHETIC_TEST_ONLY"):
        issues.append(_issue("STORE_POLICY_SNAPSHOT_INVALID", "$.store_policy_snapshot.provenance", "test-only marker mismatch"))
    if snapshot.provenance == "SYNTHETIC_TEST_ONLY" and not test_mode:
        issues.append(_issue("SYNTHETIC_POLICY_FORBIDDEN", "$.store_policy_snapshot.provenance", "normal validation never accepts synthetic policy"))
    expected_blocks = (
        ("delivery", snapshot.delivery, "Delivery", "ondine.delivery.current"),
        ("returns_and_refunds", snapshot.returns_and_refunds, "Returns and Refunds", "ondine.returns_and_refunds.current"),
    )
    for block_id, block, heading, binding in expected_blocks:
        expected_url = POLICY_URLS[block_id]
        content_hash = _sha256_bytes(block.content.encode("utf-8"))
        if (
            block.requested_url != expected_url
            or block.final_url != expected_url
            or block.heading != heading
            or block.policy_binding != binding
            or not block.content.strip()
            or block.content_sha256 != content_hash
            or block.captured_at > snapshot.verified_at
        ):
            issues.append(_issue("STORE_POLICY_SNAPSHOT_INVALID", "$.store_policy_snapshot", "exact policy heading/binding/content required"))
    snapshot_payload = snapshot.model_dump(mode="json")
    snapshot_payload.pop("canonical_sha256")
    if snapshot.canonical_sha256 != _sha256_bytes(canonical_json_bytes(snapshot_payload)):
        issues.append(_issue("STORE_POLICY_SNAPSHOT_INVALID", "$.store_policy_snapshot.canonical_sha256", "canonical policy snapshot hash mismatch"))
    return issues


def _blocking_flag_issues(plan: ListingPlan) -> List[ListingPlanIssue]:
    issues = []
    for index, flag in enumerate(plan.flags):
        if flag.affects_target_readiness and flag.code != "STORE_POLICY_SNAPSHOT_REQUIRED_AT_COMPOSE":
            issues.append(_issue(flag.code, "$.flags[%s]" % index, flag.reason or "blocking plan flag"))
        if flag.code == "STORE_POLICY_SNAPSHOT_REQUIRED_AT_COMPOSE" and plan.store_policy_snapshot is not None:
            issues.append(_issue("STALE_POLICY_BLOCKER_FLAG", "$.flags[%s]" % index, "remove blocker after binding snapshot"))
    return issues


def _copy_guard_issues(
    plan: ListingPlan,
    document: Dict[str, Any],
    source_capture: Optional[SourceCapture],
    source_artifact_root: Optional[Path],
) -> List[ListingPlanIssue]:
    if source_capture is None:
        return []
    declared = plan.originality.copy_guard_result.model_dump(mode="json")
    if declared["source_capture_sha256"] != plan.evidence.source_capture_sha256:
        return [_issue("COPY_GUARD_SOURCE_PIN_MISMATCH", "$.originality.copy_guard_result.source_capture_sha256", "copy guard must pin plan source evidence")]
    try:
        recomputed = build_copy_guard_result(
            document,
            source_capture,
            plan.evidence.source_capture_sha256,
            source_artifact_root,
            declared["exemptions"],
        )
    except (CopyGuardEvidenceError, OSError, UnicodeError, ValueError, KeyError) as exc:
        return [_issue("COPY_GUARD_EVIDENCE_INVALID", "$.originality.copy_guard_result", str(exc))]
    issues: List[ListingPlanIssue] = []
    if recomputed != declared:
        issues.append(
            _issue(
                "COPY_GUARD_RECOMPUTATION_MISMATCH",
                "$.originality.copy_guard_result",
                "declared copy guard does not equal deterministic recomputation",
            )
        )
    if recomputed["result"] != "PASS":
        issues.append(
            _issue(
                "COPY_GUARD_FAILED",
                "$.originality.copy_guard_result.result",
                "originality, LCS and customer-voice gates must all pass",
            )
        )
    return issues


def _dedupe_issues(issues: Iterable[ListingPlanIssue]) -> List[ListingPlanIssue]:
    seen = set()
    result = []
    for issue in issues:
        key = (issue.code, issue.field_path, issue.message)
        if key not in seen:
            seen.add(key)
            result.append(issue)
    return result


def validate_listing_plan_document(
    document: Dict[str, Any],
    lock_path: Path = DEFAULT_PHASE_2_LOCK,
    source_capture_evidence: Any = None,
    source_artifact_root: Optional[Path] = None,
    test_mode: bool = False,
    test_projection_registry: Optional[Dict[str, Dict[str, Any]]] = None,
    test_projection_registry_root: Optional[Path] = None,
    product_registry_path: Optional[Path] = None,
    product_registry_sha256: Optional[str] = None,
    size_mapping_approval_path: Optional[Path] = None,
    size_mapping_approval_sha256: Optional[str] = None,
) -> ListingPlanValidationReport:
    listing_plan_sha256 = _phase_2_document_sha256(document)
    if listing_plan_sha256 is None:
        return ListingPlanValidationReport(
            schema_valid=False,
            committable=False,
            phase_2_lock_sha256=PHASE_2_LOCK_SHA256,
            listing_plan_sha256=None,
            issues=[
                _issue(
                    "LISTING_PLAN_CANONICALIZATION_INVALID",
                    "$",
                    "ListingPlan must be valid RFC 8785/I-JSON",
                )
            ],
        )
    raw_issues = (
        _forbidden_target_state_issues(document)
        + _raw_target_safety_issues(document)
        + _raw_source_bypass_issues(document)
        + projection_manifest_raw_issues(document)
    )
    try:
        plan = ListingPlan.model_validate(document)
    except ValidationError as exc:
        schema_issues = list(raw_issues)
        schema_issues.append(
            _issue(
                "LISTING_PLAN_SCHEMA_INVALID",
                "$",
                json.dumps(exc.errors(include_url=False), ensure_ascii=False, default=str),
            )
        )
        return ListingPlanValidationReport(
            schema_valid=False,
            committable=False,
            phase_2_lock_sha256=PHASE_2_LOCK_SHA256,
            listing_plan_sha256=listing_plan_sha256,
            issues=_dedupe_issues(schema_issues),
        )
    issues = list(raw_issues)
    try:
        lock, locked_example = _load_locked_contract(lock_path)
    except (OSError, ValueError, KeyError, StopIteration, ContractLoadError) as exc:
        issues.append(_issue("PHASE_2_LOCK_INVALID", str(lock_path), str(exc)))
        return ListingPlanValidationReport(
            schema_valid=True,
            committable=False,
            phase_2_lock_sha256=PHASE_2_LOCK_SHA256,
            listing_plan_sha256=listing_plan_sha256,
            issues=_dedupe_issues(issues),
        )
    historical_example = document == locked_example
    legacy = test_mode or historical_example
    effective_lock = lock
    if not test_mode and not historical_example:
        effective_lock = dict(lock)
        revisions = json.loads(MAINTENANCE_PATH.read_text(encoding="utf-8"))["artifacts"]
        by_path = {item["path"]: item for item in revisions}
        effective_lock["artifacts"] = [by_path.get(item["path"], item) for item in lock["artifacts"]]
    issues.extend(_profile_and_evidence_issues(plan, effective_lock))
    source_capture, source_issues = _source_capture_evidence_issues(
        plan,
        source_capture_evidence,
        test_mode,
        legacy=legacy,
    )
    issues.extend(source_issues)
    issues.extend(
        verify_projection_manifest(
            plan,
            document,
            lock,
            lock_path.resolve().parents[5],
            source_capture,
            test_registry=test_projection_registry,
            test_registry_root=test_projection_registry_root,
            test_mode=test_mode,
            product_registry_path=product_registry_path,
            product_registry_sha256=product_registry_sha256,
        )
    )
    plan_data = plan.model_dump(mode="json", by_alias=True)
    fp_ids = {binding.fact_packet_fact_id for binding in plan.fact_packet_projection.bindings}
    df_ids = {fact.derived_fact_id for fact in plan.derived_facts}
    issues.extend(_reference_issues(plan_data, fp_ids, df_ids))
    issues.extend(_derived_fact_issues(plan))
    issues.extend(_transform_application_issues(plan))
    issues.extend(_price_issues(plan))
    size_labels, size_approval_issues = _approved_size_mapping(
        plan, size_mapping_approval_path, size_mapping_approval_sha256, test_mode=test_mode,
    )
    issues.extend(size_approval_issues)
    issues.extend(_variant_issues(plan, legacy=legacy, approved_size_labels=size_labels))
    issues.extend(_structure_issues(plan, legacy=legacy, approved_size_labels=size_labels))
    issues.extend(_seo_organisation_issues(plan, legacy=legacy))
    issues.extend(_state_media_model_issues(plan, legacy=test_mode or historical_example))
    issues.extend(_ownership_issues(plan))
    issues.extend(_customer_leakage_issues(plan))
    issues.extend(_policy_issues(plan, test_mode, legacy=legacy))
    issues.extend(_blocking_flag_issues(plan))
    issues.extend(_copy_guard_issues(plan, document, source_capture, source_artifact_root))
    issues = _dedupe_issues(issues)
    return ListingPlanValidationReport(
        schema_valid=True,
        committable=not any(issue.blocking for issue in issues),
        phase_2_lock_sha256=PHASE_2_LOCK_SHA256,
        listing_plan_sha256=listing_plan_sha256,
        issues=issues,
    )
