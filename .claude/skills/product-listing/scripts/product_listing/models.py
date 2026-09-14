"""Typed Phase 1 contracts.

SourceCapture is evidence-only. It deliberately has no Shopify target state,
inventory, Ondine composition, Higgsfield record, or publication concept.
"""

import re
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCHEMA_VERSION = "1.0.0"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_ONLY_ELIGIBILITY_KEYS = {"target_fit_note_eligible", "target_composer_eligible"}
EVIDENCE_ONLY_ELIGIBILITY_COMPACT = {
    key.replace("_", "") for key in EVIDENCE_ONLY_ELIGIBILITY_KEYS
}
FORBIDDEN_STATE_TOKENS = frozenset({"target", "inventory", "higgsfield"})
FORBIDDEN_COMPACT_FAMILIES = ("target", "inventory", "mediaplan", "higgsfield")
MODEL_STATE_OWNERS = ("composed", "ondine")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class EvidenceSource(str, Enum):
    MANIFEST = "MANIFEST"
    RENDERED_DOM = "RENDERED_DOM"
    JSON_LD = "JSON_LD"
    SHOPIFY_AJAX = "SHOPIFY_AJAX"
    MEDIA_MANIFEST = "MEDIA_MANIFEST"


class ArtifactKind(str, Enum):
    BUNDLE = "bundle"
    RENDERED_HTML = "rendered_html"
    JSON_LD = "jsonld"
    SHOPIFY_AJAX = "shopify_ajax"
    STRUCTURED_PRODUCT = "structured_product"
    SECTIONS = "sections"
    SIZE_GUIDE = "size_guide"
    MEDIA_MANIFEST = "media_manifest"
    NETWORK_MANIFEST = "network_manifest"
    EVIDENCE_REGISTRY = "evidence_registry"
    CART_CURRENCY = "cart_currency"
    SIZE_GUIDE_PROVIDER = "size_guide_provider"
    MEDIA_CONTENT_HASHES = "media_content_hashes"
    PROVENANCE_SCRIPT = "provenance_script"


class SectionRole(str, Enum):
    DESCRIPTION = "DESCRIPTION"
    DESCRIPTION_AND_FIT = "DESCRIPTION_AND_FIT"
    DETAILS_AND_FIT = "DETAILS_AND_FIT"
    DETAILS_CARE = "DETAILS_CARE"
    DETAILS = "DETAILS"
    COMPOSITION_AND_CARE = "COMPOSITION_AND_CARE"
    RETAILER_POLICY_EVIDENCE_ONLY = "RETAILER_POLICY_EVIDENCE_ONLY"
    SIZE_FIT = "SIZE_FIT"
    SIZE_GUIDE = "SIZE_GUIDE"
    MATERIALS_PROVENANCE = "MATERIALS_PROVENANCE"
    DELIVERY = "DELIVERY"
    RETURNS = "RETURNS"
    SOURCE_MODEL_EVIDENCE = "SOURCE_MODEL_EVIDENCE"
    SUSTAINABILITY = "SUSTAINABILITY"
    OTHER = "OTHER"


class MeasurementBasis(str, Enum):
    BODY = "BODY"
    GARMENT = "GARMENT"
    MIXED = "MIXED"
    UNSTATED = "UNSTATED"


class FactKind(str, Enum):
    ATOMIC_PHYSICAL = "ATOMIC_PHYSICAL"
    COMMERCE = "COMMERCE"
    IDENTIFIER = "IDENTIFIER"
    RELATION = "RELATION"
    SOURCE_PROSE = "SOURCE_PROSE"


class FactConflictState(str, Enum):
    NONE = "NONE"
    UNRESOLVED = "UNRESOLVED"
    RESOLVED = "RESOLVED"


class ConflictSeverity(str, Enum):
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"


