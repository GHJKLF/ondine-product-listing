#!/usr/bin/env python3
"""Build deterministic, sanitized replay fixtures from frozen public PDP responses.

This script writes only within tests/fixtures and tests/oracles. It never opens a
browser and never calls Shopify or POKY. Network media bytes are not acquired by
this builder; their already-observed hashes are reviewer evidence below.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

from lxml import etree, html


HERE = Path(__file__).resolve().parent
ORACLES = HERE.parent / "oracles"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def table_cells(table: etree._Element) -> list[list[dict[str, object]]]:
    rows: list[list[dict[str, object]]] = []
    for row_index, row in enumerate(table.xpath(".//tr"), start=1):
        cells: list[dict[str, object]] = []
        for column_index, cell in enumerate(row.xpath("./th|./td"), start=1):
            cells.append(
                {
                    "row": row_index,
                    "source_column": column_index,
                    "tag": cell.tag.lower(),
                    "text": " ".join(cell.text_content().split()),
                    "rowspan": int(cell.get("rowspan", "1")),
                    "colspan": int(cell.get("colspan", "1")),
                }
            )
        if cells:
            rows.append(cells)
    return rows


def sanitize_rendered_html(raw_path: Path, output_path: Path) -> dict[str, object]:
    raw = raw_path.read_bytes()
    document = html.fromstring(raw.decode("utf-8", "replace"))
    removed: dict[str, int] = {}
    for xpath, label in [
        ("//script", "script"),
        ("//style", "style"),
        ("//noscript", "noscript"),
        ("//iframe", "iframe"),
        ("//*[contains(translate(local-name(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accelerated-checkout')]", "accelerated_checkout"),
    ]:
        nodes = document.xpath(xpath)
        removed[label] = len(nodes)
        for node in nodes:
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
    stripped_attributes = 0
    sensitive_attribute = re.compile(r"(?:token|session|checkout|cart)", re.I)
    for node in document.iter():
        for attribute in list(node.attrib):
            if sensitive_attribute.search(attribute):
                del node.attrib[attribute]
                stripped_attributes += 1
    etree.strip_tags(document, etree.Comment)
    rendered = html.tostring(document, encoding="utf-8", method="html", doctype="<!doctype html>")
    marker_hits = sorted(
        set(re.findall(rb"(?i)(access[_-]?token|client[_-]?secret|api[_-]?key|bearer\s+[a-z0-9._-]+)", rendered))
    )
    if marker_hits:
        raise RuntimeError(f"sanitized replay still contains credential markers: {marker_hits!r}")
    output_path.write_bytes(rendered)
    return {
        "mode": "SANITIZED_SERVER_RENDERED_HTML",
        "original_raw_sha256": sha256_bytes(raw),
        "original_raw_retained": False,
        "sanitized_sha256": sha256_bytes(rendered),
        "removed_nodes": removed,
        "stripped_sensitive_attribute_count": stripped_attributes,
        "security_note": "Executable server-rendered response with scripts, embedded frames, accelerated checkout components, styles and token/session/cart/checkout-named attributes removed. The unsanitized acquisition is not part of the denominator.",
    }


def write_hash_index(root: Path) -> str:
    target = root / "bundle-files.sha256"
    paths = sorted(p for p in root.rglob("*") if p.is_file() and p != target and "raw/response.html" not in str(p))
    lines = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}" for path in paths]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sha256_file(target)


def phase_eight() -> None:
    root = HERE / "phase-eight-avenly"
    raw_path = root / "raw" / "response.html"
    raw_document = html.fromstring(raw_path.read_bytes().decode("utf-8", "replace"))
    rendered_record = sanitize_rendered_html(raw_path, root / "rendered.sanitized.html")

    sections = [
        {
            "order": 1,
            "source_heading": "fit",
            "normalized_role": "DESCRIPTION_AND_FIT",
            "blocks": [
                {
                    "kind": "paragraph",
                    "occurrence": 1,
                    "text": "Take your outfit from day to night in the most effortless way with this forest green midi dress. Tying at the waist with a belt, it offers a flattering and classic silhouette you’ll feel comfortable in. We’ve designed it with button fastenings running down the front of the dress, as well as contrast stitch detailing on the seams. You’ll also find a collar at the neck and elasticated cuffs on the sleeves. This dress is all about the detail, so choose your accessories carefully in browns and neutrals for the complete look.",
                },
                {"kind": "subheading", "occurrence": 1, "text": "Size"},
                {"kind": "label_value", "occurrence": 1, "label": "Fit:", "value": "Regular Fit"},
                {"kind": "label_value", "occurrence": 1, "label": "Length:", "value": "120cm Side neck point to hem"},
                {"kind": "subheading", "occurrence": 1, "text": "Other details"},
                {"kind": "label_value", "occurrence": 1, "label": "Fastening:", "value": "Button"},
                {"kind": "label_value", "occurrence": 1, "label": "Sleeve length:", "value": "Long Sleeve"},
                {"kind": "label_value", "occurrence": 1, "label": "Style code:", "value": "10024680693"},
            ],
        },
        {
            "order": 2,
            "source_heading": "Material",
            "blocks": [
                {"kind": "subheading", "occurrence": 1, "text": "Details"},
                {"kind": "label_value", "occurrence": 1, "label": "Composition:", "value": "Polyamide 44% Modal 20% Cotton 20% Elastane 13%"},
                {"kind": "label_value", "occurrence": 1, "label": "Care:", "value": "Delicate Machine Wash"},
            ],
        },
    ]
    expected_absences = [
        {"field": "source_model.height", "status": "PROVEN_ABSENT", "basis": "independent PDP capture and reconciled run record"},
        {"field": "source_model.worn_size", "status": "PROVEN_ABSENT", "basis": "independent PDP capture and reconciled run record"},
        {"field": "weight", "status": "PROVEN_ABSENT", "basis": "independent PDP capture and reconciled run record"},
        {"field": "colour_relations", "status": "PROVEN_ABSENT", "basis": "single Green colour shown; no alternate swatch relation in frozen PDP"},
    ]
    write_json(root / "sections.json", {"schema": "source-sections-v1", "sections": sections, "expected_section_absences": [
        {"heading": "Description", "status": "PROVEN_ABSENT_AS_NAMED_SECTION", "note": "description prose occurs under source heading 'fit'"},
        {"heading": "Details & Care", "status": "PROVEN_ABSENT_AS_NAMED_SECTION", "note": "composition and care occur under Material"},
        {"heading": "Size & Fit", "status": "PROVEN_ABSENT_AS_NAMED_SECTION", "note": "fit and length occur under source heading 'fit'"},
        {"heading": "Sustainability", "status": "PROVEN_ABSENT_AS_NAMED_SECTION"},
    ]})
    write_json(
        root / "size-guide.json",
        {
            "schema": "source-size-guide-v1",
            "basis": "BODY",
            "basis_evidence": "size guide labels body measurements; no garment-measurement claim",
            "tables": [
                {"order": 1, "unit": "cm", "cells": table_cells(raw_document.xpath("//table")[0])},
                {"order": 2, "unit": "in", "cells": table_cells(raw_document.xpath("//table")[1])},
                {"order": 3, "unit": "size_conversion", "cells": table_cells(raw_document.xpath("//table")[2])},
            ],
            "footnotes": [],
            "duplicate_dom_tables_excluded": [8, 9, 10],
        },
    )
    structured = {
        "schema": "structured-product-v1",
        "source_class": "CONSUMER_RETAILER",
        "product_id": "100246869318",
        "style_code": "10024680693",
        "sku_or_mpn": "PE1002468",
        "title": "Avenly Long Sleeve Midi Shirt Dress",
        "vendor": "Phase Eight",
        "product_type": "Dresses",
        "seo": {"html_title": "Avenly Long Sleeve Midi Shirt Dress | Phase Eight UK | ", "meta_description": "Avenly Long Sleeve Midi Shirt Dress Phase Eight"},
        "currency": "GBP",
        "price": {"current": "95.20", "compare_at": "119.00"},
        "promotion": {"text": "20% Off Applied", "countdown_or_dated_wording": None},
        "options": [{"name": "Size", "values": ["UK 06", "UK 08", "UK 10", "UK 12", "UK 14", "UK 16", "UK 18", "UK 20", "UK 22"]}],
        "real_variant_combinations": [["UK 06"], ["UK 08"], ["UK 10"], ["UK 12"], ["UK 14"], ["UK 16"], ["UK 18"], ["UK 20"], ["UK 22"]],
        "availability": {"status": "ACQUISITION_GAP", "target_inventory_eligible": False},
        "source_model": {"namespace": "competitor_only", "height": None, "worn_size": None, "target_fit_note_eligible": False},
        "weight": None,
        "composition_percent_total": "97",
    }
    write_json(root / "structured-product.json", structured)

    rendered_urls = [
        "https://www.phase-eight.com/dw/image/v2/BDCH_PRD/on/demandware.static/-/Sites-master-Catalog-P8/default/dwa2e93e59/images/10024680693/10024680693-01-avenly-ponte-shirt-mini-dress.jpg?sw=1000&sh=1400&strip=false",
        "https://www.phase-eight.com/dw/image/v2/BDCH_PRD/on/demandware.static/-/Sites-master-Catalog-P8/default/dw131357ee/images/10024680693/10024680693-02-avenly-ponte-shirt-mini-dress.jpg?sw=1000&sh=1400&strip=false",
        "https://www.phase-eight.com/dw/image/v2/BDCH_PRD/on/demandware.static/-/Sites-master-Catalog-P8/default/dw25b034b9/images/10024680693/10024680693-03-avenly-ponte-shirt-mini-dress.jpg?sw=1000&sh=1400&strip=false",
        "https://www.phase-eight.com/dw/image/v2/BDCH_PRD/on/demandware.static/-/Sites-master-Catalog-P8/default/dw4c148b5f/images/10024680693/10024680693-04-avenly-ponte-shirt-mini-dress.jpg?sw=1000&sh=1400&strip=false",
        "https://www.phase-eight.com/dw/image/v2/BDCH_PRD/on/demandware.static/-/Sites-master-Catalog-P8/default/dw8d67ae31/images/10024680693/10024680693-05-avenly-ponte-shirt-mini-dress.jpg?sw=1000&sh=1400&strip=false",
        "https://www.phase-eight.com/dw/image/v2/BDCH_PRD/on/demandware.static/-/Sites-master-Catalog-P8/default/dwecbbad59/images/10024680693/10024680693-06-avenly-ponte-shirt-mini-dress.jpg?sw=1000&sh=1400&strip=false",
        "https://www.phase-eight.com/dw/image/v2/BDCH_PRD/on/demandware.static/-/Sites-master-Catalog-P8/default/dw225c7e1e/images/10024680693/10024680693-07-avenly-ponte-shirt-mini-dress.jpg?sw=1000&sh=1400&strip=false",
        "https://www.phase-eight.com/dw/image/v2/BDCH_PRD/on/demandware.static/-/Sites-master-Catalog-P8/default/dw8ecb139f/images/10024680693/10024680693-99-avenly-ponte-shirt-mini-dress.jpg?sw=1000&sh=1400&strip=false",
    ]
    rendered_hashes = ["7a6ac744a4c2c9df8785ca22cbe6e1f9c3383624e50f59b2cc4e9e661c52754b", "f3e6d49e5e9fb2907bd8917f6c73096640bd3bcba28c9469ad3c5c1e54a49678", "90048389c8693fd1f6f6272fbcb67750c8fa12e3ea09f76e6952de12212d5ae7", "6ead05a0f2ca9e9af960171083048f14c906b4aea0e1b2675a6d859807ff3dfc", "a3b7fb39a3a3560fefba3575653efc1ddfb717f3a52482f3773840534d1d92fd", "c4b26ddf01ffe9cde56dd3a4e3ffae913eadf676e96c5ca8153589dc6a26889c", "10db9ae06a09eeebfbe627d5798562e9184e70b4fe3cfaaec2e2a025ea84d840", "7fb0516f02262df37d10946928ae05d688adada300ef3dda830fec50630c7e93"]
    structured_hashes = ["9b75be490d9c12a78d9ab4f838b60f810c26e1d9025950fbb3f5a29a59bd0f8a", "78600217f0dbbd9f1162ef7562b4af0670d23d2182707aa42fca2f8424b9ecbc", "bf7a862b39bb61b896a0fd278adaa864baf0cf68cf732ce1acc758d48d82fff2", "c5aacd1b4cdc12556cb32d89a055c70696082c89f9abd18af55c612cad5edbd6", "97b605d14b97196cec896b34ee53f4f91527684c6e1789f0242673509ed9eb5d", "7a7359373f53fb71532a9d74c5c34fdd72474baf293df32fe6e399e5cc034bca", "9f358b8be05aefd9026c7354f433ecc16b631099514d59992bd7eee2d7c0d0a2", "a7db6ab6fd8ae8dd3863bd007374ef5410371a8a295563b9d051cd701eaac9e6"]
    media = {
        "schema": "source-media-manifest-v1",
        "colour_association": "Green",
        "rendered_gallery": [{"order": i, "url": url, "content_sha256": rendered_hashes[i - 1], "excluded": False} for i, url in enumerate(rendered_urls, 1)],
        "structured_gallery": [{"order": i, "url": f"https://assets.phase-eight.com/i/phaseeight/10024680693-{stem}-avenly-ponte-shirt-mini-dress?$x-large$", "content_sha256": structured_hashes[i - 1], "excluded": False} for i, stem in enumerate(["01", "02", "03", "04", "05", "06", "07", "99"], 1)],
        "exclusions": [],
    }
    write_json(root / "media-manifest.json", media)

    evidence_inputs = [
        Path("projects/engine-3/stores/ondine-london/output/product-listing-poki-experiment/runs/run-01-phase-eight-avenly-shirt-dress/independent-source-capture.md"),
        Path("projects/engine-3/stores/ondine-london/output/product-listing-poki-experiment/runs/run-01-phase-eight-avenly-shirt-dress/source-live-product-2026-08-31.png"),
    ]
    write_json(root / "evidence-registry.json", {"schema": "evidence-registry-v1", "accepted": [{"path": str(p), "sha256": sha256_file(Path.cwd() / p)} for p in evidence_inputs], "invalid_preserved": []})
    conflicts = [
        {"code": "MARKET_CURRENCY_RESPONSE_CONFLICT", "severity": "BLOCKING", "detail": "UK/GBP request and cookies coexisted with GlobalE MA/MAD response state; rendered GBP price is captured but same-session market integrity is unresolved."},
        {"code": "COMPOSITION_TOTAL_97_PERCENT", "severity": "BLOCKING", "detail": "44% + 20% + 20% + 13% = 97%; missing 3% is not inferred."},
    ]
    gaps = [
        {"code": "SAME_SESSION_COMMERCE_JSON_NOT_FROZEN", "severity": "BLOCKING"},
        {"code": "JSON_LD_NOT_FROZEN", "severity": "BLOCKING"},
        {"code": "VARIANT_AVAILABILITY_NOT_VERIFIED", "severity": "NONCRITICAL_FOR_STRUCTURE"},
        {"code": "FULL_UNSANITIZED_HTML_NOT_RETAINED", "severity": "SECURITY_REDACTION", "replacement": "rendered.sanitized.html"},
    ]
    bundle = {
        "schema": "source-capture-fixture-v1",
        "fixture_id": "phase-eight-avenly",
        "capture": {
            "requested_url": "https://www.phase-eight.com/product/avenly-long-sleeve-midi-shirt-dress-100246869318.html?country=GB&currency=GBP",
            "final_url": "https://www.phase-eight.com/product/avenly-long-sleeve-midi-shirt-dress-100246869318.html?country=GB&currency=GBP",
            "canonical_url": "https://www.phase-eight.com/product/avenly-long-sleeve-midi-shirt-dress-100246869318.html",
            "market": "GB",
            "locale": "en-GB",
            "currency": "GBP",
            "captured_at": "2026-09-01T11:12:14Z",
            "attempt": 2,
            "rendered_html": rendered_record,
            "json_ld": {"status": "ACQUISITION_GAP_NOT_FROZEN"},
        },
        "files": {"structured_product": "structured-product.json", "sections": "sections.json", "size_guide": "size-guide.json", "media": "media-manifest.json", "evidence": "evidence-registry.json"},
        "conflicts": conflicts,
        "absences": expected_absences,
        "acquisition_gaps": gaps,
        "status": "BLOCKED_DENOMINATOR",
    }
    write_json(root / "bundle.json", bundle)
    oracle = {
        "schema": "reviewer-owned-source-capture-oracle-v1",
        "fixture_id": "phase-eight-avenly",
        "author_role": "Scout",
        "reviewer_lock": {"status": "AWAITING_ATLAS_SIGNATURE", "locked_hash": None},
        "expected": {"capture": deepcopy(bundle["capture"]), "structured_product": structured, "sections": sections, "expected_absences": expected_absences, "media": media, "conflicts": conflicts, "acquisition_gaps": gaps, "verdict": "BLOCKED_DENOMINATOR"},
    }
    write_json(ORACLES / "phase-eight-avenly.expected.json", oracle)
    # The transient unsanitized HTML is intentionally removed only after the
    # deterministic sanitized replay and its original hash have been written.
    raw_path.unlink()
    bundle_hash = write_hash_index(root)
    oracle_hash = sha256_file(ORACLES / "phase-eight-avenly.expected.json")
    print(json.dumps({"fixture": "phase-eight-avenly", "bundle_index_sha256": bundle_hash, "oracle_sha256": oracle_hash}, indent=2))


def normalize_shopify_product(product: dict[str, object], currency: str) -> dict[str, object]:
    variants = []
    for variant in product["variants"]:
        variants.append(
            {
                "id": str(variant["id"]),
                "options": variant["options"],
                "sku": variant["sku"],
                "barcode": variant["barcode"],
                "price": f"{variant['price'] / 100:.2f}",
                "compare_at_price": f"{variant['compare_at_price'] / 100:.2f}" if variant["compare_at_price"] is not None else None,
                "currency": currency,
                "source_availability": variant["available"],
                "source_weight_grams": variant["weight"],
                "target_inventory_eligible": False,
            }
        )
    return {
        "schema": "structured-product-v1",
        "source_class": "CONSUMER_RETAILER",
        "product_id": str(product["id"]),
        "title": product["title"],
        "handle": product["handle"],
        "vendor": product["vendor"],
        "product_type": product["type"],
        "currency": currency,
        "price": {"current": f"{product['price'] / 100:.2f}", "compare_at": f"{product['compare_at_price'] / 100:.2f}"},
        "options": product["options"],
        "real_variant_combinations": [variant["options"] for variant in product["variants"]],
        "variants": variants,
        "tags": product["tags"],
    }


def nfd() -> None:
    root = HERE / "nfd-abstract-tilly"
    raw_path = root / "raw" / "response.html"
    product = json.loads((root / "raw" / "product.js.json").read_text(encoding="utf-8"))
    raw_document = html.fromstring(raw_path.read_bytes().decode("utf-8", "replace"))
    rendered_record = sanitize_rendered_html(raw_path, root / "rendered.sanitized.html")
    details_blocks = [
        {"kind": "paragraph", "occurrence": 1, "text": "An abstract multicoloured print layered with gold brushstrokes and metallic flecks that catch the light. Cut from lightweight pleated fabric, it features a draped, voluminous bodice paired with a fitted midaxi skirt. Style with sandals, a beaded bag and statement jewellery for vacations, parties or summer weddings."},
        {"kind": "paragraph", "emphasis": "strong", "occurrence": 2, "text": "Garment can be worn off the shoulder or high on the shoulder. The elasticated waist allows you to adjust where the garment sits for a comfortable, personalized fit."},
        {"kind": "bullet", "occurrence": 1, "text": "Elasticated waistband"},
        {"kind": "bullet", "occurrence": 2, "text": "Pull on"},
        {"kind": "label_value", "occurrence": 1, "label": "Composition:", "value": "97% Polyester, 3% Elastane"},
        {"kind": "label_value", "occurrence": 1, "label": "Length:", "value": "131cm side neck point to hem"},
        {"kind": "paragraph", "emphasis": "strong", "occurrence": 3, "text": "Please Note - This length is based on our size 10 sample. Our products are graded, therefore smaller sizes will be shorter and larger sizes will be longer"},
        {"kind": "label_value", "occurrence": 1, "label": "Base Colour:", "value": "Multi"},
        {"kind": "label_value", "occurrence": 1, "label": "Wash Care:", "value": "30 Degree Wash"},
        {"kind": "paragraph", "occurrence": 4, "text": "XS= 4/6, S= 6/8, M = 10/12, L= 14/16, XL= 18/20, XXL = 22/24, XXXL = 26/28"},
        {"kind": "paragraph", "occurrence": 5, "text": "We’re more about the planet than we are perfection, so can’t guarantee the exact print placement shown here. This is down to how we cut the fabric to limit wastage."},
    ]
    sections = [
        {"order": 1, "source_heading": "Product Details & Fit", "blocks": details_blocks},
        {"order": 2, "source_heading": "Why Never Fully Dressed?", "blocks": [
            {"kind": "paragraph", "occurrence": 1, "text": "Never Fully Dressed is more than just a fashion brand. We’re a female-founded community that celebrates and empowers everybody."},
            {"kind": "paragraph", "occurrence": 2, "text": "We develop all fabrics, design all prints in-house, and inclusively offer all of our ranges in sizes UK 6-28, US 2-24 available globally and in our flagship London and New York stores."},
            {"kind": "paragraph", "occurrence": 3, "text": "We are passionate about feel good dressing. It is a beautiful tool to help our community unlock their confidence. We offer multi-wear product, creating styles with longevity and versatility."},
            {"kind": "paragraph", "occurrence": 4, "text": "Our customer is our influencer; We value their voice in our brand, taking inspiration from their stories and needs. Charity has always been at the heart of what we do, and our community has enabled us to help so many others…either supporting various causes financially, volunteering, or raising their voice. It is an arm of the brand, that the body would not serve without."},
        ]},
        {"order": 3, "source_heading": "Delivery & Returns", "blocks": [
            {"kind": "subheading", "occurrence": 1, "text": "Delivery & Returns"},
            {"kind": "paragraph", "occurrence": 1, "text": "Delivery: UK - Spend over £150 for Free shipping."},
            {"kind": "paragraph", "occurrence": 2, "text": "£3.95 delivery fee for orders under £150"},
            {"kind": "paragraph", "occurrence": 3, "text": "EU - Free shipping and duties included, when paying in your own currency"},
            {"kind": "paragraph", "occurrence": 4, "text": "International - Free Shipping"},
            {"kind": "paragraph", "occurrence": 5, "text": "Returns: Refunds available within 28 days (return fee applies)"},
            {"kind": "paragraph", "occurrence": 6, "text": "Free exchanges (UK Only)"},
            {"kind": "paragraph", "occurrence": 7, "text": "Get an extra 7% when choosing store credit"},
            {"kind": "paragraph", "occurrence": 8, "text": "We accept returns for scent items (i.e. perfumes, candles) that are damaged, faulty, or unopened."},
            {"kind": "paragraph", "occurrence": 9, "text": "Unfortunately, we are unable to accept returns if the plastic seal around the box has been removed."},
            {"kind": "paragraph", "occurrence": 10, "text": "Check out our Returns pages for up-to-date information."},
        ]},
        {"order": 4, "source_heading": "Reviews", "blocks": [{"kind": "label_value", "occurrence": 1, "label": "Reviews", "value": "70 reviews"}]},
    ]
    expected_section_absences = [
        {"heading": "Sustainability", "status": "PROVEN_ABSENT_AS_NAMED_SECTION"},
        {"heading": "Size & Fit", "status": "PROVEN_ABSENT_AS_SEPARATE_SECTION", "note": "fit facts occur inside Product Details & Fit and must remain there"},
    ]
    write_json(root / "sections.json", {"schema": "source-sections-v1", "sections": sections, "expected_section_absences": expected_section_absences})
    write_json(
        root / "size-guide.json",
        {
            "schema": "source-size-guide-v1",
            "basis": "BODY",
            "basis_evidence": "Items are sized to fit the following body measurements",
            "region": "UK",
            "tables": [{"order": 1, "category": "Dresses", "unit": "cm", "cells": table_cells(raw_document.xpath("//table")[0])}],
            "unit_controls": [
                {"unit": "CM", "status": "CAPTURED"},
                {"unit": "IN", "status": "ACQUISITION_GAP_CLIENT_SIDE_TRANSFORM_NOT_FROZEN"},
            ],
            "footnotes": [
                "Petite: 5'3” and under",
                "Regular: 5'4” and above",
                "Our size charts are based on the measurements shown. Use a tape measure and these guidelines to determine your size. A friend might come in handy to help you with measuring. If you don't have a tape measure, you can use a piece of string or ribbon and then measure it with a ruler. Please note: garments may vary due to design and manufacturing differences.",
            ],
            "excluded_tables": [{"indexes": [1, 2, 3, 4, 5, 6, 7, 8, 9], "reason": "other garment categories or bra guides; not the Dresses table selected for this PDP"}],
        },
    )
    structured = normalize_shopify_product(product, "GBP")
    structured["source_model"] = {"namespace": "competitor_only", "height": None, "worn_size": None, "target_fit_note_eligible": False}
    structured["seo"] = {"html_title": "Abstract Tilly Dress | Metallic Gold Fleck - Never Fully Dressed", "meta_description": "Designed in London, the Abstract Tilly Dress has gold brushstrokes, an elasticated waist and a pull-on fit for vacations, parties or summer weddings."}
    structured["description_html"] = product["description"]
    structured["colour_relations"] = [
        {"relation": "LINKED_SIBLING_PDP", "title": "Mara Abstract Tilly Dress", "product_id": "14975153111426", "path": "/products/mara-abstract-tilly-dress", "status": "UNOPENED_NOT_CAPTURED", "complete": False},
        {"relation": "LINKED_SIBLING_PDP", "title": "Burgundy Tilly Dress", "product_id": "14974776967554", "path": "/products/burgundy-tilly-dress", "status": "UNOPENED_NOT_CAPTURED", "complete": False},
        {"relation": "LINKED_SIBLING_PDP", "title": "Lucia Leopard Tilly Dress", "product_id": "14964209254786", "path": "/products/lucia-leopard-tilly-dress", "status": "UNOPENED_NOT_CAPTURED", "complete": False},
        {"relation": "LINKED_SIBLING_PDP", "title": "Animal Print Tilly Dress", "product_id": "15022002995586", "path": "/products/animal-print-tilly-dress", "status": "UNOPENED_NOT_CAPTURED", "complete": False},
        {"relation": "LINKED_SIBLING_PDP", "title": "Pastel Morocco Tilly Dress", "product_id": "15107976954242", "path": "/products/pastel-morocco-tilly-dress", "status": "UNOPENED_NOT_CAPTURED", "complete": False},
        {"relation": "LINKED_SIBLING_PDP", "title": "Fruit Tilly Dress", "product_id": "15107977183618", "path": "/products/fruit-tilly-dress", "status": "UNOPENED_NOT_CAPTURED", "complete": False},
    ]
    write_json(root / "structured-product.json", structured)
    structured_urls = [("https:" + value if value.startswith("//") else value) for value in product["images"]]
    structured_hashes = ["2624a9c906d1a875fac71945bfbcdedd3b64cf6e4275dac077e056a332cea699", "a7cf480c699191846ee35ad7585cb08b7773d304086c0408629f3562e8b8f085", "3be6b45649fa19ed381d50fb0157fc519a18595b273f1799e528d3d0d9ff330e", "8b4895328d548d4b28a152d93b0c26b5fcf14f24fb613a0f66c277ac9f9d46e6", "ebda6b4690d981e5d5fb15eac994c522e04d6bed6bd9fd8ea647df66131f8de1", "c1766d8a927eba4d762706962d187bfd3c7aed6d3a751375c2bafbb9f570c53e", "e25c6f2e5cde750ca2d0546d0bea045091954819bfac6ff863fe043369f89a6c", "e9bcbe6306551202c7d0de6af5b8fb1d4eec3a29a9c2224cfb70b2f04369cdf9", "b1e833e1d01d5229f7bbeaed42f7b942f90003be448adf185c8b104fe386d760"]
    rendered_hashes = ["28a685cb6147f1bbd118f93d438b9bc9fed256baca6e2babc26ea346d23bab1a", "c502eacabcda580c83e965c6c932399c62c58af14dbe2ba3e533c5750eabb50a", "ad8227dec4c7833119b1af4c523125c175bce2e6143a2d7b7f1cbb14ecb22a0e", "bb00e30d4797e85c34a6621eab37b7ab1ce4c87bfe8bb3a06b9e316e0b7596f7", "8c547540eccd45cc0b0191dbf59ccc22c61e13d8050d4e8bfbd7f3f9b39581a6", "48d84e10afb863ac7ae1ddba68b6f2944b346bde87404f63e8b4600d7d7de6b3", "eee47ed4c28762325f82c196cd7afcaa4e4f2afe7e571a92494d0782daad9f41", "e048a1893b9bb7326dbaaafc49a8bcbb32f33c1084d48df6aac5f00af22f04f3"]
    rendered_gallery = []
    for rendered_order, structured_order in enumerate(range(2, 10), 1):
        source = structured_urls[structured_order - 1]
        rendered_url = "https://scdn.speedsize.com/0dc5bf78-b39b-46d9-a247-2ffe3bfdc6ca/https://www.neverfullydressed.com/cdn/shop/files/" + source.split("/files/")[1] + "&width=10"
        rendered_gallery.append({"order": rendered_order, "structured_order": structured_order, "url": rendered_url, "content_sha256": rendered_hashes[rendered_order - 1], "colour_association": "Multi", "excluded": False})
    media = {
        "schema": "source-media-manifest-v1",
        "rendered_gallery": rendered_gallery,
        "structured_gallery": [{"order": i, "url": url, "content_sha256": structured_hashes[i - 1], "colour_association": "Multi", "excluded": i == 1, "exclusion_reason": "FEATURED_VARIANT_IMAGE_NOT_RENDERED_IN_EIGHT_ITEM_GALLERY" if i == 1 else None} for i, url in enumerate(structured_urls, 1)],
        "exclusions": [{"structured_order": 1, "reason": "present in structured product as featured/variant image; absent from rendered eight-item gallery"}],
    }
    write_json(root / "media-manifest.json", media)
    evidence_inputs = [
        Path("projects/engine-3/stores/ondine-london/output/product-listing-poki-experiment/runs/run-02-never-fully-dressed-abstract-tilly/independent-source-capture.md"),
        Path("projects/engine-3/stores/ondine-london/output/product-listing-poki-experiment/runs/run-02-never-fully-dressed-abstract-tilly/source-live-pdp-title-price-variants-2026-08-31.png"),
    ]
    invalid = Path("projects/engine-3/stores/ondine-london/output/product-listing-poki-experiment/runs/run-02-never-fully-dressed-abstract-tilly/shopify-duplicate-source-title-no-results-2026-08-31.png")
    write_json(root / "evidence-registry.json", {"schema": "evidence-registry-v1", "accepted": [{"path": str(p), "sha256": sha256_file(Path.cwd() / p)} for p in evidence_inputs], "invalid_preserved": [{"path": str(invalid), "sha256": sha256_file(Path.cwd() / invalid), "reason": "blank/incomplete screenshot; never denominator evidence"}]})
    conflicts: list[object] = []
    gaps = [
        {"code": "SIZE_GUIDE_INCH_UNIT_NOT_FROZEN", "severity": "BLOCKING", "detail": "IN control is present, but its client-side transformed cells were not captured."},
        {"code": "JSON_LD_NOT_FROZEN", "severity": "BLOCKING"},
        {"code": "LINKED_SIBLING_PDPS_UNOPENED", "severity": "EXPECTED_INCOMPLETE_RELATION", "count": 6},
        {"code": "SOURCE_MODEL_FACTS_ABSENT", "severity": "PROVEN_ABSENCE"},
        {"code": "FULL_UNSANITIZED_HTML_NOT_RETAINED", "severity": "SECURITY_REDACTION", "replacement": "rendered.sanitized.html"},
    ]
    bundle = {
        "schema": "source-capture-fixture-v1",
        "fixture_id": "nfd-abstract-tilly",
        "capture": {
            "requested_url": "https://www.neverfullydressed.com/en-gb/products/abstract-tilly-dress?country=GB",
            "final_url": "https://www.neverfullydressed.com/products/abstract-tilly-dress",
            "canonical_url": "https://www.neverfullydressed.com/products/abstract-tilly-dress",
            "market": "GB", "locale": "en-GB", "currency": "GBP", "captured_at": "2026-09-01T11:12:15Z", "attempt": 2,
            "rendered_html": rendered_record,
            "commerce_json": {"path": "raw/product.js.json", "sha256": sha256_file(root / "raw" / "product.js.json")},
            "json_ld": {"status": "ACQUISITION_GAP_NOT_FROZEN"},
        },
        "files": {"structured_product": "structured-product.json", "sections": "sections.json", "size_guide": "size-guide.json", "media": "media-manifest.json", "evidence": "evidence-registry.json"},
        "conflicts": conflicts,
        "absences": [{"field": "source_model.height", "status": "PROVEN_ABSENT"}, {"field": "source_model.worn_size", "status": "PROVEN_ABSENT"}],
        "acquisition_gaps": gaps,
        "status": "BLOCKED_DENOMINATOR",
    }
    write_json(root / "bundle.json", bundle)
    write_json(ORACLES / "nfd-abstract-tilly.expected.json", {"schema": "reviewer-owned-source-capture-oracle-v1", "fixture_id": "nfd-abstract-tilly", "author_role": "Scout", "reviewer_lock": {"status": "AWAITING_ATLAS_SIGNATURE", "locked_hash": None}, "expected": {"capture": deepcopy(bundle["capture"]), "structured_product": structured, "sections": sections, "expected_section_absences": expected_section_absences, "media": media, "conflicts": conflicts, "acquisition_gaps": gaps, "verdict": "BLOCKED_DENOMINATOR"}})
    raw_path.unlink()
    print(json.dumps({"fixture": "nfd-abstract-tilly", "bundle_index_sha256": write_hash_index(root), "oracle_sha256": sha256_file(ORACLES / "nfd-abstract-tilly.expected.json")}, indent=2))


def omnes() -> None:
    root = HERE / "omnes-bridie-sunset-blur"
    raw_path = root / "raw" / "response.html"
    product = json.loads((root / "raw" / "product.js.json").read_text(encoding="utf-8"))
    raw_document = html.fromstring(raw_path.read_bytes().decode("utf-8", "replace"))
    rendered_record = sanitize_rendered_html(raw_path, root / "rendered.sanitized.html")
    sections = [
        {"order": 1, "source_heading": "Sustainability", "blocks": [
            {"kind": "paragraph", "occurrence": 1, "text": "Made with Recycled Polyester"},
            {"kind": "paragraph", "occurrence": 2, "text": "Labels made from recycled plastic bottles"},
            {"kind": "paragraph", "occurrence": 3, "text": "Made in Vietnam at a fully audited factory"},
        ]},
        {"order": 2, "source_heading": "Description", "blocks": [
            {"kind": "paragraph", "occurrence": 1, "text": "Bridie is elegant but flirty. Designed in floaty chiffon, this hot pink floral maxi dress features a high boat neck and long fluted sheer sleeves. The fully lined top balances the lightness of the sleeve, whilst the skirt falls into a tiered frill hem for soft volume and movement. Bridie is made for occasions that call for understated impact."},
        ]},
        {"order": 3, "source_heading": "Size & Fit", "blocks": [
            {"kind": "label_value", "occurrence": 1, "label": "Model size:", "value": "UK 8/US 4/EU 36", "namespace": "competitor_only", "target_fit_note_eligible": False},
            {"kind": "label_value", "occurrence": 1, "label": "Model height:", "value": "5'9.5 / 176cm", "namespace": "competitor_only", "target_fit_note_eligible": False},
            {"kind": "fit_fact", "occurrence": 1, "text": "Regular"},
            {"kind": "fit_fact", "occurrence": 2, "text": "Regular"},
        ]},
        {"order": 4, "source_heading": "Details & Care", "blocks": [
            {"kind": "paragraph", "occurrence": 1, "text": "Shell: 100% Recycled Polyester Lining: 100% Recycled Polyester"},
            {"kind": "care_instruction", "occurrence": 1, "text": "Machine delicate wash on 30 degrees"},
            {"kind": "care_instruction", "occurrence": 2, "text": "Wash with similar colours"},
            {"kind": "care_instruction", "occurrence": 3, "text": "Do not tumble dry"},
            {"kind": "care_instruction", "occurrence": 4, "text": "Warm iron & iron on reverse"},
            {"kind": "care_instruction", "occurrence": 5, "text": "Use eco detergents"},
            {"kind": "paragraph", "occurrence": 2, "text": "We strive to achieve the utmost consistency in production, colour variations may occur."},
            {"kind": "paragraph", "occurrence": 3, "text": "This is due to fabric availability and the nature of our viscose fabric."},
        ]},
    ]
    write_json(root / "sections.json", {"schema": "source-sections-v1", "sections": sections, "expected_section_absences": []})
    write_json(root / "size-guide.json", {"schema": "source-size-guide-v1", "basis": "GARMENT", "basis_evidence": "product-specific Length, Bust, Waist and Hem values across all offered UK sizes", "tables": [{"order": 1, "unit": "cm", "cells": table_cells(raw_document.xpath("//table")[0])}, {"order": 2, "unit": "in", "cells": table_cells(raw_document.xpath("//table")[1])}], "footnotes": [], "complete_for_options": ["4", "6", "8", "10", "12", "14", "16", "18"]})
    structured = normalize_shopify_product(product, "GBP")
    structured["description_html"] = product["description"]
    structured["seo"] = {"html_title": "Bridie Dress in Sunset Blur Print – OMNES", "meta_description": "Bridie is elegant but flirty. Designed in floaty chiffon, this hot pink floral maxi dress features a high boat neck and long fluted sheer sleeves. The fully lined top balances the lightness of the sleeve, whilst the skirt falls into a tiered frill hem for soft volume and movement. Bridie is made for occasions that call for understated impact."}
    structured["source_model"] = {"namespace": "competitor_only", "height": "5'9.5 / 176cm", "worn_size": "UK 8/US 4/EU 36", "target_fit_note_eligible": False}
    structured["colour_relations"] = [
        {"relation": "LINKED_SIBLING_PDP", "title": "Bridie Dress in Black Polka Dot", "product_id": "9081571049696", "path": "/products/bridie-dress-in-black-polka-dot", "swatch_image": "Bridie-Dress-Black-Polka-Dot-9081571049696_007.jpg", "status": "UNOPENED_NOT_CAPTURED", "complete": False}
    ]
    write_json(root / "structured-product.json", structured)
    structured_urls = [("https:" + value if value.startswith("//") else value) for value in product["images"]]
    hashes = ["d027a47f5540b6bab839bfd424080886a96cc2a5215d0a452d8e31cad446961c", "8bdfb6ddd4c76401c2169ee74c1d0d6373810cbddbbc33813e8ff91629808622", "bfe1eb26620429de29342e78e4b19137a3ca5d61dda9bee9233b35bf30629944", "fbdaa861acd08de600bab2dc89b16491708414d5e40c1dfb3c3fd955c3851e57", "334f93193b4877b87ec02b1e97a0e233b20f7ba58784a7107087d7963c755587"]
    rendered_urls = []
    for value in structured_urls:
        filename_and_query = value.rsplit("/files/", 1)[1]
        filename, query = filename_and_query.split("?", 1)
        rendered_urls.append(f"https://www.omnes.com/cdn/shop/files/{filename}?crop=center&height=2048&{query}&width=1536")
    media = {
        "schema": "source-media-manifest-v1",
        "rendered_gallery": [{"order": i, "url": url, "content_sha256": hashes[i - 1], "colour_association": "Sunset Blur Print", "excluded": False} for i, url in enumerate(rendered_urls, 1)],
        "structured_gallery": [{"order": i, "url": url, "content_sha256": hashes[i - 1], "colour_association": "Sunset Blur Print", "excluded": False} for i, url in enumerate(structured_urls, 1)],
        "exclusions": [],
    }
    write_json(root / "media-manifest.json", media)
    run = Path("projects/engine-3/stores/ondine-london/output/product-listing-poki-experiment/runs/run-03-omnes-bridie-sunset-blur")
    accepted_names = ["independent-source-capture.md", "source-live-gbp-title-price-sizes-2026-09-01.png", "source-live-materials-care-2026-09-01.png", "source-live-model-size-fit-2026-09-01.png", "shopify-final-draft-and-disabled-save-accepted-2026-09-01T101052+0100.png"]
    rejected_reasons = {
        "shopify-replacement-live-read-draft-no-unsaved-2026-09-01.png": "REJECTED_UNRELATED_LOGITECH_SCREEN_MISLABELED_AS_SHOPIFY_PROOF",
        "shopify-final-draft-no-unsaved-verified-2026-09-01T1010.png": "REJECTED_UNRELATED_DOLPHIN_SCREEN",
        "shopify-final-draft-no-unsaved-verified-2026-09-01T1014.png": "REJECTED_UNRELATED_CLICKUP_SCREEN",
        "shopify-final-draft-no-unsaved-verified-2026-09-01T1017.png": "REJECTED_INCOMPLETE_STATUS_OR_SAVE_PROOF",
        "shopify-final-draft-no-unsaved-verified-2026-09-01T1020.png": "REJECTED_INCOMPLETE_STATUS_OR_SAVE_PROOF",
        "shopify-final-draft-no-unsaved-verified-2026-09-01T1022.png": "REJECTED_INCOMPLETE_STATUS_OR_SAVE_PROOF",
        "shopify-final-draft-no-unsaved-verified-2026-09-01T1025.png": "REJECTED_UNRELATED_MISSION_CONTROL_OR_3D_SCREEN",
        "shopify-final-draft-no-unsaved-verified-2026-09-01T1028.png": "REJECTED_INCOMPLETE_STATUS_OR_SAVE_PROOF",
        "shopify-final-draft-and-disabled-save-side-by-side-verified-2026-09-01T1035.png": "REJECTED_PARTIAL_OR_MISTIMESTAMPED_SIDE_BY_SIDE",
        "shopify-final-draft-and-disabled-save-side-by-side-verified-2026-09-01T1038.png": "REJECTED_PARTIAL_OR_MISTIMESTAMPED_SIDE_BY_SIDE",
        "display2-test.png": "REJECTED_DISPLAY_TEST_NOT_EVIDENCE",
    }
    write_json(root / "evidence-registry.json", {
        "schema": "evidence-registry-v1",
        "accepted": [{"path": str(run / name), "sha256": sha256_file(Path.cwd() / run / name), "scope": "source_fixture" if name.startswith("source-") or name.endswith("capture.md") else "historical_shopify_status_only_not_source_denominator"} for name in accepted_names],
        "invalid_preserved": [{"path": str(run / name), "sha256": sha256_file(Path.cwd() / run / name), "reason": reason} for name, reason in rejected_reasons.items()],
    })
    conflicts = [
        {"code": "MATERIAL_POLYESTER_VS_VISCOSE", "severity": "BLOCKING", "claims": ["Shell: 100% Recycled Polyester Lining: 100% Recycled Polyester", "This is due to fabric availability and the nature of our viscose fabric."], "resolution": "UNRESOLVED_DO_NOT_PUBLISH_MATERIAL_CLAIM"},
    ]
    gaps = [
        {"code": "LINKED_SIBLING_PDP_UNOPENED", "severity": "EXPECTED_INCOMPLETE_RELATION", "product_id": "9081571049696"},
        {"code": "JSON_LD_NOT_FROZEN", "severity": "BLOCKING"},
        {"code": "FULL_UNSANITIZED_HTML_NOT_RETAINED", "severity": "SECURITY_REDACTION", "replacement": "rendered.sanitized.html"},
    ]
    bundle = {
        "schema": "source-capture-fixture-v1",
        "fixture_id": "omnes-bridie-sunset-blur",
        "capture": {
            "requested_url": "https://www.omnes.com/products/bridie-dress-in-sunset-blur-print-cam?country=GB",
            "final_url": "https://www.omnes.com/products/bridie-dress-in-sunset-blur-print-cam?country=GB",
            "canonical_url": "https://www.omnes.com/products/bridie-dress-in-sunset-blur-print-cam",
            "market": "GB", "locale": "en-GB", "currency": "GBP", "captured_at": "2026-09-01T11:12:16Z", "attempt": 2,
            "rendered_html": rendered_record,
            "commerce_json": {"path": "raw/product.js.json", "sha256": sha256_file(root / "raw" / "product.js.json")},
            "json_ld": {"status": "ACQUISITION_GAP_NOT_FROZEN"},
        },
        "files": {"structured_product": "structured-product.json", "sections": "sections.json", "size_guide": "size-guide.json", "media": "media-manifest.json", "evidence": "evidence-registry.json"},
        "conflicts": conflicts,
        "absences": [],
        "acquisition_gaps": gaps,
        "status": "EXPECTED_BLOCKER_FIXTURE",
    }
    write_json(root / "bundle.json", bundle)
    write_json(ORACLES / "omnes-bridie-sunset-blur.expected.json", {"schema": "reviewer-owned-source-capture-oracle-v1", "fixture_id": "omnes-bridie-sunset-blur", "author_role": "Scout", "reviewer_lock": {"status": "AWAITING_ATLAS_SIGNATURE", "locked_hash": None}, "expected": {"capture": deepcopy(bundle["capture"]), "structured_product": structured, "sections": sections, "expected_section_absences": [], "media": media, "conflicts": conflicts, "acquisition_gaps": gaps, "verdict": "EXPECTED_BLOCKER_FIXTURE"}})
    raw_path.unlink()
    print(json.dumps({"fixture": "omnes-bridie-sunset-blur", "bundle_index_sha256": write_hash_index(root), "oracle_sha256": sha256_file(ORACLES / "omnes-bridie-sunset-blur.expected.json")}, indent=2))


if __name__ == "__main__":
    if (HERE / "phase-eight-avenly" / "raw" / "response.html").exists():
        phase_eight()
    if (HERE / "nfd-abstract-tilly" / "raw" / "response.html").exists():
        nfd()
    if (HERE / "omnes-bridie-sunset-blur" / "raw" / "response.html").exists():
        omnes()
