"""Mock-only tests for the isolated Phase 3 Shopify DRAFT sender."""

import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from product_listing.listing_plan_canonical_json import canonical_json_bytes  # noqa: E402
from product_listing.listing_plan_models import (  # noqa: E402
    ListingPlan,
    ListingPlanValidationReport,
)
from product_listing.shopify_draft_cli import main as draft_cli_main  # noqa: E402
from product_listing.shopify_draft_sender import (  # noqa: E402
    DraftSendBlocked,
    OndineStoreContract,
    ProductSnapshot,
    ShopIdentity,
    UnknownWriteOutcome,
    build_desired_state,
    send_shopify_draft,
)
from test_listing_plan_contract import committable_document  # noqa: E402


SHOP_GID = "gid://shopify/Shop/123456789"


def store_contract():
    return OndineStoreContract.from_dict(
        {
            "contract_id": "ondine-store-contract-test-only-v1",
            "myshopify_domain": "zfrbm1-y6.myshopify.com",
            "primary_domain_host": "ondinelondon.co.uk",
            "approved_shop_name": "Ondine London",
            "expected_shop_gid": SHOP_GID,
        }
    )


def validated_input():
    document = committable_document()
    document_hash = hashlib.sha256(canonical_json_bytes(document)).hexdigest()
    report = ListingPlanValidationReport(
        schema_valid=True,
        committable=True,
        phase_2_lock_sha256="a" * 64,
        listing_plan_sha256=document_hash,
        issues=[],
    )
    return document, report


class MockShopifyDraftTransport:
    def __init__(self):
        self.identity = ShopIdentity(
            shop_gid=SHOP_GID,
            myshopify_domain="zfrbm1-y6.myshopify.com",
            primary_domain_host="ondinelondon.co.uk",
            shop_name="Ondine London",
        )
        self.products = {}
        self.forced_candidates = None
        self.read_override = None
        self.unknown_create = False
        self.events = []
        self.create_calls = 0
        self.update_calls = 0

    def read_shop_identity(self):
        self.events.append("read_shop")
        return self.identity

    def find_candidates(self, source_key, title, handle):
        self.events.append("find")
        if self.forced_candidates is not None:
            return list(self.forced_candidates)
        return [
            snapshot
            for snapshot in self.products.values()
            if snapshot.state.get("ownership", {}).get("source_key") == source_key
            or snapshot.state.get("title") == title
            or snapshot.state.get("handle") == handle
        ]

    def create_draft(self, desired_state):
        self.events.append("create")
        self.create_calls += 1
        self.assert_write_surface(desired_state)
        product_id = "gid://shopify/Product/9001"
        self.products[product_id] = ProductSnapshot(
            product_id=product_id,
            shop_gid=SHOP_GID,
            status="DRAFT",
            publication_ids=[],
            state=copy.deepcopy(desired_state),
        )
        if self.unknown_create:
            raise UnknownWriteOutcome("response lost after Shopify accepted create")
        return product_id

    def update_draft(self, product_id, desired_state):
        self.events.append("update")
        self.update_calls += 1
        self.assert_write_surface(desired_state)
        self.products[product_id] = ProductSnapshot(
            product_id=product_id,
            shop_gid=SHOP_GID,
            status="DRAFT",
            publication_ids=[],
            state=copy.deepcopy(desired_state),
        )

    def read_product(self, product_id):
        self.events.append("read")
        return self.read_override or self.products[product_id]

    def assert_write_surface(self, desired_state):
        self.assert_no_forbidden_keys(desired_state)
        if desired_state["status"] != "DRAFT":
            raise AssertionError("sender attempted a non-DRAFT write")
        for variant in desired_state.get("variants", []):
            if variant.get("taxable") is not False:
                raise AssertionError("sender must disable tax for every variant")

    def assert_no_forbidden_keys(self, value):
        forbidden = {
            "inventory",
            "inventoryquantity",
            "availability",
            "publications",
            "publicationids",
            "media",
            "targetmedia",
        }
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).replace("_", "").casefold() in forbidden:
                    raise AssertionError("forbidden write key: %s" % key)
                self.assert_no_forbidden_keys(child)
        elif isinstance(value, list):
            for child in value:
                self.assert_no_forbidden_keys(child)


def snapshot_for(
    desired,
    *,
    product_id="gid://shopify/Product/existing",
    status="DRAFT",
    ownership=None,
    publications=(),
):
    state = copy.deepcopy(desired)
    if ownership is not None:
        state["ownership"] = ownership
    return ProductSnapshot(
        product_id=product_id,
        shop_gid=SHOP_GID,
        status=status,
        publication_ids=list(publications),
        state=state,
    )


