# Local package — 16 September 2026

Open START_HERE.md. The skill folder contains the same operating instructions, templates and checks as Ilias’s canonical product-listing skill. The package also bundles its existing gallery helper and pinned Python requirements so it does not require the TanjaiOS folder. Accounts and product work stay outside the package.

## Shared size guide update

Ondine clothing uses the existing UK 4–28 BODY guide. Its canonical centimetre table is profiles/ondine/size-guide.csv. Normal listings do not require competitor-chart extraction or per-product Kiwi editing. Verified product length/fit stays separate. The guide does not establish supplier equivalence or invent size options. Existing explicit product-specific exceptions remain scoped to their products.

The shared guide was checked on an existing draft in desktop and mobile previews. This is a guide/skill maintenance check, not a claim that Haider’s own account or a complete fresh listing run was tested. The earlier independent listing continuation still has separate completion items recorded outside this package.

The assistant manages dependencies in its available working environment. The operator connects their accounts, supplies the product link and reviews the finished DRAFT before activation. A missing host capability or account permission cannot be fixed by these instructions alone.

Distribution remains paused. This local package has not been republished or sent to Haider. Historical release notes and before-state files are preserved outside the package and in local Git history.

## Maintainer handoff update — 2026-09-16

Local revision `2026-09-16-maintainer-handoff` synchronizes the canonical category and distinct-second-model fixes, and adds evidence-based issue reporting to Tanjai Dev with pending-delivery handling and bounded recovery. The packaged visual-workflow link goes directly to Miro so it does not require the TanjaiOS folder. Distribution remains paused.

## Full PDP colour coverage update — 2026-09-16

Local revision `2026-09-16-full-pdp-colour-coverage` requires discovery of sibling product URLs in the current PDP swatches, captures each sibling’s real variants, and compares the selected source union against proposed and complete Shopify readback rows. The offline validator rejects missing, extra or duplicate combinations. Single-product JSON sources retain the existing validation path. Distribution remains paused.

## Offline workflow — 2026-09-16

The maintained visual reference is now bundled as `references/workflow.html`, with the same flowchart shapes and connections as the former Miro diagram. No Miro account or network is required. This supersedes the earlier Miro-link maintenance requirement. Distribution remains paused.

## Source design details — 2026-09-16

Image prompt rendering now requires `product.design_details` with feature, placement and source evidence. Existing runs must inspect sources and populate that record before rendering new prompts. Each slot carries the details; visual QA checks counts and bilateral/asymmetric placement against source images, not only generated continuity references. No Shopify data is changed by this patch.

## Category readback gate — 2026-09-17

Before data-ready/completion and the master-sheet Draft update, run `scripts/verify_category_readback.py` against source-supported expectations and fresh actual connector readback. Missing fields, wrong values, unresolved references, wrong identity/revision or incomplete pagination fail closed. This is a category gate within the existing flow, not a new approval step.

## GitHub distribution — 2026-09-17

Ilias authorized pushing this package to GitHub for Haider. This supersedes the earlier distribution hold. Use the private repository GHJKLF/ondine-product-listing and its current complete ZIP; START_HERE.md explains installation. Haider needs repository access. Latest full package validation: 178 tests passed.

Ilias requested temporary public access for Haider’s download on 2026-09-17. Return the repository to private after download is confirmed; GitHub does not report who downloaded a ZIP.
