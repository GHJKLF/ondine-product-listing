"""A shallow skill folder must preserve pinned checks and path boundaries."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from product_listing import artifact_paths


class ArtifactPathTests(unittest.TestCase):
    def test_renamed_shallow_skill_resolves_historical_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "skill"
            target = root / "profiles/example.json"
            target.parent.mkdir(parents=True)
            target.write_text('{}')
            with patch.object(artifact_paths, "SKILL_ROOT", root):
                self.assertEqual(target.resolve(), artifact_paths.locked_skill_file(
                    '.claude/skills/product-listing/profiles/example.json'))

    def test_traversal_and_unrelated_paths_are_rejected(self):
        for path in ('.claude/skills/product-listing/../outside.json',
                     '.claude/skills/product-listing//tmp/outside.json',
                     '/tmp/outside.json', 'other-skill/SKILL.md'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                artifact_paths.locked_skill_file(path)

    def test_symlink_cannot_escape_the_skill(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "skill"
            root.mkdir()
            outside = Path(folder) / "outside.json"
            outside.write_text('{}')
            (root / "escape.json").symlink_to(outside)
            with patch.object(artifact_paths, "SKILL_ROOT", root), self.assertRaises(ValueError):
                artifact_paths.locked_skill_file('.claude/skills/product-listing/escape.json')
