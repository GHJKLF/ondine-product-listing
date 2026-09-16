"""Offline adapter tests; no browser or network is used."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from product_listing.adapters.jsonld_dom import JsonLdDomAdapter  # noqa: E402
from product_listing.adapters.shopify_ajax import ShopifyAjaxAdapter  # noqa: E402
from product_listing.models import ColourRelationType, MeasurementBasis, SectionRole  # noqa: E402


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

    def test_custom_product_controls_bound_gallery_sections_and_model_facts(self):
        html = (Path(__file__).parent / "fixtures" / "product-custom-controls.sanitized.html").read_text()
        result = JsonLdDomAdapter().extract_html(html, CAPTURED_AT, "custom", "https://example.test/source")

        self.assertEqual([item.url for item in result.rendered_media], [
            "https://example.test/" + name + ".jpg" for name in ("front", "back", "side", "detail")
        ])
        self.assertTrue(all(not item.excluded for item in result.rendered_media))
        self.assertEqual([section.heading for section in result.sections], [
            "Description", "Fabric & Fit", "Materials & Care Advice", "Size Guide",
            "Size Guide / Women's Clothing / Size Conversion",
            "Size Guide / Women's Clothing / Length Measurements",
            "Size Guide / Women's Clothing / Body Measurements",
            "Size Guide / Men's Clothing", "Size Guide / Children's Clothing",
        ])
        care = result.sections[2]
        self.assertEqual(care.role, SectionRole.DETAILS_CARE)
        for instruction in ("Do not bleach", "Do not tumble dry", "Machine wash, delicate"):
            self.assertIn(instruction, care.raw_text)
        materials = [item.value for item in result.candidates if item.field_path == "material_composition"]
        self.assertEqual(materials, [[{"material": "cotton", "percentage": "100"}]])
        guide = result.sections[4]
        self.assertEqual(guide.role, SectionRole.SIZE_GUIDE)
        self.assertEqual(guide.tables[0].headings, ["Supplier Size", "S", "M"])
        self.assertEqual(guide.tables[0].rows[0].cells[1].raw_text, "10-12")
        self.assertEqual([section.tables[0].measurement_basis for section in result.sections[4:]], [
            MeasurementBasis.UNSTATED, MeasurementBasis.MIXED, MeasurementBasis.BODY,
            MeasurementBasis.UNSTATED, MeasurementBasis.UNSTATED,
        ])
        self.assertEqual(result.colour_relations[0].relation_type, ColourRelationType.SELF_ONLY_SINGLE_COLOUR)
        self.assertEqual(result.colour_relations[0].capture_status.value, "CAPTURED")
        self.assertEqual(result.variants, [])
        self.assertEqual(result.options, [])
        model = result.source_model_evidence[0]
        self.assertEqual(model.model_height, "5'7")
        self.assertEqual(model.size_worn, "S")
        self.assertEqual(model.wearing_length, "58 inches")
        self.assertIn("UK 8-10", model.source_line)
        self.assertFalse(model.target_fit_note_eligible)
        self.assertEqual([item.occurrence_type for item in result.fit_occurrences], [
            "MODEL_HEIGHT", "MODEL_SIZE", "GARMENT_LENGTH",
        ])

    def test_model_size_tokens_do_not_parse_retailer_names_or_truncate_ranges(self):
        for prose, expected in (
            ("Model wears Aab clothing.", None),
            ("Model wears Atelier size S.", "S"),
            ("Model wears size XXL.", "XXL"),
            ("Model wears UK 8-10.", "UK 8-10"),
            ("Model is UK 8-10 and wears S.", "S"),
        ):
            with self.subTest(prose=prose):
                result = JsonLdDomAdapter().extract_html(
                    "<main><section><h2>Size &amp; Fit</h2><p>" + prose + "</p></section></main>",
                    CAPTURED_AT, "fit", "https://example.test/source",
                )
                self.assertEqual(result.source_model_evidence[0].size_worn if result.source_model_evidence else None, expected)

    def test_unlabelled_worn_length_does_not_invent_units(self):
        result = JsonLdDomAdapter().extract_html(
            "<main><section><h2>Size &amp; Fit</h2><p>Model wears size S 58.</p></section></main>",
            CAPTURED_AT, "fit", "https://example.test/source",
        )
        self.assertEqual(result.source_model_evidence[0].wearing_length, "58")
        self.assertIsNone(result.fit_occurrences[-1].unit)

    def test_product_info_does_not_hide_sibling_product_gallery(self):
        for outer in ('<section id="MainProduct-1"><div class="product">', '<section id="MainProduct-1"><div>'):
            with self.subTest(outer=outer):
                result = JsonLdDomAdapter().extract_html(
                    '<main>' + outer + '<div class="product__media"><img src="/dress.jpg"></div>'
                    '<product-info><h1>Dress</h1><div data-product-description>Floral dress.</div></product-info>'
                    '<div class="product-recommendations"><img src="/related-inside.jpg"></div>'
                    '</div></section><section class="product-recommendations"><img src="/related-outside.jpg"></section></main>',
                    CAPTURED_AT, "scope", "https://example.test/products/dress",
                )
                self.assertEqual([item.url for item in result.rendered_media], ["https://example.test/dress.jpg"])
                self.assertTrue(any("Floral dress." in section.raw_text for section in result.sections))

    def test_plain_main_fallback_keeps_inner_sections_without_footer(self):
        result = JsonLdDomAdapter().extract_html(
            "<body><main><h1>Dress</h1><section><h2>Product information</h2>"
            "<section><h3>Description</h3><p>Printed dress.</p></section>"
            "<details><summary>Materials &amp; Care</summary><p>100% Cotton</p></details>"
            "</section><img src='/dress.jpg'></main>"
            "<footer><section><h2>About us</h2>Our story</section><img src='/logo.jpg'></footer></body>",
            CAPTURED_AT, "main", "https://example.test/source",
        )
        self.assertEqual([section.heading for section in result.sections], ["Description", "Materials & Care"])
        self.assertEqual([item.url for item in result.rendered_media], ["https://example.test/dress.jpg"])

    def test_td_header_detection_does_not_reinterpret_unlabelled_data_rows(self):
        result = JsonLdDomAdapter().extract_html(
            "<main><section><h2>Size Guide</h2><table><tr><td>S</td><td>86</td></tr>"
            "<tr><td>M</td><td>92</td></tr></table></section></main>",
            CAPTURED_AT, "guide", "https://example.test/source",
        )
        table = result.sections[0].tables[0]
        self.assertEqual(table.headings, [])
        self.assertEqual(len(table.rows), 2)

    def test_current_colour_is_not_a_sibling_when_other_colour_links_exist(self):
        result = JsonLdDomAdapter().extract_html(
            "<main><h1>Dress</h1><a class='swatch' href='/products/dress?variant=1' data-colour='Green'>Green</a>"
            "<a class='swatch' href='/products/dress-blue' data-colour='Blue'>Blue</a></main>",
            CAPTURED_AT, "colours", "https://example.test/products/dress",
        )
        self.assertEqual(len(result.colour_relations), 1)
        self.assertEqual(result.colour_relations[0].colour_value, "Blue")
        self.assertEqual(result.colour_relations[0].relation_type, ColourRelationType.LINKED_SIBLING_PDP)

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