class ShopifyDraftSenderTest(unittest.TestCase):
    def test_new_draft_defaults_to_diff_then_commit_creates_draft(self):
        document, report = validated_input()
        contract = store_contract()
        transport = MockShopifyDraftTransport()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            report_path = root / "report.json"
            contract_path = root / "contract.json"
            plan_path.write_text(json.dumps(document), encoding="utf-8")
            report_path.write_text(report.model_dump_json(), encoding="utf-8")
            contract_path.write_text(
                json.dumps(
                    {
                        "contract_id": contract.contract_id,
                        "myshopify_domain": contract.myshopify_domain,
                        "primary_domain_host": contract.primary_domain_host,
                        "approved_shop_name": contract.approved_shop_name,
                        "expected_shop_gid": contract.expected_shop_gid,
                    }
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                dry_exit = draft_cli_main(
                    [str(plan_path), str(report_path), str(contract_path)],
                    transport=transport,
                )
            dry = json.loads(output.getvalue())
            self.assertEqual(dry_exit, 0)
            self.assertEqual(dry["action"], "CREATE")
            self.assertFalse(dry["committed"])
            self.assertTrue(dry["diff"])
            self.assertEqual(transport.create_calls, 0)

            output = io.StringIO()
            with redirect_stdout(output):
                commit_exit = draft_cli_main(
                    [
                        str(plan_path),
                        str(report_path),
                        str(contract_path),
                        "--commit",
                    ],
                    transport=transport,
                )
            committed = json.loads(output.getvalue())
            self.assertEqual(commit_exit, 0)
            self.assertTrue(committed["committed"])
            self.assertEqual(committed["action"], "CREATE")
            self.assertEqual(transport.create_calls, 1)
            product = transport.products[committed["product_id"]]
            self.assertEqual(product.status, "DRAFT")
            self.assertTrue(product.state["variants"])
            self.assertTrue(
                all(variant["taxable"] is False for variant in product.state["variants"])
            )
            self.assertEqual(list(product.publication_ids), [])

    def test_identical_retry_returns_same_id_without_duplicate(self):
        document, report = validated_input()
        contract = store_contract()
        transport = MockShopifyDraftTransport()
        first = send_shopify_draft(document, report, contract, transport, commit=True)
        second = send_shopify_draft(document, report, contract, transport, commit=True)
        self.assertEqual(first.product_id, second.product_id)
        self.assertEqual(second.action, "NOOP")
        self.assertEqual(transport.create_calls, 1)
        self.assertEqual(transport.update_calls, 0)
        self.assertEqual(len(transport.products), 1)

    def test_wrong_store_blocks_before_preflight_or_write(self):
        document, report = validated_input()
        transport = MockShopifyDraftTransport()
        transport.identity = ShopIdentity(
            shop_gid=SHOP_GID,
            myshopify_domain="wrong-store.myshopify.com",
            primary_domain_host="ondinelondon.co.uk",
            shop_name="Ondine London",
        )
        with self.assertRaisesRegex(DraftSendBlocked, "expected Ondine") as caught:
            send_shopify_draft(document, report, store_contract(), transport, commit=True)
        self.assertEqual(caught.exception.code, "WRONG_SHOP")
        self.assertEqual(transport.events, ["read_shop"])

    def test_unmanaged_or_active_match_blocks(self):
        document, report = validated_input()
        contract = store_contract()
        plan = ListingPlan.model_validate(document)
        desired = build_desired_state(plan, contract)
        cases = (
            (
                "unmanaged",
                snapshot_for(desired, ownership={"managed_by": "someone-else"}),
                "MATCH_NOT_OWNED",
            ),
            ("active", snapshot_for(desired, status="ACTIVE"), "MATCH_NOT_DRAFT"),
        )
        for name, candidate, expected_code in cases:
            with self.subTest(case=name):
                transport = MockShopifyDraftTransport()
                transport.forced_candidates = [candidate]
                with self.assertRaises(DraftSendBlocked) as caught:
                    send_shopify_draft(
                        document, report, contract, transport, commit=True
                    )
                self.assertEqual(caught.exception.code, expected_code)
                self.assertEqual(transport.create_calls, 0)
                self.assertEqual(transport.update_calls, 0)

    def test_unknown_write_outcome_reads_before_any_retry(self):
        document, report = validated_input()
        transport = MockShopifyDraftTransport()
        transport.unknown_create = True
        result = send_shopify_draft(
            document, report, store_contract(), transport, commit=True
        )
        self.assertEqual(result.action, "RECOVERED_CREATE")
        self.assertEqual(transport.create_calls, 1)
        self.assertEqual(
            transport.events,
            ["read_shop", "find", "create", "find", "read"],
        )

    def test_final_canonical_read_back_mismatch_blocks(self):
        document, report = validated_input()
        contract = store_contract()
        transport = MockShopifyDraftTransport()
        desired = build_desired_state(ListingPlan.model_validate(document), contract)
        mismatched = copy.deepcopy(desired)
        mismatched["title"] = "Unexpected read-back title"
        transport.read_override = snapshot_for(
            mismatched,
            product_id="gid://shopify/Product/9001",
        )
        with self.assertRaises(DraftSendBlocked) as caught:
            send_shopify_draft(document, report, contract, transport, commit=True)
        self.assertEqual(caught.exception.code, "READ_BACK_MISMATCH")
        self.assertEqual(transport.create_calls, 1)


if __name__ == "__main__":
    unittest.main()
