# Profile — Ondine London

UK women's fashion. Product selection is not restricted to covered styles, long sleeves or occasionwear (Ilias, 2026-09-07). Engine 3, Haider's store. Operating entity **Talen and Haten Limited**.

- Shopify admin handle `getaquablade` (legacy) → `admin.shopify.com/store/getaquablade` · myshopify `zfrbm1-y6.myshopify.com` · domain ondinelondon.co.uk
- ⚠ **`getaquablade` is legacy ONDINE, not the AquaBLADE brand** — Ondine was renamed from AquaBLADE. AquaBLADE's own admin is `outletgreen-2`. Check the handle before every write.
- Shopify MCP is connected to this store. Product writes = draft only. `themePublish` is blocked and stays blocked.

## Voice and copy formulas

Calm editorial. Short sentences. No exclamation marks. **Never** "premium", "exclusive", "luxury". Urgency only as factual mechanics (shipping cutoffs), never scarcity.

- **Shared Shopify/GMC title (apparel):** Build one natural title from current buyer-search language and verified product facts. Prefer `[gender?] + [colour?] + [high-intent verified attributes] + [product type]`, but arrange the words naturally rather than forcing a keyword stack. Product type is required; gender, colour, fabric, print, sleeve, length or occasion may be used only when relevant and proven. For multi-size products, size belongs in variant data, not the shared title. Target ≤70 characters; hard stop >150.
- **Description opening:** silhouette → fabric/coverage benefit. Keep the styling suggestion in description slot 4 so each of the five slots has one job.
- **Metafields:** size · fabric · occasion · neckline · age group. Populate applicable fields from verified evidence; occasion follows the editorial rule below. Unknown physical facts stay blank and are flagged. An incomplete review DRAFT is not an activation-ready listing.
- **Originality gate:** `ondine_copy_guard_v1` must independently derive PASS from the locked source and target corpora. Competitor expression stays in the private audit lane; the ListingPlan carries only field paths, counts, hashes, exact whitelisted spans and the derived result.
- **Verified FactPacket gate:** normal Ondine composition accepts an `fp.*` binding only when it is present unchanged in a product-specific FactPacket projection manifest whose ID and SHA-256 are pinned by the ListingPlan. The assistant verifies every fact against the source and records `ASSISTANT_SELF_CHECK`; no separate reviewer or routine human fact approval is required. Real independent reviews remain supported when explicitly requested, and must never be fabricated. Missing, added, removed, reordered or changed bindings—including value, evidence, scope, conflict state, claim eligibility, policy eligibility or allowed transforms—are a STOP. The Calloway manifest is a golden-fixture dependency only, never a runtime default.

`references/copy-templates.md` holds the shape that applies to any brand (slot count, character limits, banned content); these formulas are the Ondine-specific fill. A non-apparel brand replaces this section in its own profile.

## Price

Use **the price the reference competitor currently charges, including a sale price**, forced to the nearest `.95` strictly below the input, as Ondine's regular price (Ilias 2026-08-31). Exact boundaries: `£59.00 → £58.95`, `£59.40 → £58.95`, `£59.95 → £58.95`, `£59.96 → £59.95`.

This pricing rule lives only in this profile. The shared engine captures source prices and applies the loaded profile; it does not contain an Ondine pricing decision.

Confirmed test instance: Karen Millen charged £99 for Cobalt and £80 for Ivory against a £199 struck price, so the Ondine draft uses **£98.95** and **£79.95** as its regular variant prices. The competitor's countdown does not change that result.

No price band. Occasion pieces may sit high when the reference supports it.

## Draft review and default sales channels

Ilias clarified on 2026-09-09: keep every new listing **DRAFT until Haider reviews and activates it**, with **Online Store and Google & YouTube selected by default**. Resolve these channels on the connected store and assign them through the existing Shopify connector while preserving DRAFT. Do not leave all channels off. Activation belongs to Haider; channel assignment is part of draft preparation. Google sync remains subject to channel processing and product eligibility. This supersedes older “no publications / no sales channels” checks; it does not authorize making existing ACTIVE products newly visible.

## Inventory

No stock is tracked. Every variant ships with `inventoryItem.tracked=false` so Shopify treats it as always available, matching the four live products. Never set quantities or an inventory policy; a tracked variant with 0 stock reads Sold out on the storefront (Ilias 2026-09-03).

## Tax

Ondine does not charge tax. Set `taxable=false` (Shopify “Charge taxes” disabled) on every variant. Never inherit the competitor's tax setting or rely on Shopify's default; verify it after writing.

## Sizes — verified product-specific mapping

