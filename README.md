# Ondine product listing

One competitor product link becomes one original, checked Shopify draft, with seven images per selected colour. Images are checked and uploaded directly; Haider reviews the finished draft before activation.

**Distribution is paused.** Three real listings passed in Ilias's connected environment. This local package has not been republished or sent to Haider; sharing requires Ilias's authorization. These tests do not prove access in Haider's account.

Start with [START_HERE.md](START_HERE.md). The assistant handles package extraction, scripts and checks. The operator provides the product link after connecting the required tools.

![Listing workflow](.claude/skills/product-listing/references/ondine-listing-workflow.png)

Required capabilities: readable package files, Python and Node runtime, a supported source reader, built-in image generation, and the existing Shopify connector connected to Ondine. Master-sheet work also needs the operator's own Google connection with sheet read/update access.

Scrapling is a useful first reader. Rendering, Firecrawl and browser checks remain available when needed. No reader's successful request alone proves complete or accurate product facts. Firecrawl has not been removed.

The package contains the canonical listing instructions, profile, current templates, validators, required test fixtures and the minimal gallery handoff compiler. No credentials, private operator history or generated product files belong in it. Signed historical fixtures are retained for regression checks; do not follow their old workflow as current instructions.

See [release notes](RELEASE_NOTES.md) for verification and [operator readiness](.claude/skills/product-listing/references/operator-readiness.md) for setup, exact-row sheet updates and manual package updates. Keep all work in an external operator-state folder. There is no automatic updater or onboarding mode.
