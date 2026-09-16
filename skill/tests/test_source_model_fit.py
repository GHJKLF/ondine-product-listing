"""A source fit note must stay bound to verified measurements, never image approval."""
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests'))
import test_current_release as release_fixtures
from product_listing.listing_plan_models import FactBinding
from product_listing import listing_plan_validation as v


def source_plan():
    fixture=release_fixtures.CurrentReleaseTests();fixture.setUp();p=fixture.current_plan()
    p.approved_target_model_record=None
    size=next(b for b in p.fact_packet_projection.bindings if b.fact_packet_fact_id=='fp.options.size')
    size.value=['18'];next(o for o in p.shopify_target_state.options if o.name=='Size').values=['18']
    b=size.model_dump();b.update(fact_packet_fact_id='fp.source_model_fit',value={'height_cm':168,'source_size':'18','uk_size':'18','size_basis':'EXPLICIT_UK_NUMERIC','evidence_id':'synthetic-source-model'},publishable_as_claim=True,conflict_state='NONE',allowed_transform_ids=['ondine_original_five_slot_copy_v1'])
    p.fact_packet_projection.bindings.append(FactBinding.model_validate(b))
    p.composition.buy_box.size_module['live_model_line']={'render':True,'text':'Model is 168cm and wears UK 18','target_model_record_ref':None,'provenance':'VERIFIED_SOURCE_MODEL_FIT','source_fact_ref':'fp.source_model_fit'}
    return p


class SourceModelFitTests(unittest.TestCase):
    def test_verified_source_note_needs_no_fabricated_model_approval(self):
        p=source_plan();self.assertEqual(v._state_media_model_issues(p),[]);self.assertIsNone(p.approved_target_model_record)

    def test_wrong_displayed_measurement_is_rejected(self):
        p=source_plan();p.composition.buy_box.size_module['live_model_line']['text']='Model is 175cm and wears UK 18'
        self.assertIn('SOURCE_MODEL_FIT_BINDING_INVALID',{i.code for i in v._state_media_model_issues(p)})

    def test_explicit_uk_prefix_is_preserved_as_source_and_normalized_for_display(self):
        p=source_plan()
        size=next(b for b in p.fact_packet_projection.bindings if b.fact_packet_fact_id=='fp.options.size')
        size.value=['UK 18']
        p.fact_packet_projection.bindings[-1].value['source_size']='UK 18'
        self.assertEqual(v._source_model_fit_text(p),'Model is 168cm and wears UK 18')
        self.assertEqual(size.value,['UK 18'])
        size.value=['US 18'];p.fact_packet_projection.bindings[-1].value['source_size']='US 18'
        self.assertIsNone(v._source_model_fit_text(p))

    def test_unbound_conflicted_or_nonclaim_fact_cannot_unlock_note(self):
        for change in ({'fact_packet_fact_id':'fp.unrelated'},{'publishable_as_claim':False},{'conflict_state':'UNRESOLVED'},{'allowed_transform_ids':[]}):
            p=source_plan();b=p.fact_packet_projection.bindings[-1]
            for k,x in change.items():setattr(b,k,x)
            self.assertIsNone(v._source_model_fit_text(p))

    def test_letters_ranges_and_different_target_size_are_not_converted(self):
        for source,uk,basis in [('L','18','EXPLICIT_UK_NUMERIC'),('18–20','18','EXPLICIT_UK_NUMERIC'),('18','20','EXPLICIT_UK_NUMERIC'),('18','18','ASSUMED')]:
            p=source_plan();p.fact_packet_projection.bindings[-1].value.update(source_size=source,uk_size=uk,size_basis=basis)
            self.assertIsNone(v._source_model_fit_text(p))

    def test_unrelated_model_claim_cannot_enter_fit_section(self):
        p=source_plan();p.shopify_target_state.rich_text_metafields={'fit_details':{'type':'root','children':[{'type':'paragraph','children':[{'type':'text','value':'Our model has a 90cm bust.'}]}]},'fabric_care':{'type':'root','children':[]}}
        p.shopify_target_state.metafield_fact_refs['fit_details']=['fp.source_model_fit']
        self.assertIn('MODEL_TEXT_REQUIRES_VERIFIED_FIT_EVIDENCE',{i.code for i in v._rich_text_issues(p)})

    def test_us_color_spelling_preserves_source_and_maps_target_only(self):
        p=source_plan();b=p.fact_packet_projection.bindings[-1].model_dump()
        b.update(fact_packet_fact_id='fp.options.colour',value=['Navy'],source_option_name='Color',source_option_position=1)
        p.fact_packet_projection.bindings.append(FactBinding.model_validate(b))
        raw=[x[0] for x in v._ordered_option_bindings(p)]
        target=[x[0] for x in v._target_option_bindings(p)]
        self.assertIn('Color',raw);self.assertIn('Colour',target);self.assertNotIn('Color',target)
        self.assertEqual(p.fact_packet_projection.bindings[-1].source_option_name,'Color')

    def test_verified_garment_words_are_not_source_identity(self):
        p=source_plan();url=next(b for b in p.fact_packet_projection.bindings if b.fact_packet_fact_id=='fp.canonical_source_url');url.value='https://supplier.example/products/isabelle-velvet-sleeve-maxi-dress'
        b=p.fact_packet_projection.bindings[-1].model_dump();b.update(fact_packet_fact_id='fp.fabric',value='Velvet');p.fact_packet_projection.bindings.append(FactBinding.model_validate(b))
        p.shopify_target_state.title='Navy Velvet Maxi Dress'
        paths={i.field_path for i in v._customer_leakage_issues(p)};self.assertNotIn('$.title',paths)
        url.value='https://supplier.example/products/isabelle-brown-velvet-sleeve-maxi-dress'
        colour=b.copy();colour.update(fact_packet_fact_id='fp.colour',value='Brown')
        p.fact_packet_projection.bindings.append(FactBinding.model_validate(colour))
        p.shopify_target_state.title='Brown Velvet Maxi Dress'
        self.assertNotIn('$.title',{i.field_path for i in v._customer_leakage_issues(p)})
        p.shopify_target_state.title='Isabelle Velvet Maxi Dress'
        self.assertIn('$.title',{i.field_path for i in v._customer_leakage_issues(p)})

if __name__=='__main__':unittest.main()
