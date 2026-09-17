# Start an Ondine listing

This package has two items: this guide and the **skill** folder. Keep the folder intact; the assistant uses its contents for you.

## Before your first listing

1. Open a ChatGPT Work task with image generation and code execution available.
2. Connect **Shopify** to your existing Ondine London account.
3. Connect **Google Drive** with your own Google account, which needs Editor access to the Ondine master sheet.
4. Open https://github.com/GHJKLF/ondine-product-listing, choose **Code → Download ZIP**, and attach the complete ZIP to the task. Paste the prompt below, replacing the product link. You need repository access while signed in to GitHub.

The assistant handles extraction, installs or corrects the required software in its working environment, and runs the checks. You do not need to install Python or manage libraries yourself. You still connect your own accounts. If the app cannot provide a required capability, the assistant will explain the specific limitation.

## Copy this prompt

```text
Extract the attached Ondine listing ZIP. Read skill/SKILL.md and its required references, then create one complete Ondine Shopify draft from this link:

PASTE_PRODUCT_LINK_HERE

Handle setup and checks yourself using the actual files and tools available in this task. Install missing Python/Node runtimes and libraries, or correct incompatible versions in your task's environment, following the skill's tested requirements. Do not ask me to run developer commands. Use skill/requirements.txt for the listing libraries; follow the source-reading instructions for Scrapling and its fallbacks. The gallery tool is bundled at skill/gallery. Do not ask me to browse folders or supply a separate reviewer.

Verify the product facts, follow all listing and image rules, and upload the checked original images directly to the draft. Use my existing Ondine Shopify connection and my connected Google account for the master sheet. Update the exact product row only after the requested listing is complete and verified.

Keep the product as DRAFT. I will review it before activation. Keep my product work and account details outside the skill folder. If a required file, connection or capability is missing, explain exactly what is missing in simple language; do not claim success.
```

## After setup

Sizing uses Ondine’s existing shared clothing guide. The assistant keeps each product’s verified length and fit details; it does not need to build a new chart for every listing.

In the same task, send only the next product link. You do not need to repeat setup for every product. Review each finished Shopify draft before activating it.

For an update or a new task, attach the complete current ZIP. The assistant loads that version and preserves earlier product work separately. Updates are not automatic.

The skill folder contains the instructions, templates and checks. You do not need to open or edit them.

**Current distribution:** the complete package is maintained at https://github.com/GHJKLF/ondine-product-listing. Download a fresh ZIP for updates; an older attachment does not update itself.
