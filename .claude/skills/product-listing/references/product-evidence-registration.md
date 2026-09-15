# Register evidence for a new product

This is assistant-facing implementation guidance. Haider starts with one product URL. Do the evidence work internally; do not ask him to construct files, run commands or find a reviewer.

## Evidence and assistant verification

1. Capture the actual source in a run folder outside the skill checkout. Retain HTML/rendered evidence, structured product data, UK market/currency evidence, sections, sizing and the verified source gallery. `fetch_source.py` collects raw inputs only; its report is **not** a validated SourceCapture or a FactPacket.
2. Build and validate a product-specific SourceCapture using the schemas and source adapters in this package. Preserve actual artifact paths/hashes and the complete replay-result envelope required by `validate_listing_plan.py`. Do not substitute a bundled fixture. Raw HTTP collection alone does not fulfil these checks.
3. Prepare the ordered FactPacket bindings and corresponding projection records. Each record states the real source locator, typed value, scope, eligibility and allowed transforms. Use a new product-specific manifest ID and the actual assistant identity/time. Do not inherit example facts, IDs, hashes or approval statements.
4. Check every proposed fact against the captured evidence. Cross-check the customer-paid GBP price, sizing, all options, real combinations, garment details and source-gallery identity. Resolve conflicts; omit unsupported optional claims and stop only where a necessary fact is unresolved. Record this as the assistant's own check. **A separate reviewer, reviewer plugin or human fact approval is not required for a normal listing.**

Set the manifest's `verification_method` to `ASSISTANT_SELF_CHECK`. Keep `actors.author_auditor` with the real `actor_id`, `attestation_status=AUTHOR_AUDIT_COMPLETE` and timezone-aware `attested_at`. Each projection record uses `assistant_verification` containing that same `actor_id`, `verified=true`, timezone-aware `checked_at`, nonempty `evidence_sources` and `notes` describing the comparison actually made. Evidence sources may be precise capture locators or artifact records with path, hash, locator and optional raw value/hash. Preserve detailed evidence when available. Complete the check after preparing the facts and before registration. Do not include `required_reviewer_signatory` or `reviewer_verification`, invent a second persona or describe this as independent or human approval.

These records and hashes provide traceability and integrity, not a guarantee that every interpretation is correct. The assistant must actually inspect the evidence; adding a `verified` flag alone is not the work. If a binding changes, check and register the new version before using it. Internal image QA and DRAFT-only writes remain required. Upload accepted original images without intermediate approval; final human review precedes activation.

## Register and validate

After checking the facts, the assistant runs:

```sh
python3 .claude/skills/product-listing/scripts/register_projection.py \
  RUN/fact-manifest.json RUN/source-capture.json \
  --output RUN/verified-evidence
```

No review file or reviewer ID is needed. The command checks the records, source identity, price, options and real combinations; records the assistant's verification; refuses an existing output directory; and returns `registry_sha256`. Retain that hash with the run record outside the ListingPlan. It makes no Shopify write and does not approve the composed listing.

Compose the ListingPlan using the registered manifest ID and hash in both evidence and FactPacket pins, preserving the binding array exactly. Use the current profile/composition hashes from the maintenance record and the current seven-image gallery rules. Then run:

```sh
python3 .claude/skills/product-listing/scripts/validate_listing_plan.py \
  RUN/listing-plan.json --source-capture RUN/source-capture.json \
  --source-bundle RUN/source-bundle \
  --product-registry RUN/verified-evidence/registry.json \
  --product-registry-sha256 RECORDED_REGISTRY_SHA256
```

All ordinary source, copy, variant, price, policy and ownership checks still apply. An unknown product, altered registry, wrong source, unchecked binding or noncommittable report still blocks the write. Never use test-registry injection or change the historical lock to admit a product.

Only after the full report passes may the assistant use the existing Shopify connector for the authorized owned DRAFT, then read it back. The Python sender is a library requiring that connector; its standalone CLI does not bundle a live transport. Do not build a second connection or describe the CLI as a one-command live listing tool.

Existing genuine independent reviews remain supported by the older three-file command with `--reviewer-id`. That path still requires distinct identities and actual approval. It is optional for explicitly requested reviews and historical evidence; do not choose it as a prerequisite for a normal listing or relabel it to bypass an existing unresolved review.

## Current composition and approved source size ranges

Keep the source options and real variant rows unchanged in the FactPacket. Record each option's exact `source_option_name` and `source_option_position`. The target adds Colour first and preserves the source's remaining dimensions, including names such as `Length (Inches)`. Never turn every available option value into invented combinations.

An explicit single UK numeric source label such as `UK 8 (S)` may display as `8` through `ondine_uk_numeric_size_identity_v1`. This preserves the supplier's stated UK number; it is not a conversion from S or a range. Retain the exact original source label in the FactPacket and use the numeric target in the Size option, size module and numeric SKU code. No separate user mapping approval is needed. Letter-only labels, other markets, UK ranges and colliding mappings remain unresolved and cannot use this path.

For the profile's seasonal colour selection, keep every captured colour and row in the source evidence. Add `seasonal_colour_selection` to the ListingPlan with `season` (`AUTUMN_WINTER` or `SPRING_SUMMER`), `selected_colours` (exact source values in source order) and a product-specific `reason`. Inspect actual garment colours against the profile before selecting; this record documents the assistant's selection, not new user approval. The target retains every real size/fit combination within the selected colours, in source order. Without this record the validator still requires all source colours. An unknown colour, reordered selection, omitted retained row or invented combination blocks the write.

The current description uses five prose paragraphs. Put factual fit and care details in `shopify_target_state.rich_text_metafields.fit_details` and `.fabric_care` as Shopify rich-text JSON roots, with eligible source references in `metafield_fact_refs`. Empty roots represent missing information; do not fabricate content to fill them. Delivery and returns remain theme policy rows. Keep private source markers out of public tags. Every target variant has tax and inventory tracking off; no stock quantity is set.

The Python desired state uses transport-neutral field names, not a ready-to-send GraphQL input. It retains the category path, GMC fields and verified weight when present. Through the existing connector, resolve the actual taxonomy and applicable category-metafield IDs for the connected Ondine shop, assign them, and verify them on read-back. Do not mistake a mock transport comparison or the offline shape check for that live category verification or the complete data-ready gate. Never invent a taxonomy/metaobject ID or a missing weight.

When Ilias explicitly approves retaining a particular product's supplier size labels and published UK ranges, keep that actual decision in an external run-local `SizeMappingApprovalRecord`. Record the exact user wording and conversation reference, the product URL, the validated capture hash and the exact original-label-to-display-label mapping. Use the time the approval was recorded without claiming a more precise user-message timestamp. This is an exception for that product, not a new default or a licence to choose numeric endpoints. A source model's usual UK size does not by itself establish a size conversion.

The verified size binding must allow `ondine_approved_source_size_label_v1`. Include `approved_size_mapping` in the plan, pinned to the external approval record, and pass the actual record path and hash separately:

```sh
--size-mapping-approval RUN/size-approval.json \
--size-mapping-approval-sha256 RECORDED_APPROVAL_SHA256
```

Never mint an approval from silence, a plan field, a fixture or another product's decision. These arguments preserve the existing user decision; they do not replace source verification or any gallery approval.
