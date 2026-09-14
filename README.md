# Ondine Product Listing

This private package prepares one original Ondine London Shopify **DRAFT** from a competitor product URL. It preserves the signed offline evidence fixtures, the locked listing-plan contract, and the approved seven-slot gallery templates. It cannot publish a product, change stock, or use a new Shopify connection.

## Workflow at a glance

![How the Ondine listing skill works](.claude/skills/product-listing/references/ondine-listing-workflow.png)

Follow the full skill for approval rules. The skill leaves the product as DRAFT; human activation is separate.

## What is proven here

- The package validates in this standalone repository layout with the complete offline Python test suite.
- The included gallery handoff compiler runs locally and rejects incomplete, unapproved, foreign, duplicate, non-ready, or non-DRAFT gallery inputs.
- The signed Phase 2 contract still resolves its locked files and checks their hashes. Do not move or rename `.claude/skills/product-listing` within this repository.

## What still needs setup

Haider's client is not confirmed. This package has been proven as a repository checkout on a Mac/Linux shell with Python 3.9+ and Node 22.6+; it has **not** been installed or end-to-end tested in Claude Code, Codex, or ChatGPT. The live workflow also needs, in Haider's client:

- authenticated source extraction;
- built-in image generation;
- the existing authenticated Ondine Shopify connector with read and DRAFT-only write access; and
- a supported product-specific FactPacket registration path and a real-product end-to-end test.

Do not treat the offline tests as proof that a live Shopify run is ready.

## Install for one trial

1. Accept the GitHub invitation, then download the repository:

   ```sh
   git clone https://github.com/GHJKLF/ondine-product-listing.git
   cd ondine-product-listing
   ```

   Open this folder in your assistant. Keep its root intact; the skill must remain at `.claude/skills/product-listing`. Claude Code uses that location; a Codex discovery link is included at `.agents/skills/product-listing`. Client discovery and connected tools still need verification on your machine.
2. Create an isolated Python environment, then install the pinned dependencies:

   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   python3 -m pip install -r requirements.txt
   ```

3. Confirm the offline package before the trial:

   ```sh
   PYTHONPATH=.claude/skills/product-listing/scripts python3 -m unittest discover -s .claude/skills/product-listing/tests -p 'test_*.py'
   node --test projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/tests/*.test.ts
   ```

   The repository ships only the handoff compiler fixtures, so use these two focused compiler tests instead if the glob expands to missing app tests:

   ```sh
   node --test projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/tests/gallery.test.ts projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/tests/listing-manifest.test.ts
   ```

4. Attach or configure the existing Ondine Shopify connector in Haider's client. Verify it identifies the Ondine shop and can read products before asking it to list anything.
5. Run one supervised, data-only product trial from an exact UK competitor URL. Follow [the skill](.claude/skills/product-listing/SKILL.md) and stop at every stated gate. Keep run evidence and local feedback outside this release directory.

## Use the skill

Give the assistant one competitor product link—the only required user input. It applies the Ondine UK defaults, discovers available colours and follows the profile’s seasonal selection rules. You may optionally specify colours or request data only; these are not mandatory inputs. Connected tools and the skill’s approval gates still apply. The skill does the following in order: verifies source evidence; checks for an existing managed draft; makes or resumes exactly one DRAFT; reads it back; then, only for a complete listing, follows the seven-slot gallery approval process. It never activates the product.

The gallery compiler is local and makes no network call. After approved media is attached to the same DRAFT, give it a complete Shopify product snapshot and approved colour manifest:

```sh
node projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/scripts/listing-handoff.ts PRODUCT_SNAPSHOT.json APPROVED_MEDIA_MANIFEST.json > REVIEWABLE_GRAPHQL_PAYLOAD.json
```

Execute the resulting payload only through the already-authenticated Shopify connector, then read it back. The compiler documentation is at [listing-handoff.md](projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/docs/listing-handoff.md).

## Manual updates before the next run

Updates are manual: the maintainer pushes an approved release to this private repository, tells Haider, and Haider pulls it **before beginning the next product run**. Finish or archive the current run first. Then retain the last known working checkout, pull the approved revision, reinstall dependencies only if `requirements.txt` changed, and run the two verification commands above. There is no automatic updater. From the repository folder, run:

```sh
git pull --ff-only
```

If Git reports local changes or a conflict, stop and ask the maintainer; do not discard your changes. Restart the assistant session after updating so it reads the new instructions.

## Integrity and privacy notes

Historical fixtures and signed locks are intentionally retained byte-for-byte, including historical product evidence and internal path strings used by the lock records. The included material has no runtime credentials or Shopify tokens. Do not edit locked files to make paths prettier: a mismatch is meant to stop validation. See [SECURITY-NOTES.md](SECURITY-NOTES.md) for the hygiene boundary.
