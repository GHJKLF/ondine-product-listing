"""Synthetic regression coverage for normal registration without a reviewer."""
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import unittest

import test_product_registry as registry_tests
from product_listing.listing_plan_canonical_json import canonical_json_bytes
from product_listing.listing_plan_projection_registry import sha256_bytes, _binding_from_record
from product_listing.product_registry_cli import register_product, main
from product_listing.listing_plan_cli import main as validate_cli
from test_listing_plan_contract import load_example


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
