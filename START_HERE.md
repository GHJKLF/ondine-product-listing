# Start an Ondine listing

Open this repository in ChatGPT Work (or another assistant with file access, Python, image generation and the existing Ondine Shopify connector). Paste this, replacing the link:

```text
Read .claude/skills/product-listing/SKILL.md and its required references in this repository. Apply them to create one Ondine listing from this product link:

PASTE_PRODUCT_LINK_HERE

Use the tools available in this session. If automatic skill registration is unavailable, load the instructions directly. Follow the supported source-reading and product-evidence steps; do not stop just because Firecrawl is absent or no earlier test listing exists.

Keep the product as DRAFT, use only the existing Ondine Shopify connector, and keep every product check and approval gate. Explain any real blocker simply. Do not invent facts or approvals, or claim a step is complete without checking it.
```

After the instructions are loaded, a product link is the only required starting input. The assistant does the research and preparation. You may still need to resolve missing product facts or approve images at the existing review points.

For updates, ask your assistant to pull the latest approved GitHub version before the next product and reload the instructions. It should preserve your previous work and stop on conflicts. There is no automatic updater or onboarding mode.

The instructions do not grant tool access. A successful run ends with an actual checked DRAFT link; reading the files or passing tests alone is not that result.
