# Release notes

## 2026-09-14 — first-run repair (local, awaiting release)

- Added a short `START_HERE.md` prompt that explicitly loads the skill for a task; automatic client registration is not mandatory.
- Removed the Firecrawl-only requirement from both the workflow and compliance checklist. Added a standard-library, read-only Shopify source collector with one cookie session and retained URL/hash evidence. It marks its output as raw, unverified HTML; market/product checks still apply.
- Added registration of independently reviewed product FactPacket manifests and an explicitly hash-pinned run-registry input to normal validation. No edit to historical approvals or test mode is needed for new products. Registration never creates reviewer approval.
- Normal validation now rechecks source validity, rather than trusting a replay's claimed result, and returns blocking reports for malformed review artifacts.
- Kept DRAFT-only connector writes, store/duplicate/ownership checks, tax/inventory/pricing rules, compliance checks, seven images and visual approvals. No onboarding mode, replacement connection or automatic updater was added.

Verification: 79 Python checks pass in both canonical skill and standalone checkout; 15 gallery compiler checks pass. Skill-format and workspace reference checks pass. A separate reviewer verified the two additional validation fixes. No source/model/gallery approval is implied by that code review.

Read-only real-product check: the Aab Pink Vintage Blooms Maxi page, product JSON and cart currency were captured successfully without Firecrawl, in GB/GBP, with 35 real variants and four source images. The size guide maps S to UK 10–12 while the model text says UK 8–10 wears S; a single numeric target size cannot be inferred. The raw collector is not an automated normalized SourceCapture/FactPacket generator: source interpretation and independent review remain assistant work.

Readiness limit: no successful end-to-end listing in Haider's actual ChatGPT Work session has been demonstrated. The checking session's connected shop was not Ondine; no store connection was changed and no draft, media or activation was performed. A supervised trial must use the actual Ondine connection and resolve the product's sizing before target variants. This local repair has not been pushed or sent to Haider.

## 2026-09-13 — initial private distribution

- Packaged the canonical Ondine product-listing skill, its profiles, schemas, signed offline fixtures, maintenance record, and seven gallery slots `01`, `01b`, `02`–`06`.
- Added the minimal local gallery handoff compiler: its handoff script, three source modules, documentation, and two historical test fixtures. The Shopify app, app configuration, and dependency tree are excluded.
- Preserved all signed contract files unchanged and used the repository root plus `.claude/skills/product-listing` layout so their validation remains active.
- Documented manual update flow only: approved private-repository push, Haider notification, and pull before the next run. No automatic update mechanism is included.

Known setup gaps: Haider's client and connector are unconfirmed; authenticated source extraction, image generation, connector access, FactPacket registration, and a real product trial remain pending.

Historical issue, resolved by the repair below: the canonical `pack-manifest.json` has seven template SHA-256 mismatches against the supplied slot files. The same mismatches exist in the source skill. This package preserves both sides unchanged; no replacement hashes or approval records were made.

### Gallery verification repair

Refreshed template, human-note, combined-template and manifest checksums after the documented runtime metadata change. Added an offline regression test covering all referenced gallery files. The pre-repair manifest is preserved in the skill archives. No image template or historical composition approval was changed.

## 2026-09-14 — GitHub handoff

Included the approved complete workflow image in the README, clarified that the product link is the only required input, and added repository download/manual-update instructions. Verified 64 listing tests plus 15 gallery tests before publication. Live operator setup and the first supervised product trial remain separate.