**Locked by Ilias 2026-08-08.** Every Ondine product ships UK numeric sizes, even numbers, whatever the supplier labels them. The conversion table below runs to 28 for stretch pieces that genuinely span that far; the everyday range is 4–24. Convert at listing time in the Shopify variant option so Shopify, the size chart and the Google feed agree.

| Letter | UK | EU | Bust cm |
|---|---|---|---|
| XS | 4–6 | 32–34 | 82 |
| S | 8–10 | 36–38 | 90 |
| M | 12–14 | 40–42 | 100 |
| L | 16–18 | 44–46 | 114 |
| XL | 20–22 | 48–50 | 124 |
| 2XL | 24–26 | 52–54 | — |
| 3XL | 28 | 56 | — |

**Product-specific sizing takes precedence (Ilias, 2026-09-07).** Use a verified chart for the individual product when its sizing differs from Ondine's general chart. Keep the general chart unchanged as a fallback only for products it accurately describes. The generic conversion table above is a reference convention, not an automatic supplier conversion. Do not expand one supplier size into two UK variants. Preserve each real source size once and assign a single UK numeric size only when verified by product-specific fit evidence; do not infer fit from nearest measurements when body-versus-garment basis or ease is unknown. Keep linked `shopify.size` numeric options once the mapping is verified.

**Kiwi assignment:** Match an individual chart to the exact owned Shopify product ID, give it higher priority than the general chart, and verify the product shows only its intended chart. Do not change the general chart's measurements or unrelated products. Unconfirmed source measurements may be prepared in a clearly marked internal review chart but must not be published as verified fit guidance. Haider confirms missing measurement basis and UK equivalents before activation.

**Size chart (2026-09-03):** the storefront size guide is the **Kiwi Size Chart app block**, first block in `templates/product.json` on every PDP; its data lives inside the Kiwi app, not in a page or theme snippet, so never log "no size guide". The chart is being extended past UK 18 (Ilias, 2026-09-03); do not flag or mention sizes above 18 in reports. Preserve every verified source size in the option set; never truncate.

**Fit dimension (Petite/Regular/Tall):** map it to the linked option `shopify.size-type`, creating the missing metaobject. When the fits state different compositions or lengths, list both verbatim per fit under one product (Ilias 2026-09-03, Hobbs Thea); never average them and never split into two products.

**Sheet is a pointer, never a price source.** Read price, currency, reviews and option set from the live UK page; the master sheet has been stale on both (Sunfere £86 vs £90 live).

## Seasonal palette (multi-colour sources)

When a source carries more colourways than the season supports, the listing carries only the colours a UK buyer picks in that season, decided before the DRAFT write. Autumn/winter launch (Sept–Feb): Black, Navy Blue, Burgundy, Dark Green, Teal, Damson, Mulberry, Chocolate Brown and similar deep tones; drop White, Pink, Fuchsia, Dusty Blue, Eucalyptus, Sapphire, Vermilion, Melon, Burnt Orange. Spring/summer: the reverse. Ilias set the autumn list on 2026-09-03 (Ever-Pretty 20 → 8).

## Taxonomy value notes

Shopify's neckline list has no "High neck"; use `Mock`. Colour-pattern and size metaobjects that do not exist on the store are created in the run (`metaobjectCreate`: `label`, `color` hex, `color_taxonomy_reference` list, `pattern_taxonomy_reference`); there is no separate `shopify--pattern` definition on this store.

## Capture extras this brand needs

Beyond the engine's list: the source's stated **model height and size worn** (for fit evidence and the conditional live PDP fit note), **fabric composition**, and **garment length**. Absent is fine and becomes a FLAG; invented is never fine.

## Variants

**Colour option always present (2026-09-03).** The Google & YouTube channel takes `color` only from a variant option named Colour; single-colour products listed with a Size-only option were flagged "Missing value [color]" in Merchant Center (Gerard Darel, Sahara, both Haider imports). Every product therefore carries a `Colour` option, even with one value, ordered Colour then Size. Plain colours link to `shopify.color-pattern` (Green, Burgundy); prints use the customer-facing name as an unlinked value ("Olive Floral", "Brown Deer Print") because the linked label would read "Multicolor".

Every dimension the source offers gets listed — never drop one (Ilias 2026-08-28). Sizes follow verified product-specific mapping, never automatic expansion from the generic table. Explicit product-specific label approvals take precedence. Capture all colours; list the selected seasonal colours and retain all real size/fit combinations within them. Each colourway takes its own real-paid price, so the same garment can hold two prices on one product.

