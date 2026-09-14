"""Rendered DOM and JSON-LD evidence extraction.

The adapter keeps source prose as evidence-only section text. It extracts only
small atomic facts (prices, material composition, model height/size) for later
reconciliation; raw competitor sentences are never composer-eligible.
"""

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin

from lxml import html as lxml_html
from lxml.html import HtmlElement

from product_listing.adapters.base import AdapterResult, FactCandidate, MediaCandidate
from product_listing.evidence import sha256_text
from product_listing.models import (
    CaptureStatus,
    ColourRelation,
    ColourRelationType,
    EvidenceSource,
    FactKind,
    FitOccurrence,
    MeasurementBasis,
    SectionRole,
    SourceModelEvidence,
    SourceOption,
    SourceSectionBlock,
    SourceSectionContentBlock,
    SourceTable,
    SourceTableCell,
    SourceTableRow,
    SourceVariant,
    VariantOptionValue,
)


SPACE_RE = re.compile(r"\s+")
PERCENT_MATERIAL_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%\s*([A-Za-z][A-Za-z\- ]{1,50})", re.I)
HEIGHT_RE = re.compile(
    r"(?:model(?:'s)?\s+(?:height\s*(?:is|:)?|is)|height\s*:?)\s*"
    r"((?:\d{3}\s*cm)|(?:\d\s*[’']\s*\d{1,2}(?:\s*(?:in|\"))?))",
    re.I,
)
SIZE_RE = re.compile(
    r"(?:model\s+)?(?:wears?|wearing|size\s*worn\s*:?)\s*(?:a\s+)?((?:UK\s*)?\d{1,2}|[A-Z]{1,3})",
    re.I,
)
GARMENT_LENGTH_RE = re.compile(r"(?:garment\s+)?length\s*:?[ ]*(\d+(?:\.\d+)?\s*(?:cm|in|inches))", re.I)


def _text(node: HtmlElement) -> str:
    return SPACE_RE.sub(" ", " ".join(node.itertext())).strip()


def _role(heading: str) -> SectionRole:
    normalized = heading.lower()
    if "detail" in normalized and "fit" in normalized:
        return SectionRole.DETAILS_AND_FIT
    if "size guide" in normalized or "size chart" in normalized:
        return SectionRole.SIZE_GUIDE
    if "size" in normalized and "fit" in normalized:
        return SectionRole.SIZE_FIT
    if "care" in normalized or "detail" in normalized:
        return SectionRole.DETAILS_CARE
    if any(word in normalized for word in ("material", "fabric", "composition", "sustainab", "provenance")):
        return SectionRole.MATERIALS_PROVENANCE
    if "deliver" in normalized or "shipping" in normalized:
        return SectionRole.DELIVERY
    if "return" in normalized or "refund" in normalized:
        return SectionRole.RETURNS
    if "description" in normalized or "about" in normalized:
        return SectionRole.DESCRIPTION
    return SectionRole.OTHER


def _basis(text: str) -> MeasurementBasis:
    lowered = text.lower()
    has_body = "body measurement" in lowered or "measure your body" in lowered
    has_garment = "garment measurement" in lowered or "laid flat" in lowered
    if has_body and has_garment:
        return MeasurementBasis.MIXED
    if has_body:
        return MeasurementBasis.BODY
    if has_garment:
        return MeasurementBasis.GARMENT
    return MeasurementBasis.UNSTATED


def _decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation:
        return None


