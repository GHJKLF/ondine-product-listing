# Release notes

## 2026-09-15 — Normal listings without a separate reviewer (local)

- Removed the mandatory separate fact reviewer from the canonical skill, the shareable package and the actual validator. Normal listings use an explicitly recorded assistant source check. No reviewer plugin, second persona or routine human fact approval is needed.
- The normal registration command now takes the manifest and SourceCapture only. It validates per-fact checks, source identity, price, options and real combinations, and records the assistant check honestly. Missing evidence and incorrect core facts still fail. Historical genuine independent reviews retain their original integrity checks.
- Removed the obsolete Figma dependency. Gallery QA uses the bundled profile, seven shot templates and approved product images. Product copy, GMC checks, image approvals, upload approval and DRAFT-only writes remain.
- Updated the copy-paste prompt and ZIP instructions. Source research starts from the product link; sheet write access is proven by the first authorized real update, not a dummy edit or an installation claim.
- Added regression coverage for the two-file command, normal validator loading, incorrect price/options/variants, missing source checks, false reviewer claims, altered records and protected existing runs.

Verification: 117 Python tests pass, including 14 focused regressions for the assistant verification path. Final ZIP and gallery checks are recorded in the accompanying local verification report.

This is a local package correction. No new live Shopify listing, sheet edit, GitHub push or delivery to Haider is claimed by these checks. Older notes below describe previous releases; this entry supersedes their mandatory separate-reviewer wording.

## 2026-09-14 — release authorized; fresh test skipped

- Ilias explicitly authorized pushing this package so Haider can start without the fresh-product simulation. The cancelled trial made no Shopify or sheet writes. No complete live workflow pass is claimed.
- Clarified external operator-state storage, duplicate-search fallback, missing private design references, separate ACTIVE-product workflow and runtime requirements. Google and Shopify connections must identify the intended sheet and Ondine store.
- Existing product checks, independent fact review, visual approval gates and human-only activation remain in force.
- Release checks: 103 Python tests and 15 gallery tests passed; skill references, frontmatter, tracked file presence and common credential-pattern scan passed. These checks do not establish a live workflow pass.


## 2026-09-14 — operator Google connection and sheet handoff (local)

- Added the Google Drive plugin link and clear setup guidance: Haider connects his own Google account with Editor access to the Ondine master sheet; the package contains no account access.
- Added exact sheet/tab/row discovery, live source pricing, Draft/link updates after the requested listing scope is verified, and read-back. A sheet failure preserves the Shopify draft for retry; Active is recorded only after human activation is verified.
- Kept the product link as the only per-product starting input after connections and the sheet location are configured. No onboarding mode or automatic updater was added.
- This is an instructions update, not a successful first-use listing or a verification of Haider's Google account. The full new-product test remains outstanding.

## 2026-09-14 — strict copy compliance (local)

- Added a required five-slot copy review before every Shopify write and after read-back.
- A missing purpose, repeated idea, unsupported statement or vague filler now fails the listing instead of receiving a partial pass.
- Corrected the supervised Aab floral maxi draft description in Shopify and verified the saved copy after reload.

## 2026-09-14 — local Aab trial corrections (not released)

- The source reader now stays within the complete product container, keeps custom accordions and guide tables separate, excludes recommendations, recognises the current colour's self-link, and reads the supplier model size without treating the brand name as a size.
- Current composition preserves exact source option names and real variant rows, adds Colour first, uses five prose paragraphs and separate fit/care rich-text fields, and permits genuinely unknown optional facts to stay blank. Product-specific source size ranges require the actual user's external approval record; there is no global numeric-size conversion override.
- The draft builder keeps source ownership private, disables tax and inventory tracking, and retains GMC/category information and verified weight. The existing connector still resolves actual category/metaobject IDs and performs live read-back.
- Source-copy checks cover the new prose, rich-text and scalar custom fields, accept the explicitly pinned source-page HTML with honest HTTP provenance, and return blocking reports for malformed rich text.
- Historical signed fixtures remain unchanged. No new connector, onboarding mode, automatic updater, media approval or publication authority was added.

The Aab source was normalized from the actual UK page and commerce data: 35 real variants, £79 source price and four gallery images. Each gallery/CDN image pair matched by independently fetched bytes. The source structure validates and reproduces deterministically. This is evidence preparation, not a complete Shopify listing.

Sizing correction: the model's usual UK size and the supplier size she wears are different facts, not evidence of contradictory conversion tables. Ilias approved retaining this product's original labels with its published UK ranges. That approval is kept outside the release and applies only to this product.

Local checks: 103 Python tests pass in canonical and standalone copies; 15 gallery tests pass. The independent code recheck covered 102 tests before the final historical-oracle-nullability regression was added. The independent reviewer rechecked the reported defects and found no remaining actionable issue in those targeted fixes. Live store access still requires reauthentication; no Shopify draft, image upload, activation, or GitHub push is established by these tests.

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
