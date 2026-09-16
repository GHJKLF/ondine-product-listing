"""Deterministic merge of rendered and structured source evidence."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from product_listing.adapters.base import AdapterResult, FactCandidate, MediaCandidate
from product_listing.evidence import canonical_json_bytes, sha256_bytes, sha256_text
from product_listing.models import (
    AtomicFact,
    ConflictSeverity,
    ConflictState,
    ConflictValue,
    EvidenceSource,
    ExpectedRoleAbsence,
    ExplicitAbsence,
    FactConflictState,
    FactKind,
    MediaOrderKind,
    SectionRole,
    SourceArtifact,
    SourceAcquisitionGap,
    SourceCapture,
    SourceClassEvidence,
    SourceConflict,
    SourceMedia,
)


BLOCKED_OUTPUTS = {
    "canonical_url": ["listing.canonical_source"],
    "currency": ["listing.price", "feed.currency"],
    "current_price": ["listing.price"],
    "compare_at_price": ["listing.price_evidence"],
    "title": ["listing.title"],
    "material_composition": ["listing.claim.material_composition", "listing.metafield.fabric"],
    "options": ["listing.variants"],
    "variants": ["listing.variants"],
    "rendered_media": ["listing.source_media_evidence"],
    "structured_media": ["listing.source_media_evidence"],
}
BLOCKING_FIELDS = set(BLOCKED_OUTPUTS)


@dataclass(frozen=True)
class ReconcileContext:
    requested_url: str
    final_url: str
    canonical_url: str
    captured_at: datetime
    market: str
    currency: str
    consumer_retail_source: bool
    source_class_evidence: SourceClassEvidence
    artifacts: List[SourceArtifact]
    expected_section_roles: List[SectionRole]
    expected_role_absences: List[ExpectedRoleAbsence]
    explicit_absences: List[ExplicitAbsence]
    acquisition_gaps: List[SourceAcquisitionGap]
    declared_conflicts: List[SourceConflict]


def _normalized(value: Any) -> bytes:
    if isinstance(value, str):
        value = " ".join(value.split())
    if isinstance(value, Decimal):
        value = format(value.normalize(), "f")
    return canonical_json_bytes(value)


def _dedupe_models(values: Iterable[Any], key_name: str) -> List[Any]:
    seen = set()
    result = []
    for value in values:
        key = getattr(value, key_name)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _candidate_conflict(
    field_path: str,
    candidates: Sequence[FactCandidate],
) -> Optional[SourceConflict]:
    if candidates and all(candidate.fact_kind == FactKind.SOURCE_PROSE for candidate in candidates):
        return None
    distinct: Dict[bytes, FactCandidate] = {}
    for candidate in candidates:
        distinct.setdefault(_normalized(candidate.value), candidate)
    if len(distinct) <= 1:
        return None
    severity = ConflictSeverity.BLOCKING if field_path in BLOCKING_FIELDS else ConflictSeverity.WARNING
    return SourceConflict(
        conflict_id="conflict-%s" % sha256_bytes(
            b"|".join(sorted(distinct.keys())) + field_path.encode("utf-8")
        )[:16],
        code="FIELD_EVIDENCE_CONFLICT",
        field_path=field_path,
        severity=severity,
        state=ConflictState.UNRESOLVED,
        values=[
            ConflictValue(source=value.source, value=value.value, locator=value.locator)
            for value in sorted(distinct.values(), key=lambda item: (item.source.value, item.locator))
        ],
        blocked_output_ids=BLOCKED_OUTPUTS.get(field_path, []),
        rationale="rendered and structured source evidence disagree",
    )


def _normalized_decimal(value: Optional[Decimal]) -> Optional[str]:
    return format(value.normalize(), "f") if value is not None else None


def _model_list_bytes(field_path: str, values: Sequence[Any]) -> bytes:
    if field_path == "variants":
        # IDs, SKUs, titles and source availability can legitimately exist only
        # in the raw commerce artifact. Reconciliation compares the mandatory
        # exact structure: ordered combinations and prices.
        projected = [
            {
                "option_values": [item.model_dump(mode="json") for item in value.option_values],
                "current_price": _normalized_decimal(value.current_price),
                "compare_at_price": _normalized_decimal(value.compare_at_price),
            }
            for value in values
        ]
        return canonical_json_bytes(projected)
    return canonical_json_bytes([value.model_dump(mode="json") for value in values])


def _structure_conflict(
    field_path: str,
    values: Sequence[Tuple[EvidenceSource, Sequence[Any]]],
) -> Optional[SourceConflict]:
    distinct: Dict[bytes, Tuple[EvidenceSource, Sequence[Any]]] = {}
    for source, models in values:
        if not models:
            continue
        distinct.setdefault(_model_list_bytes(field_path, models), (source, models))
    if len(distinct) <= 1:
        return None
    return SourceConflict(
        conflict_id="conflict-%s" % sha256_text(field_path + "|" + "|".join(
            sorted(value.hex() for value in distinct)
        ))[:16],
        code="STRUCTURE_EVIDENCE_CONFLICT",
        field_path=field_path,
        severity=ConflictSeverity.BLOCKING,
        state=ConflictState.UNRESOLVED,
        values=[
            ConflictValue(
                source=source,
                value=[model.model_dump(mode="json") for model in models],
                locator="adapter:%s/%s" % (source.value, field_path),
            )
            for source, models in sorted(distinct.values(), key=lambda item: item[0].value)
        ],
        blocked_output_ids=BLOCKED_OUTPUTS[field_path],
        rationale="source structures disagree",
    )


def _media_conflict(
    field_path: str,
    candidates: Sequence[MediaCandidate],
    manifest_media: Sequence[SourceMedia],
) -> Optional[SourceConflict]:
    if not candidates or not manifest_media:
        return None
    candidate_urls = [item.url for item in candidates]
    manifest_urls = [item.url for item in manifest_media]
    if candidate_urls == manifest_urls:
        return None
    candidate_source = candidates[0].source
    return SourceConflict(
        conflict_id="conflict-%s" % sha256_text(field_path + "|" + "|".join(candidate_urls + manifest_urls))[:16],
        code="MEDIA_ORDER_CONFLICT",
        field_path=field_path,
        severity=ConflictSeverity.BLOCKING,
        state=ConflictState.UNRESOLVED,
        values=[
            ConflictValue(
                source=candidate_source,
                value=candidate_urls,
                locator="adapter:%s/%s" % (candidate_source.value, field_path),
            ),
            ConflictValue(
                source=EvidenceSource.MEDIA_MANIFEST,
                value=manifest_urls,
                locator="artifact:media_manifest#/%s" % field_path,
            ),
        ],
        blocked_output_ids=BLOCKED_OUTPUTS[field_path],
        rationale="captured media order disagrees with the hashed media manifest",
    )


def reconcile(
    context: ReconcileContext,
    adapter_results: Sequence[Tuple[EvidenceSource, AdapterResult]],
    rendered_media: Sequence[SourceMedia],
    structured_media: Sequence[SourceMedia],
) -> SourceCapture:
    all_candidates = [
        candidate
        for _, result in adapter_results
        for candidate in result.candidates
    ]
    all_candidates.extend(
        [
            FactCandidate(
                field_path="currency",
                value=context.currency,
                source=EvidenceSource.MANIFEST,
                locator="bundle.json#/capture/market_currency",
                captured_at=context.captured_at,
                fact_kind=FactKind.COMMERCE,
                priority=400,
            ),
            FactCandidate(
                field_path="canonical_url",
                value=context.canonical_url,
                source=EvidenceSource.MANIFEST,
                locator="bundle.json#/capture/canonical_url",
                captured_at=context.captured_at,
                fact_kind=FactKind.IDENTIFIER,
                priority=400,
            ),
        ]
    )

    candidates_by_field: Dict[str, List[FactCandidate]] = {}
    for candidate in all_candidates:
        candidates_by_field.setdefault(candidate.field_path, []).append(candidate)

    conflicts: List[SourceConflict] = list(context.declared_conflicts)
    selected: Dict[str, FactCandidate] = {}
    conflict_fields = {
        conflict.field_path
        for conflict in conflicts
        if conflict.state == ConflictState.UNRESOLVED
    }
    for field_path, candidates in sorted(candidates_by_field.items()):
        selected[field_path] = sorted(
            candidates,
            key=lambda item: (-item.priority, item.source.value, item.locator),
        )[0]
        conflict = _candidate_conflict(field_path, candidates)
        if conflict:
            conflicts.append(conflict)
            conflict_fields.add(field_path)

    structure_options = [
        (source, result.options)
        for source, result in adapter_results
        if result.options
    ]
    structure_variants = [
        (source, result.variants)
        for source, result in adapter_results
        if result.variants
    ]
    for field_path, values in (("options", structure_options), ("variants", structure_variants)):
        conflict = _structure_conflict(field_path, values)
        if conflict:
            conflicts.append(conflict)
            conflict_fields.add(field_path)

    precedence = {
        EvidenceSource.SHOPIFY_AJAX: 500,
        EvidenceSource.MANIFEST: 400,
        EvidenceSource.RENDERED_DOM: 200,
        EvidenceSource.JSON_LD: 100,
    }
    option_source = max(structure_options, key=lambda item: precedence[item[0]]) if structure_options else None
    variant_source = max(structure_variants, key=lambda item: precedence[item[0]]) if structure_variants else None
    options = list(option_source[1]) if option_source else []
    variants = list(variant_source[1]) if variant_source else []

    rendered_candidates = [
        item
        for _, result in adapter_results
        for item in result.rendered_media
    ]
    structured_candidates_by_source = [
        (source, result.structured_media)
        for source, result in adapter_results
        if result.structured_media
    ]
    structured_candidates = (
        max(structured_candidates_by_source, key=lambda item: precedence[item[0]])[1]
        if structured_candidates_by_source
        else []
    )
    for field_path, candidates, manifest_media in (
        ("rendered_media", rendered_candidates, rendered_media),
        ("structured_media", structured_candidates, structured_media),
    ):
        conflict = _media_conflict(field_path, candidates, manifest_media)
        if conflict:
            conflicts.append(conflict)
            conflict_fields.add(field_path)
        if candidates and not manifest_media:
            conflicts.append(
                SourceConflict(
                    conflict_id="conflict-%s" % sha256_text(field_path + "|missing-content-hashes")[:16],
                    code="MEDIA_CONTENT_HASH_NOT_FROZEN",
                    field_path=field_path,
                    severity=ConflictSeverity.BLOCKING,
                    state=ConflictState.UNRESOLVED,
                    values=[
                        ConflictValue(
                            source=candidates[0].source,
                            value=[item.url for item in candidates],
                            locator="adapter:%s/%s" % (candidates[0].source.value, field_path),
                        ),
                        ConflictValue(
                            source=EvidenceSource.MEDIA_MANIFEST,
                            value="ABSENT",
                            locator="bundle.json#/files",
                        ),
                    ],
                    blocked_output_ids=BLOCKED_OUTPUTS[field_path],
                    rationale="media URLs lack required content hashes and exclusions",
                )
            )

    facts: List[AtomicFact] = []
    for candidate in sorted(all_candidates, key=lambda item: (item.field_path, item.source.value, item.locator)):
        conflicted = candidate.field_path in conflict_fields
        physical = candidate.fact_kind == FactKind.ATOMIC_PHYSICAL and not conflicted
        facts.append(
            AtomicFact(
                fact_id="fact-%s" % sha256_text(
                    "%s|%s|%s" % (candidate.field_path, candidate.source.value, candidate.locator)
                )[:16],
                field_path=candidate.field_path,
                value=candidate.value,
                fact_kind=candidate.fact_kind,
                source=candidate.source,
                locator=candidate.locator,
                captured_at=candidate.captured_at,
                scope=candidate.scope,
                conflict_state=FactConflictState.UNRESOLVED if conflicted else FactConflictState.NONE,
                publishable_as_claim=physical,
                usable_as_policy_input=False,
                composer_input_eligible=physical,
                allowed_transform_ids=[],
            )
        )

    sections = _dedupe_models(
        (section for _, result in adapter_results for section in result.sections),
        "section_id",
    )
    sections = sorted(sections, key=lambda section: section.order)
    fit_occurrences = _dedupe_models(
        (item for _, result in adapter_results for item in result.fit_occurrences),
        "occurrence_id",
    )
    source_model_evidence = _dedupe_models(
        (item for _, result in adapter_results for item in result.source_model_evidence),
        "evidence_id",
    )
    colour_relations = _dedupe_models(
        (item for _, result in adapter_results for item in result.colour_relations),
        "relation_id",
    )
    size_guide_table_ids = [
        table.table_id
        for section in sections
        for table in section.tables
        if table.role == SectionRole.SIZE_GUIDE
    ]

    capture_seed = canonical_json_bytes(
        {
            "canonical_url": selected["canonical_url"].value,
            "captured_at": context.captured_at.isoformat(),
            "artifact_hashes": [artifact.sha256 for artifact in context.artifacts],
        }
    )
    return SourceCapture(
        capture_id="capture-%s" % sha256_bytes(capture_seed)[:16],
        requested_url=context.requested_url,
        final_url=context.final_url,
        canonical_url=str(selected["canonical_url"].value),
        captured_at=context.captured_at,
        market=context.market,
        currency=str(selected["currency"].value).upper(),
        consumer_retail_source=context.consumer_retail_source,
        source_class_evidence=context.source_class_evidence,
        artifacts=context.artifacts,
        expected_section_roles=context.expected_section_roles,
        expected_role_absences=context.expected_role_absences,
        title=str(selected["title"].value) if "title" in selected else None,
        vendor=str(selected["vendor"].value) if "vendor" in selected else None,
        current_price=(
            Decimal(str(selected["current_price"].value))
            if "current_price" in selected
            else None
        ),
        compare_at_price=(
            Decimal(str(selected["compare_at_price"].value))
            if "compare_at_price" in selected
            else None
        ),
        facts=facts,
        sections=sections,
        size_guide_table_ids=size_guide_table_ids,
        fit_occurrences=fit_occurrences,
        source_model_evidence=source_model_evidence,
        options=options,
        variants=variants,
        rendered_media=list(rendered_media),
        structured_media=list(structured_media),
        colour_relations=colour_relations,
        conflicts=sorted(conflicts, key=lambda item: (item.field_path, item.conflict_id)),
        acquisition_gaps=context.acquisition_gaps,
        explicit_absences=context.explicit_absences,
    )
