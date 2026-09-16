"""Stable adapter output shared by live capture and offline replay."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from product_listing.models import (
    ColourRelation,
    EvidenceSource,
    FactKind,
    FitOccurrence,
    SourceModelEvidence,
    SourceOption,
    SourceSectionBlock,
    SourceVariant,
)


@dataclass(frozen=True)
class FactCandidate:
    field_path: str
    value: Any
    source: EvidenceSource
    locator: str
    captured_at: datetime
    fact_kind: FactKind
    priority: int
    scope: str = "source_product"


@dataclass(frozen=True)
class MediaCandidate:
    url: str
    position: int
    source: EvidenceSource
    locator: str
    colour_relation_id: Optional[str] = None
    exclusion_group_ids: List[str] = field(default_factory=list)
    excluded: bool = False


@dataclass
class AdapterResult:
    candidates: List[FactCandidate] = field(default_factory=list)
    sections: List[SourceSectionBlock] = field(default_factory=list)
    fit_occurrences: List[FitOccurrence] = field(default_factory=list)
    source_model_evidence: List[SourceModelEvidence] = field(default_factory=list)
    options: List[SourceOption] = field(default_factory=list)
    variants: List[SourceVariant] = field(default_factory=list)
    rendered_media: List[MediaCandidate] = field(default_factory=list)
    structured_media: List[MediaCandidate] = field(default_factory=list)
    colour_relations: List[ColourRelation] = field(default_factory=list)

