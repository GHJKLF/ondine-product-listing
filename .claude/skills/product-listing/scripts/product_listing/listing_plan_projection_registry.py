"""Registry-only verification for reviewer-signed FactPacket projections.

This module never derives normalized facts from SourceCapture prose.  It
resolves a plan's manifest ID through an Atlas-locked registry and compares
the complete ordered binding array byte-for-byte under canonical JSON.
"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from product_listing.listing_plan_canonical_json import canonical_json_bytes
from product_listing.listing_plan_models import ListingPlan, ListingPlanIssue
from product_listing.models import SourceCapture


REQUIRED_CODE = "FACT_PACKET_PROJECTION_MANIFEST_REQUIRED"
INVALID_CODE = "FACT_PACKET_PROJECTION_MANIFEST_INVALID"
SEPARATION_CODE = "FACT_PACKET_PROJECTION_REVIEW_SEPARATION_INVALID"
BINDINGS_CODE = "FACT_PACKET_PROJECTION_BINDINGS_MISMATCH"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _issue(code: str, path: str, message: str) -> ListingPlanIssue:
    return ListingPlanIssue(
        code=code,
        field_path=path,
        message=message,
        blocking=True,
    )


def projection_manifest_raw_issues(document: Dict[str, Any]) -> List[ListingPlanIssue]:
    """Keep the locked manifest codes visible even when schema parsing fails."""

    issues: List[ListingPlanIssue] = []
    evidence = document.get("evidence")
    packet = document.get("fact_packet_projection")
    required = (
        (evidence, "fact_packet_projection_manifest_id", "$.evidence"),
        (evidence, "fact_packet_projection_manifest_sha256", "$.evidence"),
        (packet, "manifest_id", "$.fact_packet_projection"),
        (packet, "manifest_sha256", "$.fact_packet_projection"),
    )
    for parent, key, path in required:
        if not isinstance(parent, dict) or not isinstance(parent.get(key), str) or not parent[key]:
            issues.append(
                _issue(
                    REQUIRED_CODE,
                    "%s.%s" % (path, key),
                    "all four registry manifest pins are required",
                )
            )
    for parent, path in ((evidence, "$.evidence"), (packet, "$.fact_packet_projection")):
        if not isinstance(parent, dict):
            continue
        for key in parent:
            compact = str(key).replace("_", "").casefold()
            if "manifest" in compact and ("path" in compact or "url" in compact):
                issues.append(
                    _issue(
                        INVALID_CODE,
                        "%s.%s" % (path, key),
                        "plans may carry manifest ID and SHA-256 pins only",
                    )
                )
    return issues


def _safe_file(root: Path, relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("registry artifact path is missing")
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("registry artifact escapes its trusted root") from exc
    if not candidate.is_file():
        raise ValueError("registry artifact is missing: %s" % relative_path)
    return candidate


def _read_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("registry artifact root must be an object")
    return value


def _lock_registry(lock: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    singular = lock.get("fact_packet_projection_dependency")
    if isinstance(singular, dict):
        entries.append(singular)
    plural = lock.get("fact_packet_projection_registry")
    if isinstance(plural, list):
        entries.extend(item for item in plural if isinstance(item, dict))
    result: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        manifest_id = entry.get("manifest_id")
        if not isinstance(manifest_id, str) or not manifest_id or manifest_id in result:
            raise ValueError("Atlas registry has a missing or duplicate manifest ID")
        result[manifest_id] = entry
    return result


def _pins(plan: ListingPlan) -> Tuple[str, str]:
    ids = {
        plan.evidence.fact_packet_projection_manifest_id,
        plan.fact_packet_projection.manifest_id,
    }
    hashes = {
        plan.evidence.fact_packet_projection_manifest_sha256,
        plan.fact_packet_projection.manifest_sha256,
    }
    if len(ids) != 1 or len(hashes) != 1:
        raise ValueError("evidence and FactPacket manifest pins must be identical")
    return next(iter(ids)), next(iter(hashes))


def _binding_from_record(record: Dict[str, Any]) -> Dict[str, Any]:
    typed = record.get("typed_value")
    claim = record.get("claim_eligibility")
    policy = record.get("policy_eligibility")
    if not isinstance(typed, dict) or "value" not in typed:
        raise ValueError("projection record typed value is missing")
    if not isinstance(claim, dict) or not isinstance(policy, dict):
        raise ValueError("projection record eligibility is missing")
    binding = {
        "fact_packet_fact_id": record.get("fact_packet_fact_id"),
        "value": typed["value"],
        "source_fact_or_path": record.get("source_fact_or_path"),
        "evidence_locator": record.get("evidence_locator"),
        "captured_at": record.get("captured_at"),
        "market": record.get("market"),
        "locale": record.get("locale"),
        "scope": record.get("scope"),
        "conflict_state": record.get("conflict_state"),
        "publishable_as_claim": claim.get("publishable_as_claim"),
        "usable_as_policy_input": policy.get("usable_as_policy_input"),
        "allowed_transform_ids": record.get("allowed_transform_ids"),
    }
    if record.get("unit") is not None:
        binding["unit"] = record["unit"]
    if record.get("currency") is not None:
        binding["currency"] = record["currency"]
    for key in ("source_option_name", "source_option_position"):
        if record.get(key) is not None:
            binding[key] = record[key]
    return binding


def _manifest_structure_errors(
    manifest: Dict[str, Any],
    entry: Dict[str, Any],
) -> List[str]:
    errors: List[str] = []
    bindings = manifest.get("bindings")
    records = manifest.get("records")
    if not isinstance(bindings, list) or not isinstance(records, list):
        return ["manifest bindings and records must be arrays"]
    binding_hash = sha256_bytes(canonical_json_bytes(bindings))
    pins = manifest.get("candidate_projection_pins") or {}
    summary = manifest.get("summary") or {}
    expected_count = entry.get("ordered_binding_count")
    expected_hash = entry.get("ordered_bindings_canonical_sha256")
    if (
        len(bindings) != expected_count
        or len(records) != expected_count
        or len({item.get("fact_packet_fact_id") for item in bindings if isinstance(item, dict)})
        != len(bindings)
    ):
        errors.append("manifest binding count or identity uniqueness is invalid")
    if binding_hash != expected_hash or pins.get("ordered_bindings_canonical_sha256") != expected_hash:
        errors.append("manifest ordered binding hash is invalid")
    if (
        summary.get("candidate_binding_count") != len(bindings)
        or summary.get("ordered_record_count") != len(records)
        or summary.get("allowed_count") != len(bindings)
        or summary.get("blocked_count") != 0
        or summary.get("unsupported_values_invented") != 0
    ):
        errors.append("manifest summary does not describe a complete allowed projection")
    for index, (binding, record) in enumerate(zip(bindings, records), start=1):
        if not isinstance(binding, dict) or not isinstance(record, dict):
            errors.append("manifest binding/record %s is not an object" % index)
            continue
        try:
            reconstructed = _binding_from_record(record)
        except ValueError as exc:
            errors.append("record %s: %s" % (index, exc))
            continue
        verification = record.get("reviewer_verification") or {}
        rule = record.get("projection_rule") or {}
        if (
            record.get("order") != index
            or record.get("projection_status") != "ALLOW"
            or record.get("block_reason") is not None
            or not isinstance(rule.get("id"), str)
            or not isinstance(rule.get("version"), str)
            or verification.get("reviewer_verified") is not True
            or not verification.get("evidence_sources")
            or canonical_json_bytes(reconstructed) != canonical_json_bytes(binding)
        ):
            errors.append("record %s does not exactly attest its binding" % index)
    return errors


def _parse_time(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _separation_errors(
    manifest: Dict[str, Any],
    reviewer_lock: Dict[str, Any],
    entry: Dict[str, Any],
    manifest_sha256: str,
) -> List[str]:
    errors: List[str] = []
    actors = manifest.get("actors") or {}
    author = actors.get("author_auditor") or {}
    required_reviewer = actors.get("required_reviewer_signatory") or {}
    reviewer = reviewer_lock.get("reviewer_signatory") or {}
    locked_manifest = reviewer_lock.get("manifest") or {}
    author_id = entry.get("author_actor_id")
    reviewer_id = entry.get("reviewer_actor_id")
    author_time = _parse_time(author.get("attested_at"))
    review_time = _parse_time(reviewer_lock.get("locked_at"))
    if (
        not isinstance(author_id, str)
        or not isinstance(reviewer_id, str)
        or not author_id
        or not reviewer_id
        or author_id == reviewer_id
        or author.get("actor_id") != author_id
        or author.get("role") != "AUTHOR_AUDITOR"
        or author.get("attestation_status") != "AUTHOR_AUDIT_COMPLETE"
        or author.get("review_or_signature_authority") is not False
        or required_reviewer.get("actor_id") != reviewer_id
        or required_reviewer.get("must_be_distinct_from_author_auditor") is not True
        or reviewer.get("actor_id") != reviewer_id
        or reviewer.get("role") != "REVIEWER_SIGNATORY"
        or reviewer.get("approval_status") != "APPROVED"
        or reviewer.get("distinct_from_author_actor_id") != author_id
        or locked_manifest.get("author_actor_id") != author_id
        or locked_manifest.get("reviewer_actor_id") != reviewer_id
        or locked_manifest.get("author_status") != "AUTHOR_AUDIT_COMPLETE"
        or locked_manifest.get("review_status") != "APPROVED_BY_DETACHED_LOCK"
        or author_time is None
        or review_time is None
        or review_time <= author_time
    ):
        errors.append("manifest author and detached reviewer attestations are not independent")
    if (
        locked_manifest.get("manifest_id") != manifest.get("manifest_id")
        or locked_manifest.get("sha256") != manifest_sha256
    ):
        errors.append("detached reviewer lock does not attest the finalized manifest")
    return errors


def _registry_artifact_errors(
    plan: ListingPlan,
    capture: Optional[SourceCapture],
    manifest: Dict[str, Any],
    reviewer_lock: Dict[str, Any],
    entry: Dict[str, Any],
) -> List[str]:
    errors: List[str] = []
    pins = manifest.get("candidate_projection_pins") or {}
    source = manifest.get("source_capture") or {}
    accepted = reviewer_lock.get("accepted_projection") or {}
    source_output = plan.evidence.source_capture_sha256
    source_determinism = plan.evidence.source_capture_determinism_sha256
    if (
        source.get("output_sha256") != source_output
        or source.get("determinism_sha256") != source_determinism
        or source.get("valid") is not True
        or source.get("issues") != []
        or pins.get("source_capture_sha256") != source_output
        or pins.get("source_capture_determinism_sha256") != source_determinism
        or accepted.get("source_capture_output_sha256") != source_output
        or accepted.get("source_capture_determinism_sha256") != source_determinism
    ):
        errors.append("manifest SourceCapture pins do not match the plan")
    bindings = manifest.get("bindings") if isinstance(manifest.get("bindings"), list) else []
    binding_map = {
        item.get("fact_packet_fact_id"): item.get("value")
        for item in bindings
        if isinstance(item, dict)
    }
    if capture is not None:
        source_product_id = (capture.structured_product_evidence or {}).get("product_id")
        if (
            binding_map.get("fp.canonical_source_url") != capture.canonical_url
            or (
                source_product_id is not None
                and str(binding_map.get("fp.source_product_id")) != str(source_product_id)
            )
        ):
            errors.append("manifest product identity does not match supplied SourceCapture")
    if (
        accepted.get("ordered_binding_count") != entry.get("ordered_binding_count")
        or accepted.get("ordered_bindings_canonical_sha256")
        != entry.get("ordered_bindings_canonical_sha256")
        or accepted.get("allowed_count") != entry.get("ordered_binding_count")
        or accepted.get("blocked_count") != 0
    ):
        errors.append("detached reviewer lock projection denominator is inconsistent")
    return errors


def verify_projection_manifest(
    plan: ListingPlan,
    document: Dict[str, Any],
    lock: Dict[str, Any],
    registry_root: Path,
    capture: Optional[SourceCapture],
    test_registry: Optional[Dict[str, Dict[str, Any]]] = None,
    test_registry_root: Optional[Path] = None,
    test_mode: bool = False,
    product_registry_path: Optional[Path] = None,
    product_registry_sha256: Optional[str] = None,
) -> List[ListingPlanIssue]:
    """Resolve and verify one immutable projection dependency pair."""

    issues: List[ListingPlanIssue] = []
    try:
        manifest_id, plan_manifest_sha = _pins(plan)
    except ValueError as exc:
        return [_issue(INVALID_CODE, "$.fact_packet_projection", str(exc))]
    try:
        registry = _lock_registry(lock)
    except ValueError as exc:
        return [_issue(INVALID_CODE, "$.fact_packet_projection.manifest_id", str(exc))]
    root = registry_root
    if product_registry_path is not None or product_registry_sha256 is not None:
        try:
            if test_registry is not None:
                raise ValueError("product registry and test registry cannot be combined")
            if product_registry_path is None or not product_registry_sha256:
                raise ValueError("product registry requires an externally supplied SHA-256 pin")
            raw = product_registry_path.read_bytes()
            if sha256_bytes(raw) != product_registry_sha256:
                raise ValueError("product registry hash mismatch")
            product_registry = json.loads(raw)
            if product_registry.get("schema_version") != 1:
                raise ValueError("unsupported product registry version")
            additional = _lock_registry(product_registry)
            if len(additional) != 1 or set(additional) & set(registry):
                raise ValueError("product registry must add exactly one new product, not replace a locked fixture")
            if any(entry.get("fixture_only") is not False for entry in additional.values()):
                raise ValueError("product registry must explicitly declare non-fixture evidence")
            # A supplied run registry never redirects a historical dependency.
            if manifest_id in additional:
                registry = additional
                root = product_registry_path.resolve().parent
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            return [_issue(INVALID_CODE, "$.fact_packet_projection.manifest_id", str(exc))]
    if test_registry is not None:
        if not test_mode or test_registry_root is None:
            return [
                _issue(
                    INVALID_CODE,
                    "$.fact_packet_projection.manifest_id",
                    "test registry injection is allowed only in explicit in-process test mode",
                )
            ]
        registry = test_registry
        root = test_registry_root
    entry = registry.get(manifest_id)
    if not isinstance(entry, dict):
        return [
            _issue(
                INVALID_CODE,
                "$.fact_packet_projection.manifest_id",
                "manifest ID is not present in the trusted registry",
            )
        ]
    try:
        manifest_path = _safe_file(root, str(entry.get("manifest_path") or ""))
        review_path = _safe_file(root, str(entry.get("atlas_lock_path") or ""))
        manifest_actual_sha = sha256_bytes(manifest_path.read_bytes())
        review_actual_sha = sha256_bytes(review_path.read_bytes())
        if (
            manifest_actual_sha != entry.get("manifest_sha256")
            or manifest_actual_sha != plan_manifest_sha
            or review_actual_sha != entry.get("atlas_lock_sha256")
        ):
            raise ValueError("manifest or detached reviewer lock hash mismatch")
        manifest = _read_json(manifest_path)
        reviewer_lock = _read_json(review_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [_issue(INVALID_CODE, "$.fact_packet_projection.manifest_id", str(exc))]
    if manifest.get("manifest_id") != manifest_id:
        issues.append(
            _issue(INVALID_CODE, "$.fact_packet_projection.manifest_id", "registry artifact ID mismatch")
        )
    try:
        structure_errors = _manifest_structure_errors(manifest, entry)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        structure_errors = [str(exc)]
    for message in structure_errors:
        issues.append(_issue(INVALID_CODE, "$.fact_packet_projection.manifest_id", message))
    try:
        separation_errors = _separation_errors(manifest, reviewer_lock, entry, manifest_actual_sha)
        artifact_errors = _registry_artifact_errors(plan, capture, manifest, reviewer_lock, entry)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        return issues + [_issue(INVALID_CODE, "$.fact_packet_projection.manifest_id",
                                "malformed review evidence: %s" % exc)]
    for message in separation_errors:
        code = SEPARATION_CODE if "independent" in message else INVALID_CODE
        issues.append(_issue(code, "$.fact_packet_projection.manifest_id", message))
    for message in artifact_errors:
        issues.append(_issue(INVALID_CODE, "$.fact_packet_projection.manifest_id", message))

    raw_packet = document.get("fact_packet_projection")
    raw_bindings = raw_packet.get("bindings") if isinstance(raw_packet, dict) else None
    manifest_bindings = manifest.get("bindings")
    try:
        bindings_match = (
            isinstance(raw_bindings, list)
            and isinstance(manifest_bindings, list)
            and canonical_json_bytes(raw_bindings)
            == canonical_json_bytes(manifest_bindings)
        )
    except ValueError:
        bindings_match = False
    if not bindings_match:
        issues.append(
            _issue(
                BINDINGS_CODE,
                "$.fact_packet_projection.bindings",
                "ordered FactPacket bindings must exactly equal the reviewer-signed manifest",
            )
        )
    return issues
