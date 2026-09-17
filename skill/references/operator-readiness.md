# Ondine operator readiness

Revised 2026-09-16 after the three real listing trials. This document is part of the listing skill; it does not grant Shopify access or publication authority.


## Distribution paused — 2026-09-15

Ilias withdrew the shared GitHub repository until real product listings demonstrate that the skill works. Do not republish or send this package to Haider until those tests pass and Ilias authorizes sharing. Local real-product listing tests are explicitly authorized and should proceed using this skill; this distribution pause is not a listing blocker. Three complete drafts have now been verified locally. Sharing still requires Ilias's current authorization.

## Visual workflow

![Ondine listing workflow](ondine-listing-workflow.png)

This overview follows the skill; internal image QA, final human review before activation and operator readiness still apply.

## Private operator state

Create one persistent `ondine-operator-state` folder beside the repository, outside the replaceable checkout. In these instructions `<operator-state>` means its resolved absolute path. Create it before writing settings. Store `LEARNINGS.md`, `recent-settings.json`, the private master-sheet location and `runs/` there. Do not commit it or copy another operator’s history. For each run, retain its product URL, Shopify draft link, source capture, verification registry and pins, approvals, images and sheet outcome together. Before resuming an owned draft, find its matching run record; missing evidence is a specific resume blocker, not permission to invent approvals or create a duplicate.

## Assistant-managed runtime setup

Before creating the local environments, inspect the versions of the executables that will actually run. Scrapling requires Python 3.10 or newer; read the bundled gallery tool's `package.json` for its Node minimum (currently 22.18.0). An older shell default does not mean a compatible runtime is unavailable.

If the default is too old, inspect the host's available runtime paths and select an already installed compatible version. Use its explicit executable path, or a task-local PATH, consistently for installation and execution. Record those paths in private operator settings outside the skill. Do not change the machine-wide default or ask the operator to troubleshoot developer commands. If no suitable runtime exists, install it in the task when the host supports that; otherwise report the exact unavailable capability. Source-reader fallbacks remain available as described in [source-reading guidance](source-reading.md).

Keep the listing validators and Scrapling in separate environments, using their respective requirements files. If a required library is missing or its installed version differs from the package requirement, install the specified version in the appropriate task-local environment automatically. Upgrade or replace incompatible task-local copies as needed; do not alter the operator's system libraries or change the package's pins just to match preinstalled software. A newer library number is not automatically the tested version. `pytest` is not required for the bundled `unittest` suite and its absence is not a blocker.

Prefer a maintained Python release that is compatible with the package requirements; the documented minimum is a compatibility floor, not a request to install an obsolete release. When Python or Node itself is missing or incompatible, the assistant selects or installs a compatible runtime within the environment it can control. This means the ChatGPT Work task's environment when that is where code runs; do not claim to install software on Haider's laptop without actual local execution access.

Check imports and actual versions after installation, then run the included checks with those same executables. A successful install command alone is not proof that the correct runtime is being used. Do this once per task/package setup, not for every product. If the same installation failure persists after checking its cause and trying an available compatible runtime or supported fallback, report the concrete host restriction and the smallest user action needed. Do not send Haider a developer setup checklist, invent a successful installation or repeatedly retry an unchanged failure. Account sign-in and granting access remain the operator's actions.

## Start a listing

Handle setup and product review at their actual stages. Once the package, required runtime and source/Shopify tools are available, an authorized product URL starts source research. This is readiness to begin work, not a claim that the listing is complete. Do not label the final human draft review or the untested first real sheet update as installation failures.

The assistant verifies the product facts itself against the captured source, records `ASSISTANT_SELF_CHECK` and runs the included registration and listing checks. Follow [product evidence registration](product-evidence-registration.md). No separate reviewer, reviewer plugin or routine human fact approval is required. Do not ask Haider to arrange infrastructure or create evidence files. A genuine missing or conflicting fact may need clarification; absence of an independent reviewer is never a setup or listing blocker.

Gallery QA uses the bundled Ondine profile, seven JSON shot templates and approved run images. No Figma connection, link or export is required. Upload internally accepted original images directly to the DRAFT; no intermediate image/gallery/upload approval is needed. A missing external design file is not a prerequisite to starting this skill.

Read `SKILL.md` and its required references from the intact checkout. In ChatGPT Work, direct file reading is sufficient to apply the instructions to the task; a missing automatic skill registration is not by itself a blocker. Say “loaded for this task,” not “installed,” unless the client actually confirms installation. Do not assume a basic chat can read a repository, execute Python or use connected tools.

