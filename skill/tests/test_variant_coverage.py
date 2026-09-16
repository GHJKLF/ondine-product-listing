"""Offline regression coverage for colour-family variant validation."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from product_listing.variant_coverage import validate_variant_coverage


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class VariantCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.html = self.root / "selector.html"
        self.html.write_text("""
        <div id="product-meta" class="ProductMeta__Swatches">
          <a href="/products/runway-navy">Navy</a>
          <a href="https://source.example/products/runway-black">Black</a>
        </div>
        <div id="recommendations"><a href="/products/unrelated-red">Red</a></div>
        """)
        self.navy = self.write_source("navy", ["UK 6", "UK 8"], available=[False, True])
        self.black = self.write_source("black", ["UK 6", "UK 10"])
        self.manifest_path = self.root / "family.json"
        self.target_path = self.root / "target.json"

    def write_source(self, name, sizes, available=None, colours=None, include_handle=True):
        available = available or [True] * len(sizes)
        options = [{"name": "Size", "position": 1, "values": sizes}]
        variants = [{"options": [size], "available": status}
                    for size, status in zip(sizes, available)]
        if colours is not None:
            options = [{"name": "Colour", "position": 1, "values": colours}, *options]
            variants = [{"options": [colour, size], "available": True}
                        for colour in colours for size in sizes]
        path = self.sources / (name + ".json")
        document = {"options": options, "variants": variants}
        if include_handle:
            document["handle"] = "runway-" + name
        path.write_text(json.dumps(document))
        return path

    def manifest(self, selected=None, excluded=None, source_entries=None, size_map=None):
        source_entries = source_entries or [
            {"url": "https://source.example/products/runway-navy", "product_json": "sources/navy.json", "sha256": digest(self.navy), "colour": "Navy"},
            {"url": "https://source.example/products/runway-black", "product_json": "sources/black.json", "sha256": digest(self.black), "colour": "Black"},
        ]
        value = {
            "schema_version": 1,
            "selector": {"html_path": "selector.html", "sha256": digest(self.html),
                         "xpath": "//div[@id='product-meta']"},
            "base_url": "https://source.example/products/runway-navy",
            "sources": source_entries,
        }
        if selected is not None:
            value["selected_colours"] = selected
        if excluded is not None:
            value["excluded_colours"] = excluded
        if size_map is not None:
            value["size_label_map"] = size_map
        self.manifest_path.write_text(json.dumps(value))
        return value

    def target(self, variants=None, complete=True, sizes=None, colours=None):
        colours = ["Navy", "Black"] if colours is None else colours
        sizes = ["6", "8", "10"] if sizes is None else sizes
        variants = variants if variants is not None else [
            {"option_values": {"Colour": "Navy", "Size": "6"}},
            {"option_values": {"Colour": "Navy", "Size": "8"}},
            {"option_values": {"Colour": "Black", "Size": "6"}},
            {"option_values": {"Colour": "Black", "Size": "10"}},
        ]
        value = {"complete": complete,
                 "options": [{"name": "Colour", "values": colours},
                             {"name": "Size", "values": sizes}],
                 "variants": variants}
        self.target_path.write_text(json.dumps(value))
        return value

    def report(self):
        return validate_variant_coverage(self.manifest_path, self.target_path)

    def codes(self):
        return {error["code"] for error in self.report()["errors"]}

    def test_navy_only_target_fails_when_black_swatch_sibling_exists(self):
        self.manifest(size_map={"UK 6": "6", "UK 8": "8", "UK 10": "10"})
        self.target(colours=["Navy"], sizes=["6", "8"], variants=[
            {"option_values": {"Colour": "Navy", "Size": "6"}},
            {"option_values": {"Colour": "Navy", "Size": "8"}},
        ])
        report = self.report()
        self.assertFalse(report["ok"])
        self.assertTrue(any(row["Colour"] == "Black" for row in report["missing"]))

    def test_full_family_passes_and_keeps_unavailable_size(self):
        self.manifest(size_map={"UK 6": "6", "UK 8": "8", "UK 10": "10"})
        self.target()
        report = self.report()
        self.assertTrue(report["ok"], report)
        self.assertIn({"Colour": "Navy", "Size": "6"}, report["expected"])

    def test_missing_sibling_blocks_before_target_comparison(self):
        self.manifest(source_entries=[
            {"url": "https://source.example/products/runway-navy", "product_json": "sources/navy.json", "sha256": digest(self.navy), "colour": "Navy"}
        ])
        self.target()
        self.assertIn("DISCOVERED_SIBLING_UNCAPTURED", self.codes())

    def test_asymmetric_source_sizes_are_not_cartesian(self):
        self.manifest(size_map={"UK 6": "6", "UK 8": "8", "UK 10": "10"})
        self.target(variants=[
            {"option_values": {"Colour": "Navy", "Size": "6"}},
            {"option_values": {"Colour": "Navy", "Size": "8"}},
            {"option_values": {"Colour": "Black", "Size": "6"}},
            {"option_values": {"Colour": "Black", "Size": "10"}},
        ])
        self.assertTrue(self.report()["ok"])

    def test_missing_extra_and_duplicate_rows_fail(self):
        self.manifest(size_map={"UK 6": "6", "UK 8": "8", "UK 10": "10"})
        variants = self.target()["variants"]
        variants.pop()
        variants.append(copy.deepcopy(variants[0]))
        variants.append({"option_values": {"Colour": "Black", "Size": "8"}})
        self.target(variants=variants)
        self.assertTrue({"TARGET_VARIANT_MISSING", "TARGET_VARIANT_EXTRA", "TARGET_VARIANT_DUPLICATE"} <= self.codes())

    def test_tampered_artifact_and_path_escape_fail(self):
        self.manifest()
        self.target()
        self.html.write_text("tampered")
        self.assertIn("ARTIFACT_HASH_MISMATCH", self.codes())
        self.manifest_path.write_text(json.dumps({
            "schema_version": 1, "selector": {"html_path": "../outside.html", "sha256": "0" * 64, "xpath": "//div"},
            "sources": []
        }))
        self.assertIn("PATH_OUTSIDE_ALLOWED_ROOT", self.codes())

    def test_recommendation_swatches_are_excluded_by_exact_xpath(self):
        self.manifest(size_map={"UK 6": "6", "UK 8": "8", "UK 10": "10"})
        self.target()
        self.assertTrue(self.report()["ok"])

    def test_explicit_seasonal_exclusion_still_requires_discovery_and_capture(self):
        self.manifest(selected=["Navy"], excluded={"Black": "Existing autumn selection excludes Black."},
                      size_map={"UK 6": "6", "UK 8": "8", "UK 10": "10"})
        self.target(colours=["Navy"], sizes=["6", "8"], variants=[
            {"option_values": {"Colour": "Navy", "Size": "6"}},
            {"option_values": {"Colour": "Navy", "Size": "8"}},
        ])
        self.assertTrue(self.report()["ok"])

    def test_multicolour_source_json_uses_all_real_rows(self):
        multi = self.write_source("multi", ["S", "M"], colours=["Navy", "Black"], include_handle=False)
        self.manifest(source_entries=[
            {"url": "https://source.example/products/runway-navy", "product_json": "sources/multi.json", "sha256": digest(multi)},
            {"url": "https://source.example/products/runway-black", "product_json": "sources/multi.json", "sha256": digest(multi)},
        ])
        self.target(colours=["Navy", "Black"], sizes=["S", "M"], variants=[
            {"option_values": {"Colour": colour, "Size": size}}
            for colour in ("Navy", "Black") for size in ("S", "M")
        ])
        self.assertTrue(self.report()["ok"])

    def test_source_json_handle_must_match_its_captured_url(self):
        self.manifest(size_map={"UK 6": "6", "UK 8": "8", "UK 10": "10"})
        self.target()
        self.assertTrue(self.report()["ok"])
        payload = json.loads(self.black.read_text())
        payload["handle"] = "runway-navy"
        self.black.write_text(json.dumps(payload))
        manifest = json.loads(self.manifest_path.read_text())
        manifest["sources"][1]["sha256"] = digest(self.black)
        self.manifest_path.write_text(json.dumps(manifest))
        self.assertIn("SOURCE_URL_HANDLE_MISMATCH", self.codes())

    def test_incomplete_readback_and_colour_conflict_fail(self):
        self.manifest()
        self.target(complete=False)
        self.assertIn("TARGET_READBACK_INCOMPLETE", self.codes())
        self.manifest(source_entries=[
            {"url": "https://source.example/products/runway-navy", "product_json": "sources/navy.json", "sha256": digest(self.navy), "colour": "Black"},
            {"url": "https://source.example/products/runway-black", "product_json": "sources/black.json", "sha256": digest(self.black), "colour": "Black"},
        ])
        self.target()
        self.assertIn("COLOUR_SOURCE_CONFLICT", self.codes())

    def test_size_mapping_cannot_collapse_distinct_observed_labels(self):
        self.manifest(size_map={"UK 6": "UK 8"})  # Collides with unmapped observed UK 8.
        self.target()
        self.assertIn("SIZE_LABEL_MAP_COLLISION", self.codes())
        self.manifest(size_map={"UK 6": "6", "UK 8": "6"})
        self.assertIn("SIZE_LABEL_MAP_COLLISION", self.codes())

    def test_excluding_every_colour_cannot_pass_an_empty_target(self):
        self.manifest(selected=[], excluded={
            "Navy": "Existing seasonal selection excludes Navy.",
            "Black": "Existing seasonal selection excludes Black.",
        })
        self.target(colours=[], sizes=[], variants=[])
        self.assertTrue({"COLOUR_SELECTION_EMPTY", "EXPECTED_VARIANTS_EMPTY"} <= self.codes())


if __name__ == "__main__":
    unittest.main()
