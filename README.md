# Ondine Product Listing

This package helps your assistant prepare one original Ondine London Shopify **DRAFT** from a competitor product link. Start with [START_HERE.md](START_HERE.md). You do not need to understand the scripts or install Firecrawl to begin if your existing tools can read the source.

It keeps product checks, the seven-image workflow and approval gates. It never activates a product or creates a new Shopify connection. **Ilias authorized release without the fresh-product simulation. Haider may begin; a complete live listing is not yet proven. Normal product checks and approval gates remain.**

## Workflow at a glance

![How the Ondine listing skill works](.claude/skills/product-listing/references/ondine-listing-workflow.png)

Follow the full skill for approval rules. The skill leaves the product as DRAFT; human activation is separate.

## What is proven here

- The package validates in this standalone repository layout with the complete offline Python test suite.
- The included gallery handoff compiler runs locally and rejects incomplete, unapproved, foreign, duplicate, non-ready, or non-DRAFT gallery inputs.
- The signed Phase 2 contract still resolves its locked files and checks their hashes. Do not move or rename `.claude/skills/product-listing` within this repository.

## What still needs setup

Haider reports using ChatGPT Work and having connected Shopify. His reported offline checks passed, but no listing completed. The live workflow needs, in the actual client:

- working source reading through existing tools or the included Python helper;
- built-in image generation;
- the existing authenticated Ondine Shopify connector with read and DRAFT-only write access;
- for the master sheet, the [Google Drive plugin](https://chatgpt.com/plugins/google-drive?open_in_app) connected to **Haider's own Google account**, with Editor access to the Ondine master sheet and tools to read and update its cells; and
- independent review of product facts, followed by the included registration and validation steps.

The first supervised product run establishes readiness; a previous successful run is not a prerequisite to starting it. If automatic skill discovery is unavailable, the assistant reads the files directly.

Do not treat the offline tests as proof that a live Shopify run is ready.

## Install and start

1. Download the shared repository:

   ```sh
   git clone https://github.com/GHJKLF/ondine-product-listing.git
   cd ondine-product-listing
   ```

   Open this folder in your assistant and ask it to read `START_HERE.md`. Keep the root intact; the skill must remain at `.claude/skills/product-listing`. A discovery link is included at `.agents/skills/product-listing`; direct reading is supported when the host does not register it automatically.
2. Use Python 3.10 or newer and Node.js 24 LTS (or Node.js 22.18 or newer). The assistant can prepare these if the host permits. Create an isolated Python environment, then install the pinned dependencies:

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
   For the master-sheet handoff, also connect Google Drive with Haider's own account and locate the correct sheet. If it cannot be found uniquely, provide the sheet link once. Verify the exact row and columns before an update; only a successful real update followed by read-back proves write access. Account sign-ins and private sheet locations are not supplied by this repository.
5. Give an exact UK competitor product URL to start the authorized listing. A separate trial is not required by this release decision. Follow [the skill](.claude/skills/product-listing/SKILL.md) and its review gates. Keep evidence and feedback in the external operator-state folder described in operator readiness. Independent fact review needs a separate reviewer or a human; the assistant must not pretend to review its own work independently. Approved Figma reference links or exports are needed for the final design comparison; ask for them if unavailable.

## Use the skill

Give the assistant one competitor product link—the only required user input. It applies the Ondine UK defaults, discovers available colours and follows the profile’s seasonal selection rules. You may optionally specify colours or request data only; these are not mandatory inputs. Connected tools and the skill’s approval gates still apply. The skill does the following in order: verifies source evidence; checks for an existing managed draft; makes or resumes exactly one DRAFT; reads it back; then, only for a complete listing, follows the seven-slot gallery approval process. It never activates the product.

The gallery compiler is local and makes no network call. After approved media is attached to the same DRAFT, give it a complete Shopify product snapshot and approved colour manifest:

```sh
node projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/scripts/listing-handoff.ts PRODUCT_SNAPSHOT.json APPROVED_MEDIA_MANIFEST.json > REVIEWABLE_GRAPHQL_PAYLOAD.json
```

Execute the resulting payload only through the already-authenticated Shopify connector, then read it back. The compiler documentation is at [listing-handoff.md](projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/docs/listing-handoff.md).

## Manual updates before the next run

Updates are manual: the maintainer pushes an approved release to this shared repository, tells Haider, and Haider pulls it **before beginning the next product run**. Finish or archive the current run first. Then retain the last known working checkout, pull the approved revision, reinstall dependencies only if `requirements.txt` changed, and run the two verification commands above. There is no automatic updater. From the repository folder, run:

```sh
git pull --ff-only
```

If Git reports local changes or a conflict, stop and ask the maintainer; do not discard your changes. Restart the assistant session after updating so it reads the new instructions.

## Integrity and privacy notes

Historical fixtures and signed locks are intentionally retained byte-for-byte, including historical product evidence and internal path strings used by the lock records. The included material has no runtime credentials or Shopify tokens. Do not edit locked files to make paths prettier: a mismatch is meant to stop validation. See [SECURITY-NOTES.md](SECURITY-NOTES.md) for the hygiene boundary.