The Calloway plan is a golden fixture, not a runtime template: its 33 facts, 16 Size×Length rows and ownership values must never become constants. Each real plan derives its own FactPacket, evidence and private ownership. It supports an incoming Size selector plus zero to two additional non-colour selector dimensions in source order, preserves only the exact real combinations, treats Length as optional, and stops when the source has more than three option dimensions. A verified UK size above 18 remains in the listing and is never dropped or flagged. If Colour is encoded as a source option, it consumes one of the three available dimensions, reduces the remaining non-colour capacity accordingly and still renders first.

## PDP layout

Block order on the product page, desktop and mobile alike (Ilias 2026-08-28; fit-note placement approved 2026-09-01): title → colour → every captured non-colour option selector in source order → **price** → Add to Bag. The Size selector keeps its adjacent size guide and conditional live fit note inside the same module; every remaining selector renders in its captured order before price. Below fold: five-slot description → Fit & size → Fabric & care → Delivery → Returns and Refunds. Fit & size and Fabric & care are theme-rendered from the product metafields `custom.fit_details` and `custom.fabric_care` and the last two from `pages/shipping-policy` and `pages/returns-refund-policy`, all four as identical rows of the single `Product info accordion` block (`blocks/product-info-accordion.liquid`, theme "Ondine — policy accordion 09-03", live as MAIN since 2026-09-03; empty rows hide). The `Delivery estimate` block above Add to Bag computes the date from 1 dispatch day + 8 calendar days, not product HTML. The fit note is not an image overlay or a new PDP block. The price sits directly above the button so the number and the buying decision stay together.

**Fit-note rule:** render `Model is [height] and wears UK [size]` (height always as `175cm`, never `1.75 m` or feet) as live selectable PDP text when the reference PDP explicitly provides both the model height and size worn for that product. Convert the worn size to UK only through the source's own equivalence or the approved Ondine size mapping; never guess a conversion. The note is product fit evidence and does not claim that the generated Ondine gallery model has those measurements. Missing height, missing worn size or an unverified UK conversion → omit the note and FLAG; never show an empty placeholder or carried-over number.

**Placement evidence (checked 2026-09-01):** Nobody's Child puts the model line directly in the size-selection decision area; OMNES places it in `Size & Fit`; Karen Millen places it in `Product Details & Care`; MESHKI uses `Fit & Model Information`. Ondine adopts the strongest decision-time placement—inside the size module—while keeping the full fit section below fold for non-duplicated detail.

## Collections

Long Sleeve Dresses · Midi Dresses · Maxi Dresses · Occasion Dresses · New In. Never "All Products", never an empty collection.

## Shopify category metafields

Resolve the most specific Shopify taxonomy category independently for each product from its verified product type and facts. Never hardcode `Dresses`, reuse a prior product's category, or assume that two products expose the same attribute set. Once the category is selected, query its available standardized attributes through the existing Shopify connector and fill only those supported by verified facts. Unknown, irrelevant or category-inapplicable attributes stay blank rather than receiving a guessed fallback.

Use Shopify taxonomy/metaobject references—not free-text substitutes—and read the resolved category and display values back through the connector. When the selected category combines concepts such as colour and pattern, preserve every verified part.

For colour, inspect the garment itself as well as the retailer's swatch label. The source label remains evidence, but it does not decide the standardized value alone. A blush-labelled garment with an ecru ground and several visible print colours is `Multicolor` in Shopify while the customer-facing option may remain `Blush Print`.

## GMC fields