For a ZIP handoff, attach the complete package to the Work task and extract it before loading the skill. A connected GitHub reader does not by itself place the repository files in the code environment. Preserve the package's directory structure and use the extracted files for the required checks.

Provide the exact competitor product URL: this is the only required user input. Apply the Ondine UK profile and discover the source colours, then apply the profile’s seasonal selection rules. The shared Ondine BODY guide is already the default; do not request a competitor size chart or create or assign a per-product Kiwi chart for a normal listing. Keep actual source option identity intact, and use source sizing only when a product-specific fit, length, measurement or legitimate variant-identity check needs it. Colour preferences or a data-only request are optional overrides; ask only when a necessary decision cannot be resolved from the evidence and defaults. Verify product demand and seasonality before the research-sheet entry. Read the Ondine profile, copy template and checklist. Use one run folder for evidence, generated files, approvals and Shopify readbacks.

The assistant prepares one owned DRAFT, including Online Store and Google & YouTube selections. Haider checks product facts, any verified product-specific fit content, price, all colour galleries, variants and the actual PDP before activating. The shared BODY guide is a standing brand standard, not a product-specific measurement or supplier-mapping review. Record the draft admin link and sheet status `Draft`; after human activation and verification use `Active`.

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

Before writing Draft, run `scripts/verify_category_readback.py` with fresh actual Shopify category/metafield readback and this product’s complete source-supported expectations, following [category-readback.md](category-readback.md). Require exit 0 and `sheet_draft_allowed: true`; otherwise preserve the sheet row and repair/reverify the same draft. Do not equate product creation or category assignment with completion.

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
- The simplified package includes the gallery handoff compiler at `gallery/` beside `SKILL.md`, and Python requirements at `requirements.txt`. The standalone workspace skill uses the existing Ondine Gallery app instead. Copying the workspace skill alone is not the complete operator package.
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

## Issue reporting and repair

Ilias assigned **Tanjai Dev** as this skill's maintainer on 2026-09-16. In Ilias's Codex workspace, the destination is **Improve autonomous product listing**, task ID `01a0aaa9-4c01-7182-81b0-038ea25edca6`. Listing tasks own their run artifacts; the maintainer owns canonical skill edits. This is an event-driven handoff, not a background monitor or permission to publish products.

When a new issue occurs:

1. Append the learning immediately, preserving the failed output and the current product/run state. Include the run path, skill revision (or SKILL.md SHA-256 when unversioned), source URL, affected step, exact error or observed mismatch, expected result, attempted recovery and whether the affected step is blocked. Link only the relevant evidence; exclude credentials and unrelated operator data.
2. If a cross-task messaging tool is available and can reach the destination, send that concise report to the maintainer task. Ilias authorizes these skill-issue reports; do not ask again. Include the reporting task's ID so a fix can be returned. Send once per issue and revision, then send only material new evidence. Do not send to the reporting task itself or echo acknowledgement messages back into a reporting loop.
3. Record the tool's actual delivery outcome in the run. A sent message is not acknowledgement or a verified fix. If messaging is unavailable, fails, or the destination is inaccessible, retain the report with `REPORT_PENDING` in the run and include its path in the final handoff. Do not create another task, connect another account, or block an otherwise valid listing merely to deliver feedback.
4. Continue unaffected work under the current safeguards. Use documented fallbacks and their existing retry limits. If no limit is specified, allow at most two recovery attempts for the same failure, each informed by new evidence; then stop only the affected step and report the gap. Never waive factual, ownership, image-QA or DRAFT checks to appear autonomous.

The maintainer reproduces or verifies the report against its source evidence before changing instructions or code. After a narrow patch, run the affected checks, synchronize canonical mirrors and the local HTML workflow, and return the revision, changed files, checks, remaining limitations and exact resume step to the reporting task. Preserve the original report; append the resolution and revision under `## Merged` only when verified. Tests passing do not establish a successful live listing.

Keep one revision during normal product work. To unblock an affected run with a maintainer fix, record a deliberate revision transition: preserve its old instructions and evidence, load the corrected files, rerun the affected validation, and resume the same owned DRAFT after fresh connector read-back. Never restart by creating a second product. A report or patch does not authorize live activation or package distribution.

## Verification boundaries

Report source capture, offline validation, connector read, DRAFT creation, gallery verification and sheet update as separate observed results. A missing source provider can use a supported fallback. Missing local files or required runtime cannot be fixed by claiming that a GitHub read installed them. Stop only at the actual unavailable capability; preserve completed work outside the package.
