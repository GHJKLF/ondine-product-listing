"""Synthetic coverage of current composition; no real user approval is minted here."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from product_listing.listing_plan_models import ListingPlan
from product_listing import listing_plan_validation as validation


def current_document():
    """Composition sample only: inherited source pins/registry are intentionally invalid."""
    document = json.loads((SKILL_ROOT / "profiles/ondine/listing-plan.example.json").read_text())
    document["example_status"] = "SYNTHETIC_CURRENT_COMPOSITION_TEST_ONLY"
    document["store_policy_snapshot"] = None
    document["flags"] = []
    bindings = {b["fact_packet_fact_id"]: b for b in document["fact_packet_projection"]["bindings"]}
    labels = {
        "XXS": "XXS (UK 4–6)", "XS": "XS (UK 6–8)", "S": "S (UK 10–12)",
        "M": "M (UK 14–16)", "L": "L (UK 18–20)", "XL": "XL (UK 22–24)",
        "XXL": "XXL (UK 24–26)",
    }
    lengths = ["52", "54", "56", "58", "62"]
    # These rows are the synthetic incoming matrix, not target option multiplication.
    rows = [[size, length] for size in labels for length in lengths]
    bindings["fp.options.size"].update(value=list(labels), source_option_name="Size", source_option_position=1)
    bindings["fp.options.size"]["allowed_transform_ids"].append("ondine_approved_source_size_label_v1")
    bindings["fp.options.length"].update(value=lengths, source_option_name="Length (Inches)", source_option_position=2)
    bindings["fp.real_variant_combinations"]["value"] = rows
    bindings["fp.colour"]["value"] = "Multicolour"
    document["approved_size_mapping"] = {
        "record_id": "synthetic-size-approval-not-a-real-user-record",
        "canonical_source_url": bindings["fp.canonical_source_url"]["value"],
        "source_capture_sha256": document["evidence"]["source_capture_sha256"],
        "labels": labels, "approval_record_sha256": "0" * 64,
    }
    target = document["shopify_target_state"]
    target["options"] = [
        {"name": "Colour", "position": 1, "values": ["Multicolour"], "fact_ref": "fp.colour"},
        {"name": "Size", "position": 2, "values": list(labels.values()), "fact_ref": "fp.options.size"},
        {"name": "Length (Inches)", "position": 3, "values": lengths, "fact_ref": "fp.options.length"},
    ]
    target["option_render_order"] = ["Size", "Length (Inches)"]
    identifier = target["identifier_generation"]
    identifier["colour_code"] = "MLT"
    identifier["additional_option_codes"] = {length: length for length in lengths}
    identifier["size_code_rule"] = "uppercase ASCII letters and digits from approved original source label"
    document["transform_contracts"]["ondine_colour_code_v1"]["profile_mapping"]["Multicolour"] = "MLT"
    base_variant = copy.deepcopy(target["variants"][0])
    target["variants"] = []
    for size, length in rows:
        variant = copy.deepcopy(base_variant)
        variant["option_values"] = {"Colour": "Multicolour", "Size": labels[size], "Length (Inches)": length}
        variant["sku"] = variant["mpn"] = "OND-%s-MLT-%s-%s" % (identifier["style_code"], size, length)
        target["variants"].append(variant)
    for fact in document["derived_facts"]:
        if fact["derived_fact_id"] == base_variant["colour_code_ref"]:
            fact["value"] = "MLT"
    composition = document["composition"]
    composition["buy_box"]["colour"]["value"] = "Multicolour"
    composition["buy_box"]["size_module"].update(values=list(labels.values()), transform_id="ondine_approved_source_size_label_v1")
    composition["buy_box"]["length_selector"] = None
    composition["buy_box"]["selectors"] = [{
        "pdp_order_id": "length_selector", "option_name": "Length (Inches)",
        "values": lengths, "fact_ref": "fp.options.length", "selector_order": 2,
    }]
    composition["pdp_order"]["below_fold"] = ["description", "fit_details", "fabric_care", "delivery", "returns_and_refunds"]
    composition["below_fold_sections"] = []
    for slot in composition["description"]["slots"]:
        slot.pop("items", None)
        slot["text"] = "Synthetic prose for %s verification." % slot["id"]
    target["rich_text_metafields"] = {name: {"type": "root", "children": []} for name in ("fit_details", "fabric_care")}
    return document


def codes(issues):
    return {issue.code for issue in issues}


def synthetic_approval(document, directory):
    record = {key: value for key, value in document["approved_size_mapping"].items() if key != "approval_record_sha256"}
    record.update(
        approval_state="APPROVED", approved_by="Ilias", approved_at="2026-09-14T10:00:00Z",
        decision_text="Synthetic fixture: keep source labels and UK ranges.",
        approval_source="unittest: this is not a real conversation approval",
        provenance="SYNTHETIC_TEST_ONLY",
    )
    path = Path(directory) / "synthetic-approval.json"
    path.write_text(json.dumps(record, ensure_ascii=False))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    document["approved_size_mapping"]["approval_record_sha256"] = digest
    return path, digest


class CurrentCompositionTests(unittest.TestCase):
    def test_live_candidate_does_not_require_fabricated_historical_oracle_pins(self):
        document = current_document()
        document["evidence"]["aggregate_lock_sha256"] = None
        document["evidence"]["oracle_sha256"] = None
        report = validation.validate_listing_plan_document(document)
        self.assertTrue(report.schema_valid)
        self.assertFalse(report.committable)
        self.assertIn("SOURCE_CAPTURE_EVIDENCE_REQUIRED", codes(report.issues))
        self.assertIn("SIZE_MAPPING_APPROVAL_INVALID", codes(report.issues))

    def test_approved_mapping_preserves_all_35_rows_and_source_labels(self):
        document = current_document()
        with tempfile.TemporaryDirectory() as directory:
            path, digest = synthetic_approval(document, directory)
            plan = ListingPlan.model_validate(document)
            labels, issues = validation._approved_size_mapping(plan, path, digest, test_mode=True)
        self.assertEqual(issues, [])
        self.assertEqual(validation._variant_issues(plan, approved_size_labels=labels), [])
        self.assertEqual(validation._structure_issues(plan, approved_size_labels=labels), [])
        self.assertEqual(len(plan.shopify_target_state.variants), 35)
        size = next(b for b in plan.fact_packet_projection.bindings if b.fact_packet_fact_id == "fp.options.size")
        self.assertEqual(size.value, ["XXS", "XS", "S", "M", "L", "XL", "XXL"])
        self.assertEqual(len({v.sku for v in plan.shopify_target_state.variants}), 35)

    def test_missing_mismatched_and_synthetic_normal_approvals_block(self):
        document = current_document()
        plan = ListingPlan.model_validate(document)
        self.assertIn("SIZE_MAPPING_APPROVAL_INVALID", codes(validation._approved_size_mapping(plan, None, None)[1]))
        self.assertIn("SIZE_MAPPING_REQUIRED", codes(validation._variant_issues(plan)))
        with tempfile.TemporaryDirectory() as directory:
            path, digest = synthetic_approval(document, directory)
            plan = ListingPlan.model_validate(document)
            self.assertIn("SIZE_MAPPING_APPROVAL_INVALID", codes(validation._approved_size_mapping(plan, path, digest)[1]))
            document["approved_size_mapping"]["labels"]["S"] = "S (UK 8–10)"
            plan = ListingPlan.model_validate(document)
            self.assertIn("SIZE_MAPPING_APPROVAL_INVALID", codes(validation._approved_size_mapping(plan, path, digest, test_mode=True)[1]))

    def test_sparse_matrix_must_not_be_multiplied_or_reordered(self):
        document = current_document()
        labels = document["approved_size_mapping"]["labels"]
        binding = next(b for b in document["fact_packet_projection"]["bindings"] if b["fact_packet_fact_id"] == "fp.real_variant_combinations")
        binding["value"].pop()
        plan = ListingPlan.model_validate(document)
        self.assertIn("INVENTED_OR_MISSING_VARIANT_COMBINATION", codes(validation._variant_issues(plan, approved_size_labels=labels)))
        document["shopify_target_state"]["variants"].pop()
        self.assertEqual(validation._variant_issues(ListingPlan.model_validate(document), approved_size_labels=labels), [])
        document["shopify_target_state"]["variants"].reverse()
        self.assertIn("INVENTED_OR_MISSING_VARIANT_COMBINATION", codes(validation._variant_issues(ListingPlan.model_validate(document), approved_size_labels=labels)))

    def test_colour_first_and_exact_source_name_required(self):
        document = current_document()
        labels = document["approved_size_mapping"]["labels"]
        document["shopify_target_state"]["options"][2]["name"] = "Length"
        self.assertIn("OPTION_STRUCTURE_MISMATCH", codes(validation._variant_issues(ListingPlan.model_validate(document), approved_size_labels=labels)))
        document = current_document()
        document["shopify_target_state"]["options"].reverse()
        self.assertIn("OPTION_STRUCTURE_MISMATCH", codes(validation._variant_issues(ListingPlan.model_validate(document), approved_size_labels=labels)))

    def test_five_prose_slots_and_theme_policy_ownership(self):
        document = current_document()
        labels = document["approved_size_mapping"]["labels"]
        plan = ListingPlan.model_validate(document)
        self.assertEqual(validation._structure_issues(plan, approved_size_labels=labels), [])
        self.assertEqual(validation._policy_issues(plan, test_mode=False), [])
        self.assertIn("STORE_POLICY_SNAPSHOT_REQUIRED_AT_COMPOSE", codes(validation._policy_issues(plan, test_mode=True, legacy=True)))
        document["composition"]["description"]["slots"][2]["items"] = [{"text": "A bullet"}]
        self.assertIn("DESCRIPTION_PROSE_REQUIRED", codes(validation._structure_issues(ListingPlan.model_validate(document), approved_size_labels=labels)))

    def test_rich_text_needs_source_refs_and_valid_nodes(self):
        document = current_document()
        document["shopify_target_state"]["rich_text_metafields"]["fit_details"]["children"] = [{"type": "paragraph", "children": [{"type": "text", "value": "An unsupported fit claim"}]}]
        self.assertIn("RICH_TEXT_FACT_BINDING_REQUIRED", codes(validation._rich_text_issues(ListingPlan.model_validate(document))))
        document["shopify_target_state"]["rich_text_metafields"]["fit_details"]["children"][0]["type"] = "link"
        self.assertIn("RICH_TEXT_METAFIELD_INVALID", codes(validation._rich_text_issues(ListingPlan.model_validate(document))))

    def test_unknown_optional_facts_stay_blank_without_claimed_refs(self):
        document = current_document()
        target = document["shopify_target_state"]
        for name in ("fabric", "occasion", "neckline"):
            target["metafields"][name] = ""
            target["metafield_fact_refs"][name] = []
        for variant in target["variants"]:
            variant["weight_grams"] = variant["weight_fact_ref"] = None
        plan = ListingPlan.model_validate(document)
        self.assertEqual(validation._seo_organisation_issues(plan), [])
        self.assertEqual(validation._variant_issues(plan, approved_size_labels=document["approved_size_mapping"]["labels"]), [])
        self.assertIn("METAFIELDS_INCOMPLETE", codes(validation._seo_organisation_issues(plan, legacy=True)))
        target["metafield_fact_refs"]["neckline"] = ["fp.colour"]
        self.assertIn("UNKNOWN_METAFIELD_BINDING_INVALID", codes(validation._seo_organisation_issues(ListingPlan.model_validate(document))))

    def test_numeric_sizes_above_old_chart_cap_are_preserved_currently(self):
        document = current_document()
        document["approved_size_mapping"] = None
        bindings = {b["fact_packet_fact_id"]: b for b in document["fact_packet_projection"]["bindings"]}
        bindings["fp.options.size"]["value"] = ["20"]
        bindings["fp.real_variant_combinations"]["value"] = [["20", "52"]]
        target = document["shopify_target_state"]
        target["options"][1]["values"] = ["20"]
        target["variants"] = target["variants"][:1]
        target["variants"][0]["option_values"]["Size"] = "20"
        target["variants"][0]["sku"] = target["variants"][0]["mpn"] = "OND-%s-MLT-020-52" % target["identifier_generation"]["style_code"]
        self.assertEqual(validation._variant_issues(ListingPlan.model_validate(document)), [])

    def test_rich_text_source_identity_leakage_remains_blocking(self):
        document = current_document()
        document["shopify_target_state"]["rich_text_metafields"]["fabric_care"]["children"] = [{
            "type": "paragraph", "children": [{"type": "text", "value": "https://source.example/product"}],
        }]
        self.assertIn("CUSTOMER_SOURCE_LEAKAGE", codes(validation._customer_leakage_issues(ListingPlan.model_validate(document))))

    def test_normal_mode_wires_current_rules_and_preserves_evidence_gates(self):
        document = current_document()
        labels = document["approved_size_mapping"]["labels"]
        # Isolate routing of an already-verified mapping; real authority is tested above.
        # All source/registry/copy-guard checks remain active, so this sample cannot commit.
        with patch.object(validation, "_approved_size_mapping", return_value=(labels, [])) as approval:
            report = validation.validate_listing_plan_document(document)
        approval.assert_called_once()
        self.assertFalse(approval.call_args.kwargs["test_mode"])
        self.assertFalse(report.committable)
        self.assertIn("SOURCE_CAPTURE_EVIDENCE_REQUIRED", codes(report.issues))
        for code in ("SIZE_MAPPING_REQUIRED", "SIZE_OUTSIDE_CURRENT_CHART", "OPTION_STRUCTURE_MISMATCH", "DESCRIPTION_BENEFITS_INVALID", "DESCRIPTION_PROSE_REQUIRED", "PDP_ORDER_INVALID", "STORE_POLICY_SNAPSHOT_REQUIRED_AT_COMPOSE"):
            self.assertNotIn(code, codes(report.issues))
        unapproved = validation.validate_listing_plan_document(document)
        self.assertIn("SIZE_MAPPING_APPROVAL_INVALID", codes(unapproved.issues))
        self.assertIn("SIZE_MAPPING_REQUIRED", codes(unapproved.issues))


if __name__ == "__main__":
    unittest.main()