- Brand: `Ondine London` · Vendor: `Ondine London` · Condition: new
- Additional deterministic colour code: `Wine→WIN`.
- SKU **and MPN** both carry our own code, format `OND-<style>-<COLOUR>-<size>` for size-only products (e.g. `OND-CLSOD-COB-012`). The style code is deterministic: normalize the approved new title to ASCII word tokens and concatenate the uppercase first character of every token in order, so `Navy Embroidered Cotton Midi Day Dress → NECMDD`; any collision with an existing or planned Ondine style is a STOP, never a random suffix. Colour codes come from the explicit profile map (`Navy→NVY`, `Cobalt→COB`, `Brown→BRN`, `Blush→BLS`, `Burgundy→BUR`, `Multi→MUL`, `Cream→CRM`, `Ivory→IVR`, `Black→BLK`, `White→WHT`, `Pink→PNK`, `Green→GRN`, `Blue→BLU`, `Red→RED`, `Yellow→YLW`, `Dusty Blue→DBL`, `Eucalyptus Green→EUC`, `Dark Green→DGN`, `Purple Orchid→ORC`, `Dark Purple→DPU`, `Burnt Orange→BOR`, `Fuchsia→FUC`, `Sapphire Blue→SAP`, `Teal→TEL`, `Damson→DAM`, `Vermilion→VER`, `Brandied Melon→BML`, `Mulberry→MLB`, `Chocolate Brown→CHO`; `Navy Blue` uses `NVY`); an unmapped colour is not a stop and not a question: record a deterministic three-letter, collision-free extension in the run and continue; submit it through LEARNINGS.md for the manager to merge into the shared map (Ilias 2026-09-03: "never ask, just add it"). Print-qualified colours ("Blue Floral") use the base colour code. When the locked source has another option dimension, append its normalized option code in source-dimension order (e.g. `OND-CLSOD-COB-012-PET`) so every real variant remains unique. MPN is written as a variant metafield and verified by read-back — with no GTIN, brand + MPN is all the feed has to match on. **No invented GTIN/barcode** (Ilias 2026-08-27, `decisions/log.md`).
- Weight: use the supplier's listed weight. If absent, **FLAG**. Ilias previously allowed a 350–450 g dress estimate range for flat/free shipping (reply to Haider, 2026-08-27), but the range does not define which exact value to enter per product, so it is evidence only—not an authorized exact default. Any future profile default must name its exact value, source, and `estimate` label before use.
- Metafields follow the verified-facts rule in “Voice and copy formulas”; unknown physical facts are never fabricated for completeness.
- **Occasion is an editorial classification, not a product claim** (Ilias 2026-09-03). When the source states an occasion, map it. Otherwise choose from the fixed list `daywear · evening · occasion · wedding guest · holiday` by reading the garment's length, fabric, print and construction, and record the reasoning in the run folder. Multiple values are allowed, separated by `; `. Never leave it blank and never stop for a missing source occasion.

## Gallery template — 7 views, fixed order

Seven-view order approved by Ilias 2026-09-08; stable template IDs are not display positions.

| Slot | Shot |
|---|---|
| 01 | Front, featured — **this is the GMC feed image** |
| 01b | Front on a distinct second model |
| 02 | Back view |
| 03 | Side / movement |
| 04 | Detail close-up |
| 05 | Lifestyle — calm warm interior, product remains dominant |
| 06 | Ghost flat — closes every gallery |

**Generation:** ChatGPT’s built-in image generation with the competitor's real photos attached privately as garment references. The prompt is each slot's `generation_request.prompt_json` object sent verbatim, with `{{product.*}}` placeholders filled from the run's `product_reference_facts.json`. Footwear, hair, movement, detail focus, lifestyle setting, ghost presentation and accessories are per-product values in that file, never pack constants; `product.model` (accessories none) feeds slot 01, the GMC square and slot 06, and `product.model_styled` (discreet unbranded jewellery, Ilias 2026-09-03) feeds slots 02–05; an ankle-length dress needs a plain unbranded shoe, a floor-length one may not. The slot-01 square rendition is uploaded as a store **file**, not an additional gallery image; Shopify's featured image stays the 3:4 slot 01. Use high quality and 3:4 for every PDP slot; record actual native dimensions. Legacy Higgsfield template paths govern shot composition only. Two approved model identities: the lead model across the original model views and a distinct second model in display position 2; one consistent garment identity across the set; studio shots use the warm-neutral system and slot 05 uses a restrained warm lifestyle setting. **All seven images contain zero text, overlays or badges.** Product facts render as live PDP text.

**Slot-01 acceptance (GMC bar):** square-safe 1200×1200 or larger · product 75–90% of frame · plain light background · full garment uncropped · front-facing · zero text, overlays or badges.

When the source PDP provides both model height and worn size and the UK size is directly stated or verifiably mapped, render the conditional live fit note beside the size selector. An approved Ondine model record may also supply the line, but is not required when complete source fit evidence exists. Never place model facts inside any gallery image.

**Styling brief first (Ilias 2026-09-03):** before rendering any prompt, answer the five questions in `references/gallery-workflow.md` §7.0 (season on sale in the UK, occasion classification, UK buyer context, garment facts, competitor styling as evidence) in `styling_brief.json`, and let `scripts/apply_styling_brief.py` write footwear, accessories, lifestyle setting, movement, light and **one pose per model slot** into the facts file. **Every slide must communicate something different** (Ilias 2026-09-03): pack v4.5.0+ gives slots 01, 02, 03 and 05 their own `pose_01/02/03/05`, and the script refuses two poses whose wording overlaps by 45% or more. Never hand-patch a pose into a run prompt; fix the brief and re-run the script. The lifestyle setting follows the occasion, stays inside the warm-neutral palette, and never repeats any of the last three products (`profiles/ondine/recent-settings.json`).

