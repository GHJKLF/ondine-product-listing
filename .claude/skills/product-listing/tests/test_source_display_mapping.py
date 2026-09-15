"""Source-backed UK display labels and seasonal selection must preserve real rows."""
import copy
import unittest
from test_current_composition import current_document, codes
from product_listing.listing_plan_models import ListingPlan
from product_listing import listing_plan_validation as validation


def sample():
    doc = current_document()
    doc['approved_size_mapping'] = None
    bs = {b['fact_packet_fact_id']: b for b in doc['fact_packet_projection']['bindings']}
    source_sizes = ['UK 8 (S)', 'UK 10 (M)']
    colours = ['White', 'Navy Blue', 'Brown']
    bs['fp.options.size'].update(value=source_sizes, source_option_position=2)
    bs['fp.options.length'].update(value=['52', '54'], source_option_position=3)
    colour = copy.deepcopy(bs['fp.options.length'])
    colour.update(fact_packet_fact_id='fp.options.colour', source_option_name='Colour', source_option_position=1, value=colours)
    doc['fact_packet_projection']['bindings'].append(colour)
    # Intentionally sparse: these are fixture observations, not a Cartesian product.
    rows = [['White', source_sizes[0], '52'], ['Navy Blue', source_sizes[0], '52'],
            ['Navy Blue', source_sizes[1], '54'], ['Brown', source_sizes[0], '54'],
            ['Brown', source_sizes[1], '52']]
    bs['fp.real_variant_combinations']['value'] = rows
    doc['seasonal_colour_selection'] = {'season': 'AUTUMN_WINTER', 'selected_colours': colours[1:], 'reason': 'Retain the deep blue and brown colourways for the autumn launch.'}
    target = doc['shopify_target_state']
    target['options'] = [
        {'name': 'Colour', 'position': 1, 'values': colours[1:], 'fact_ref': 'fp.options.colour'},
        {'name': 'Size', 'position': 2, 'values': ['8', '10'], 'fact_ref': 'fp.options.size'},
        {'name': 'Length (Inches)', 'position': 3, 'values': ['52', '54'], 'fact_ref': 'fp.options.length'}]
    cc = {'Navy Blue': 'NVY', 'Brown': 'BRN'}
    target['identifier_generation']['colour_codes'] = cc
    template = copy.deepcopy(target['variants'][0])
    target['variants'] = []
    for name, size, length in rows[1:]:
        v = copy.deepcopy(template)
        numeric = size.split()[1]
        v['option_values'] = {'Colour': name, 'Size': numeric, 'Length (Inches)': length}
        v['sku'] = v['mpn'] = 'OND-%s-%s-%03d-%s' % (target['identifier_generation']['style_code'], cc[name], int(numeric), length)
        v['colour_code_ref'] = 'df.colour_' + cc[name].lower()
        target['variants'].append(v)
    for name, code in cc.items():
        doc['derived_facts'].append({'derived_fact_id': 'df.colour_' + code.lower(), 'value': code, 'transform_id': 'ondine_colour_code_v1', 'input_fact_ref': 'fp.options.colour'})
    doc['composition']['buy_box']['size_module'].update(values=['8', '10'], transform_id='ondine_uk_numeric_size_identity_v1')
    doc['composition']['buy_box']['selectors'][0]['values'] = ['52', '54']
    return doc