class ConflictState(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    RESOLVED = "RESOLVED"


class GapSeverity(str, Enum):
    BLOCKING = "BLOCKING"
    NONCRITICAL_FOR_STRUCTURE = "NONCRITICAL_FOR_STRUCTURE"
    EXPECTED_INCOMPLETE_RELATION = "EXPECTED_INCOMPLETE_RELATION"
    PROVEN_ABSENCE = "PROVEN_ABSENCE"
    SECURITY_REDACTION = "SECURITY_REDACTION"


class ColourRelationType(str, Enum):
    IN_PRODUCT_OPTION = "IN_PRODUCT_OPTION"
    LINKED_SIBLING_PDP = "LINKED_SIBLING_PDP"
    SELF_ONLY_SINGLE_COLOUR = "SELF_ONLY_SINGLE_COLOUR"


class CaptureStatus(str, Enum):
    CAPTURED = "CAPTURED"
    UNOPENED = "UNOPENED"


class MediaOrderKind(str, Enum):
    RENDERED = "RENDERED"
    STRUCTURED = "STRUCTURED"


def _validate_http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("must be an absolute HTTP(S) URL")
    return value


def _validate_sha256(value: str) -> str:
    if not SHA256_PATTERN.fullmatch(value):
        raise ValueError("must be a lowercase SHA-256 hex digest")
    return value


def _canonical_semantic_key(key: Any) -> str:
    separated = re.sub(r"[^0-9A-Za-z]+", "_", str(key).strip())
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", separated)
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return re.sub(r"_+", "_", separated).strip("_").lower()


def _is_forbidden_semantic_path(path: str) -> bool:
    tokens = tuple(part for part in path.split("_") if part)
    compact = "".join(tokens)
    if FORBIDDEN_STATE_TOKENS.intersection(tokens):
        return True
    if any(family in compact for family in FORBIDDEN_COMPACT_FAMILIES):
        return True
    return "model" in compact and any(owner in compact for owner in MODEL_STATE_OWNERS)


def _reject_target_keys(
    value: Any,
    path: str = "$",
    semantic_ancestors: tuple[str, ...] = (),
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = _canonical_semantic_key(key)
            compact = normalized.replace("_", "")
            semantic_path = semantic_ancestors + (normalized,)
            if compact in EVIDENCE_ONLY_ELIGIBILITY_COMPACT:
                if not isinstance(child, bool):
                    raise ValueError("source eligibility metadata must be boolean at %s.%s" % (path, key))
                if compact == "targetfitnoteeligible" and child:
                    raise ValueError("competitor fit evidence cannot target a live fit note at %s.%s" % (path, key))
            elif _is_forbidden_semantic_path(normalized) or _is_forbidden_semantic_path(
                "_".join(semantic_path)
            ):
                raise ValueError("forbidden target/inventory key at %s.%s" % (path, key))
            _reject_target_keys(child, "%s.%s" % (path, key), semantic_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_target_keys(child, "%s[%s]" % (path, index), semantic_ancestors)


class SourceArtifact(StrictModel):
    artifact_id: str = Field(min_length=1)
    kind: ArtifactKind
    relative_path: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    sha256: str

    _sha = field_validator("sha256")(_validate_sha256)


class SourceClassEvidence(StrictModel):
    consumer_retail_source: bool
    locator: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class ExpectedRoleAbsence(StrictModel):
    role: SectionRole
    reason: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    captured_at: datetime


class ExplicitAbsence(StrictModel):
    absence_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    captured_at: datetime


class LockedSourceDenominator(StrictModel):
    """Exact reviewer-owned denominator assembled from signed source artifacts."""

    capture: Dict[str, Any]
    structured_product: Dict[str, Any]
    sections: List[Dict[str, Any]]
    expected_absences: List[Dict[str, Any]]
    media: Dict[str, Any]
    size_guide: Dict[str, Any]
    evidence_only_exclusions: Dict[str, Any]
    conflicts: List[Dict[str, Any]]
    acquisition_gaps: List[Dict[str, Any]]
    status: str = Field(min_length=1)


class SourceTableCell(StrictModel):
    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    source_column: int = Field(ge=1)
    tag: Literal["th", "td"]
    rowspan: int = Field(default=1, ge=1)
    colspan: int = Field(default=1, ge=1)
    raw_text: str
    normalized_text: Optional[str] = None
    unit: Optional[str] = None


class SourceTableRow(StrictModel):
    order: int = Field(ge=1)
    label: Optional[str] = None
    cells: List[SourceTableCell]


class SourceTable(StrictModel):
    table_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    role: SectionRole
    headings: List[str]
    units: List[str]
    rows: List[SourceTableRow]
    footnotes: List[str]
    measurement_basis: MeasurementBasis
    measurement_basis_evidence: str = Field(min_length=1)
    locator: str = Field(min_length=1)

    @model_validator(mode="after")
    def table_rows_are_ordered(self) -> "SourceTable":
        row_orders = [row.order for row in self.rows]
        if row_orders != list(range(1, len(row_orders) + 1)):
            raise ValueError("table row order must be contiguous from 1")
        return self


class SourceSectionContentBlock(StrictModel):
    order: int = Field(ge=1)
    kind: Literal["paragraph", "subheading", "label_value", "bullet", "list", "other"]
    occurrence: int = Field(ge=1)
    text: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None


class SourceSectionBlock(StrictModel):
    section_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    role: SectionRole
    heading: str = Field(min_length=1)
    raw_text: str
    raw_text_sha256: str
    locator: str = Field(min_length=1)
    blocks: List[SourceSectionContentBlock]
    tables: List[SourceTable]
    composer_input_eligible: Literal[False] = False

    _sha = field_validator("raw_text_sha256")(_validate_sha256)

    @model_validator(mode="after")
    def section_children_are_ordered(self) -> "SourceSectionBlock":
        block_orders = [block.order for block in self.blocks]
        table_orders = [table.order for table in self.tables]
        if block_orders != list(range(1, len(block_orders) + 1)):
            raise ValueError("section block order must be contiguous from 1")
        if table_orders != list(range(1, len(table_orders) + 1)):
            raise ValueError("section table order must be contiguous from 1")
        return self


class FitOccurrence(StrictModel):
    occurrence_id: str = Field(min_length=1)
    occurrence_type: Literal["MODEL_HEIGHT", "MODEL_SIZE", "GARMENT_LENGTH", "FIT_TEXT"]
    raw_text: str = Field(min_length=1)
    normalized_value: Optional[str] = None
    unit: Optional[str] = None
    locator: str = Field(min_length=1)
    section_id: Optional[str] = None
    captured_at: datetime


class SourceModelEvidence(StrictModel):
    evidence_id: str = Field(min_length=1)
    occurrence_ids: List[str]
    model_height: Optional[str] = None
    size_worn: Optional[str] = None
    source_line: Optional[str] = None
    wearing_length: Optional[str] = None
    scope: Literal["COMPETITOR_ONLY"] = "COMPETITOR_ONLY"
    target_fit_note_eligible: Literal[False] = False


class SourceMedia(StrictModel):
    media_id: str = Field(min_length=1)
    order_kind: MediaOrderKind
    position: int = Field(ge=1)
    url: str
    url_sha256: str
    content_sha256: str
    media_type: Literal["IMAGE", "VIDEO", "OTHER"] = "IMAGE"
    source_media_id: Optional[str] = None
    byte_count: Optional[int] = Field(default=None, ge=0)
    width: Optional[int] = Field(default=None, gt=0)
    height: Optional[int] = Field(default=None, gt=0)
    colour_association: Optional[str] = None
    colour_relation_id: Optional[str] = None
    exclusion_group_ids: List[str]
    excluded: bool = False

    _url = field_validator("url")(_validate_http_url)
    _url_sha = field_validator("url_sha256")(_validate_sha256)
    _content_sha = field_validator("content_sha256")(_validate_sha256)


class ColourRelation(StrictModel):
    relation_id: str = Field(min_length=1)
    relation_type: ColourRelationType
    colour_value: str = Field(min_length=1)
    linked_url: Optional[str] = None
    capture_status: CaptureStatus
    locator: str = Field(min_length=1)

    @field_validator("linked_url")
    @classmethod
    def validate_linked_url(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            return _validate_http_url(value)
        return value


class SourceOption(StrictModel):
    name: str = Field(min_length=1)
    # Capture the exact source even when Shopify's three-option limit is
    # exceeded; critical-stop validation owns the fail-closed decision.
    position: int = Field(ge=1)
    values: List[str] = Field(min_length=1)


class VariantOptionValue(StrictModel):
    option_name: str = Field(min_length=1)
    value: str = Field(min_length=1)


class SourceVariant(StrictModel):
    source_variant_id: str = Field(min_length=1)
    title: Optional[str] = None
    option_values: List[VariantOptionValue]
    current_price: Decimal = Field(gt=0)
    compare_at_price: Optional[Decimal] = Field(default=None, gt=0)
    source_available: Optional[bool] = None
    source_sku: Optional[str] = None
    source_barcode: Optional[str] = None
    source_weight_grams: Optional[int] = Field(default=None, ge=0)


class AtomicFact(StrictModel):
    fact_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    value: Any
    fact_kind: FactKind
    source: EvidenceSource
    locator: str = Field(min_length=1)
    captured_at: datetime
    scope: str = Field(min_length=1)
    conflict_state: FactConflictState = FactConflictState.NONE
    publishable_as_claim: bool = False
    usable_as_policy_input: bool = False
    composer_input_eligible: bool = False
    allowed_transform_ids: List[str]
    reviewer_id: Optional[str] = None
    transform_id: Optional[str] = None

    @model_validator(mode="after")
    def source_prose_is_evidence_only(self) -> "AtomicFact":
        if self.fact_kind == FactKind.SOURCE_PROSE and (
            self.publishable_as_claim
            or self.usable_as_policy_input
            or self.composer_input_eligible
            or self.allowed_transform_ids
        ):
            raise ValueError("source prose cannot be a claim, policy, transform, or composer input")
        if self.field_path.lower().startswith(("target.", "inventory.")):
            raise ValueError("target and inventory facts are forbidden in SourceCapture")
        return self


class ConflictValue(StrictModel):
    source: EvidenceSource
    value: Any
    locator: str = Field(min_length=1)


class SourceConflict(StrictModel):
    conflict_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    severity: ConflictSeverity
    state: ConflictState
    values: List[ConflictValue] = Field(min_length=2)
    blocked_output_ids: List[str]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def blocking_conflict_names_outputs(self) -> "SourceConflict":
        if (
            self.severity == ConflictSeverity.BLOCKING
            and self.state == ConflictState.UNRESOLVED
            and not self.blocked_output_ids
        ):
            raise ValueError("unresolved blocking conflicts require blocked_output_ids")
        return self


class SourceAcquisitionGap(StrictModel):
    code: str = Field(min_length=1)
    severity: GapSeverity
    detail: Optional[str] = None
    replacement: Optional[str] = None


class ValidationIssue(StrictModel):
    code: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    message: str = Field(min_length=1)
    blocking: bool = True


class SourceCapture(StrictModel):
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    capture_id: str = Field(min_length=1)
    requested_url: str
    final_url: str
    canonical_url: str
    captured_at: datetime
    market: str = Field(pattern=r"^[A-Z]{2}$")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    locale: Optional[str] = None
    capture_attempt: Optional[int] = Field(default=None, ge=1)
    rendered_capture: Optional[Dict[str, Any]] = None
    json_ld_capture: Optional[Dict[str, Any]] = None
    same_session_commerce: Optional[Dict[str, Any]] = None
    consumer_retail_source: bool
    source_class_evidence: SourceClassEvidence
    artifacts: List[SourceArtifact] = Field(min_length=1)
    expected_section_roles: List[SectionRole]
    expected_role_absences: List[ExpectedRoleAbsence]
    title: Optional[str] = None
    vendor: Optional[str] = None
    current_price: Optional[Decimal] = Field(default=None, gt=0)
    compare_at_price: Optional[Decimal] = Field(default=None, gt=0)
    facts: List[AtomicFact]
    sections: List[SourceSectionBlock]
    size_guide_table_ids: List[str]
    fit_occurrences: List[FitOccurrence]
    source_model_evidence: List[SourceModelEvidence]
    options: List[SourceOption]
    variants: List[SourceVariant]
    rendered_media: List[SourceMedia]
    structured_media: List[SourceMedia]
    colour_relations: List[ColourRelation]
    conflicts: List[SourceConflict]
    acquisition_gaps: List[SourceAcquisitionGap]
    explicit_absences: List[ExplicitAbsence]
    structured_product_evidence: Optional[Dict[str, Any]] = None
    size_guide_evidence: Optional[Dict[str, Any]] = None
    media_manifest_evidence: Optional[Dict[str, Any]] = None
    evidence_only_exclusions: Optional[Dict[str, Any]] = None
    media_orders_match: Optional[bool] = None
    media_gallery_count: Optional[int] = Field(default=None, ge=0)
    media_exclusions: List[Dict[str, Any]] = Field(default_factory=list)
    locked_denominator: Optional[LockedSourceDenominator] = None

    @model_validator(mode="before")
    @classmethod
    def source_contract_has_no_target_state(cls, value: Any) -> Any:
        _reject_target_keys(value)
        return value

    @field_validator("requested_url", "final_url", "canonical_url")
    @classmethod
    def validate_urls(cls, value: str) -> str:
        return _validate_http_url(value)

    @model_validator(mode="after")
    def ordered_collections_are_well_formed(self) -> "SourceCapture":
        section_orders = [section.order for section in self.sections]
        if section_orders != sorted(section_orders) or len(section_orders) != len(set(section_orders)):
            raise ValueError("sections must have unique ascending order values")
        for collection_name, media in (
            ("rendered_media", self.rendered_media),
            ("structured_media", self.structured_media),
        ):
            positions = [item.position for item in media]
            if positions != list(range(1, len(positions) + 1)):
                raise ValueError("%s positions must be contiguous from 1" % collection_name)
        table_ids = {
            table.table_id
            for section in self.sections
            for table in section.tables
        }
        if any(table_id not in table_ids for table_id in self.size_guide_table_ids):
            raise ValueError("size_guide_table_ids must reference captured section tables")
        return self


class ReplayResult(StrictModel):
    source_capture: SourceCapture
    determinism_sha256: str
    valid: bool
    issues: List[ValidationIssue]

    _sha = field_validator("determinism_sha256")(_validate_sha256)
