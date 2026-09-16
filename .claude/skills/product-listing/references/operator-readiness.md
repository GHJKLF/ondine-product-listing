# Ondine operator readiness

Revised 2026-09-16 after the three real listing trials. This document is part of the listing skill; it does not grant Shopify access or publication authority.


## Distribution paused — 2026-09-15

Ilias withdrew the shared GitHub repository until real product listings demonstrate that the skill works. Do not republish or send this package to Haider until those tests pass and Ilias authorizes sharing. Local real-product listing tests are explicitly authorized and should proceed using this skill; this distribution pause is not a listing blocker. Three complete drafts have now been verified locally. Sharing still requires Ilias's current authorization.

## Visual workflow

![Ondine listing workflow](ondine-listing-workflow.png)

This overview follows the skill; internal image QA, final human review before activation and operator readiness still apply.

## Private operator state

Create one persistent `ondine-operator-state` folder beside the repository, outside the replaceable checkout. In these instructions `<operator-state>` means its resolved absolute path. Create it before writing settings. Store `LEARNINGS.md`, `recent-settings.json`, the private master-sheet location and `runs/` there. Do not commit it or copy another operator’s history. For each run, retain its product URL, Shopify draft link, source capture, verification registry and pins, approvals, images and sheet outcome together. Before resuming an owned draft, find its matching run record; missing evidence is a specific resume blocker, not permission to invent approvals or create a duplicate.

## Start a listing

Handle setup and product review at their actual stages. Once the package, required runtime and source/Shopify tools are available, an authorized product URL starts source research. This is readiness to begin work, not a claim that the listing is complete. Do not label the final human draft review or the untested first real sheet update as installation failures.

The assistant verifies the product facts itself against the captured source, records `ASSISTANT_SELF_CHECK` and runs the included registration and listing checks. Follow [product evidence registration](product-evidence-registration.md). No separate reviewer, reviewer plugin or routine human fact approval is required. Do not ask Haider to arrange infrastructure or create evidence files. A genuine missing or conflicting fact may need clarification; absence of an independent reviewer is never a setup or listing blocker.

Gallery QA uses the bundled Ondine profile, seven JSON shot templates and approved run images. No Figma connection, link or export is required. Upload internally accepted original images directly to the DRAFT; no intermediate image/gallery/upload approval is needed. A missing external design file is not a prerequisite to starting this skill.

Read `SKILL.md` and its required references from the intact checkout. In ChatGPT Work, direct file reading is sufficient to apply the instructions to the task; a missing automatic skill registration is not by itself a blocker. Say “loaded for this task,” not “installed,” unless the client actually confirms installation. Do not assume a basic chat can read a repository, execute Python or use connected tools.

For a ZIP handoff, attach the complete package to the Work task and extract it before loading the skill. A connected GitHub reader does not by itself place the repository files in the code environment. Preserve the package's directory structure and use the extracted files for the required checks.

Provide the exact competitor product URL: this is the only required user input. Apply the Ondine UK profile and discover the source colours, then apply the profile’s seasonal selection rules. Colour preferences or a data-only request are optional overrides; ask only when a necessary decision cannot be resolved from the evidence and defaults. Verify product demand and seasonality before the research-sheet entry. Read the Ondine profile, copy template and checklist. Use one run folder for evidence, generated files, approvals and Shopify readbacks.

The assistant prepares one owned DRAFT, including Online Store and Google & YouTube selections. Haider checks product facts, sizing, price, all colour galleries, variants and the actual PDP before activating. Record the draft admin link and sheet status `Draft`; after human activation and verification use `Active`.

The September 13 operating decision permits operator self-review/publication subject to supervised tests and readiness. It does not establish that Haider has passed that readiness test. Ilias removed intermediate image, colour-front, gallery and upload approvals on 2026-09-15. Apply internal QA and direct uploads to DRAFT without repeatedly asking Ilias. Final human review precedes operator activation. The assistant's Shopify writes remain DRAFT-only.

## Connect Google Sheets with the operator's own account

