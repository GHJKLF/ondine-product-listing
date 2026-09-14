# Ondine operator readiness

Reviewed 2026-09-13. This document is part of the listing skill; it does not grant Shopify access or publication authority.

## Visual workflow

![Ondine listing workflow](ondine-listing-workflow.png)

This overview follows the skill; full approval rules and operator readiness still apply.

## Start a listing

Provide the exact competitor product URL: this is the only required user input. Apply the Ondine UK profile and discover the source colours, then apply the profile’s seasonal selection rules. Colour preferences or a data-only request are optional overrides; ask only when a necessary decision cannot be resolved from the evidence and defaults. Verify product demand and seasonality before the research-sheet entry. Read the Ondine profile, copy template and checklist. Use one run folder for evidence, generated files, approvals and Shopify readbacks.

The assistant prepares one owned DRAFT, including Online Store and Google & YouTube selections. Haider checks product facts, sizing, price, all colour galleries, variants and the actual PDP before activating. Record the draft admin link and sheet status `Draft`; after human activation and verification use `Active`.

The September 13 operating decision permits operator self-review/publication subject to supervised tests and readiness. It does not establish that Haider has passed that readiness test. Until readiness and the applicable gallery-review delegation are recorded, retain the existing visual gates. Once Ilias explicitly delegates those gates for the operator workflow, record that scope and apply it without repeatedly asking Ilias. The assistant's Shopify writes remain DRAFT-only.

## Complete distribution contents

- Entire `product-listing` directory: SKILL.md, profile, references, scripts, Python package, schemas and seven JSON shot templates under `profiles/ondine/higgsfield/`.
- The gallery handoff compiler and its dependencies from the separate Ondine Gallery app, or an installed equivalent validated against its contract. The referenced workspace path is not included merely by copying this skill folder.
- Python dependencies used by validators (including Pydantic) and framing analysis; compatible Node runtime for the gallery compiler. Determine actual installed versions during packaging rather than inventing requirements.
- Authenticated source extraction, built-in image generation and the existing Ondine Shopify connector available in Haider's client. Never include Ilias's credentials or vault-wide private context.
- Keep run evidence, local settings history and operator feedback outside the replaceable release directory; do not overwrite them during updates.

## Known release blockers

The outdated document checksum mismatch is repaired through a separately pinned maintenance record, authorized by Ilias in this conversation. Original signed locks and historical fixtures remain unchanged; the maintenance record does not claim independent reviewer approval. Current production media checks require seven ordered images and the current review gate. The original exact example remains a historical, noncommittable fixture.

The runtime still resolves product FactPacket manifests through a trusted registry; a fixture is not a registration path for a new product. A supported product-specific registration path and a real-product end-to-end test remain required before claiming the compiled workflow is ready for Haider. Never use test mode or manufacture reviewer attestations to bypass these requirements.

Haider's client is not yet confirmed (Claude Code, Codex or ChatGPT). Therefore no portable installation, end-to-end operator test or automatic update mechanism is claimed complete by this review.

## Updates

Distribute approved versioned releases from one private source. Check for a newer approved release before a new listing; download and validate it completely before switching. Pin the selected version for the whole product run, retain the last working version and never overwrite local feedback. A stable document link alone does not update an installed skill. The actual update mechanism depends on Haider's client and access and remains to be configured.

## Verification on this revision

Before repair, unittest discovery ran 57 tests and reported 33 failures (including subtests), caused by the outdated contract checks. After repair, the original 57 tests pass. All 63 offline tests pass. Six additional regression checks cover current gallery requirements, duplicate filenames, release integrity and historical-example restrictions. Source references passed the workspace reference checker. No Shopify writes, operator messages, repository pushes or updater installation were performed.
