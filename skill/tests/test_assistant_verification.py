"""Synthetic regression coverage for normal registration without a reviewer."""
import io
import json
import copy
from contextlib import redirect_stdout
from pathlib import Path
import unittest

import test_product_registry as registry_tests
from product_listing.listing_plan_canonical_json import canonical_json_bytes
from product_listing.listing_plan_projection_registry import sha256_bytes, _binding_from_record
from product_listing.product_registry_cli import register_product, main
from product_listing.listing_plan_cli import main as validate_cli
from product_listing import listing_plan_validation as validation
from product_listing.evidence import canonical_json_bytes as source_canonical_json_bytes
from product_listing.models import ReplayResult, SourceCapture
from product_listing.validation import validate_source_capture
from product_listing.listing_plan_copy_guard import build_copy_guard_result
from test_listing_plan_contract import CALLOWAY_BUNDLE, committable_document, load_example
from test_current_composition import current_document


class AssistantVerificationTests(unittest.TestCase):
    write_pair = registry_tests.ProductRegistryTests.write_pair

    def setUp(self):
        registry_tests.ProductRegistryTests.setUp(self)
        self.manifest['verification_method'] = 'ASSISTANT_SELF_CHECK'
        self.manifest['actors'].pop('required_reviewer_signatory')
        for record in self.manifest['records']:
            old = record.pop('reviewer_verification')
            record['assistant_verification'] = {
                'actor_id': 'TEST-ONLY-author', 'verified': True,
                'checked_at': '2026-09-02T10:00:00Z',
                'evidence_sources': old['evidence_sources'],
                'notes': 'Synthetic test comparison: ' + old['note'],
            }
            if record['fact_packet_fact_id'].startswith('fp.options.'):
                position = int(record['source_fact_or_path'].split('[')[1].split(']')[0])
                source = self.capture.source_capture.options[position]
                record.update(source_option_name=source.name, source_option_position=source.position)
        self.write_manifest()

    def write_manifest(self):
        self.manifest['bindings'] = [_binding_from_record(record) for record in self.manifest['records']]
        self.manifest['candidate_projection_pins']['ordered_bindings_canonical_sha256'] = sha256_bytes(canonical_json_bytes(self.manifest['bindings']))
        self.manifest_path.write_text(json.dumps(self.manifest))

    def register(self):
        self.write_manifest()
        return register_product(self.manifest_path, None, self.capture_path, self.root/'registered')

    def record(self, fact_id):
        return next(r for r in self.manifest['records'] if r['fact_packet_fact_id'] == fact_id)

    def assert_rejected(self, message):
        with self.assertRaisesRegex(ValueError, message):
            self.register()
        self.assertFalse((self.root/'registered').exists())

    def test_normal_cli_accepts_same_assistant_without_reviewer_and_validator_loads_it(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = main([str(self.manifest_path), str(self.capture_path), '--output', str(self.root/'registered')])
        self.assertEqual(result, 0, output.getvalue())
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt['verification_method'], 'ASSISTANT_SELF_CHECK')
        self.assertFalse(receipt['shopify_written'])
        saved = json.loads((self.root/'registered/verification.json').read_text())
        self.assertNotIn('reviewer_signatory', saved)
        self.assertEqual(saved['assistant_verifier']['actor_id'], 'TEST-ONLY-author')
        self.assertEqual([], registry_tests.ProductRegistryTests.verify(self, receipt,
            lambda doc: doc['fact_packet_projection'].update(bindings=self.manifest['bindings'])))
        doc = load_example()
        doc['fact_packet_projection'].update(bindings=self.manifest['bindings'],
            manifest_id=receipt['manifest_id'], manifest_sha256=receipt['manifest_sha256'])
        doc['evidence'].update(fact_packet_projection_manifest_id=receipt['manifest_id'],
            fact_packet_projection_manifest_sha256=receipt['manifest_sha256'])
        plan_path = self.root/'plan.json'
        plan_path.write_text(json.dumps(doc))
        output = io.StringIO()
        with redirect_stdout(output):
            result = validate_cli([str(plan_path), '--source-capture', str(self.capture_path),
                '--product-registry', receipt['registry'], '--product-registry-sha256', receipt['registry_sha256']])
        report = json.loads(output.getvalue())
        codes = {issue['code'] for issue in report['issues']}
        self.assertFalse(any(code.startswith('FACT_PACKET_PROJECTION_') for code in codes), codes)
        self.assertIn('PROFILE_HASH_MISMATCH', codes) # historical plan still blocked, no bypass
        self.assertEqual(result, 2)

    def test_normal_run_registry_accepts_chart_absent_numeric_source(self):
        capture_data = self.capture.source_capture.model_dump(mode='json', exclude_none=False)
        for section in capture_data['sections']:
            section['tables'] = []
        capture_data['size_guide_table_ids'] = []
        capture_data['size_guide_evidence'] = None
        capture_data['locked_denominator'] = None
        capture_data['options'] = [
            {'name': 'Size', 'position': 1, 'values': ['20', '28']},
            {'name': 'Length (Inches)', 'position': 2, 'values': ['52', '54']},
        ]
        capture_data['variants'] = [
            {
                'source_variant_id': 'chart-free-%s-%s' % (size, length),
                'option_values': [
                    {'option_name': 'Size', 'value': size},
                    {'option_name': 'Length (Inches)', 'value': length},
                ],
                'current_price': '55.00',
                'source_available': True,
                'source_weight_grams': 340,
            }
            for size in ('20', '28') for length in ('52', '54')
        ]
        source_capture = SourceCapture.model_validate(capture_data)
        self.assertEqual([], validate_source_capture(source_capture))
        determinism_sha = sha256_bytes(source_canonical_json_bytes(
            source_capture.model_dump(mode='json', exclude_none=False)
        ))
        self.capture = ReplayResult(
            source_capture=source_capture,
            determinism_sha256=determinism_sha,
            valid=True,
            issues=[],
        )
        output_sha = sha256_bytes(source_canonical_json_bytes(
            self.capture.model_dump(mode='json', exclude_none=False)
        ) + b'\n')
        self.capture_path.write_text(self.capture.model_dump_json())
        self.manifest['source_capture'].update(
            output_sha256=output_sha,
            determinism_sha256=determinism_sha,
        )
        self.manifest['candidate_projection_pins'].update(
            source_capture_sha256=output_sha,
            source_capture_determinism_sha256=determinism_sha,
        )
        document = current_document()
        document['plan_id'] = 'synthetic-chart-absent-numeric-run-registry'
        document['example_status'] = 'SYNTHETIC_NORMAL_RUN_REGISTRY_TEST_ONLY'
        document['approved_size_mapping'] = None
        document['evidence']['aggregate_lock_sha256'] = None
        document['evidence']['oracle_sha256'] = None
        bindings = {
            item['fact_packet_fact_id']: item
            for item in document['fact_packet_projection']['bindings']
        }
        rows = [[size, length] for size in ('20', '28') for length in ('52', '54')]
        bindings['fp.options.size'].update(
            value=['20', '28'],
            source_option_name='Size',
            source_option_position=1,
            allowed_transform_ids=[
                'ondine_uk_numeric_size_identity_v1',
                'ondine_variant_matrix_preserve_real_v1',
                'ondine_sku_mpn_v3',
                'ondine_original_five_slot_copy_v1',
            ],
        )
        bindings['fp.options.length'].update(
            value=['52', '54'],
            source_option_name='Length (Inches)',
            source_option_position=2,
        )
        bindings['fp.real_variant_combinations']['value'] = rows
        target = document['shopify_target_state']
        target['options'][1]['values'] = ['20', '28']
        target['options'][2]['name'] = 'Length (Inches)'
        target['options'][2]['values'] = ['52', '54']
        target['option_render_order'] = ['Size', 'Length (Inches)']
        target['identifier_generation']['additional_option_codes'] = {'52': '52', '54': '54'}
        template = copy.deepcopy(target['variants'][0])
        target['variants'] = []
        for size, length in rows:
            variant = copy.deepcopy(template)
            code = 'OND-%s-MLT-%03d-%s' % (target['identifier_generation']['style_code'], int(size), length)
            variant.update(
                option_values={'Colour': 'Multicolour', 'Size': size, 'Length (Inches)': length},
                sku=code,
                mpn=code,
            )
            target['variants'].append(variant)
        document['composition']['buy_box']['size_module'].update(
            values=['20', '28'],
            transform_id='ondine_uk_numeric_size_identity_v1',
        )
        document['composition']['buy_box']['selectors'][0].update(
            option_name='Length (Inches)', values=['52', '54'],
        )
        media = document['MediaPlan']
        second = copy.deepcopy(media['slots'][0])
        second.update(slot='01b', role='SECOND_MODEL_FRONT', filename=second['filename'] + 'b')
        second['acceptance'].append('visibly distinct adult from slot 01, checked side-by-side')
        media['slots'].insert(1, second)
        media['generation_gate'] = 'INTERNAL_QA_THEN_DIRECT_DRAFT_UPLOAD'
        target['media_status'] = 'PENDING_GENERATION'
        target['read_back_contract']['media_status'] = 'PENDING_GENERATION'
        policy = committable_document()['store_policy_snapshot']
        policy.update(provenance='LIVE_STORE_READ_ONLY', test_only=False)
        policy_payload = copy.deepcopy(policy)
        policy_payload.pop('canonical_sha256')
        policy['canonical_sha256'] = sha256_bytes(canonical_json_bytes(policy_payload))
        document['store_policy_snapshot'] = policy
        for record in self.manifest['records']:
            binding = bindings[record['fact_packet_fact_id']]
            record['typed_value']['value'] = copy.deepcopy(binding['value'])
            record['source_fact_or_path'] = binding['source_fact_or_path']
            record['evidence_locator'] = binding['evidence_locator']
            record['captured_at'] = binding['captured_at']
            record['market'] = binding['market']
            record['locale'] = binding['locale']
            record['scope'] = binding['scope']
            record['conflict_state'] = binding['conflict_state']
            record['claim_eligibility']['publishable_as_claim'] = binding['publishable_as_claim']
            record['policy_eligibility']['usable_as_policy_input'] = binding['usable_as_policy_input']
            record['allowed_transform_ids'] = binding['allowed_transform_ids']
            for key in ('unit', 'currency', 'source_option_name', 'source_option_position'):
                if key in binding:
                    record[key] = binding[key]
                else:
                    record.pop(key, None)
        receipt = self.register()
        profile_sha = next(
            item['sha256']
            for item in json.loads(validation.MAINTENANCE_PATH.read_text())['artifacts']
            if item['path'].endswith('profiles/ondine.md')
        )
        document['evidence'].update(
            source_capture_sha256=output_sha,
            source_capture_determinism_sha256=determinism_sha,
            ondine_profile_sha256=profile_sha,
            fact_packet_projection_manifest_id=receipt['manifest_id'],
            fact_packet_projection_manifest_sha256=receipt['manifest_sha256'],
        )
        document['fact_packet_projection'].update(
            source_capture_sha256=output_sha,
            source_capture_determinism_sha256=determinism_sha,
            ondine_profile_sha256=profile_sha,
            manifest_id=receipt['manifest_id'],
            manifest_sha256=receipt['manifest_sha256'],
            bindings=copy.deepcopy(self.manifest['bindings']),
        )
        copy_guard_probe = build_copy_guard_result(
            document,
            source_capture,
            output_sha,
            CALLOWAY_BUNDLE,
            [],
        )
        exemption_rules = {
            'double gauze cotton': 'EXACT_CAPTURED_MATERIAL_NAME',
            'lining 100 cotton': 'EXACT_CAPTURED_COMPOSITION_VALUE',
        }
        document['originality']['copy_guard_result'] = build_copy_guard_result(
            document,
            source_capture,
            output_sha,
            CALLOWAY_BUNDLE,
            [
                {
                    'normalized_span': item['normalized_span'],
                    'whitelist_rule_id': exemption_rules[item['normalized_span']],
                    'source_field_paths': item['source_field_paths'],
                    'target_field_paths': item['target_field_paths'],
                }
                for item in copy_guard_probe['non_whitelisted_shared_three_grams']
            ],
        )
        plan_path = self.root / 'chart-absent-numeric-plan.json'
        plan_path.write_text(json.dumps(document))
        output = io.StringIO()
        with redirect_stdout(output):
            result = validate_cli([
                str(plan_path), '--source-capture', str(self.capture_path),
                '--source-bundle', str(CALLOWAY_BUNDLE),
                '--product-registry', receipt['registry'],
                '--product-registry-sha256', receipt['registry_sha256'],
            ])
        report = json.loads(output.getvalue())
        codes = {issue['code'] for issue in report['issues']}
        self.assertEqual(result, 0, report)
        self.assertTrue(report['schema_valid'])
        self.assertTrue(report['committable'])
        self.assertFalse(any(code.startswith('FACT_PACKET_PROJECTION_') for code in codes), codes)
        self.assertNotIn('SOURCE_CAPTURE_EVIDENCE_INVALID', codes)
        self.assertNotIn('PROFILE_HASH_MISMATCH', codes)
        self.assertNotIn('SIZE_MAPPING_REQUIRED', codes)
        self.assertNotIn('SIZE_OUTSIDE_CURRENT_CHART', codes)

    def test_incorrect_price_rejected_even_with_consistent_manifest_hashes(self):
        self.record('fp.current_customer_paid_price_gbp')['typed_value']['value'] = '99.00'
        self.assert_rejected('SourceCapture fact mismatch')

    def test_invented_variant_rejected_even_with_consistent_hashes(self):
        self.record('fp.real_variant_combinations')['typed_value']['value'][0][0] = '999'
        self.assert_rejected('real combinations must match')

    def test_changed_size_values_rejected(self):
        self.record('fp.options.size')['typed_value']['value'].append('999')
        self.assert_rejected('option facts must match')

    def test_missing_per_fact_check_rejected(self):
        self.manifest['records'][0].pop('assistant_verification')
        self.assert_rejected('attest its binding|completed assistant source check')

    def test_pending_check_rejected(self):
        self.manifest['records'][0]['assistant_verification']['verified'] = False
        self.assert_rejected('attest its binding|completed assistant source check')

    def test_empty_source_reference_rejected(self):
        self.manifest['records'][0]['assistant_verification']['evidence_sources'] = [' ']
        self.assert_rejected('completed assistant source check')

    def test_source_raw_value_hash_mismatch_rejected(self):
        self.manifest['records'][0]['assistant_verification']['evidence_sources'][0]['raw_value'] = 'changed'
        self.assert_rejected('completed assistant source check')

    def test_wrong_actor_rejected(self):
        self.manifest['records'][0]['assistant_verification']['actor_id'] = 'invented-second-persona'
        self.assert_rejected('completed assistant source check')

    def test_unlabelled_self_check_rejected(self):
        self.manifest.pop('verification_method')
        self.assert_rejected('requires ASSISTANT_SELF_CHECK')

    def test_cannot_claim_independent_review_alongside_self_check(self):
        self.manifest['actors']['required_reviewer_signatory'] = {'actor_id': 'not-real'}
        self.assert_rejected('must not claim a separate reviewer')

    def test_future_check_rejected(self):
        self.manifest['records'][0]['assistant_verification']['checked_at'] = '2999-01-01T00:00:00Z'
        self.assert_rejected('completed assistant source check')

    def test_changed_saved_verification_rejected(self):
        receipt = self.register()
        (self.root/'registered/verification.json').write_text('{}')
        issues = registry_tests.ProductRegistryTests.verify(self, receipt)
        self.assertTrue(any('hash mismatch' in i.message for i in issues))

    def test_registration_does_not_overwrite_an_existing_run(self):
        self.register()
        with self.assertRaises(FileExistsError):
            self.register()