For the master-sheet workflow, Haider installs the
[Google Drive plugin](https://chatgpt.com/plugins/google-drive?open_in_app)
in his ChatGPT client and signs in with his own Google account. The plugin
includes Google Sheets tools. An equivalent connected Google Sheets integration
is also usable when it provides the required capabilities.
That account needs **Editor access** to the Ondine master sheet, and the
integration must expose both sheet-reading and cell-update tools. A connected
search-only app is not sufficient. Available integrations can differ by client;
check the tools actually available instead of assuming a particular app name
guarantees editing.

Find the exact Ondine master sheet through the connected account. If it cannot be
identified uniquely, ask Haider for its link once and retain it in his private
operator notes outside the release. Reuse that saved location on later runs.
The competitor product link remains the only per-product starting input after
the sheet and connections are configured.

No Google login, token or connection is supplied by this repository. Never ask
for Ilias's credentials or put credentials in GitHub. The host handles sign-in.
Use the operator's available Google connector; the local `gws` CLI is not a
package requirement. An expired connection in another session does not establish
that Haider's account is broken. A missing or read-only connection blocks the
sheet step, not an otherwise separately authorized URL-based draft.

## Match and update the master-sheet row

1. Read the sheet metadata, real tab names and column headings. Record the sheet,
   tab, source-link column, status column and existing draft-link column, if any,
   in private operator notes outside the release. Never assume column letters or
   a tab called Sheet1.
2. Match the competitor URL to exactly one product row, checking hyperlink
   targets when the visible cell is a product name. Preserve meaningful variant
   and market information in URLs. If the task is to choose the next product,
   use the sheet's recorded assignment/priority rules and check Shopify for an
   existing listing. Do not choose the old Aab test product by default. Missing
   or ambiguous rows require clarification; do not insert a duplicate row or
   infer a selection rule from row order alone.
3. Use the live competitor page for price and product facts. The sheet supplies
   the assignment; it is not the price source. Complete the requested scope and
   verify the Shopify draft first. For a complete listing, this includes the
   internally checked, uploaded gallery and final read-back; for an explicitly data-only request,
   record that narrower completion in the handoff.
4. Re-read the matched row immediately before writing, since rows can move or
   another operator can update them. If it still matches and is eligible for
   this transition, update only its existing Status cell to **Draft** and its
   existing draft-link cell to the verified Shopify admin link. Preserve all
   other cells, formulas and formatting. Never downgrade an Active row. Do not
   add columns, change permissions or perform a dummy write to prove access.
5. Read back the changed cells. This first authorized real update proves write
   access; installing an integration or successfully reading a sheet does not.
   Report draft completion and sheet-update completion separately. If the sheet
   update fails, retain the draft link and pending row change so a retry does
   not create another Shopify product.
6. Only after Haider activates the product and Shopify confirms Active may the
   requested sheet handoff record **Active**. The assistant never activates the
   Shopify product as a side effect of updating the sheet.

## Complete distribution contents

- Entire `product-listing` directory: SKILL.md, profile, references, scripts, Python package, schemas and seven JSON shot templates under `profiles/ondine/higgsfield/`.
- The gallery handoff compiler and its dependencies from the separate Ondine Gallery app, or an installed equivalent validated against its contract. The referenced workspace path is not included merely by copying this skill folder.
- Python dependencies used by validators (including Pydantic) and framing analysis; compatible Node runtime for the gallery compiler. Determine actual installed versions during packaging rather than inventing requirements.
- Working source-reading tools, built-in image generation and the existing Ondine Shopify connector available in Haider's client. Scrapling is the first reader with a separate source-reading runtime described in [source-reading guidance](source-reading.md). Keep existing Firecrawl access available as a fallback, alongside the browser and explicit stdlib helper, until the real listing workflow is verified and Ilias authorizes removal. An operator without Firecrawl can still use other supported readers. Never include Ilias's credentials or vault-wide private context.
- Keep run evidence, local settings history and operator feedback outside the replaceable release directory; do not overwrite them during updates.

## Actual readiness

Three complete product drafts have been verified in Ilias's connected environment, including original galleries and real master-sheet updates. The local package checks are recorded in release notes. These results do not establish Haider's connection or permissions.

At first use, check the actual package files, Python/Node runtime, source reader, image generation and existing Ondine connector. For a master-sheet task, also check its exact row and the available Google read/update tools. Then perform the authorized listing. Do not require a separate reviewer, Figma, a prior successful listing or a dummy sheet write.

The assistant prepares and verifies source facts, validates the plan and uses only the existing connector for the owned DRAFT. Upload internally checked original images directly. Report the real draft link and sheet result, or the concrete step that failed. Do not treat an image-generation result, offline validation or connector read as proof of the complete workflow.

Signed locks and historical fixtures remain unchanged for regression checks. Their historical product data and review language are not a template for new work. Current production rules require seven images per selected colour, internal QA, direct DRAFT upload and final human review before activation.

## Updates

The maintainer supplies an approved update and tells Haider. For an attached ZIP, attach the new complete ZIP and extract it into a new folder; do not attempt `git pull` inside a ZIP extraction. For a real Git checkout with working network access, the assistant may use `git pull --ff-only`. Reload the instructions and run the checks before the next product. Keep one revision throughout a product run. Preserve the previous working revision, run evidence and local feedback outside the new release; stop on conflicts rather than discarding work. There is no automatic updater. Do not change repository visibility as part of updates.

## Verification boundaries

Report source capture, offline validation, connector read, DRAFT creation, gallery verification and sheet update as separate observed results. A missing source provider can use a supported fallback. Missing local files or required runtime cannot be fixed by claiming that a GitHub read installed them. Stop only at the actual unavailable capability; preserve completed work outside the package.
