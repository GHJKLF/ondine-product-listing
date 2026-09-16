"""Verify the distributed gallery manifest against actual file bytes."""
import hashlib
import json
from pathlib import Path
import unittest

PACK = Path(__file__).resolve().parents[1] / "profiles/ondine/higgsfield"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class GalleryPackIntegrityTests(unittest.TestCase):
    def test_execution_and_qa_use_the_same_layout_and_current_provider(self):
        manifest = json.loads((PACK / "pack-manifest.json").read_text())
        for order, slot in enumerate(manifest["slot_templates"], 1):
            data = json.loads((PACK / slot["json_path"]).read_text())
            with self.subTest(slot=slot["slot"]):
                self.assertEqual(order, data["order"])
                self.assertEqual(data["layout"], data["generation_request"]["prompt_json"]["layout"])
                self.assertEqual("chatgpt_builtin_image_generation", data["generation_request"]["provider"])
                self.assertNotIn("resolution", data["generation_request"]["parameters"])
                for check in data["acceptance_conditions"]:
                    if check["metric"] == "detected.subject_bbox.height":
                        self.assertEqual(check["min"], data["layout"]["subject_bbox_allowed"]["height"]["min"])
                        self.assertEqual(check["max"], data["layout"]["subject_bbox_allowed"]["height"]["max"])

    def test_manifest_and_all_referenced_files(self):
        manifest = json.loads((PACK / "pack-manifest.json").read_text())
        expected = manifest.pop("pack_sha256")
        self.assertEqual(expected, digest(canonical(manifest)))
        slots = manifest["slot_templates"]
        self.assertEqual(["01", "01b", "02", "03", "04", "05", "06"], [s["slot"] for s in slots])
        for slot in slots:
            with self.subTest(template=slot["json_path"]):
                self.assertEqual(slot["sha256"], digest((PACK / slot["json_path"]).read_bytes()))
        combined = [{"json_path":s["json_path"], "sha256":s["sha256"]} for s in slots]
        self.assertEqual(manifest["executable_templates_sha256"], digest(canonical(combined)))
        for note in manifest["human_notes"]:
            if isinstance(note, dict) and "path" in note:
                with self.subTest(note=note["path"]):
                    self.assertEqual(note["sha256"], digest((PACK / note["path"]).read_bytes()))
