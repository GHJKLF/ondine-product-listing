"""Offline adapter tests; no browser or network is used."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from product_listing.adapters.jsonld_dom import JsonLdDomAdapter  # noqa: E402
from product_listing.adapters.shopify_ajax import ShopifyAjaxAdapter  # noqa: E402
from product_listing.models import ColourRelationType, SectionRole  # noqa: E402


CAPTURED_AT = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


class SourceAdapterTest(unittest.TestCase):
    def test_dom_and_jsonld_preserve_sections_tables_media_and_four_dimensions(self):
        html = """
        <html><head>
          <link rel="canonical" href="/products/evidence-dress">
          <meta property="product:price:amount" content="59.40">
          <meta property="product:price:currency" content="GBP">
          <script type="application/ld+json">
            {"@type":"Product","name":"Evidence Dress","image":["/structured-1.jpg"],
             "offers":{"price":"59.40","priceCurrency":"GBP"}}
          </script>
        </head><body><main>
          <h1>Evidence Dress</h1>
          <section><h2>Size Guide</h2><p>Body measurements in cm.</p>
            <table><tr><th>Size</th><th>Bust cm</th></tr><tr><td>8</td><td>84</td></tr></table>
            <small class="footnote">Measure around the fullest point.</small>
          </section>
          <section><h2>Size &amp; Fit</h2><p>Model height is 176 cm. Model wears UK 8.</p></section>
          <select data-option="Colour"><option value="green">Green</option></select>
          <select data-option="Size"><option value="8">8</option></select>
          <select data-option="Length"><option value="regular">Regular</option></select>
          <select data-option="Finish"><option value="matte">Matte</option></select>
          <a class="swatch" data-colour="Blue" href="/products/evidence-dress-blue">Blue</a>
          <img src="/rendered-1.jpg" class="product-image">
        </main></body></html>
        """
        result = JsonLdDomAdapter().extract_html(
            html,
            captured_at=CAPTURED_AT,
            artifact_id="rendered",
            base_url="https://example.test/source",
        )

        self.assertEqual(len(result.options), 4)
        self.assertEqual(result.sections[0].role, SectionRole.SIZE_GUIDE)
        table = result.sections[0].tables[0]
        self.assertEqual(table.headings, ["Size", "Bust cm"])
        self.assertEqual(table.rows[0].cells[1].source_column, 2)
        self.assertEqual(table.footnotes, ["Measure around the fullest point."])
        self.assertEqual(len(result.fit_occurrences), 2)
        self.assertFalse(result.source_model_evidence[0].target_fit_note_eligible)
        self.assertEqual(len(result.rendered_media), 1)
        self.assertEqual(len(result.structured_media), 1)
        sibling = [
            item for item in result.colour_relations
            if item.relation_type == ColourRelationType.LINKED_SIBLING_PDP
        ][0]
        self.assertEqual(sibling.capture_status.value, "UNOPENED")

    def test_shopify_ajax_preserves_sparse_variants_without_inventory(self):
        payload = {
            "title": "Source Dress",
            "vendor": "Source Retailer",
            "price": 5940,
            "options": [
                {"name": "Colour", "position": 1, "values": ["Green", "Blue"]},
                {"name": "Size", "position": 2, "values": ["8", "10"]},
            ],
            "variants": [
                {"id": 1, "options": ["Green", "8"], "price": 5940, "available": True},
                {"id": 2, "options": ["Blue", "10"], "price": 5940, "available": False},
            ],
            "images": ["https://cdn.example.test/a.jpg"],
        }
        result = ShopifyAjaxAdapter().extract(
            payload,
            captured_at=CAPTURED_AT,
            artifact_id="shopify-ajax",
            currency="GBP",
        )

        combinations = [
            [value.value for value in variant.option_values]
            for variant in result.variants
        ]
        self.assertEqual(combinations, [["Green", "8"], ["Blue", "10"]])
        self.assertEqual([variant.source_available for variant in result.variants], [True, False])
        serialized = [variant.model_dump(mode="json") for variant in result.variants]
        self.assertTrue(all("inventory_quantity" not in variant for variant in serialized))
        self.assertEqual(
            {relation.relation_type for relation in result.colour_relations},
            {ColourRelationType.IN_PRODUCT_OPTION},
        )


if __name__ == "__main__":
    unittest.main()