def _jsonld_nodes(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from _jsonld_nodes(item)
    elif isinstance(value, dict):
        graph = value.get("@graph")
        if graph is not None:
            yield from _jsonld_nodes(graph)
        yield value


def _is_product(node: Dict[str, Any]) -> bool:
    node_type = node.get("@type")
    types = node_type if isinstance(node_type, list) else [node_type]
    return any(value in {"Product", "ProductGroup"} for value in types)


class JsonLdDomAdapter:
    source = EvidenceSource.RENDERED_DOM

    def extract_html(
        self,
        html: str,
        captured_at: datetime,
        artifact_id: str,
        base_url: str,
    ) -> AdapterResult:
        soup = lxml_html.fromstring(html, base_url=base_url)
        result = AdapterResult()
        locator = "artifact:%s" % artifact_id

        canonical_nodes = soup.xpath(
            "//link[contains(concat(' ', normalize-space(@rel), ' '), ' canonical ')][@href]"
        )
        canonical = canonical_nodes[0] if canonical_nodes else None
        if canonical is not None and canonical.get("href"):
            result.candidates.append(
                FactCandidate(
                    field_path="canonical_url",
                    value=urljoin(base_url, str(canonical.get("href"))),
                    source=self.source,
                    locator="%s#link[rel=canonical]" % locator,
                    captured_at=captured_at,
                    fact_kind=FactKind.IDENTIFIER,
                    priority=300,
                )
            )

        title_nodes = soup.xpath("(//main//h1 | //article//h1 | //h1)[1]")
        title_node = title_nodes[0] if title_nodes else None
        if title_node is not None and _text(title_node):
            result.candidates.append(
                FactCandidate(
                    field_path="title",
                    value=_text(title_node),
                    source=self.source,
                    locator="%s#h1" % locator,
                    captured_at=captured_at,
                    fact_kind=FactKind.IDENTIFIER,
                    priority=300,
                )
            )

        self._extract_meta(soup, result, captured_at, locator)
        result.sections = self._sections(soup, captured_at, locator)
        self._extract_fit(result, captured_at)
        self._extract_material(result, captured_at)
        self._extract_dom_options(soup, result, locator)
        self._extract_sibling_colours(soup, result, locator, base_url)
        result.rendered_media = self._rendered_media(soup, locator, base_url)

        jsonld_documents: List[Any] = []
        for index, script in enumerate(soup.xpath("//script[@type='application/ld+json']")):
            try:
                jsonld_documents.append(json.loads(script.text or _text(script)))
            except (TypeError, json.JSONDecodeError):
                continue
        if jsonld_documents:
            structured = self.extract_jsonld(
                jsonld_documents,
                captured_at=captured_at,
                artifact_id=artifact_id,
                base_url=base_url,
            )
            self._merge(result, structured)
        return result

    def extract_jsonld(
        self,
        payload: Any,
        captured_at: datetime,
        artifact_id: str,
        base_url: str,
    ) -> AdapterResult:
        result = AdapterResult()
        locator = "artifact:%s" % artifact_id
        products = [node for node in _jsonld_nodes(payload) if _is_product(node)]
        for product_index, product in enumerate(products):
            prefix = "%s#jsonld/product/%s" % (locator, product_index)
            for field_path, key, kind, priority in (
                ("title", "name", FactKind.IDENTIFIER, 100),
                ("source_description", "description", FactKind.SOURCE_PROSE, 50),
                ("material_composition", "material", FactKind.ATOMIC_PHYSICAL, 100),
            ):
                value = product.get(key)
                if value in (None, ""):
                    continue
                if field_path == "material_composition":
                    value = self._material_value(str(value))
                result.candidates.append(
                    FactCandidate(
                        field_path=field_path,
                        value=value,
                        source=EvidenceSource.JSON_LD,
                        locator="%s/%s" % (prefix, key),
                        captured_at=captured_at,
                        fact_kind=kind,
                        priority=priority,
                    )
                )

            brand = product.get("brand")
            if isinstance(brand, dict):
                brand = brand.get("name")
            if brand:
                result.candidates.append(
                    FactCandidate(
                        field_path="vendor",
                        value=str(brand),
                        source=EvidenceSource.JSON_LD,
                        locator="%s/brand" % prefix,
                        captured_at=captured_at,
                        fact_kind=FactKind.IDENTIFIER,
                        priority=100,
                    )
                )

            offers = product.get("offers") or []
            if isinstance(offers, dict):
                offers = [offers]
            for offer_index, offer in enumerate(offers):
                if not isinstance(offer, dict):
                    continue
                price = _decimal(offer.get("price") or offer.get("lowPrice"))
                currency = offer.get("priceCurrency")
                if price is not None:
                    result.candidates.append(
                        FactCandidate(
                            field_path="current_price",
                            value=price,
                            source=EvidenceSource.JSON_LD,
                            locator="%s/offers/%s/price" % (prefix, offer_index),
                            captured_at=captured_at,
                            fact_kind=FactKind.COMMERCE,
                            priority=100,
                        )
                    )
                if currency:
                    result.candidates.append(
                        FactCandidate(
                            field_path="currency",
                            value=str(currency).upper(),
                            source=EvidenceSource.JSON_LD,
                            locator="%s/offers/%s/priceCurrency" % (prefix, offer_index),
                            captured_at=captured_at,
                            fact_kind=FactKind.COMMERCE,
                            priority=100,
                        )
                    )

            images = product.get("image") or []
            if isinstance(images, (str, dict)):
                images = [images]
            for index, image in enumerate(images, start=1):
                if isinstance(image, dict):
                    image = image.get("url") or image.get("contentUrl")
                if not image:
                    continue
                result.structured_media.append(
                    MediaCandidate(
                        url=urljoin(base_url, str(image)),
                        position=len(result.structured_media) + 1,
                        source=EvidenceSource.JSON_LD,
                        locator="%s/image/%s" % (prefix, index - 1),
                    )
                )
            self._jsonld_variants(product, result, prefix)
        return result

    @staticmethod
    def _extract_meta(
        soup: HtmlElement,
        result: AdapterResult,
        captured_at: datetime,
        locator: str,
    ) -> None:
        mappings = {
            "product:price:amount": ("current_price", FactKind.COMMERCE),
            "og:price:amount": ("current_price", FactKind.COMMERCE),
            "product:price:currency": ("currency", FactKind.COMMERCE),
            "og:price:currency": ("currency", FactKind.COMMERCE),
        }
        seen = set()
        for meta in soup.xpath("//meta"):
            key = meta.get("property") or meta.get("name")
            if key not in mappings or key in seen:
                continue
            content = meta.get("content")
            if content in (None, ""):
                continue
            field_path, kind = mappings[key]
            value: Any = str(content).upper() if field_path == "currency" else _decimal(content)
            if value is None:
                continue
            seen.add(key)
            result.candidates.append(
                FactCandidate(
                    field_path=field_path,
                    value=value,
                    source=EvidenceSource.RENDERED_DOM,
                    locator="%s#meta[%s]" % (locator, key),
                    captured_at=captured_at,
                    fact_kind=kind,
                    priority=300,
                )
            )

    def _sections(
        self,
        soup: HtmlElement,
        captured_at: datetime,
        locator: str,
    ) -> List[SourceSectionBlock]:
        roots = soup.xpath("(//main | //article | //body)[1]")
        root = roots[0] if roots else soup
        nodes: List[HtmlElement] = []
        for node in root.xpath(".//details | .//section"):
            if any(parent in nodes for parent in node.iterancestors()):
                continue
            heading_nodes = node.xpath("(.//summary | .//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6)[1]")
            heading_node = heading_nodes[0] if heading_nodes else None
            heading = _text(heading_node) if heading_node is not None else ""
            body = _text(node)
            if not heading or not body:
                continue
            nodes.append(node)

        sections: List[SourceSectionBlock] = []
        for order, node in enumerate(nodes, start=1):
            heading_nodes = node.xpath("(.//summary | .//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6)[1]")
            heading_node = heading_nodes[0] if heading_nodes else None
            heading = _text(heading_node) if heading_node is not None else "Section %s" % order
            raw_text = _text(node)
            section_id = "section-%s-%s" % (order, sha256_text(heading.lower())[:8])
            tables = self._tables(node, section_id, heading)
            sections.append(
                SourceSectionBlock(
                    section_id=section_id,
                    order=order,
                    role=_role(heading),
                    heading=heading,
                    raw_text=raw_text,
                    raw_text_sha256=sha256_text(raw_text),
                    locator="%s#section/%s" % (locator, order),
                    blocks=[
                        SourceSectionContentBlock(
                            order=1,
                            kind="paragraph",
                            occurrence=1,
                            text=raw_text,
                        )
                    ],
                    tables=tables,
                    composer_input_eligible=False,
                )
            )
        return sections

    @staticmethod
    def _tables(node: HtmlElement, section_id: str, heading: str) -> List[SourceTable]:
        tables: List[SourceTable] = []
        for table_order, table in enumerate(node.xpath(".//table"), start=1):
            rows = table.xpath(".//tr")
            headings: List[str] = []
            parsed_rows: List[SourceTableRow] = []
            for row_index, row in enumerate(rows):
                cells = row.xpath("./th | ./td")
                values = [_text(cell) for cell in cells]
                if not values:
                    continue
                if row_index == 0 and row.xpath("./th"):
                    headings = values
                    continue
                parsed_cells = [
                    SourceTableCell(
                        row_index=len(parsed_rows),
                        column_index=column_index,
                        source_column=column_index + 1,
                        tag=cell.tag,
                        raw_text=value,
                        normalized_text=value,
                    )
                    for column_index, (cell, value) in enumerate(zip(cells, values))
                ]
                parsed_rows.append(
                    SourceTableRow(
                        order=len(parsed_rows) + 1,
                        label=values[0] if values else None,
                        cells=parsed_cells,
                    )
                )
            surrounding = _text(node)
            units = sorted(set(re.findall(r"\b(?:cm|inches|inch|in)\b", surrounding, re.I)))
            footnotes = []
            for item in node.xpath(
                ".//*[contains(concat(' ', normalize-space(@class), ' '), ' footnote ') or @data-footnote or self::small]"
            ):
                value = _text(item)
                if value:
                    footnotes.append(value)
            tables.append(
                SourceTable(
                    table_id="%s-table-%s" % (section_id, table_order),
                    order=table_order,
                    role=_role(heading),
                    headings=headings,
                    units=units,
                    rows=parsed_rows,
                    footnotes=footnotes,
                    measurement_basis=_basis(surrounding),
                    measurement_basis_evidence=(
                        "inferred from explicit body/garment measurement wording"
                        if _basis(surrounding) != MeasurementBasis.UNSTATED
                        else "source did not state a measurement basis"
                    ),
                    locator="section:%s/table:%s" % (section_id, table_order),
                )
            )
        return tables

    @staticmethod
    def _extract_fit(result: AdapterResult, captured_at: datetime) -> None:
        occurrences: List[FitOccurrence] = []
        patterns: Sequence[Tuple[str, re.Pattern, Optional[str]]] = (
            ("MODEL_HEIGHT", HEIGHT_RE, None),
            ("MODEL_SIZE", SIZE_RE, None),
            ("GARMENT_LENGTH", GARMENT_LENGTH_RE, None),
        )
        for section in result.sections:
            for occurrence_type, pattern, unit in patterns:
                for match_index, match in enumerate(pattern.finditer(section.raw_text), start=1):
                    value = SPACE_RE.sub(" ", match.group(1)).strip()
                    occurrences.append(
                        FitOccurrence(
                            occurrence_id="fit-%s" % sha256_text(
                                "%s|%s|%s|%s" % (section.section_id, occurrence_type, match.start(), value)
                            )[:16],
                            occurrence_type=occurrence_type,
                            raw_text=match.group(0),
                            normalized_value=value,
                            unit=unit,
                            locator="section:%s/text:%s" % (section.section_id, match.start()),
                            section_id=section.section_id,
                            captured_at=captured_at,
                        )
                    )
        result.fit_occurrences.extend(occurrences)
        heights = [item for item in occurrences if item.occurrence_type == "MODEL_HEIGHT"]
        sizes = [item for item in occurrences if item.occurrence_type == "MODEL_SIZE"]
        if heights or sizes:
            model_occurrences = [
                item for item in occurrences
                if item.occurrence_type in {"MODEL_HEIGHT", "MODEL_SIZE"}
            ]
            result.source_model_evidence.append(
                SourceModelEvidence(
                    evidence_id="model-%s" % sha256_text(
                        "|".join(item.occurrence_id for item in model_occurrences)
                    )[:16],
                    occurrence_ids=[item.occurrence_id for item in model_occurrences],
                    model_height=heights[0].normalized_value if heights else None,
                    size_worn=sizes[0].normalized_value if sizes else None,
                    scope="COMPETITOR_ONLY",
                    target_fit_note_eligible=False,
                )
            )

    def _extract_material(self, result: AdapterResult, captured_at: datetime) -> None:
        for section in result.sections:
            if section.role not in {SectionRole.DETAILS_CARE, SectionRole.MATERIALS_PROVENANCE}:
                continue
            value = self._material_value(section.raw_text)
            if not value:
                continue
            result.candidates.append(
                FactCandidate(
                    field_path="material_composition",
                    value=value,
                    source=EvidenceSource.RENDERED_DOM,
                    locator="section:%s" % section.section_id,
                    captured_at=captured_at,
                    fact_kind=FactKind.ATOMIC_PHYSICAL,
                    priority=300,
                )
            )

    @staticmethod
    def _material_value(text: str) -> List[Dict[str, str]]:
        values = []
        for percentage, material in PERCENT_MATERIAL_RE.findall(text):
            normalized_material = SPACE_RE.sub(" ", material).strip(" ,.;:").lower()
            values.append({"material": normalized_material, "percentage": percentage})
        return sorted(values, key=lambda item: (item["material"], item["percentage"]))

    @staticmethod
    def _extract_dom_options(soup: HtmlElement, result: AdapterResult, locator: str) -> None:
        selects = soup.xpath(
            "//select[contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'option') or @data-option]"
        )
        for position, select in enumerate(selects, start=1):
            name = select.get("data-option") or select.get("aria-label") or select.get("name") or "Option %s" % position
            values = [
                _text(option)
                for option in select.xpath(".//option")
                if option.get("value") not in (None, "") and _text(option)
            ]
            if not values:
                continue
            result.options.append(SourceOption(name=str(name), position=position, values=values))
            if str(name).lower() in {"color", "colour"}:
                for value in values:
                    result.colour_relations.append(
                        ColourRelation(
                            relation_id="colour-%s" % sha256_text(value.lower())[:12],
                            relation_type=ColourRelationType.IN_PRODUCT_OPTION,
                            colour_value=value,
                            capture_status=CaptureStatus.CAPTURED,
                            locator="%s#select/%s" % (locator, position),
                        )
                    )

    @staticmethod
    def _extract_sibling_colours(
        soup: HtmlElement,
        result: AdapterResult,
        locator: str,
        base_url: str,
    ) -> None:
        links = soup.xpath(
            "//a[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'swatch') or @data-color or @data-colour]"
        )
        for index, link in enumerate(links, start=1):
            href = link.get("href")
            value = link.get("data-color") or link.get("data-colour") or link.get("aria-label") or _text(link)
            if not href or not value:
                continue
            linked_url = urljoin(base_url, str(href))
            result.colour_relations.append(
                ColourRelation(
                    relation_id="sibling-%s" % sha256_text(linked_url)[:12],
                    relation_type=ColourRelationType.LINKED_SIBLING_PDP,
                    colour_value=str(value),
                    linked_url=linked_url,
                    capture_status=CaptureStatus.UNOPENED,
                    locator="%s#swatch/%s" % (locator, index),
                )
            )

    @staticmethod
    def _rendered_media(
        soup: HtmlElement,
        locator: str,
        base_url: str,
    ) -> List[MediaCandidate]:
        roots = soup.xpath("(//main | //article | //body)[1]")
        root = roots[0] if roots else soup
        media: List[MediaCandidate] = []
        seen = set()
        for image in root.xpath(".//img"):
            url = image.get("src") or image.get("data-src") or image.get("data-original")
            if not url:
                continue
            absolute_url = urljoin(base_url, str(url))
            if absolute_url in seen:
                continue
            seen.add(absolute_url)
            classes = str(image.get("class") or "").lower()
            excluded = any(token in classes for token in ("nav", "icon", "logo", "recommend", "editorial"))
            groups = ["dom:excluded" if excluded else "dom:product"]
            media.append(
                MediaCandidate(
                    url=absolute_url,
                    position=len(media) + 1,
                    source=EvidenceSource.RENDERED_DOM,
                    locator="%s#img/%s" % (locator, len(media) + 1),
                    exclusion_group_ids=groups,
                    excluded=excluded,
                )
            )
        return media

    @staticmethod
    def _jsonld_variants(product: Dict[str, Any], result: AdapterResult, prefix: str) -> None:
        raw_variants = product.get("hasVariant") or []
        if isinstance(raw_variants, dict):
            raw_variants = [raw_variants]
        observed: Dict[str, List[str]] = {}
        rows: List[Tuple[Dict[str, Any], Dict[str, str]]] = []
        for raw in raw_variants:
            if not isinstance(raw, dict):
                continue
            values: Dict[str, str] = {}
            for source_key, option_name in (("color", "Colour"), ("size", "Size")):
                if raw.get(source_key) not in (None, ""):
                    values[option_name] = str(raw[source_key])
            for prop in raw.get("additionalProperty") or []:
                if isinstance(prop, dict) and prop.get("name") and prop.get("value"):
                    values[str(prop["name"])] = str(prop["value"])
            for name, value in values.items():
                observed.setdefault(name, [])
                if value not in observed[name]:
                    observed[name].append(value)
            rows.append((raw, values))
        if not rows:
            return
        result.options = [
            SourceOption(name=name, position=index, values=values)
            for index, (name, values) in enumerate(observed.items(), start=1)
        ]
        for index, (raw, values) in enumerate(rows, start=1):
            offer = raw.get("offers") or {}
            if isinstance(offer, list):
                offer = offer[0] if offer else {}
            price = _decimal(offer.get("price")) if isinstance(offer, dict) else None
            if price is None:
                continue
            result.variants.append(
                SourceVariant(
                    source_variant_id=str(raw.get("sku") or raw.get("@id") or index),
                    title=str(raw.get("name")) if raw.get("name") else None,
                    option_values=[
                        VariantOptionValue(option_name=option.name, value=values[option.name])
                        for option in result.options
                        if option.name in values
                    ],
                    current_price=price,
                    source_available=None,
                    source_sku=str(raw.get("sku")) if raw.get("sku") else None,
                )
            )

    @staticmethod
    def _merge(target: AdapterResult, source: AdapterResult) -> None:
        target.candidates.extend(source.candidates)
        target.structured_media.extend(source.structured_media)
        if not target.options:
            target.options = source.options
        if not target.variants:
            target.variants = source.variants
        target.colour_relations.extend(source.colour_relations)
