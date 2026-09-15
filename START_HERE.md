# Start an Ondine listing

> Distribution paused by Ilias on 2026-09-15. The GitHub repository has been removed. Keep this copy locally for real listing tests; do not republish or send it to Haider until those tests pass and sharing is authorized.

## ChatGPT Work setup

Attach the complete Ondine listing package ZIP to the ChatGPT Work task, then ask the assistant to extract it into its working folder. A GitHub connector can read this repository, but that does **not** make the files available to ChatGPT Work's code environment. The package files must be visible in that environment before it can install `requirements.txt` or run the included checks.

Keep the extracted folder intact. In particular, do not move or rename `.claude/skills/product-listing`.

Before starting a listing, ask the assistant to confirm that it can see:

- `START_HERE.md`
- `requirements.txt`
- `.claude/skills/product-listing/SKILL.md`
- `.claude/skills/product-listing/scripts/register_projection.py`
- `.claude/skills/product-listing/scripts/validate_listing_plan.py`

The assistant handles dependency installation and the included checks. When these have passed for this package in this task, continue with a product link; do not repeat setup for every product.

Before using the master sheet, install the [Google Drive plugin](https://chatgpt.com/plugins/google-drive?open_in_app) and connect **your own Google account**. That account needs **Editor access** to the Ondine master sheet. Ask the assistant to find the correct sheet; provide its link once if needed. It must have tools to read and update cells, not just search files. Keep your existing Ondine Shopify connection too.

After setup, paste this, replacing the product link:

```text
Read .claude/skills/product-listing/SKILL.md and its required references in this repository. Apply them to create one Ondine listing from this product link:

PASTE_PRODUCT_LINK_HERE

Use the tools available in this session. If automatic skill registration is unavailable, load the instructions directly. Follow the supported source-reading and product-evidence steps; do not stop just because Firecrawl is absent or no earlier test listing exists.

Begin the source research and verify the product facts yourself against the captured evidence. Use the normal assistant self-check and registration path. Do not ask me to supply a separate reviewer or approve routine fact checks. Handle all scripts and evidence records yourself; do not invent independent or human approval. Use the bundled profile and seven image templates for gallery QA. Figma is not part of this workflow.

Keep the product as DRAFT, use only the existing Ondine Shopify connector, and keep every product check and approval gate. Explain any real blocker simply. Do not invent facts or approvals, or claim a step is complete without checking it.

Use my connected Google account for the Ondine master sheet. Match this product's row and follow the sheet handoff instructions. Record Draft and the draft link only after the requested listing is complete and verified, then check the saved cells. If sheet access is missing, explain that separately and preserve any completed Shopify draft.
```

After the instructions are loaded, a product link is the only required starting input. The assistant does the research and preparation. You may still need to resolve missing product facts or approve images at the existing review points.

For updates to a ZIP installation, attach the new complete package before the next product. The assistant extracts it into a new folder and preserves your previous work outside it. A real Git checkout can use a normal pull instead. Reload the instructions after updating. There is no automatic updater or onboarding mode.

The instructions do not grant tool access. A successful run ends with an actual checked DRAFT link; reading the files or passing tests alone is not that result.
