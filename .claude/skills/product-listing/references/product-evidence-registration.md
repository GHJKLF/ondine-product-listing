# Register evidence for a new product

This is assistant-facing implementation guidance. Haider starts with one product URL. Do the evidence work internally; do not ask him to construct JSON files or run commands himself.

## Evidence and independent review

1. Capture the actual source in a run folder outside the skill checkout. Retain HTML/rendered evidence, structured product data, UK market/currency evidence, sections, sizing and the verified source gallery. `fetch_source.py` collects raw inputs only; its report is **not** a validated SourceCapture or a FactPacket.
2. Build and validate a product-specific SourceCapture using the schemas and source adapters in this package. Preserve actual artifact paths/hashes and the complete replay-result envelope required by `validate_listing_plan.py`. Do not substitute a bundled fixture. Raw HTTP collection alone does not fulfil these checks.
3. The author prepares the ordered FactPacket bindings and corresponding projection records. Use the existing manifest structure for field names only: each record states the real source locator, typed value, scope, eligibility and allowed transforms. Use a new product-specific manifest ID and real author identity/time. Do not inherit example facts, IDs, hashes, reviewer identities or approval statements.
4. A genuinely separate reviewer checks those facts against the captured source. This may be an independently run reviewer when the host supports it, or a human reviewer. The same assistant adopting a second persona does not count. The reviewer supplies the detached approval only after review, pinning the finalized manifest SHA-256, source hashes and exact ordered binding hash/count. Preserve the real review record. If no reviewer is available, stop before Shopify writes and name that limitation; never generate an approval on their behalf.

The detached review structure is the same one already checked by `listing_plan_projection_registry.py`: distinct author/reviewer identities, review after author attestation, `APPROVED`, finalized manifest hash, accepted source hashes and complete allowed binding count. This is a recorded review with integrity hashes, **not a cryptographically authenticated identity system**.

## Register and validate

The assistant runs these commands after genuine independent approval, substituting the actual run paths and reviewer identity:

```sh
python3 .claude/skills/product-listing/scripts/register_projection.py \
  RUN/fact-manifest.json RUN/reviewer-approval.json RUN/source-capture.json \
  --reviewer-id ACTUAL_REVIEWER_ID --output RUN/approved-evidence
```

The command verifies the approved evidence, refuses an existing output directory and returns `registry_sha256`. Retain that hash with the review record, outside the ListingPlan. It makes no Shopify write and does not approve the composed listing.

Compose the ListingPlan using the registered manifest ID and hash in both evidence and FactPacket pins, preserving the binding array exactly. Use the current profile/composition hashes from the maintenance record and the current seven-image gallery rules. Then run:

```sh
python3 .claude/skills/product-listing/scripts/validate_listing_plan.py \
  RUN/listing-plan.json --source-capture RUN/source-capture.json \
  --source-bundle RUN/source-bundle \
  --product-registry RUN/approved-evidence/registry.json \
  --product-registry-sha256 REVIEWED_REGISTRY_SHA256
```

All ordinary source, copy, variant, price, policy and ownership checks still apply. An unknown product, altered registry, wrong source, unreviewed binding or noncommittable report still blocks the write. Never use the test-registry injection or change the signed historical lock to admit a product.

Only after the full report passes may the assistant use the existing Shopify connector for the authorized owned DRAFT, then read it back. The Python sender is a library requiring that connector; its standalone CLI does not bundle a live transport. Do not build a second connection or describe the CLI as a one-command live listing tool.

## Current composition and approved source size ranges

Keep the source options and real variant rows unchanged in the FactPacket. Record each option's exact `source_option_name` and `source_option_position`. The target adds Colour first and preserves the source's remaining dimensions, including names such as `Length (Inches)`. Never turn every available option value into invented combinations.

The current description uses five prose paragraphs. Put factual fit and care details in `shopify_target_state.rich_text_metafields.fit_details` and `.fabric_care` as Shopify rich-text JSON roots, with eligible source references in `metafield_fact_refs`. Empty roots represent missing information; do not fabricate content to fill them. Delivery and returns remain theme policy rows. Keep private source markers out of public tags. Every target variant has tax and inventory tracking off; no stock quantity is set.

The Python desired state uses transport-neutral field names, not a ready-to-send GraphQL input. It retains the category path, GMC fields and verified weight when present. Through the existing connector, resolve the actual taxonomy and applicable category-metafield IDs for the connected Ondine shop, assign them, and verify them on read-back. Do not mistake a mock transport comparison or the offline shape check for that live category verification or the complete data-ready gate. Never invent a taxonomy/metaobject ID or a missing weight.

When Ilias explicitly approves retaining a particular product's supplier size labels and published UK ranges, keep that actual decision in an external run-local `SizeMappingApprovalRecord`. Record the exact user wording and conversation reference, the product URL, the validated capture hash and the exact original-label-to-display-label mapping. Use the time the approval was recorded without claiming a more precise user-message timestamp. This is an exception for that product, not a new default or a licence to choose numeric endpoints. A source model's usual UK size does not by itself establish a size conversion.

The independently reviewed size binding must allow `ondine_approved_source_size_label_v1`. Include `approved_size_mapping` in the plan, pinned to the external approval record, and pass the actual record path and hash separately:

```sh
--size-mapping-approval RUN/size-approval.json \
--size-mapping-approval-sha256 RECORDED_APPROVAL_SHA256
```

Never mint an approval from silence, a plan field, a fixture or another product's decision. These arguments preserve the existing user decision; they do not replace fact review or any gallery approval.
