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
