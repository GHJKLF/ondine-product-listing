"""Parser for read-only Shopify Ajax product JSON evidence."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional

from product_listing.adapters.base import AdapterResult, FactCandidate, MediaCandidate
from product_listing.evidence import sha256_text
from product_listing.models import (
    CaptureStatus,
    ColourRelation,
    ColourRelationType,
    EvidenceSource,
    FactKind,
    SourceOption,
    SourceVariant,
    VariantOptionValue,
)


def _money(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, int):
            return Decimal(value) / Decimal(100)
        text = str(value).strip()
        if text.isdigit():
            return Decimal(text) / Decimal(100)
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _image_url(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("src", "url", "preview_image", "original_src"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate
            if isinstance(candidate, dict):
                nested = candidate.get("src") or candidate.get("url")
                if isinstance(nested, str):
                    return nested
    return None


class ShopifyAjaxAdapter:
    """Extract exact Shopify option/variant structure without inventory fields."""

    source = EvidenceSource.SHOPIFY_AJAX

    def extract(
        self,
        payload: Dict[str, Any],
        captured_at: datetime,
        artifact_id: str,
        currency: str,
    ) -> AdapterResult:
        result = AdapterResult()
        locator = "artifact:%s" % artifact_id

        for field_path, key, kind, priority in (
            ("title", "title", FactKind.IDENTIFIER, 200),
            ("vendor", "vendor", FactKind.IDENTIFIER, 200),
            ("source_description", "description", FactKind.SOURCE_PROSE, 100),
        ):
            value = payload.get(key)
            if value not in (None, ""):
                result.candidates.append(
                    FactCandidate(
                        field_path=field_path,
                        value=value,
                        source=self.source,
                        locator="%s#/%s" % (locator, key),
                        captured_at=captured_at,
                        fact_kind=kind,
                        priority=priority,
                    )
                )

        result.candidates.append(
            FactCandidate(
                field_path="currency",
                value=currency,
                source=self.source,
                locator="%s#capture-context/currency" % locator,
                captured_at=captured_at,
                fact_kind=FactKind.COMMERCE,
                priority=200,
            )
        )

        current_price = _money(payload.get("price"))
        compare_at_price = _money(payload.get("compare_at_price"))
        if current_price is not None:
            result.candidates.append(
                FactCandidate(
                    field_path="current_price",
                    value=current_price,
                    source=self.source,
                    locator="%s#/price" % locator,
                    captured_at=captured_at,
                    fact_kind=FactKind.COMMERCE,
                    priority=200,
                )
            )
        if compare_at_price is not None:
            result.candidates.append(
                FactCandidate(
                    field_path="compare_at_price",
                    value=compare_at_price,
                    source=self.source,
                    locator="%s#/compare_at_price" % locator,
                    captured_at=captured_at,
                    fact_kind=FactKind.COMMERCE,
                    priority=200,
                )
            )

        result.options = self._options(payload.get("options") or [])
        result.variants = self._variants(
            payload.get("variants") or [],
            result.options,
        )

        for option in result.options:
            if option.name.strip().lower() in {"color", "colour"}:
                for value in option.values:
                    relation_id = "colour-%s" % sha256_text(value.lower())[:12]
                    result.colour_relations.append(
                        ColourRelation(
                            relation_id=relation_id,
                            relation_type=ColourRelationType.IN_PRODUCT_OPTION,
                            colour_value=value,
                            capture_status=CaptureStatus.CAPTURED,
                            locator="%s#/options/%s" % (locator, option.position - 1),
                        )
                    )

        media_values: Iterable[Any] = payload.get("media") or payload.get("images") or []
        for index, value in enumerate(media_values, start=1):
            url = _image_url(value)
            if not url:
                continue
            result.structured_media.append(
                MediaCandidate(
                    url=url,
                    position=index,
                    source=self.source,
                    locator="%s#/media/%s" % (locator, index - 1),
                )
            )
        return result

    @staticmethod
    def _options(raw_options: List[Any]) -> List[SourceOption]:
        options: List[SourceOption] = []
        for index, raw in enumerate(raw_options, start=1):
            if isinstance(raw, str):
                name = raw
                values: List[str] = []
                position = index
            elif isinstance(raw, dict):
                name = str(raw.get("name") or raw.get("title") or "Option %s" % index)
                values = [str(value) for value in (raw.get("values") or [])]
                position = int(raw.get("position") or index)
            else:
                continue
            options.append(SourceOption(name=name, position=position, values=values or ["Default"] ))
        return options

    @staticmethod
    def _variants(
        raw_variants: List[Any],
        options: List[SourceOption],
    ) -> List[SourceVariant]:
        variants: List[SourceVariant] = []
        for index, raw in enumerate(raw_variants, start=1):
            if not isinstance(raw, dict):
                continue
            raw_values = raw.get("options")
            if not isinstance(raw_values, list):
                raw_values = [raw.get("option%s" % position) for position in range(1, len(options) + 1)]
            option_values = [
                VariantOptionValue(option_name=option.name, value=str(value))
                for option, value in zip(options, raw_values)
                if value not in (None, "")
            ]
            current_price = _money(raw.get("price"))
            if current_price is None:
                continue
            variant_id = raw.get("id") or raw.get("sku") or index
            variants.append(
                SourceVariant(
                    source_variant_id=str(variant_id),
                    title=str(raw.get("title")) if raw.get("title") is not None else None,
                    option_values=option_values,
                    current_price=current_price,
                    compare_at_price=_money(raw.get("compare_at_price")),
                    source_available=raw.get("available") if isinstance(raw.get("available"), bool) else None,
                    source_sku=str(raw.get("sku")) if raw.get("sku") else None,
                    source_barcode=str(raw.get("barcode")) if raw.get("barcode") else None,
                    source_weight_grams=(
                        int(raw.get("weight"))
                        if isinstance(raw.get("weight"), (int, float))
                        else None
                    ),
                )
            )
        return variants
