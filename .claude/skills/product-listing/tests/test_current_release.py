"""Current release integrity and gallery requirements; no live store access."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from product_listing import listing_plan_validation as validation
from product_listing.listing_plan_models import ListingPlan


class CurrentReleaseTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "profiles/ondine/listing-plan.example.json").read_text())

    def current_plan(self):
        document = copy.deepcopy(self.document)
        media = document["MediaPlan"]
        second = copy.deepcopy(media["slots"][0])
        second.update(slot="01b", role="SECOND_MODEL_FRONT", filename=second["filename"] + "b")
        media["slots"].insert(1, second)
        media["generation_gate"] = "LEAD_INTERNAL_QA_THEN_SECOND_MODEL_GALLERY_UPLOAD_REVIEW"
        return ListingPlan.model_validate(document)

    def test_current_gallery_passes(self):
        self.assertEqual([], validation._state_media_model_issues(self.current_plan()))

    def test_six_images_fail_current_rules(self):
        codes = {x.code for x in validation._state_media_model_issues(ListingPlan.model_validate(self.document))}
        self.assertIn("MEDIA_PLAN_INVALID", codes)
        self.assertIn("MEDIA_GENERATION_GATE_INVALID", codes)

    def test_duplicate_filename_fails(self):
        plan = self.current_plan()
        plan.media_plan.slots[1].filename = plan.media_plan.slots[0].filename
        self.assertIn("MEDIA_PLAN_FILENAME_DUPLICATE", {x.code for x in validation._state_media_model_issues(plan)})

    def test_altered_maintenance_record_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "maintenance.json"
            changed.write_bytes(validation.MAINTENANCE_PATH.read_bytes() + b"\n")
            with patch.object(validation, "MAINTENANCE_PATH", changed):
                with self.assertRaises(validation.ContractLoadError):
                    validation._load_locked_contract(validation.DEFAULT_PHASE_2_LOCK)

    def test_historical_example_cannot_commit(self):
        report = validation.validate_listing_plan_document(self.document)
        self.assertFalse(report.committable)
        self.assertNotIn("PHASE_2_LOCK_INVALID", {x.code for x in report.issues})

    def test_modified_example_requires_current_profile(self):
        self.document["plan_id"] += "-new"
        report = validation.validate_listing_plan_document(self.document)
        self.assertFalse(report.committable)
        self.assertIn("PROFILE_HASH_MISMATCH", {x.code for x in report.issues})

