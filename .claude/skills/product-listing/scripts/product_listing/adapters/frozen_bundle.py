"""Bridge from Scout's signed Gate 0A bundle artifacts to adapter evidence.

This adapter does not define or rewrite Scout's bundle. It consumes the frozen
`bundle.json` contract and maps its normalized evidence into SourceCapture.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List
from urllib.parse import urljoin

from product_listing.adapters.base import AdapterResult, FactCandidate
from product_listing.evidence import sha256_text
from product_listing.models import (
    CaptureStatus,
    ColourRelation,
    ColourRelationType,
    EvidenceSource,
    ExplicitAbsence,
    FactKind,
    FitOccurrence,
    MeasurementBasis,
    MediaOrderKind,
    SectionRole,
    SourceModelEvidence,
    SourceMedia,
    SourceOption,
    SourceSectionBlock,
    SourceSectionContentBlock,
    SourceTable,
    SourceTableCell,
    SourceTableRow,
    SourceVariant,
    VariantOptionValue,
)


MATERIAL_RE = re.compile(r"([A-Za-z][A-Za-z\- ]+?)\s+(\d{1,3}(?:\.\d+)?)%")
MODEL_HEIGHT_RE = re.compile(r"model.*?(\d{3}\s*cm|\d\s*[’']\s*\d{1,2})", re.I)
MODEL_SIZE_RE = re.compile(r"model.*?(?:wears?|wearing).*?((?:UK\s*)?\d{1,2}|[A-Z]{1,3})", re.I)


@dataclass
class FrozenBundleEvidence:
    adapter_result: AdapterResult
    rendered_media: List[SourceMedia]
    structured_media: List[SourceMedia]
    explicit_absences: List[ExplicitAbsence]
    expected_roles: List[SectionRole]


class FrozenBundleAdapter:
    source = EvidenceSource.MANIFEST

    def extract(
        self,
        structured_product: Dict[str, Any],
        sections_payload: Dict[str, Any],
        size_guide_payload: Dict[str, Any],
        media_payload: Dict[str, Any],
        bundle_payload: Dict[str, Any],
        captured_at: datetime,
        base_url: str,
    ) -> FrozenBundleEvidence:
        result = AdapterResult()
        self._structured_product(structured_product, result, captured_at)
        self._sections(sections_payload, result, captured_at)
        self._source_model_evidence(structured_product, result, captured_at)
        self._colour_relations(structured_product, result, base_url)
        self._size_guide(size_guide_payload, result)
        rendered_media = self._media(
            media_payload.get("rendered_gallery") or [],
            MediaOrderKind.RENDERED,
            media_payload.get("colour_association"),
        )
        structured_media = self._media(
            media_payload.get("structured_gallery") or [],
            MediaOrderKind.STRUCTURED,
            media_payload.get("colour_association"),
        )
        explicit_absences = self._absences(bundle_payload, captured_at)

        expected_roles = []
        for section in result.sections:
            if section.role not in expected_roles:
                expected_roles.append(section.role)
        if result.source_model_evidence:
            expected_roles.append(SectionRole.SOURCE_MODEL_EVIDENCE)
        elif any(
            str(raw.get("field") or "").startswith("source_model.")
            for raw in (bundle_payload.get("absences") or [])
        ):
            expected_roles.append(SectionRole.SOURCE_MODEL_EVIDENCE)
        for absence in sections_payload.get("expected_section_absences") or []:
            role = self._section_role(
                str(absence.get("heading") or absence.get("section") or "")
            )
            if role not in expected_roles:
                expected_roles.append(role)
        return FrozenBundleEvidence(
            adapter_result=result,
            rendered_media=rendered_media,
            structured_media=structured_media,
            explicit_absences=explicit_absences,
            expected_roles=expected_roles,
        )

    @staticmethod
    def _structured_product(
        payload: Dict[str, Any],
        result: AdapterResult,
        captured_at: datetime,
    ) -> None:
        mappings = (
            ("title", payload.get("title"), FactKind.IDENTIFIER),
            ("vendor", payload.get("vendor"), FactKind.IDENTIFIER),
            ("currency", payload.get("currency"), FactKind.COMMERCE),
            ("current_price", (payload.get("price") or {}).get("current"), FactKind.COMMERCE),
            ("compare_at_price", (payload.get("price") or {}).get("compare_at"), FactKind.COMMERCE),
            ("composition_percent_total", payload.get("composition_percent_total"), FactKind.ATOMIC_PHYSICAL),
        )
        for field_path, value, kind in mappings:
            if value in (None, ""):
                continue
            if field_path in {"current_price", "compare_at_price"}:
                value = Decimal(str(value))
            result.candidates.append(
                FactCandidate(
                    field_path=field_path,
                    value=value,
                    source=EvidenceSource.MANIFEST,
                    locator="artifact:structured_product#/%s" % field_path,
                    captured_at=captured_at,
                    fact_kind=kind,
                    priority=350,
                )
            )

        options = []
        for position, raw in enumerate(payload.get("options") or [], start=1):
            options.append(
                SourceOption(
                    name=str(raw.get("name") or "Option %s" % position),
                    position=position,
                    values=[str(value) for value in (raw.get("values") or [])],
                )
            )
        result.options = options
        current = Decimal(str((payload.get("price") or {}).get("current")))
        compare_at_raw = (payload.get("price") or {}).get("compare_at")
        compare_at = Decimal(str(compare_at_raw)) if compare_at_raw else None
        for index, combination in enumerate(payload.get("real_variant_combinations") or [], start=1):
            result.variants.append(
                SourceVariant(
                    source_variant_id="combination-%03d" % index,
                    option_values=[
                        VariantOptionValue(option_name=option.name, value=str(value))
                        for option, value in zip(options, combination)
                    ],
                    current_price=current,
                    compare_at_price=compare_at,
                    source_available=None,
                )
            )

    def _sections(
        self,
        payload: Dict[str, Any],
        result: AdapterResult,
        captured_at: datetime,
    ) -> None:
        for raw_section in payload.get("sections") or []:
            order = int(raw_section["order"])
            heading = str(raw_section.get("source_heading") or "Section %s" % order)
            normalized_role = raw_section.get("normalized_role")
            role = (
                SectionRole(str(normalized_role))
                if normalized_role in {item.value for item in SectionRole}
                else self._section_role(heading)
            )
            blocks: List[SourceSectionContentBlock] = []
            raw_parts: List[str] = []
            for block_order, raw_block in enumerate(raw_section.get("blocks") or [], start=1):
                kind = str(raw_block.get("kind") or "other")
                if kind not in {"paragraph", "subheading", "label_value", "bullet", "list", "other"}:
                    kind = "other"
                text = raw_block.get("text")
                label = raw_block.get("label")
                value = raw_block.get("value")
                blocks.append(
                    SourceSectionContentBlock(
                        order=block_order,
                        kind=kind,
                        occurrence=int(raw_block.get("occurrence") or 1),
                        text=str(text) if text is not None else None,
                        label=str(label) if label is not None else None,
                        value=str(value) if value is not None else None,
                    )
                )
                rendered = " ".join(
                    part for part in (str(label or ""), str(value or ""), str(text or "")) if part
                ).strip()
                if rendered:
                    raw_parts.append(rendered)

                label_lower = str(label or "").lower()
                if label_lower.startswith("fit") and value:
                    result.fit_occurrences.append(
                        FitOccurrence(
                            occurrence_id="fit-%s" % sha256_text(
                                "%s|%s|%s" % (order, block_order, value)
                            )[:16],
                            occurrence_type="FIT_TEXT",
                            raw_text=rendered,
                            normalized_value=str(value),
                            locator="artifact:sections#/sections/%s/blocks/%s" % (order - 1, block_order - 1),
                            section_id="section-%s" % order,
                            captured_at=captured_at,
                        )
                    )
                if label_lower.startswith("length") and value:
                    result.fit_occurrences.append(
                        FitOccurrence(
                            occurrence_id="fit-%s" % sha256_text(
                                "%s|%s|%s" % (order, block_order, value)
                            )[:16],
                            occurrence_type="GARMENT_LENGTH",
                            raw_text=rendered,
                            normalized_value=str(value),
                            locator="artifact:sections#/sections/%s/blocks/%s" % (order - 1, block_order - 1),
                            section_id="section-%s" % order,
                            captured_at=captured_at,
                        )
                    )
                if label_lower.startswith(("composition", "fabric")) and value:
                    result.candidates.append(
                        FactCandidate(
                            field_path="material_composition",
                            value={"raw_source_value": str(value)},
                            source=EvidenceSource.RENDERED_DOM,
                            locator="artifact:sections#/sections/%s/blocks/%s" % (order - 1, block_order - 1),
                            captured_at=captured_at,
                            fact_kind=FactKind.ATOMIC_PHYSICAL,
                            priority=350,
                        )
                    )

                for occurrence_type, pattern in (
                    ("MODEL_HEIGHT", MODEL_HEIGHT_RE),
                    ("MODEL_SIZE", MODEL_SIZE_RE),
                ):
                    for match_index, match in enumerate(pattern.finditer(rendered), start=1):
                        normalized = " ".join(match.group(1).split())
                        result.fit_occurrences.append(
                            FitOccurrence(
                                occurrence_id="fit-%s" % sha256_text(
                                    "%s|%s|%s|%s" % (
                                        order,
                                        block_order,
                                        occurrence_type,
                                        match_index,
                                    )
                                )[:16],
                                occurrence_type=occurrence_type,
                                raw_text=match.group(0),
                                normalized_value=normalized,
                                locator="artifact:sections#/sections/%s/blocks/%s" % (
                                    order - 1,
                                    block_order - 1,
                                ),
                                section_id="section-%s" % order,
                                captured_at=captured_at,
                            )
                        )

            raw_text = " ".join(raw_parts)
            result.sections.append(
                SourceSectionBlock(
                    section_id="section-%s" % order,
                    order=order,
                    role=role,
                    heading=heading,
                    raw_text=raw_text,
                    raw_text_sha256=sha256_text(raw_text),
                    locator="artifact:sections#/sections/%s" % (order - 1),
                    blocks=blocks,
                    tables=[],
                    composer_input_eligible=False,
                )
            )

    @staticmethod
    def _source_model_evidence(
        payload: Dict[str, Any],
        result: AdapterResult,
        captured_at: datetime,
    ) -> None:
        source_model = payload.get("source_model") or {}
        height = source_model.get("height")
        size = source_model.get("worn_size") or source_model.get("size_worn")
        wearing_length = source_model.get("wearing_length")
        for occurrence_type, value, field in (
            ("MODEL_HEIGHT", height, "height"),
            ("MODEL_SIZE", size, "worn_size"),
            ("GARMENT_LENGTH", wearing_length, "wearing_length"),
        ):
            if value in (None, ""):
                continue
            if any(
                item.occurrence_type == occurrence_type and item.normalized_value == str(value)
                for item in result.fit_occurrences
            ):
                continue
            result.fit_occurrences.append(
                FitOccurrence(
                    occurrence_id="fit-%s" % sha256_text("source_model|%s|%s" % (field, value))[:16],
                    occurrence_type=occurrence_type,
                    raw_text=str(value),
                    normalized_value=str(value),
                    locator="artifact:structured_product#/source_model/%s" % field,
                    captured_at=captured_at,
                )
            )
        model_occurrences = [
            item
            for item in result.fit_occurrences
            if item.occurrence_type in {"MODEL_HEIGHT", "MODEL_SIZE", "GARMENT_LENGTH"}
        ]
        if not model_occurrences:
            return
        heights = [item for item in model_occurrences if item.occurrence_type == "MODEL_HEIGHT"]
        sizes = [item for item in model_occurrences if item.occurrence_type == "MODEL_SIZE"]
        result.source_model_evidence.append(
            SourceModelEvidence(
                evidence_id="model-%s" % sha256_text(
                    "|".join(item.occurrence_id for item in model_occurrences)
                )[:16],
                occurrence_ids=[item.occurrence_id for item in model_occurrences],
                model_height=heights[0].normalized_value if heights else None,
                size_worn=sizes[0].normalized_value if sizes else None,
                source_line=(
                    str(source_model.get("source_line"))
                    if source_model.get("source_line") not in (None, "")
                    else None
                ),
                wearing_length=(
                    str(wearing_length) if wearing_length not in (None, "") else None
                ),
                scope="COMPETITOR_ONLY",
                target_fit_note_eligible=False,
            )
        )

    @staticmethod
    def _colour_relations(
        payload: Dict[str, Any],
        result: AdapterResult,
        base_url: str,
    ) -> None:
        source_colour = payload.get("colour")
        for index, raw in enumerate(payload.get("colour_relations") or []):
            relation_type = ColourRelationType(str(raw.get("relation")))
            path = raw.get("path") or raw.get("url")
            linked_url = urljoin(base_url, str(path)) if path else None
            colour_value = str(
                raw.get("colour")
                or source_colour
                or raw.get("title")
                or raw.get("product_id")
                or "Unspecified source colour"
            )
            result.colour_relations.append(
                ColourRelation(
                    relation_id="colour-%s" % sha256_text(
                        linked_url or "%s|%s" % (relation_type.value, colour_value)
                    )[:16],
                    relation_type=relation_type,
                    colour_value=colour_value,
                    linked_url=linked_url,
                    capture_status=(
                        CaptureStatus.CAPTURED
                        if bool(raw.get("complete"))
                        else CaptureStatus.UNOPENED
                    ),
                    locator="artifact:structured_product#/colour_relations/%s" % index,
                )
            )

    @staticmethod
    def _size_guide(payload: Dict[str, Any], result: AdapterResult) -> None:
        if not payload.get("tables"):
            return
        section_order = len(result.sections) + 1
        tables: List[SourceTable] = []
        footnotes = [str(value) for value in (payload.get("footnotes") or [])]
        basis = MeasurementBasis(
            str(payload.get("measurement_basis") or payload.get("basis") or "UNSTATED")
        )
        basis_evidence = str(
            payload.get("basis_evidence")
            or payload.get("name")
            or "source did not state a measurement basis"
        )
        for raw_table in payload.get("tables") or []:
            matrix = raw_table.get("cells") or raw_table.get("rows") or []
            def cell_text(cell: Dict[str, Any]) -> str:
                return str(cell.get("text") if "text" in cell else cell.get("value") or "")

            headings = [cell_text(cell) for cell in matrix[0]] if matrix else []
            rows: List[SourceTableRow] = []
            for row_index, raw_row in enumerate(matrix):
                cells = [
                    SourceTableCell(
                        row_index=row_index,
                        column_index=column_index,
                        source_column=int(cell.get("source_column") or column_index + 1),
                        tag=str(
                            cell.get("tag")
                            or ("th" if cell.get("type") == "header" else "td")
                        ),
                        rowspan=int(cell.get("rowspan") or 1),
                        colspan=int(cell.get("colspan") or 1),
                        raw_text=cell_text(cell),
                        normalized_text=cell_text(cell),
                        unit=(
                            str(cell.get("unitType"))
                            if cell.get("unitType") not in (None, "", "string")
                            else str(raw_table.get("unit")) if raw_table.get("unit") else None
                        ),
                    )
                    for column_index, cell in enumerate(raw_row)
                ]
                rows.append(
                    SourceTableRow(
                        order=row_index + 1,
                        label=cells[0].raw_text if cells else None,
                        cells=cells,
                    )
                )
            table_order = int(raw_table.get("order") or len(tables) + 1)
            table_footnotes = [str(value) for value in (raw_table.get("footnotes") or footnotes)]
            units = sorted(
                {
                    cell.unit
                    for row in rows
                    for cell in row.cells
                    if cell.unit
                }
            )
            tables.append(
                SourceTable(
                    table_id=str(raw_table.get("id") or "size-guide-table-%s" % table_order),
                    order=table_order,
                    role=SectionRole.SIZE_GUIDE,
                    headings=headings,
                    units=units or ([str(raw_table.get("unit"))] if raw_table.get("unit") else []),
                    rows=rows,
                    footnotes=table_footnotes,
                    measurement_basis=basis,
                    measurement_basis_evidence=basis_evidence,
                    locator="artifact:size_guide#/tables/%s" % (table_order - 1),
                )
            )
        raw_text = " | ".join(
            "%s: %s rows" % (table.units[0] if table.units else "unit unstated", len(table.rows))
            for table in tables
        )
        result.sections.append(
            SourceSectionBlock(
                section_id="section-size-guide",
                order=section_order,
                role=SectionRole.SIZE_GUIDE,
                heading="Size Guide",
                raw_text=raw_text,
                raw_text_sha256=sha256_text(raw_text),
                locator="artifact:size_guide#/tables",
                blocks=[],
                tables=tables,
                composer_input_eligible=False,
            )
        )

    @staticmethod
    def _media(
        items: List[Dict[str, Any]],
        order_kind: MediaOrderKind,
        colour_association: Any,
    ) -> List[SourceMedia]:
        result = []
        for item in items:
            position = int(item["order"])
            url = str(item["url"])
            result.append(
                SourceMedia(
                    media_id=str(
                        item.get("media_id")
                        or "%s-%03d" % (order_kind.value.lower(), position)
                    ),
                    order_kind=order_kind,
                    position=position,
                    url=url,
                    url_sha256=sha256_text(url),
                    content_sha256=str(item["content_sha256"]),
                    source_media_id=(
                        str(item.get("media_id")) if item.get("media_id") not in (None, "") else None
                    ),
                    byte_count=(int(item["bytes"]) if item.get("bytes") is not None else None),
                    width=(int(item["width"]) if item.get("width") is not None else None),
                    height=(int(item["height"]) if item.get("height") is not None else None),
                    colour_association=(
                        str(item.get("colour_association") or colour_association)
                        if (item.get("colour_association") or colour_association) not in (None, "")
                        else None
                    ),
                    exclusion_group_ids=[
                        str(value) for value in (item.get("exclusion_group_ids") or [])
                    ],
                    excluded=bool(item.get("excluded", False)),
                )
            )
        return result

    @staticmethod
    def _absences(bundle_payload: Dict[str, Any], captured_at: datetime) -> List[ExplicitAbsence]:
        absences = []
        for index, raw in enumerate(bundle_payload.get("absences") or [], start=1):
            field_path = str(
                raw.get("field")
                or ("section:%s" % raw.get("section") if raw.get("section") else "unknown")
            )
            absences.append(
                ExplicitAbsence(
                    absence_id="absence-%s" % sha256_text(field_path)[:16],
                    field_path=field_path,
                    reason="; ".join(
                        str(value)
                        for value in (raw.get("status"), raw.get("basis"))
                        if value not in (None, "")
                    ) or "proven absent",
                    locator="bundle.json#/absences/%s" % (index - 1),
                    captured_at=captured_at,
                )
            )
        return absences

    @staticmethod
    def _section_role(heading: str) -> SectionRole:
        lowered = heading.lower()
        if "retailer_policy_evidence_only" in lowered:
            return SectionRole.RETAILER_POLICY_EVIDENCE_ONLY
        if "composition_and_care" in lowered:
            return SectionRole.COMPOSITION_AND_CARE
        if lowered.strip() == "details":
            return SectionRole.DETAILS
        if "detail" in lowered and "fit" in lowered:
            return SectionRole.DETAILS_AND_FIT
        if "description" in lowered:
            return SectionRole.DESCRIPTION
        if "detail" in lowered and "care" in lowered:
            return SectionRole.DETAILS_CARE
        if "sustainab" in lowered:
            return SectionRole.SUSTAINABILITY
        if "size guide" in lowered or "size chart" in lowered:
            return SectionRole.SIZE_GUIDE
        if "material" in lowered or "fabric" in lowered:
            return SectionRole.MATERIALS_PROVENANCE
        if "fit" in lowered:
            return SectionRole.SIZE_FIT
        if "deliver" in lowered:
            return SectionRole.DELIVERY
        if "return" in lowered:
            return SectionRole.RETURNS
        return SectionRole.OTHER