class SourceDisplayMappingTests(unittest.TestCase):
    def test_explicit_uk_labels_and_seasonal_sparse_rows_pass_without_user_approval(self):
        doc = sample()
        original = copy.deepcopy(doc['fact_packet_projection'])
        plan = ListingPlan.model_validate(doc)
        self.assertEqual(validation._variant_issues(plan), [])
        self.assertEqual(validation._structure_issues(plan), [])
        self.assertEqual(doc['fact_packet_projection'], original)

    def test_missing_invented_or_reordered_retained_rows_fail(self):
        for change in ('missing', 'invented', 'reordered'):
            with self.subTest(change=change):
                doc = sample()
                vs = doc['shopify_target_state']['variants']
                if change == 'missing': vs.pop()
                elif change == 'invented': vs[0]['option_values']['Length (Inches)'] = '54'
                else: vs.reverse()
                self.assertIn('INVENTED_OR_MISSING_VARIANT_COMBINATION', codes(validation._variant_issues(ListingPlan.model_validate(doc))))

    def test_colour_filter_requires_explicit_valid_record(self):
        for selection in (None, {'season':'AUTUMN_WINTER', 'selected_colours':['Purple'], 'reason':'Autumn'},
                          {'season':'AUTUMN_WINTER', 'selected_colours':['Brown','Navy Blue'], 'reason':'Autumn'},
                          {'season':'AUTUMN_WINTER', 'selected_colours':['Brown','Brown'], 'reason':'Autumn'}):
            with self.subTest(selection=selection):
                doc = sample()
                doc['seasonal_colour_selection'] = selection
                issues = codes(validation._variant_issues(ListingPlan.model_validate(doc)))
                self.assertTrue({'SEASONAL_COLOUR_SELECTION_INVALID', 'OPTION_STRUCTURE_MISMATCH'} & issues)

    def test_letters_ranges_and_other_markets_never_infer_uk_number(self):
        for label in ('S', 'EU 8 (S)', 'UK 8–10 (S)', 'UK 8/10', 'UK 9 (S)', 'US 8'):
            with self.subTest(label=label):
                doc = sample()
                size = next(b for b in doc['fact_packet_projection']['bindings'] if b['fact_packet_fact_id']=='fp.options.size')
                size['value'][0] = label
                issues = codes(validation._variant_issues(ListingPlan.model_validate(doc)))
                self.assertIn('SIZE_MAPPING_REQUIRED', issues)

    def test_collision_between_distinct_supplier_sizes_fails(self):
        doc = sample()
        size = next(b for b in doc['fact_packet_projection']['bindings'] if b['fact_packet_fact_id']=='fp.options.size')
        size['value'] = ['UK 8 (S)', 'UK 8 (M)']
        self.assertIn('SIZE_MAPPING_COLLISION', codes(validation._variant_issues(ListingPlan.model_validate(doc))))

    def test_legacy_does_not_silently_adopt_display_or_colour_changes(self):
        plan = ListingPlan.model_validate(sample())
        self.assertEqual(validation._explicit_uk_size_labels(plan, legacy=True), {})
        self.assertIn('SEASONAL_COLOUR_SELECTION_INVALID', codes(validation._variant_issues(plan, legacy=True)))

    def test_generic_garment_words_are_not_supplier_identity(self):
        doc = sample()
        url = next(b for b in doc['fact_packet_projection']['bindings'] if b['fact_packet_fact_id']=='fp.canonical_source_url')
        url['value'] = 'https://supplier.example/products/lanna-floral-button-maxi-dress'
        doc['shopify_target_state']['title'] = 'Floral Button-Front Maxi Dress'
        issues = validation._customer_leakage_issues(ListingPlan.model_validate(doc))
        self.assertFalse(any(i.field_path == '$.title' for i in issues))
        doc['shopify_target_state']['title'] = 'Lanna Floral Button-Front Maxi Dress'
        issues = validation._customer_leakage_issues(ListingPlan.model_validate(doc))
        self.assertTrue(any(i.field_path == '$.title' for i in issues))

    def test_full_validator_still_requires_real_registered_evidence(self):
        report = validation.validate_listing_plan_document(sample())
        self.assertTrue(report.schema_valid)
        self.assertFalse(report.committable)
        self.assertIn('SOURCE_CAPTURE_EVIDENCE_REQUIRED', codes(report.issues))
        self.assertNotIn('SIZE_MAPPING_REQUIRED', codes(report.issues))
        self.assertNotIn('INVENTED_OR_MISSING_VARIANT_COMBINATION', codes(report.issues))

if __name__ == '__main__':
    unittest.main()
