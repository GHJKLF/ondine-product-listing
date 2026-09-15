"""Typed, offline-only Phase 2 composition contracts.

These models deliberately contain no Shopify client, writer, inventory state,
publication action, browser session, or media-generation capability.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


SHA256_PATTERN = r"^[0-9a-f]{64}$"
FACT_ID_PATTERN = r"^fp\.[a-z0-9_.-]+$"
DERIVED_ID_PATTERN = r"^df\.[a-z0-9_.-]+$"
TRANSFORM_ID_PATTERN = r"^[a-z0-9_]+_v[0-9]+$"


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
    )


class FactBinding(StrictModel):
    fact_packet_fact_id: str = Field(pattern=FACT_ID_PATTERN)
    value: Any
    source_fact_or_path: str = Field(min_length=1)
    evidence_locator: str = Field(min_length=1)
    captured_at: datetime
    market: str = Field(pattern=r"^[A-Z]{2}$")
    locale: str = Field(min_length=2)
    scope: str = Field(min_length=1)
    conflict_state: str = Field(min_length=1)
    publishable_as_claim: bool
    usable_as_policy_input: bool
    allowed_transform_ids: List[str]
    unit: Optional[str] = None
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    source_option_name: Optional[str] = Field(default=None, min_length=1)
    source_option_position: Optional[int] = Field(default=None, ge=1, le=3)


class FactPacket(StrictModel):
    manifest_id: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    projection_rule_id: str = Field(min_length=1)
    source_capture_immutable: Literal[True]
    source_capture_sha256: str = Field(pattern=SHA256_PATTERN)
    source_capture_determinism_sha256: str = Field(pattern=SHA256_PATTERN)
    ondine_profile_sha256: str = Field(pattern=SHA256_PATTERN)
    bindings: List[FactBinding]

    @model_validator(mode="after")
    def binding_ids_are_unique(self) -> "FactPacket":
        ids = [binding.fact_packet_fact_id for binding in self.bindings]
        if len(ids) != len(set(ids)):
            raise ValueError("FactPacket binding IDs must be unique")
        return self


class PlanProfile(StrictModel):
    brand: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    inventory_scope: Literal["OUT_OF_SCOPE"]


class EvidencePins(StrictModel):
    # Historical fixture pins; ordinary product runs must not invent oracles.
    aggregate_lock_sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    oracle_sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    source_capture_determinism_sha256: str = Field(pattern=SHA256_PATTERN)
    fixture_role: str = Field(min_length=1)
    market: str = Field(pattern=r"^[A-Z]{2}$")
    locale: str = Field(min_length=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    captured_at: datetime
    source_capture_sha256: str = Field(pattern=SHA256_PATTERN)
    ondine_profile_sha256: str = Field(pattern=SHA256_PATTERN)
    fact_packet_projection_manifest_id: str = Field(min_length=1)
    fact_packet_projection_manifest_sha256: str = Field(pattern=SHA256_PATTERN)


class DerivedFact(StrictModel):
    derived_fact_id: str = Field(pattern=DERIVED_ID_PATTERN)
    value: Any
    transform_id: str = Field(pattern=TRANSFORM_ID_PATTERN)
    input_fact_ref: Optional[str] = None
    input_fact_refs: Optional[List[str]] = None
    input_value: Optional[Any] = None
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    visibility: Optional[str] = None

    @model_validator(mode="after")
    def has_one_input_shape(self) -> "DerivedFact":
        if (self.input_fact_ref is None) == (self.input_fact_refs is None):
            raise ValueError("derived fact requires exactly one input_fact_ref shape")
        return self


class TitleComposition(StrictModel):
    value: str = Field(min_length=1, max_length=150)
    character_count: int = Field(ge=1, le=150)
    authorship_rule_id: str = Field(min_length=1)
    fact_refs: List[str]
    derived_fact_ref: str = Field(pattern=DERIVED_ID_PATTERN)


class PdpOrder(StrictModel):
    buy_box: List[str]
    below_fold: List[str]


class BuyBox(StrictModel):
    colour: Dict[str, Any]
    size_module: Dict[str, Any]
    price: Dict[str, Any]
    primary_action: str = Field(min_length=1)
    length_selector: Optional[Dict[str, Any]] = None
    selectors: Optional[List["AdditionalSelector"]] = None


class AdditionalSelector(StrictModel):
    pdp_order_id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*_selector$")
    option_name: str = Field(min_length=1)
    values: List[str] = Field(min_length=1)
    fact_ref: str = Field(pattern=FACT_ID_PATTERN)
    selector_order: int = Field(ge=2, le=3)


class DescriptionPlan(StrictModel):
    authorship_rule_id: str = Field(min_length=1)
    slots: List[Dict[str, Any]]


class Composition(StrictModel):
    title: TitleComposition
    pdp_order: PdpOrder
    buy_box: BuyBox
    description: DescriptionPlan
    below_fold_sections: List[Dict[str, Any]]


class TargetOption(StrictModel):
    name: str = Field(min_length=1)
    position: int = Field(ge=1, le=3)
    values: List[str]
    fact_ref: str = Field(pattern=FACT_ID_PATTERN)


class TargetVariant(StrictModel):
    option_values: Dict[str, str]
    price: str = Field(pattern=r"^[0-9]+\.[0-9]{2}$")
    sku: str = Field(min_length=1)
    mpn: str = Field(min_length=1)
    weight_grams: Optional[int] = Field(default=None, gt=0)
    combination_fact_ref: str = Field(pattern=FACT_ID_PATTERN)
    price_fact_ref: str = Field(pattern=DERIVED_ID_PATTERN)
    weight_fact_ref: Optional[str] = Field(default=None, pattern=FACT_ID_PATTERN)
    sku_mpn_transform_id: str = Field(min_length=1)
    style_code_ref: str = Field(pattern=DERIVED_ID_PATTERN)
    colour_code_ref: str = Field(pattern=DERIVED_ID_PATTERN)


class SeoPlan(StrictModel):
    handle: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
    canonical_path: str = Field(pattern=r"^/products/[a-z0-9]+(?:-[a-z0-9]+)+$")
    page_title: str = Field(min_length=1)
    page_title_character_count: int = Field(ge=1)
    meta_description: str = Field(min_length=1)
    meta_description_character_count: int = Field(ge=1)
    transform_id: str = Field(min_length=1)
    input_fact_refs: List[str]


class GmcPlan(StrictModel):
    brand: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    condition: Literal["new"]
    google_product_category: str = Field(min_length=1)
    age_group: str = Field(min_length=1)
    gender: str = Field(min_length=1)
    colour: str = Field(min_length=1)
    link_path: str = Field(min_length=1)
    feed_image_binding: None
    fact_refs: Dict[str, str]


class SourceKeyPlan(StrictModel):
    value_ref: Literal["run_state.source_key_sha256"]
    hash_algorithm: Literal["SHA-256"]
    transform_id: Literal["ondine_source_key_v1"]
    input_refs: List[str]
    required_before_first_write: Literal[True]


class InternalTag(StrictModel):
    value: str = Field(pattern=r"^source:[a-z0-9.-]+-[a-z0-9-]+$")
    derived_fact_ref: Literal["df.source_tag"]


class PrivateMetafields(StrictModel):
    managed_by: Literal["product-listing-v2"]
    source_key_ref: Literal["run_state.source_key_sha256"]
    source_url_ref: Literal["fp.canonical_source_url"]


class PrivateOwnership(StrictModel):
    visibility: Literal["PRIVATE_INTERNAL_NOT_CUSTOMER_FACING"]
    canonical_source_identity_ref: Literal["df.canonical_source_identity"]
    canonical_source_identity_sha256: str = Field(pattern=SHA256_PATTERN)
    canonical_source_url_ref: Literal["fp.canonical_source_url"]
    source_key: SourceKeyPlan
    internal_tags: List[InternalTag]
    private_metafields: PrivateMetafields


class ReadBackContract(StrictModel):
    verdict: Literal["DATA_READY_DRAFT"]
    status: Literal["DRAFT"]
    private_ownership: Dict[str, Dict[str, str]]
    target_media: List[Any]
    media_status: Literal["PENDING_APPROVAL"]


class ShopifyTargetState(StrictModel):
    status: Literal["DRAFT"]
    target_kind: Literal["DATA_READY_DRAFT"]
    title: str = Field(min_length=1, max_length=150)
    handle: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    product_type: str = Field(min_length=1)
    content_binding: Dict[str, str]
    options: List[TargetOption]
    variants: List[TargetVariant]
    collections: List[str]
    tags: List[str]
    metafields: Dict[str, str]
    rich_text_metafields: Dict[Literal["fit_details", "fabric_care"], Dict[str, Any]] = Field(default_factory=dict)
    seo: SeoPlan
    gmc: GmcPlan
    target_media: List[Any]
    media_status: Literal["PENDING_APPROVAL"]
    title_ref: str = Field(pattern=DERIVED_ID_PATTERN)
    product_type_fact_ref: str = Field(pattern=FACT_ID_PATTERN)
    option_render_order: List[str]
    identifier_generation: Dict[str, Any]
    tags_transform: Dict[str, Any]
    metafield_fact_refs: Dict[str, List[str]]
    private_ownership: PrivateOwnership
    read_back_contract: ReadBackContract


class MediaPlanSlot(StrictModel):
    slot: str = Field(pattern=r"^(?:01b|0[1-6])$")
    role: str = Field(min_length=1)
    filename: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
    shot_brief: str = Field(min_length=1)
    garment_fact_refs: List[str]
    alt_text: str = Field(min_length=1)
    acceptance: List[str]
    status: Literal["SPEC_ONLY"]


class MediaPlan(StrictModel):
    scope: Literal["PLANNING_ONLY_NOT_SHOPIFY_TARGET"]
    generation_gate: Literal["SLOT_01_SAMPLE_APPROVAL_REQUIRED_BEFORE_SLOTS_02_TO_06", "LEAD_INTERNAL_QA_THEN_SECOND_MODEL_GALLERY_UPLOAD_REVIEW"]
    slots: List[MediaPlanSlot]


class PlanFlag(StrictModel):
    code: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    affects_target_readiness: bool
    reason: Optional[str] = None


class PolicyBlock(StrictModel):
    requested_url: str = Field(min_length=1)
    final_url: str = Field(min_length=1)
    captured_at: datetime
    heading: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_sha256: str = Field(pattern=SHA256_PATTERN)
    policy_binding: str = Field(min_length=1)


class StorePolicySnapshot(StrictModel):
    snapshot_id: str = Field(min_length=1)
    profile_id: Literal["ondine-live-policy-v1"]
    provenance: Literal["SYNTHETIC_TEST_ONLY", "LIVE_STORE_READ_ONLY"]
    test_only: bool
    status: Literal["CURRENT_AT_COMPOSE"]
    verified_at: datetime
    delivery: PolicyBlock
    returns_and_refunds: PolicyBlock
    canonical_sha256: str = Field(pattern=SHA256_PATTERN)


class CopyGuardExemption(StrictModel):
    normalized_span: str = Field(min_length=1)
    whitelist_rule_id: Literal[
        "EXACT_CAPTURED_MATERIAL_NAME",
        "EXACT_CAPTURED_COMPOSITION_VALUE",
        "EXACT_CAPTURED_MEASUREMENT_VALUE",
    ]
    source_field_paths: List[str] = Field(min_length=1)
    target_field_paths: List[str] = Field(min_length=1)


class SharedThreeGram(StrictModel):
    normalized_span: str = Field(min_length=1)
    source_field_paths: List[str] = Field(min_length=1)
    target_field_paths: List[str] = Field(min_length=1)


class SourceOrderLcs(StrictModel):
    source_token_count: int = Field(ge=0)
    target_token_count: int = Field(gt=0)
    lcs_token_count: int = Field(ge=0)
    denominator: Literal["TARGET_TOKEN_COUNT"]
    ratio: float = Field(ge=0, le=1)
    threshold: Literal[0.5]


class CopyGuardResult(StrictModel):
    algorithm_id: Literal["ondine_copy_guard_v1"]
    normalization_version: Literal["ondine_copy_guard_normalization_v1"]
    customer_field_paths: List[str] = Field(min_length=1)
    source_field_paths: List[str] = Field(min_length=1)
    source_media_alt_field_count: int = Field(ge=0)
    source_capture_sha256: str = Field(pattern=SHA256_PATTERN)
    source_corpus_sha256: str = Field(pattern=SHA256_PATTERN)
    target_corpus_sha256: str = Field(pattern=SHA256_PATTERN)
    report_sha256: str = Field(pattern=SHA256_PATTERN)
    non_whitelisted_shared_three_grams: List[SharedThreeGram]
    exemptions: List[CopyGuardExemption]
    forbidden_customer_hits: List[Dict[str, str]]
    source_order_lcs: SourceOrderLcs
    result: Literal["PASS", "FAIL"]


class OriginalityRecord(StrictModel):
    copy_guard_result: CopyGuardResult


class ApprovedTargetModelRecord(StrictModel):
    record_id: str = Field(min_length=1)
    approval_state: Literal["APPROVED"]
    height: str = Field(min_length=1)
    uk_worn_size: str = Field(min_length=1)
    product_binding: str = Field(min_length=1)
    approved_image_binding: str = Field(min_length=1)


class ApprovedSizeMapping(StrictModel):
    record_id: str = Field(min_length=1)
    canonical_source_url: str = Field(min_length=1)
    source_capture_sha256: str = Field(pattern=SHA256_PATTERN)
    labels: Dict[str, str] = Field(min_length=1)
    approval_record_sha256: str = Field(pattern=SHA256_PATTERN)


class SizeMappingApprovalRecord(StrictModel):
    record_id: str = Field(min_length=1)
    canonical_source_url: str = Field(min_length=1)
    source_capture_sha256: str = Field(pattern=SHA256_PATTERN)
    labels: Dict[str, str] = Field(min_length=1)
    approval_state: Literal["APPROVED"]
    approved_by: Literal["Ilias"]
    approved_at: datetime
    decision_text: str = Field(min_length=1)
    approval_source: str = Field(min_length=1)
    provenance: Literal["USER_MESSAGE", "SYNTHETIC_TEST_ONLY"]


class SeasonalColourSelection(StrictModel):
    season: Literal["AUTUMN_WINTER", "SPRING_SUMMER"]
    selected_colours: List[str] = Field(min_length=1)
    reason: str = Field(min_length=1)


class ListingPlan(StrictModel):
    schema_id: str = Field(alias="$schema", min_length=1)
    schema_version: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    example_status: str = Field(min_length=1)
    target_verdict: Literal["DATA_READY_DRAFT"]
    profile: PlanProfile
    evidence: EvidencePins
    fact_packet_projection: FactPacket
    transform_contracts: Dict[str, Dict[str, Any]]
    derived_facts: List[DerivedFact]
    composition: Composition
    shopify_target_state: ShopifyTargetState
    media_plan: MediaPlan = Field(alias="MediaPlan")
    flags: List[PlanFlag]
    originality: OriginalityRecord
    store_policy_snapshot: Optional[StorePolicySnapshot] = None
    approved_target_model_record: Optional[ApprovedTargetModelRecord] = None
    approved_size_mapping: Optional[ApprovedSizeMapping] = None
    seasonal_colour_selection: Optional[SeasonalColourSelection] = None

    @model_validator(mode="after")
    def derived_ids_are_unique(self) -> "ListingPlan":
        ids = [fact.derived_fact_id for fact in self.derived_facts]
        if len(ids) != len(set(ids)):
            raise ValueError("derived fact IDs must be unique")
        return self


class ListingPlanIssue(StrictModel):
    code: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    message: str = Field(min_length=1)
    blocking: bool = True


class ListingPlanValidationReport(StrictModel):
    schema_valid: bool
    committable: bool
    phase_2_lock_sha256: str = Field(pattern=SHA256_PATTERN)
    listing_plan_sha256: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)
    issues: List[ListingPlanIssue]
