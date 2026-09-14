#!/usr/bin/env python3
"""Build the frozen Nobody's Child Calloway positive-denominator bundle offline."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree, html


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
ORACLES = ROOT.parents[1] / "oracles"
FIXTURE_ID = "nobodys-child-calloway"
CAPTURED_AT = "2026-09-01T11:35:24Z"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_text(node: etree._Element) -> str:
    return " ".join(node.text_content().split())


raw_html = RAW / "response.html"
raw_html_sha = sha(raw_html)
assert raw_html_sha == "9847e284e6d526b707fb1351d52120ba22e2e3438610e351305c6a11937cbbd3"
source_bytes = raw_html.read_bytes()
document = html.fromstring(source_bytes)
product = json.loads((RAW / "product.js.json").read_text(encoding="utf-8"))
cart_currency = json.loads((RAW / "cart.currency.json").read_text(encoding="utf-8"))
size_api = json.loads((RAW / "size-guide.api.json").read_text(encoding="utf-8"))
media_hashes = json.loads((RAW / "media-content-hashes.json").read_text(encoding="utf-8"))

assert product["id"] == 15364155539841
assert product["title"] == "Navy Embroidered Tiered Calloway Midi Dress"
assert product["price"] == 5500 and product["compare_at_price"] == 13900
assert cart_currency == {"currency": "GBP", "item_count": 0, "total_price": 0, "items_subtotal_price": 0}
assert len(product["variants"]) == 16
assert len(product["media"]) == 5
assert size_api["sizings"][0]["id"] == 2100276


# Freeze the one source Product JSON-LD block before sanitising executable HTML.
jsonld_nodes = document.xpath("//script[@type='application/ld+json']")
assert len(jsonld_nodes) == 1
jsonld = json.loads(jsonld_nodes[0].text)
assert jsonld["@type"] == "Product"
assert jsonld["offers"]["price"] == "55.00"
assert jsonld["offers"]["priceCurrency"] == "GBP"
assert jsonld["aggregateRating"] == {
    "@type": "AggregateRating",
    "ratingValue": "4.6",
    "reviewCount": "25",
    "bestRating": "5",
    "worstRating": "1",
}
write_json(ROOT / "product.jsonld.json", jsonld)


# Sanitize the complete server-rendered document, retaining source content and order.
sanitized = html.fromstring(source_bytes)
removed_nodes = {name: 0 for name in ("script", "style", "noscript", "iframe", "form", "input")}
for name in removed_nodes:
    nodes = sanitized.xpath(f"//{name}")
    removed_nodes[name] = len(nodes)
    for node in nodes:
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)

sensitive = re.compile(
    r"(?i)(access[_-]?token|client[_-]?secret|api[_-]?key|authorization|credential|"
    r"session|cart|checkout|customer|email|_gl(?:=|\b)|gclid)"
)
stripped_sensitive_attributes = []
for node in sanitized.iter():
    for attribute, value in list(node.attrib.items()):
        if sensitive.search(attribute) or sensitive.search(value or ""):
            stripped_sensitive_attributes.append({"tag": node.tag, "attribute": attribute})
            del node.attrib[attribute]

sanitized_bytes = etree.tostring(sanitized, encoding="utf-8", method="html", pretty_print=True)
secret_scan = re.compile(r"(?i)(access[_-]?token|client[_-]?secret|api[_-]?key|authorization:\s*bearer|credential[_-]?secret)")
assert not secret_scan.search(sanitized_bytes.decode("utf-8", errors="replace"))
(ROOT / "rendered.sanitized.html").write_bytes(sanitized_bytes)


description = clean_text(document.xpath("//*[contains(concat(' ',normalize-space(@class),' '),' product-page__details--item-description-paragraph ')]")[0])
model_line = clean_text(document.xpath("//*[contains(concat(' ',normalize-space(@class),' '),' product-page__details--model-size ')]")[0])
assert description == (
    "This piece is part of the Nobody's Child x Elizabeth Scarlett Collection, a London-based brand known for nature-inspired designs. "
    "Made from double gauze cotton in our icon silhouette, this navy midi dress is designed with sun goddess embroidery and intricate "
    "laddering. It features a shirred bodice and a relaxed skirt with pockets.\u200b"
)
assert model_line == "Model's height is 5'9\" - she wears a UK size 8. Wearing length is: 140cm"

details_root = document.xpath("//*[contains(concat(' ',normalize-space(@class),' '),' accordion-details-tab ')]")[0]
detail_bullets = [clean_text(item) for item in details_root.xpath(".//ul/li")]
expected_bullets = [
    "Embroidery designed in collaboration with Elizabeth Scarlett\u200b",
    "Round neck\u200b",
    "Sleeveless\u200b",
    "Shirred bodice \u200b",
    "Elasticated waist\u200b",
    "Side pockets\u200b",
    "Relaxed skirt\u200b",
    "Tiered skirt\u200b",
    "Ruffle trim\u200b",
    "Lightly lined\u200b \u200b",
    "Available in regular and petite. Under 5’3\"? Find out more about petite sizing here",
    "Find out more about Nobody’s Child x Elizabeth Scarlett and shop the full collection",
]
assert detail_bullets == expected_bullets

variants = []
for variant in product["variants"]:
    variants.append(
        {
            "id": str(variant["id"]),
            "combination": variant["options"],
            "sku": variant["sku"],
            "barcode": variant["barcode"],
            "available": variant["available"],
            "price": "55.00",
            "compare_at": "139.00",
            "weight_grams": variant["weight"],
        }
    )

structured_product = {
    "schema": "structured-product-v1",
    "source_class": "CONSUMER_RETAILER",
    "product_id": str(product["id"]),
    "handle": product["handle"],
    "item": "2616171001",
    "title": product["title"],
    "vendor": product["vendor"],
    "product_type": product["type"],
    "tags": product["tags"],
    "seo": {
        "html_title": clean_text(document.xpath("//title")[0]),
        "meta_description": document.xpath("//meta[@name='description']/@content")[0],
    },
    "currency": "GBP",
    "price": {"current": "55.00", "compare_at": "139.00"},
    "promotion": {"text": "60% off", "mathematical_discount_percent": "60.43", "displayed_exactly": True},
    "options": product["options"],
    "real_variant_combinations": [variant["options"] for variant in product["variants"]],
    "variants": variants,
    "availability": {"product_available": product["available"], "variant_level_frozen": True},
    "description": description,
    "source_model": {
        "namespace": "competitor_only",
        "source_line": model_line,
        "height": "5'9\"",
        "worn_size": "UK size 8",
        "wearing_length": "140cm",
        "target_fit_note_eligible": False,
    },
    "colour": "Navy",
    "colour_relations": [
        {
            "relation": "SELF_ONLY_SINGLE_COLOUR",
            "title": product["title"],
            "url": "https://www.nobodyschild.com/products/calloway-midi-dress-2616171001",
            "aria_current": "page",
            "complete": True,
            "note": "The rendered selector states 1 Colours available and contains only the canonical PDP itself; no sibling PDP is represented.",
        }
    ],
    "identifiers": {
        "primary_sku": product["variants"][0]["sku"],
        "primary_gtin": product["variants"][0]["barcode"],
        "all_variant_skus_and_gtins_frozen": True,
    },
    "same_session_commerce_evidence": {
        "product_json": "raw/product.js.json",
        "cart_currency_json": "raw/cart.currency.json",
        "currency": cart_currency["currency"],
        "json_ld_currency": jsonld["offers"]["priceCurrency"],
        "rendered_price_currency_symbol": "£",
        "content_language_header": "en-GB",
        "cookie_names_observed_not_values": [
            "_shopify_analytics", "_shopify_essential", "_shopify_marketing", "_shopify_s", "_shopify_y", "cart_currency", "localization"
        ],
    },
}
write_json(ROOT / "structured-product.json", structured_product)


def block(kind: str, occurrence: int, **values: object) -> dict[str, object]:
    return {"kind": kind, "occurrence": occurrence, **values}


delivery = document.xpath("//*[contains(concat(' ',normalize-space(@class),' '),' accordion-delivery-and-returns ')]")[0]
delivery_items = [clean_text(item) for item in delivery.xpath(".//div[1]//li")]
return_paragraphs = [clean_text(item) for item in delivery.xpath(".//div[2]//p")]
sections = {
    "schema": "source-sections-v1",
    "sections": [
        {
            "order": 1,
            "source_heading": "Product description",
            "normalized_role": "DESCRIPTION",
            "blocks": [block("paragraph", 1, text=description)],
        },
        {
            "order": 2,
            "source_heading": "Details",
            "normalized_role": "DETAILS",
            "blocks": [
                block("subheading", 1, text="Details"),
                *[block("bullet", index, text=text) for index, text in enumerate(detail_bullets, 1)],
                block("label_value", 1, label="Country of Manufacture", value="India"),
            ],
        },
        {
            "order": 3,
            "source_heading": "Fabric & care",
            "normalized_role": "COMPOSITION_AND_CARE",
            "blocks": [
                block("label_value", 1, label="Fabric", value="Main: 100% Cotton | Lining: 100% Cotton | Embroidery: 100% Polyester | Embroidery 2: 73% Polyester, 27% Metallised Fibre"),
                block("label_value", 2, label="Washcare", value="Machine Wash"),
                block("label_value", 3, label="Item", value="2616171001"),
            ],
        },
        {
            "order": 4,
            "source_heading": "Delivery & returns",
            "normalized_role": "RETAILER_POLICY_EVIDENCE_ONLY",
            "target_composer_eligible": False,
            "blocks": [
                block("subheading", 1, text="Delivery Information"),
                *[block("bullet", index, text=text) for index, text in enumerate(delivery_items, 1)],
                block("subheading", 2, text="Return Information"),
                *[block("paragraph", index, text=text) for index, text in enumerate(return_paragraphs, 1)],
            ],
        },
    ],
    "expected_section_absences": [
        {"section": "separate Size & Fit PDP accordion", "status": "PROVEN_ABSENT", "basis": "Rendered PDP accordion contains only Details, Fabric & care, and Delivery & returns; size/model evidence is frozen separately."},
        {"section": "separate Sustainability PDP accordion", "status": "PROVEN_ABSENT", "basis": "No product accordion with this heading; retailer transparency/editorial claims are evidence-only exclusions."},
    ],
}
write_json(ROOT / "sections.json", sections)


sizing = size_api["sizings"][0]
table = sizing["tables"]["PcbHfA2"]
layout = sizing["layout"]["data"]
layout_blocks = []
for index, item in enumerate(layout, 1):
    if item["type"] == 1:
        layout_blocks.append({"order": index, "kind": "table_reference", "table_id": item["value"]})
    elif item["type"] == 6:
        layout_blocks.append({"order": index, "kind": "image", "url": item["data"]["url"], "content_sha256": media_hashes["items"][5]["structured"]["sha256"]})
    elif item["type"] in (0, 8):
        fragment = html.fragment_fromstring(item["value"], create_parent="div")
        parsed = []
        for node in fragment.xpath(".//p|.//li|.//button"):
            text = clean_text(node)
            if text:
                parsed.append({"kind": "bullet" if node.tag == "li" else "control" if node.tag == "button" else "paragraph", "text": text})
        layout_blocks.append({
            "order": index,
            "kind": "hidden_control" if item["type"] == 8 else "rich_text",
            "source_html": item["value"],
            "parsed_blocks": parsed,
            "target_composer_eligible": item["type"] != 8,
        })

size_guide = {
    "schema": "source-size-guide-v1",
    "status": "COMPLETE",
    "provider": "KiwiSizing",
    "source_endpoint": "https://app.kiwisizing.com/api/getSizingChart",
    "sizing_id": str(sizing["id"]),
    "name": sizing["name"],
    "enabled": sizing["isEnabled"],
    "measurement_basis": "BODY",
    "tables": [
        {
            "id": "PcbHfA2",
            "direction": table["direction"],
            "rows": table["data"],
            "dimensions": {"rows": len(table["data"]), "columns": len(table["data"][0])},
            "country_sizes": table["countrySizes"],
            "canonical_authored_measurement_unit": "cm",
            "authored_inch_table_status": "PROVEN_ABSENT",
            "footnotes": [],
            "footnote_status": "PROVEN_ABSENT",
        }
    ],
    "layout_blocks": layout_blocks,
    "complete_content_checks": {
        "how_to_measure_paragraphs": 6,
        "petite_intro_paragraphs": 3,
        "petite_adjustment_bullets": 11,
        "illustration_hashed": True,
        "hidden_select_size_control_excluded": True,
    },
}
assert size_guide["tables"][0]["dimensions"] == {"rows": 5, "columns": 12}
assert sum(len(block.get("parsed_blocks", [])) for block in layout_blocks if block["kind"] == "rich_text") >= 20
write_json(ROOT / "size-guide.json", size_guide)


rendered_gallery = []
structured_gallery = []
for source_media, hashes in zip(product["media"], media_hashes["items"][:5]):
    assert source_media["position"] == hashes["position"]
    rendered_gallery.append(
        {
            "order": hashes["position"],
            "url": hashes["rendered"]["requested_url"],
            "content_sha256": hashes["rendered"]["sha256"],
            "bytes": hashes["rendered"]["bytes"],
            "colour_association": "Navy",
            "excluded": False,
        }
    )
    structured_gallery.append(
        {
            "order": source_media["position"],
            "media_id": str(source_media["id"]),
            "url": source_media["src"],
            "content_sha256": hashes["structured"]["sha256"],
            "bytes": hashes["structured"]["bytes"],
            "width": source_media["width"],
            "height": source_media["height"],
            "colour_association": "Navy",
            "excluded": False,
        }
    )

media_manifest = {
    "schema": "source-media-manifest-v1",
    "rendered_gallery": rendered_gallery,
    "structured_gallery": structured_gallery,
    "orders_match": [item["url"].split("/")[-1].split("?")[0] for item in rendered_gallery] == [item["url"].split("/")[-1].split("?")[0] for item in structured_gallery],
    "gallery_count": 5,
    "explicit_exclusions": [
        {"class": "product-page__shop-the-look", "reason": "related products, not Calloway product media"},
        {"class": "product-card__image", "reason": "recommendation carousel, not Calloway product media"},
        {"class": "pdp-review", "reason": "review imagery and review UI are not product-gallery media"},
        {"class": "navigation/editorial/footer imagery", "reason": "page chrome and collection editorial are outside the product gallery"},
        {"class": "colour-selector thumbnail duplicates", "reason": "self-only colour navigation duplicates gallery item 1"},
    ],
}
assert media_manifest["orders_match"] is True
write_json(ROOT / "media-manifest.json", media_manifest)


trust_claims = [clean_text(node) for node in document.xpath("//*[contains(concat(' ',normalize-space(@class),' '),' product-page__details--transparency-icons-info ')]")]
editorial = document.xpath("//*[contains(concat(' ',normalize-space(@class),' '),' media-and-text__texts ')]")[0]
editorial_blocks = []
for node in editorial.xpath(".//*[self::h1 or self::h2 or self::h3 or self::p or contains(@class,'quote')]"):
    text = clean_text(node)
    if text and text not in editorial_blocks:
        editorial_blocks.append(text)

evidence_registry = {
    "schema": "source-evidence-registry-v1",
    "acquisition": {
        "bounded_passes_used": 3,
        "pass_1": {
            "mode": "single in-memory public HTTP session",
            "artifacts": ["raw/response.html (sanitized replacement retained)", "raw/product.js.json", "raw/cart.currency.json"],
            "requested_final_url": "https://www.nobodyschild.com/products/calloway-midi-dress-2616171001?country=GB",
            "http_status": 200,
            "content_language": "en-GB",
            "same_session": True,
            "cookies_persisted": False,
            "token_bearing_cart_response_original_sha256": "a04ff9f34c87547d7849273e7ff5aef211c3e287dfa5eaa76f27e3d73e58ab38",
            "token_bearing_cart_response_retained": False,
            "sanitized_cart_currency_subset_sha256": sha(RAW / "cart.currency.json"),
        },
        "pass_2": {
            "mode": "public provider client-code endpoint discovery",
            "provider_script_sha256": "269b02dd94eec13db901bf1d10843df0ac24815338cc9b6ef9e06e3fd0adbc23",
            "provider_script_retained": False,
            "discovered_endpoint": "https://app.kiwisizing.com/api/getSizingChart",
        },
        "pass_3": {
            "mode": "bounded official size-chart endpoint plus enumerated source-media byte hashing",
            "size_guide_response_sha256": sha(RAW / "size-guide.api.json"),
            "media_hash_manifest_sha256": sha(RAW / "media-content-hashes.json"),
            "further_live_acquisition_permitted": False,
        },
    },
    "price_provenance": {
        "rendered": {"current": "£55.00", "struck": "£139.00", "promo": "60% off"},
        "commerce_json_minor_units": {"current": 5500, "compare_at": 13900},
        "json_ld": {"current": "55.00", "currency": "GBP"},
        "currency_cart_json": "GBP",
    },
    "reviews_evidence_only": {
        "aggregate": {"rating": "4.6", "review_count": "25", "best": "5", "worst": "1"},
        "provenance": ["rendered PDP review summary", "Product JSON-LD aggregateRating"],
        "individual_review_bodies": "NOT_SERVER_RENDERED_IN_CAPTURE",
        "target_composer_eligible": False,
        "exclusion_reason": "Customer reviews are evidence-only and never source copy inputs.",
    },
    "retailer_sustainability_and_trust_evidence_only": {
        "transparency_claims": trust_claims,
        "editorial_blocks": editorial_blocks,
        "target_composer_eligible": False,
        "exclusion_reason": "Retailer packaging, factory-audit, collaboration, donation and conservation claims require target-specific substantiation and are not composer inputs.",
    },
    "explicit_exclusions": [
        "all reviews and ratings",
        "Recycled Packaging and Audited Factory transparency claims",
        "£15,000 Blue Marine Foundation donation/conservation claim and collaboration editorial",
        "delivery/returns policy as target copy",
        "shop-the-look products and all their facts/model/media",
        "recommendation carousels and review media",
        "navigation, announcements, wishlist, footer/newsletter and collection editorial media",
        "hidden size-guide Select Size control",
    ],
    "invalid_or_sensitive_evidence": [
        {
            "artifact": "raw cart response containing an ephemeral cart token",
            "status": "REJECTED_AND_DELETED",
            "original_sha256": "a04ff9f34c87547d7849273e7ff5aef211c3e287dfa5eaa76f27e3d73e58ab38",
            "replacement": "raw/cart.currency.json",
        },
        {
            "artifact": "unsanitized rendered HTML",
            "status": "REJECTED_FROM_BUNDLE_AND_DELETED_AFTER_EXTRACTION",
            "original_sha256": raw_html_sha,
            "replacement": "rendered.sanitized.html",
        },
    ],
    "acquisition_gaps": [],
}
assert any("£15,000 to Blue Marine Foundation" in block for block in editorial_blocks)
write_json(ROOT / "evidence-registry.json", evidence_registry)


bundle = {
    "schema": "source-capture-fixture-v1",
    "fixture_id": FIXTURE_ID,
    "capture": {
        "requested_url": "https://www.nobodyschild.com/products/calloway-midi-dress-2616171001?country=GB",
        "final_url": "https://www.nobodyschild.com/products/calloway-midi-dress-2616171001?country=GB",
        "canonical_url": "https://www.nobodyschild.com/products/calloway-midi-dress-2616171001",
        "market": "GB",
        "locale": "en-GB",
        "currency": "GBP",
        "captured_at": CAPTURED_AT,
        "attempt": 3,
        "rendered_html": {
            "mode": "SANITIZED_SERVER_RENDERED_HTML",
            "original_raw_sha256": raw_html_sha,
            "original_raw_retained": False,
            "sanitized_sha256": sha(ROOT / "rendered.sanitized.html"),
            "removed_nodes": removed_nodes,
            "stripped_sensitive_attribute_count": len(stripped_sensitive_attributes),
            "security_note": "Complete server-rendered document with scripts, styles, frames, forms/inputs and token/session/cart/checkout/customer/email/tracking-bearing attributes removed; product content and order retained.",
        },
        "json_ld": {"status": "FROZEN", "path": "product.jsonld.json", "sha256": sha(ROOT / "product.jsonld.json")},
        "same_session_commerce_json": {
            "status": "FROZEN",
            "product_path": "raw/product.js.json",
            "cart_currency_path": "raw/cart.currency.json",
            "currency": "GBP",
        },
    },
    "files": {
        "structured_product": "structured-product.json",
        "sections": "sections.json",
        "size_guide": "size-guide.json",
        "media": "media-manifest.json",
        "evidence": "evidence-registry.json",
    },
    "conflicts": [],
    "absences": sections["expected_section_absences"] + [
        {"field": "linked_sibling_colour_pdp", "status": "PROVEN_ABSENT", "basis": "Rendered 1 Colours available selector links only to aria-current canonical self."},
        {"field": "authored_size_guide_inch_table", "status": "PROVEN_ABSENT", "basis": "Official sizing response contains only cm cells; measurement instructions mention a dual-unit tape but do not provide inch cells."},
        {"field": "size_guide_footnotes", "status": "PROVEN_ABSENT", "basis": "Official sizing table and layout contain no footnote block."},
    ],
    "acquisition_gaps": [],
    "status": "POSITIVE_DENOMINATOR_COMPLETE",
}
write_json(ROOT / "bundle.json", bundle)


oracle = {
    "schema": "reviewer-owned-source-capture-oracle-v1",
    "fixture_id": FIXTURE_ID,
    "author_role": "Scout",
    "reviewer_lock": {"status": "AWAITING_ATLAS_SIGNATURE", "locked_hash": None},
    "expected": {
        "capture": bundle["capture"],
        "structured_product": structured_product,
        "sections": sections["sections"],
        "expected_absences": bundle["absences"],
        "media": media_manifest,
        "size_guide": size_guide,
        "evidence_only_exclusions": {
            "reviews": evidence_registry["reviews_evidence_only"],
            "retailer_sustainability_and_trust": evidence_registry["retailer_sustainability_and_trust_evidence_only"],
            "explicit_exclusions": evidence_registry["explicit_exclusions"],
        },
        "conflicts": [],
        "acquisition_gaps": [],
        "status": "POSITIVE_DENOMINATOR_COMPLETE",
    },
}
write_json(ORACLES / f"{FIXTURE_ID}.expected.json", oracle)


# Delete only the unsafe, newly acquired raw HTML after all extracted evidence exists.
raw_html.unlink()

index_files = [
    "bundle.json",
    "rendered.sanitized.html",
    "product.jsonld.json",
    "structured-product.json",
    "sections.json",
    "size-guide.json",
    "media-manifest.json",
    "evidence-registry.json",
    "raw/product.js.json",
    "raw/cart.currency.json",
    "raw/size-guide.api.json",
    "raw/media-content-hashes.json",
    "fetch-size-guide-pass3.py",
    "fetch-media-pass3.py",
    "build-bundle.py",
]
lines = [f"{sha(ROOT / relative)}  {relative}" for relative in index_files]
(ROOT / "bundle-files.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "fixture_id": FIXTURE_ID,
    "status": bundle["status"],
    "bundle_sha256": sha(ROOT / "bundle.json"),
    "bundle_index_sha256": sha(ROOT / "bundle-files.sha256"),
    "oracle_sha256": sha(ORACLES / f"{FIXTURE_ID}.expected.json"),
    "acquisition_gaps": [],
}, indent=2))