**Multi-colour products (Ilias 2026-09-07):** approve the full seven-shot lead-colour gallery, then adapt those same shots into seven images per additional selected colour. Change only garment/belt colour using actual source colour evidence; preserve model, pose, crop, construction, background and lighting. Reuse existing approved fronts. Approve new colour fronts before generating their remaining views from the target front plus the matching approved lead-colour shot. Inspect all edits and show complete sets before upload. Follow `references/gallery-workflow.md` §7.3b for the per-colour manifest and approval records. Assign each colour front to that colour’s variants; keep the lead front featured.

**First-image QA:** internally validate slot 01 and its separate square, then continue without requesting first-image approval. Remaining review and upload gates follow the shared gallery workflow, including explicit user overrides. Before upload, read existing Shopify media. For new assets use `ondine-<product>-<colour>-<slot>` with stable IDs `01`, `01b`, `02`, `03`, `04`, `05`, `06`; preserve existing approved filenames and map them explicitly. Read back before any retry. The finished product must match the approved manifest: seven assets per colour in order, with no duplicates.

Live reference gallery: `projects/engine-3/stores/ondine-london/store/live-gallery-order.html`.

## Store rules (AB gate)

**Standards hierarchy:** the AB course is the compliance floor—product images contain no promotional text or overlays [AB 7.2 @ 02:50–03:16], and the listing stays DRAFT until a separate activation audit [AB FAQ-13.13]. The seven-slot gallery, fit-note placement, bundled image templates, anti-copy checks and evidence/read-back gates are Ondine's stronger operating layer **[NOT IN AB COURSE]**; they extend the floor without weakening it.

Free-UK-shipping banner · EXTRA- stacking codes 10/15/20/25% at 2/3/4/5 items · 30-day money-back · seasonal sales ≤50%, no timers, no fake stock counts · **no on-site reviews** · policy names verbatim across site, FAQ and GMC.

**Policy source of truth is the LIVE store pages**, `ondinelondon.co.uk/pages/shipping-policy` and `/pages/returns-refund-policy` — read them at run time. Verified live 2026-08-28: **30 days to return**, **5 to 8 working days after dispatch**, free UK delivery.

The policy snapshot profile is `ondine-live-policy-v1`. A real committable plan requires exact requested and final URLs on `https://ondinelondon.co.uk/pages/shipping-policy` and `https://ondinelondon.co.uk/pages/returns-refund-policy`, plus capture time, exact heading, content and content SHA-256 for each block and a canonical snapshot SHA-256. `SYNTHETIC_TEST_ONLY` is valid only under an explicit validator test mode and is rejected by the normal CLI.

⚠ The vault drafts in `projects/engine-3/stores/ondine-london/store/copy/` are STALE and still carry unresolved `[CONFIRM WITH HAIDER]` markers — returns-refund-policy.md says 28 days, shipping-policy.md says 2 to 4 working days. Never generate PDP copy from them. Promising a shorter refund window than the live policy page is a self-inflicted inconsistency on a Merchant Center account that has already been suspended once.

Block headings copy the live page titles exactly: **Delivery** and **Returns and Refunds**.

## Seven-image gallery update — approved 2026-09-08

Display order is **1 front (lead model), 2 front (second model), 3 back, 4 movement, 5 detail, 6 lifestyle, 7 garment-only**. Stable template IDs are `01`, `01b`, `02`, `03`, `04`, `05`, `06`; IDs are not display positions. This update overrides older six-view examples and any single-model continuity wording. Use `01b-second-model.json` for the additional view. Record `product.second_model` and `product.pose_second_model` with reasons in the styling brief; keep these separate from the lead model. Choose the hero avatar during product analysis and record its product-specific rationale under §7.0 of the gallery workflow. The second model must be a different adult person who adds variety. Neither slot has a fixed ethnicity; a previous product's model order is not a default for the next listing.

Generate and internally validate the lead portrait, its separate square and the second-model preview without requesting individual user approval, then continue to the remaining views. Preserve the lead model in back, movement and lifestyle shots. Use the approved lead as garment/style reference for the second model, explicitly changing identity; all other views retain their original reference rules. Match garment, lighting and background across the two front views. For additional colours, preserve each shot's corresponding approved model identity, including the second-model front. The GMC square is separate and the lead remains featured and assigned to variants. Show all seven images for gallery approval and require explicit upload approval.

New colour manifests use `schema_version: 2`, the complete canonical shot order is `front, second-model, back, side-movement, detail, lifestyle, ghost-flat`, numbered 1–7. Legacy version-1 six-view manifests remain valid historical records; do not silently add media to existing approved products.
