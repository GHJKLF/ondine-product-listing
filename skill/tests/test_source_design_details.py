"""The actual prompt renderer must retain source placement, including GMC."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/render_slot_prompt.py'

class SourceDesignDetailsTests(unittest.TestCase):
    def render(self, details, slot='01'):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = {'garment': 'Cotton dress'}
            if details is not None:
                product['design_details'] = details
            (root / 'product_reference_facts.json').write_text(json.dumps({'product': product}))
            request = {'prompt_json': {'garment': '{{product.garment}}'}}
            template = root / 'template.json'
            template.write_text(json.dumps({'generation_request': request, 'gmc_feed_rendition': {'generation_request': request}}))
            result = subprocess.run([sys.executable, str(SCRIPT), slot, str(template), str(root)], capture_output=True, text=True)
            output = root / 'prompts' / (slot + '.prompt.json')
            return result, json.loads(output.read_text()) if output.exists() else None

    def test_bilateral_count_carried_to_every_slot(self):
        details = [{'feature': 'Three gold buttons per shoulder, six total', 'placement': 'Both wearer-left and wearer-right shoulders', 'source_evidence': 'source/front.jpg; inspected front view'}]
        for slot in ['01','01gmc','01b','02','03','04','05','06']:
            with self.subTest(slot=slot):
                result, prompt = self.render(details, slot)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(prompt['source_design_details'], details)

    def test_asymmetry_and_unknown_preserved(self):
        details = [{'feature': 'One buckle', 'placement': 'Wearer-left waist; wearer-right obscured and unknown', 'source_evidence': 'source/side.jpg'}]
        result, prompt = self.render(details)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(prompt['source_design_details'], details)

    def test_missing_empty_or_unproven_details_fail_without_prompt(self):
        for details in [None, [], [{'feature':'Buttons','placement':'Both shoulders'}], [{'feature':'Buttons','placement':'','source_evidence':'source.jpg'}]]:
            with self.subTest(details=details):
                result, prompt = self.render(details)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(prompt)

if __name__ == '__main__':
    unittest.main()
