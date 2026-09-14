"""Deterministic offline replay of Scout-owned signed fixture bundles."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from product_listing.adapters import FrozenBundleAdapter, JsonLdDomAdapter, ShopifyAjaxAdapter
from product_listing.evidence import model_sha256, sha256_file, sha256_text
from product_listing.errors import PipelineStop
from product_listing.models import (
    ArtifactKind,
    ConflictSeverity,
    ConflictState,
    ConflictValue,
    EvidenceSource,
    ExpectedRoleAbsence,
    GapSeverity,
    ReplayResult,
    SectionRole,
    SourceAcquisitionGap,
    SourceArtifact,
    SourceCapture,
    SourceClassEvidence,
    SourceConflict,
    LockedSourceDenominator,
)
from product_listing.reconcile import ReconcileContext, reconcile
from product_listing.validation import validate_source_capture


BUNDLE_FILENAME = "bundle.json"
HASH_INDEX_FILENAME = "bundle-files.sha256"

KIND_BY_FILENAME = {
    "bundle.json": ArtifactKind.BUNDLE,
    "rendered.sanitized.html": ArtifactKind.RENDERED_HTML,
    "structured-product.json": ArtifactKind.STRUCTURED_PRODUCT,
    "sections.json": ArtifactKind.SECTIONS,
    "size-guide.json": ArtifactKind.SIZE_GUIDE,
    "media-manifest.json": ArtifactKind.MEDIA_MANIFEST,
    "evidence-registry.json": ArtifactKind.EVIDENCE_REGISTRY,
}


def _artifact_kind(relative_path: str) -> ArtifactKind:
    lowered = relative_path.lower()
    filename = Path(lowered).name
    if lowered.endswith("/product.js.json"):
        return ArtifactKind.SHOPIFY_AJAX
    if "json-ld" in filename or "jsonld" in filename:
        return ArtifactKind.JSON_LD
    if lowered == "raw/cart.currency.json":
        return ArtifactKind.CART_CURRENCY
    if lowered == "raw/size-guide.api.json":
        return ArtifactKind.SIZE_GUIDE_PROVIDER
    if lowered == "raw/media-content-hashes.json":
        return ArtifactKind.MEDIA_CONTENT_HASHES
    if lowered in {"fetch-size-guide-pass3.py", "fetch-media-pass3.py", "build-bundle.py"}:
        return ArtifactKind.PROVENANCE_SCRIPT
    kind = KIND_BY_FILENAME.get(lowered)
    if kind is None:
        raise PipelineStop(
            "BUNDLE_ARTIFACT_KIND_UNKNOWN",
            "signed artifact kind is not in the consumer contract",
            {"path": relative_path},
        )
    return kind

CONFLICT_FIELDS = {
    "MARKET_CURRENCY_RESPONSE_CONFLICT": (
        "currency",
        ["listing.price", "feed.currency"],
    ),
    "COMPOSITION_TOTAL_97_PERCENT": (
        "material_composition",
        ["listing.claim.material_composition", "listing.metafield.fabric"],
    ),
    "MATERIAL_POLYESTER_VS_VISCOSE": (
        "material_composition",
        ["listing.claim.material_composition", "listing.metafield.fabric"],
    ),
}


def _load_json(path: Path) -> Dict[str, Any]:
    value = _load_json_value(path)
    if not isinstance(value, dict):
        raise PipelineStop("BUNDLE_JSON_INVALID", "%s must contain a JSON object" % path.name)
    return value


def _load_json_value(path: Path) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineStop(
            "BUNDLE_JSON_INVALID",
            "cannot read %s" % path.name,
            {"error": str(exc)},
        )
    return value


def _require_signed(
    relative_path: str,
    signed_hashes: Dict[str, str],
    declared_sha256: Any = None,
) -> None:
    if relative_path not in signed_hashes:
        raise PipelineStop(
            "BUNDLE_ARTIFACT_UNSIGNED",
            "consumed artifact is absent from bundle-files.sha256",
            {"path": relative_path},
        )
    if declared_sha256 not in (None, "") and str(declared_sha256) != signed_hashes[relative_path]:
        raise PipelineStop(
            "BUNDLE_DECLARED_HASH_MISMATCH",
            "bundle metadata disagrees with the verified artifact hash",
            {
                "path": relative_path,
                "declared": str(declared_sha256),
                "verified": signed_hashes[relative_path],
            },
        )


def _safe_path(bundle_dir: Path, relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise PipelineStop("BUNDLE_PATH_INVALID", "bundle paths must be non-empty and relative")
    root = bundle_dir.resolve()
    candidate = (bundle_dir / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise PipelineStop("BUNDLE_PATH_INVALID", "bundle path escapes fixture directory")
    return candidate


def _verified_hashes(bundle_dir: Path) -> List[Tuple[str, str]]:
    index_path = bundle_dir / HASH_INDEX_FILENAME
    if not index_path.is_file():
        raise PipelineStop(
            "BUNDLE_HASH_INDEX_MISSING",
            "%s is required" % HASH_INDEX_FILENAME,
        )
    values: List[Tuple[str, str]] = []
    seen = set()
    for line_number, raw_line in enumerate(index_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise PipelineStop(
                "BUNDLE_HASH_INDEX_INVALID",
                "invalid hash index line",
                {"line": line_number},
            )
        expected, relative_path = parts[0].lower(), parts[1].strip().lstrip("*")
        if relative_path in seen:
            raise PipelineStop("BUNDLE_HASH_INDEX_INVALID", "duplicate hash entry", {"path": relative_path})
        seen.add(relative_path)
        path = _safe_path(bundle_dir, relative_path)
        if not path.is_file():
            raise PipelineStop("BUNDLE_ARTIFACT_MISSING", "signed artifact is missing", {"path": relative_path})
        actual = sha256_file(path)
        if actual != expected:
            raise PipelineStop(
                "ARTIFACT_HASH_MISMATCH",
                "signed artifact hash does not match",
                {"path": relative_path, "expected": expected, "actual": actual},
            )
        values.append((relative_path, actual))
    if BUNDLE_FILENAME not in seen:
        raise PipelineStop("BUNDLE_HASH_INDEX_INVALID", "bundle.json must be signed")
    return values


def _artifacts(values: List[Tuple[str, str]]) -> List[SourceArtifact]:
    artifacts = []
    for relative_path, digest in values:
        kind = _artifact_kind(relative_path)
        artifacts.append(
            SourceArtifact(
                artifact_id=Path(relative_path).stem.replace(".", "-"),
                kind=kind,
                relative_path=relative_path,
                media_type=(
                    "text/html"
                    if relative_path.endswith(".html")
                    else "text/x-python"
                    if relative_path.endswith(".py")
                    else "application/json"
                ),
                sha256=digest,
            )
        )
    return artifacts


def _section_role(heading: str) -> SectionRole:
    lowered = heading.lower()
    if "description" in lowered:
        return SectionRole.DESCRIPTION
    if "detail" in lowered and "care" in lowered:
        return SectionRole.DETAILS_CARE
    if "sustainab" in lowered:
        return SectionRole.SUSTAINABILITY
    if "size guide" in lowered or "size chart" in lowered:
        return SectionRole.SIZE_GUIDE
    if "fit" in lowered:
        return SectionRole.SIZE_FIT
    if "material" in lowered or "fabric" in lowered:
        return SectionRole.MATERIALS_PROVENANCE
    return SectionRole.OTHER


def _expected_role_absences(
    bundle: Dict[str, Any],
    sections: Dict[str, Any],
    captured_at: datetime,
) -> List[ExpectedRoleAbsence]:
    values: List[ExpectedRoleAbsence] = []
    for index, raw in enumerate(sections.get("expected_section_absences") or []):
        heading = str(raw.get("heading") or raw.get("section") or "")
        values.append(
            ExpectedRoleAbsence(
                role=_section_role(heading),
                reason="; ".join(
                    str(value)
                    for value in (raw.get("status"), raw.get("note"), raw.get("basis"))
                    if value not in (None, "")
                ) or "proven absent",
                locator="artifact:sections#/expected_section_absences/%s" % index,
                captured_at=captured_at,
            )
        )
    model_absences = [
        raw
        for raw in (bundle.get("absences") or [])
        if str(raw.get("field") or "").startswith("source_model.")
    ]
    if model_absences:
        values.append(
            ExpectedRoleAbsence(
                role=SectionRole.SOURCE_MODEL_EVIDENCE,
                reason="; ".join(str(raw.get("basis") or raw.get("status")) for raw in model_absences),
                locator="bundle.json#/absences",
                captured_at=captured_at,
            )
        )
    return values


def _declared_conflicts(bundle: Dict[str, Any]) -> List[SourceConflict]:
    conflicts = []
    for index, raw in enumerate(bundle.get("conflicts") or []):
        code = str(raw.get("code") or "UNNAMED_SOURCE_CONFLICT")
        field_path, blocked_outputs = CONFLICT_FIELDS.get(
            code,
            ("source_evidence", ["listing.unknown_output"]),
        )
        if code == "MARKET_CURRENCY_RESPONSE_CONFLICT":
            values = [
                ConflictValue(
                    source=EvidenceSource.MANIFEST,
                    value={"market": "GB", "currency": "GBP"},
                    locator="bundle.json#/capture",
                ),
                ConflictValue(
                    source=EvidenceSource.RENDERED_DOM,
                    value={"market": "MA", "currency": "MAD"},
                    locator="bundle.json#/conflicts/%s" % index,
                ),
            ]
        elif code == "COMPOSITION_TOTAL_97_PERCENT":
            values = [
                ConflictValue(
                    source=EvidenceSource.RENDERED_DOM,
                    value={"captured_percent_total": "97"},
                    locator="artifact:sections#/sections/1",
                ),
                ConflictValue(
                    source=EvidenceSource.MANIFEST,
                    value={"required_percent_total": "100", "missing_percent": "3"},
                    locator="bundle.json#/conflicts/%s" % index,
                ),
            ]
        elif isinstance(raw.get("claims"), list) and len(raw["claims"]) >= 2:
            values = [
                ConflictValue(
                    source=EvidenceSource.RENDERED_DOM,
                    value=str(claim),
                    locator="bundle.json#/conflicts/%s/claims/%s" % (index, claim_index),
                )
                for claim_index, claim in enumerate(raw["claims"])
            ]
        else:
            values = [
                ConflictValue(
                    source=EvidenceSource.MANIFEST,
                    value="declared conflict",
                    locator="bundle.json#/conflicts/%s" % index,
                ),
                ConflictValue(
                    source=EvidenceSource.RENDERED_DOM,
                    value=str(raw.get("detail") or code),
                    locator="bundle.json#/conflicts/%s/detail" % index,
                ),
            ]
        conflicts.append(
            SourceConflict(
                conflict_id="conflict-%s" % sha256_text(code)[:16],
                code=code,
                field_path=field_path,
                severity=ConflictSeverity(str(raw.get("severity") or "BLOCKING")),
                state=ConflictState.UNRESOLVED,
                values=values,
                blocked_output_ids=blocked_outputs,
                rationale=str(raw.get("detail") or raw.get("resolution") or code),
            )
        )
    return conflicts


def _acquisition_gaps(bundle: Dict[str, Any]) -> List[SourceAcquisitionGap]:
    gaps = []
    for raw in bundle.get("acquisition_gaps") or []:
        code = str(raw.get("code") or "UNNAMED_ACQUISITION_GAP")
        severity = GapSeverity(str(raw.get("severity") or "BLOCKING"))
        detail = raw.get("detail")
        if not detail and code == "SAME_SESSION_COMMERCE_JSON_NOT_FROZEN":
            detail = "same-session commerce JSON was not frozen; source price/variant authority is incomplete"
        gaps.append(
            SourceAcquisitionGap(
                code=code,
                severity=severity,
                detail=str(detail) if detail else None,
                replacement=str(raw.get("replacement")) if raw.get("replacement") else None,
            )
        )
    return gaps


def _locked_denominator(
    bundle: Dict[str, Any],
    structured: Dict[str, Any],
    sections: Dict[str, Any],
    size_guide: Dict[str, Any],
    media: Dict[str, Any],
    evidence: Dict[str, Any],
) -> LockedSourceDenominator:
    """Assemble the reviewer denominator without inventing or normalizing fields."""

    return LockedSourceDenominator(
        capture=bundle.get("capture") or {},
        structured_product=structured,
        sections=sections.get("sections") or [],
        expected_absences=bundle.get("absences") or [],
        media=media,
        size_guide=size_guide,
        evidence_only_exclusions={
            "reviews": evidence.get("reviews_evidence_only") or {},
            "retailer_sustainability_and_trust": (
                evidence.get("retailer_sustainability_and_trust_evidence_only") or {}
            ),
            "explicit_exclusions": evidence.get("explicit_exclusions") or [],
        },
        conflicts=bundle.get("conflicts") or [],
        acquisition_gaps=bundle.get("acquisition_gaps") or [],
        status=str(bundle.get("status") or bundle.get("verdict") or "UNSPECIFIED"),
    )


def replay_bundle(bundle_dir: Path) -> ReplayResult:
    bundle_dir = bundle_dir.resolve()
    bundle_path = bundle_dir / BUNDLE_FILENAME
    if not bundle_path.is_file():
        raise PipelineStop("BUNDLE_ENTRYPOINT_MISSING", "%s is required" % BUNDLE_FILENAME)
    signed_hash_values = _verified_hashes(bundle_dir)
    signed_hashes = dict(signed_hash_values)
    bundle = _load_json(bundle_path)
    if bundle.get("schema") != "source-capture-fixture-v1":
        raise PipelineStop("BUNDLE_SCHEMA_UNSUPPORTED", "unsupported bundle schema")

    files = bundle.get("files") or {}
    required = {"structured_product", "sections", "size_guide", "media", "evidence"}
    if set(files) != required:
        raise PipelineStop(
            "BUNDLE_FILES_INVALID",
            "bundle files map must contain the frozen Phase 1 roles",
            {"expected": sorted(required), "actual": sorted(files)},
        )
    consumed_paths = [str(files[role]) for role in sorted(required)]
    if len(consumed_paths) != len(set(consumed_paths)):
        raise PipelineStop("BUNDLE_FILES_INVALID", "bundle file roles must have unique paths")
    for relative_path in consumed_paths:
        _require_signed(relative_path, signed_hashes)
    capture_data = bundle.get("capture") or {}
    rendered_record = capture_data.get("rendered_html") or {}
    _require_signed(
        "rendered.sanitized.html",
        signed_hashes,
        rendered_record.get("sanitized_sha256"),
    )
    structured = _load_json(_safe_path(bundle_dir, str(files["structured_product"])))
    sections = _load_json(_safe_path(bundle_dir, str(files["sections"])))
    size_guide = _load_json(_safe_path(bundle_dir, str(files["size_guide"])))
    media = _load_json(_safe_path(bundle_dir, str(files["media"])))
    evidence = _load_json(_safe_path(bundle_dir, str(files["evidence"])))

    captured_at = datetime.fromisoformat(str(capture_data["captured_at"]).replace("Z", "+00:00"))
    frozen = FrozenBundleAdapter().extract(
        structured_product=structured,
        sections_payload=sections,
        size_guide_payload=size_guide,
        media_payload=media,
        bundle_payload=bundle,
        captured_at=captured_at,
        base_url=str(capture_data["final_url"]),
    )
    consumer_retail = structured.get("source_class") == "CONSUMER_RETAILER"
    expected_absences = _expected_role_absences(bundle, sections, captured_at)
    context = ReconcileContext(
        requested_url=str(capture_data["requested_url"]),
        final_url=str(capture_data["final_url"]),
        canonical_url=str(capture_data["canonical_url"]),
        captured_at=captured_at,
        market=str(capture_data["market"]).upper(),
        currency=str(capture_data["currency"]).upper(),
        consumer_retail_source=consumer_retail,
        source_class_evidence=SourceClassEvidence(
            consumer_retail_source=consumer_retail,
            locator="artifact:structured_product#/source_class",
            rationale="frozen source class is %s" % structured.get("source_class"),
        ),
        artifacts=_artifacts(signed_hash_values),
        expected_section_roles=frozen.expected_roles,
        expected_role_absences=expected_absences,
        explicit_absences=frozen.explicit_absences,
        acquisition_gaps=_acquisition_gaps(bundle),
        declared_conflicts=_declared_conflicts(bundle),
    )
    adapter_results = [(EvidenceSource.MANIFEST, frozen.adapter_result)]
    commerce_json = capture_data.get("commerce_json") or {}
    same_session_commerce = capture_data.get("same_session_commerce_json") or {}
    commerce_path = commerce_json.get("path") or same_session_commerce.get("product_path")
    if commerce_path:
        _require_signed(
            str(commerce_path),
            signed_hashes,
            commerce_json.get("sha256"),
        )
        cart_currency = str(capture_data["currency"]).upper()
        cart_currency_path = same_session_commerce.get("cart_currency_path")
        if cart_currency_path:
            _require_signed(str(cart_currency_path), signed_hashes)
            cart_payload = _load_json(_safe_path(bundle_dir, str(cart_currency_path)))
            cart_currency = str(cart_payload.get("currency") or "").upper()
            if not cart_currency:
                raise PipelineStop(
                    "SAME_SESSION_CURRENCY_MISSING",
                    "same-session cart currency evidence is empty",
                )
        ajax_payload = _load_json(_safe_path(bundle_dir, str(commerce_path)))
        ajax_result = ShopifyAjaxAdapter().extract(
            payload=ajax_payload,
            captured_at=captured_at,
            artifact_id="shopify-ajax",
            currency=cart_currency,
        )
        adapter_results.append((EvidenceSource.SHOPIFY_AJAX, ajax_result))

    jsonld_record = capture_data.get("json_ld") or {}
    jsonld_path = jsonld_record.get("path")
    if jsonld_path:
        _require_signed(str(jsonld_path), signed_hashes, jsonld_record.get("sha256"))
        jsonld_payload = _load_json_value(_safe_path(bundle_dir, str(jsonld_path)))
        jsonld_result = JsonLdDomAdapter().extract_jsonld(
            jsonld_payload,
            captured_at=captured_at,
            artifact_id="json-ld",
            base_url=str(capture_data["final_url"]),
        )
        adapter_results.append((EvidenceSource.JSON_LD, jsonld_result))

    capture = reconcile(
        context=context,
        adapter_results=adapter_results,
        rendered_media=frozen.rendered_media,
        structured_media=frozen.structured_media,
    )
    locked_denominator = None
    if bundle.get("status") == "POSITIVE_DENOMINATOR_COMPLETE":
        locked_denominator = _locked_denominator(
            bundle=bundle,
            structured=structured,
            sections=sections,
            size_guide=size_guide,
            media=media,
            evidence=evidence,
        )
    capture = SourceCapture.model_validate(
        {
            **capture.model_dump(mode="python", exclude_none=False),
            "locale": capture_data.get("locale"),
            "capture_attempt": capture_data.get("attempt"),
            "rendered_capture": capture_data.get("rendered_html"),
            "json_ld_capture": capture_data.get("json_ld"),
            "same_session_commerce": (
                capture_data.get("same_session_commerce_json")
                or capture_data.get("commerce_json")
            ),
            "structured_product_evidence": structured if locked_denominator is not None else None,
            "size_guide_evidence": size_guide if locked_denominator is not None else None,
            "media_manifest_evidence": media if locked_denominator is not None else None,
            "evidence_only_exclusions": (
                locked_denominator.evidence_only_exclusions
                if locked_denominator is not None
                else None
            ),
            "media_orders_match": media.get("orders_match"),
            "media_gallery_count": media.get("gallery_count"),
            "media_exclusions": media.get("explicit_exclusions") or [],
            "locked_denominator": locked_denominator,
        }
    )
    issues = validate_source_capture(capture)
    return ReplayResult(
        source_capture=capture,
        determinism_sha256=model_sha256(capture),
        valid=not any(issue.blocking for issue in issues),
        issues=issues,
    )
