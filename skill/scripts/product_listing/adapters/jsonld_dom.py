"""Rendered DOM and JSON-LD evidence extraction.

The adapter keeps source prose as evidence-only section text. It extracts only
small atomic facts (prices, material composition, model height/size) for later
reconciliation; raw competitor sentences are never composer-eligible.
"""

import json
from copy import deepcopy
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlsplit

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
    r"(?:model(?:'s)?\s+(?:height\s*(?:is|:)?|is)|height\s*:)\s*"
    r"((?:\d{3}\s*cm)|(?:\d\s*[’']\s*\d{1,2}(?:\s*(?:in|\"))?))",
    re.I,
)
SIZE_RE = re.compile(
    r"(?:model\s+)?(?:(?:wears?|wearing)\b|size\s*worn\s*:?)\s*(?:a\s+)?"
    r"(?:(?:[A-Za-z][\w'’-]*\s+){0,4}size\s+)?"
    r"((?:UK\s*)?\d{1,2}(?:\s*[-–]\s*\d{1,2})?|[2-6]?X{1,3}[SL]|[SML]|ONE\s+SIZE)\b"
    r"(?:\s+(?P<wearing_length>\d{2}(?:\.\d+)?)\b(?:\s*(?P<length_unit>inches|inch|in|cm)\b)?)?",
    re.I,
)
GARMENT_LENGTH_RE = re.compile(r"(?:garment\s+)?length\s*:?[ ]*(\d+(?:\.\d+)?\s*(?:cm|in|inches))", re.I)


def _text(node: HtmlElement) -> str:
    return SPACE_RE.sub(" ", " ".join(node.itertext())).strip()


def _excluded_region(node: HtmlElement) -> bool:
    if node.tag in {"nav", "footer", "script", "style", "noscript", "template"}:
        return True
    identity = " ".join((str(node.tag), node.get("class") or "", node.get("id") or "")).lower()
    return any(token in identity for token in ("recommend", "related-products", "recently-viewed", "footer"))


def _clean_region(node: HtmlElement) -> HtmlElement:
    root = deepcopy(node)
    for child in list(root.iterdescendants()):
        if _excluded_region(child) and child.getparent() is not None:
            child.drop_tree()
    return root


def _product_root(soup: HtmlElement) -> HtmlElement:
    # A union with body first in document order accidentally chooses the whole page.
    roots = soup.xpath("//main") or soup.xpath("//article") or soup.xpath("//body")
    root = roots[0] if roots else soup
    headings = root.xpath(".//h1")
    if headings:
        for ancestor in headings[0].iterancestors():
            classes = set(ancestor.get("class", "").lower().split())
            # product-info can be only the text/purchase column beside the gallery.
            # Prefer its product ancestor, or the main/article fallback if unmarked.
            if (ancestor.tag == "product-section"
                    or "product" in classes or "product-detail" in classes
                    or ancestor.get("id", "").lower().startswith("mainproduct-")
                    or ancestor.get("itemtype", "").rstrip("/").endswith("/Product")):
                return _clean_region(ancestor)
            if ancestor is root:
                break
    return _clean_region(root)


def _section_text(node: HtmlElement) -> str:
    # Retain prose boundaries: cotton followed by a care bullet is not a material name.
    copy = deepcopy(node)
    for child in copy.iter():
        if child.tag in {"p", "li", "div", "br", "summary", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            child.tail = "\n" + (child.tail or "")
    lines = (SPACE_RE.sub(" ", line).strip() for line in "".join(copy.itertext()).splitlines())
    return "\n".join(line for line in lines if line)


def _guide_table_entries(node: HtmlElement, heading: str) -> List[Tuple[HtmlElement, str]]:
    """Keep each guide table beside its own headings and explanatory prose."""
    entries = []
    elements = list(node.iter())
    heading_stack: List[Tuple[int, str]] = []
    last_heading_index = -1
    for index, element in enumerate(elements):
        if isinstance(element.tag, str) and re.fullmatch(r"h[1-6]", element.tag) and _text(element):
            title = _text(element)
            level = int(element.tag[1])
            # Some source guides use h2 for a new audience after an h1 audience.
            # Explicit audience headings start a new subject regardless of HTML level.
            if re.search(r"\b(?:women|men|children|girls|boys|kids|unisex|adults|babies)\b", title, re.I):
                heading_stack = []
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            last_heading_index = index
        elif element.tag == "table":
            region = lxml_html.Element("div")
            if heading_stack:
                title_node = lxml_html.Element("h2")
                title_node.text = heading_stack[-1][1]
                region.append(title_node)
            for previous in elements[last_heading_index + 1:index]:
                if previous.tag == "p" and not any(parent.tag == "table" for parent in previous.iterancestors()):
                    region.append(deepcopy(previous))
            region.append(deepcopy(element))
            title = " / ".join([heading] + [value for _, value in heading_stack])
            entries.append((region, title))
    return entries


def _td_header(values: List[str]) -> bool:
    """Recognize labelled size/length axes without converting any source value."""
    if len(values) < 2 or not re.search(r"\b(?:size|length)(?:\s*\([^)]*\))?$", values[0], re.I):
        return False
    return all(re.fullmatch(r"(?:\d+(?:[.\-–]\d+)?|[2-6]?X{0,3}[SML]|one size|regular|long|short)", value, re.I)
               for value in values[1:])


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
    has_garment = ("garment measurement" in lowered or "laid flat" in lowered
                   or all(word in lowered for word in ("garment", "shoulder", "ankle")))
    if has_garment and "recommended height" in lowered:
        has_body = True
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
        product_root = _product_root(soup)
        result.sections = self._sections(product_root, captured_at, locator, document=soup)
        length_units = set(re.findall(r"\blength\s*\((inches|inch|in|cm)\)", _text(product_root), re.I))
        length_unit = next(iter(length_units)).lower() if len(length_units) == 1 else None
        self._extract_fit(result, captured_at, length_unit)
        self._extract_material(result, captured_at)
        self._extract_dom_options(product_root, result, locator)
        current_product_url = urljoin(base_url, str(canonical.get("href"))) if canonical is not None else base_url
        self._extract_sibling_colours(product_root, result, locator, current_product_url)
        result.rendered_media = self._rendered_media(product_root, locator, base_url)

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
        document: Optional[HtmlElement] = None,
    ) -> List[SourceSectionBlock]:
        root = soup
        entries: List[Tuple[HtmlElement, str]] = []
        # Semantic controls also cover custom accordions and drawers outside main.
        for control in root.xpath(".//*[@aria-controls]"):
            heading = _text(control)
            if _role(heading) == SectionRole.OTHER:
                continue
            for target_id in control.get("aria-controls", "").split():
                targets = root.xpath(".//*[@id=$target_id]", target_id=target_id)
                if not targets and document is not None:
                    targets = document.xpath("//*[@id=$target_id]", target_id=target_id)
                if targets and _text(targets[0]):
                    if not any(node is targets[0] for node, _ in entries):
                        entries.append((targets[0], heading))

        for node in root.xpath(".//details | .//section"):
            heading_nodes = node.xpath("(.//summary | .//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6)[1]")
            if not heading_nodes or not _text(node):
                continue
            # A layout section must not swallow its independent inner sections.
            if node.xpath(".//details | .//section") or any(
                node is entry or node in entry.iterancestors() or entry in node.iterancestors()
                for entry, _ in entries
            ):
                continue
            entries.append((node, _text(heading_nodes[0])))

        # Many themes place the actual description in an unheaded rich-text block.
        for node in root.xpath(".//*[@itemprop='description' or @data-product-description or "
                               "contains(concat(' ', normalize-space(@class), ' '), ' richtext ')]"):
            description_markers = ("product__header", "product-header", "product__description", "product-description")
            labelled = node.get("itemprop") == "description" or node.get("data-product-description") is not None
            if not labelled and not any(
                any(marker in (ancestor.get("class") or "") for marker in description_markers)
                for ancestor in [node] + list(node.iterancestors())
            ):
                continue
            if not _text(node) or any(
                node is entry or entry in node.iterancestors() or node in entry.iterancestors()
                for entry, _ in entries
            ):
                continue
            entries.append((node, "Description"))

        document_order = {node: index for index, node in enumerate(root.iter())}
        entries.sort(key=lambda entry: document_order.get(entry[0], len(document_order)))
        guide_overviews = set()
        expanded_entries = []
        for node, heading in entries:
            expanded_entries.append((node, heading))
            if _role(heading) == SectionRole.SIZE_GUIDE and len(node.xpath(".//table")) > 1:
                guide_overviews.add(node)
                expanded_entries.extend(_guide_table_entries(node, heading))
        sections: List[SourceSectionBlock] = []
        for order, (source_node, heading) in enumerate(expanded_entries, start=1):
            node = _clean_region(source_node)
            raw_text = _section_text(node)
            section_id = "section-%s-%s" % (order, sha256_text(heading.lower())[:8])
            tables = [] if source_node in guide_overviews else self._tables(node, section_id, heading)
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
                if row_index == 0 and (row.xpath("./th") or _td_header(values)):
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
    def _extract_fit(result: AdapterResult, captured_at: datetime, length_unit: Optional[str] = None) -> None:
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
        worn_lengths = []
        model_lines = []
        for section in result.sections:
            for match in SIZE_RE.finditer(section.raw_text):
                model_lines.extend(line for line in section.raw_text.splitlines() if match.group(0) in line)
                if match.group("wearing_length"):
                    unit = match.group("length_unit") or length_unit
                    value = match.group("wearing_length") + (" " + unit if unit else "")
                    worn_lengths.append(value)
                    occurrences.append(FitOccurrence(
                        occurrence_id="fit-%s" % sha256_text(
                            "%s|wearing-length|%s" % (section.section_id, match.start())
                        )[:16],
                        occurrence_type="GARMENT_LENGTH", raw_text=match.group(0),
                        normalized_value=value, unit=unit,
                        locator="section:%s/text:%s" % (section.section_id, match.start()),
                        section_id=section.section_id, captured_at=captured_at,
                    ))
        result.fit_occurrences.extend(occurrences)
        heights = [item for item in occurrences if item.occurrence_type == "MODEL_HEIGHT"]
        sizes = [item for item in occurrences if item.occurrence_type == "MODEL_SIZE"]
        if heights or sizes:
            model_occurrences = [
                item for item in occurrences
                if item.occurrence_type in {"MODEL_HEIGHT", "MODEL_SIZE"} or item.normalized_value in worn_lengths
            ]
            result.source_model_evidence.append(
                SourceModelEvidence(
                    evidence_id="model-%s" % sha256_text(
                        "|".join(item.occurrence_id for item in model_occurrences)
                    )[:16],
                    occurrence_ids=[item.occurrence_id for item in model_occurrences],
                    model_height=heights[0].normalized_value if heights else None,
                    size_worn=sizes[0].normalized_value if sizes else None,
                    source_line=model_lines[0] if model_lines else None,
                    wearing_length=worn_lengths[0] if worn_lengths else None,
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
            ".//select[contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'option') or @data-option]"
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
            ".//a[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'swatch') or @data-color or @data-colour]"
        )
        for index, link in enumerate(links, start=1):
            href = link.get("href")
            value = link.get("data-color") or link.get("data-colour") or link.get("aria-label") or _text(link)
            if not href or not value:
                continue
            linked_url = urljoin(base_url, str(href))
            linked_parts, current_parts = urlsplit(linked_url), urlsplit(base_url)
            is_self = (linked_parts.netloc.lower(), linked_parts.path.rstrip("/")) == (
                current_parts.netloc.lower(), current_parts.path.rstrip("/")
            )
            if is_self and any(
                (urlsplit(urljoin(base_url, candidate.get("href", ""))).netloc.lower(),
                 urlsplit(urljoin(base_url, candidate.get("href", ""))).path.rstrip("/"))
                != (current_parts.netloc.lower(), current_parts.path.rstrip("/"))
                for candidate in links if candidate.get("href")
            ):
                continue
            result.colour_relations.append(
                ColourRelation(
                    relation_id="sibling-%s" % sha256_text(linked_url)[:12],
                    relation_type=(ColourRelationType.SELF_ONLY_SINGLE_COLOUR if is_self
                                   else ColourRelationType.LINKED_SIBLING_PDP),
                    colour_value=str(value),
                    linked_url=linked_url,
                    capture_status=CaptureStatus.CAPTURED if is_self else CaptureStatus.UNOPENED,
                    locator="%s#swatch/%s" % (locator, index),
                )
            )

    @staticmethod
    def _rendered_media(
        soup: HtmlElement,
        locator: str,
        base_url: str,
    ) -> List[MediaCandidate]:
        root = soup
        galleries = root.xpath(".//*[contains(@class, 'product__gallery') or "
                               "contains(@class, 'product-gallery') or "
                               "contains(@class, 'product__media') or @data-product-gallery or self::media-gallery]")
        gallery_nodes = set(galleries)
        media: List[MediaCandidate] = []
        seen = set()
        for image in root.xpath(".//img"):
            ancestors = list(image.iterancestors())
            if galleries and not any(parent in gallery_nodes for parent in ancestors):
                continue
            url = image.get("src") or image.get("data-src") or image.get("data-original")
            if not url:
                continue
            # Gallery zoom links identify the original asset across responsive thumbnails.
            zoom_links = image.xpath("ancestor::a[@href and (@data-pswp-width or @data-fancybox)][1]")
            if zoom_links:
                url = zoom_links[0].get("href")
            absolute_url = urljoin(base_url, str(url))
            if absolute_url in seen:
                continue
            seen.add(absolute_url)
            classes = " ".join(str(node.get("class") or "") for node in [image] + ancestors).lower()
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
