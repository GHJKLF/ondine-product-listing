---
name: product-listing
description: Turn a competitor product URL into an original, complete Shopify DRAFT for an Engine 3 store. Use when asked to list, import, re-list, improve, or adapt a product for Ondine London or another supported store profile.
---

# Product Listing

For starting a task, tool fallbacks and updates, read [operator readiness](references/operator-readiness.md). If the app does not register repository skills automatically, read this file and its required references directly and report it as **loaded for this task**, not installed. Discovery is not a prerequisite to following readable instructions. A first supervised listing tests readiness; a previous successful listing is not required to start that test.

Turn one competitor product URL into a better, original Ondine listing and save it through the **existing Shopify connector as DRAFT**.

For an explicitly authorized gallery-only update to an existing ACTIVE product, use the separately installed product-image-set skill if available. It is outside this listing package; if absent, report that separate capability as unavailable. Do not run this listing workflow or its DRAFT compiler against that product. New listings and owned DRAFT updates retain every safeguard below.

## Fixed boundary

- **One reference URL → one owned Shopify DRAFT.** The skill may create a new DRAFT or resume exactly one matching managed DRAFT; it must never duplicate, seize, downgrade, delete or edit an unrelated product.
- **Competitor content is evidence only.** Facts may inform the Ondine listing and competitor images may be attached privately as garment references, but competitor wording, identifiers, pixels, models, styling, watermarks and media must never enter Shopify.
- **Shopify writes use only the existing connector.** This includes product fields, variants, category metafields and approved original media. Do not build or request another Shopify connection, token system, app, browser-writing path or transport.
- **DRAFT review gate is permanent.** Every Shopify write must create or preserve `status=DRAFT` and be followed by read-back. Select the store-profile default sales channels while the product is still DRAFT. For Ondine these are Online Store and Google & YouTube. Haider reviews and changes the product to ACTIVE; the listing skill never activates it. Channel assignment is authorized preparation, not authorization to activate, change GMC/Ads settings or delete products. Never apply this draft-only assignment step to an already ACTIVE product without explicit authorization for that live change.
- **Inventory is out of scope, but tracking must be off.** Capture source availability for audit only; never set stock quantities or inventory policy. Every variant is created with `inventoryItem.tracked=false` (the store convention on all live Ondine products; a tracked variant with quantity 0 shows Sold out, found 2026-09-03 on product 10609107599626). Verify `tracked=false` on read-back. A DRAFT may not be available on the storefront; Haider verifies sale availability after activation.
- **Ondine tax is always off.** Every target variant must set and preserve `taxable=false`; never inherit a competitor tax setting or rely on Shopify defaults.
- **Step 7 generates only original Ondine media.** Use ChatGPT’s built-in image generation with the seven approved JSON shot templates and 3:4 PDP aspect ratio. Record actual output dimensions; do not claim unsupported resolution tiers. Legacy `higgsfield/` template paths specify composition, not the generation provider. The fixed order is front, second-model front, back, side/movement, detail, lifestyle, ghost flat; slot 01 also has a separate 1:1 GMC rendition.
- **Slot 01 requires internal QA, not user approval.** Generate and validate the first portrait and its separate GMC square, then continue without asking Ilias to approve either. Ilias retains the second-model preview, complete-gallery and Shopify-upload gates. For multiple colours, approve the full lead-colour gallery before adapting it, then review the complete additional-colour galleries before upload. Reference-pack assembly and template mapping are internal team QA and must not be pushed to Ilias for document review. Approval of one visual gate authorizes only that gate's stated next action.

## Store profile

Load the requested store profile before doing any work:

- Ondine London: `profiles/ondine.md`

Unknown store or missing profile → stop and name the missing profile.

For Ondine, the connected store must identify as:

- MyShopify domain: `zfrbm1-y6.myshopify.com`
- Primary domain: `ondinelondon.co.uk`
- Shop name: `Ondine London`

Any mismatch → stop before writing.

## Workflow

For a master-sheet assignment or status update, follow the Google connection and
exact-row handoff instructions in [operator readiness](references/operator-readiness.md).
Use the operator's own connected Google account; sheet access is not bundled with
the skill. Resolve the assigned product before listing and update its row only
after the requested listing scope is verified. Report a blocked sheet step
separately from the Shopify draft result.

### 1. Read the reference product

Use **Scrapling first** for read-only source collection, following [source-reading guidance](references/source-reading.md). For Shopify sources, run `scripts/fetch_source.py PRODUCT_URL --output RUN_FOLDER/source` with the installed Scrapling Python; it captures HTML, public product data and cart currency in one session. Use Scrapling rendering when required content is missing from the initial HTML. If unavailable, use the helper's explicit `--backend stdlib` or available browser/page-reading tools. Firecrawl is no longer the default and is not required. Preserve UK English/market evidence and record the method that actually ran; successful fetching alone does not verify product facts.

The helper saves server HTML, not browser-rendered output, and **does not verify the product or its market**. Review the visible product content, source market signals, price, real variants, sizing and gallery against structured data. If the HTML lacks rendered content, a selector changes the market, or evidence conflicts, inspect the actual rendered page with an available browser. If that cannot be done, stop at the specific unresolved fact; do not certify a successful fetch as a successful listing. Preserve both requested and final URLs and the raw evidence in the run folder.

Also fetch the store's `<product-url>.json` (or `.js`) and locale-specific `/cart.js` as same-session structured commerce data. For non-Shopify sources, use page JSON-LD plus the visible per-option markup. **Market state first:** a GB language request alone does not prove UK currency or a complete option set. Read the storefront's market state and, when needed, select the UK market through its localization control before trusting price or options. Save output only in the run evidence folder; never send source output to Shopify.

Extraction output is **not authoritative by itself** for market, price, currency, variants or product-gallery identity. A locale redirect is a conflict, not permission to use the redirected market values.

Capture:

- source URL, title, brand and product type
- current customer-paid price, struck price and currency
- every option dimension, ordered value and real variant combination
- composition, construction, care, fit, measurements and model facts
- all customer-facing product sections
- source gallery order for internal reference only

Before composition, cross-check the source page content and the same-session structured commerce data; verify the browser-rendered page whenever the HTML is incomplete or market state is uncertain:

- final URL, country, language, price and currency must match the requested market
- option dimensions, values and real combinations must match structured product data; never generate Cartesian variants
- keep only the actual product gallery, in verified order; exclude recommendations, navigation, service icons, size-guide graphics and embedded app assets
- resolve duplicate or conflicting sections explicitly rather than counting repeated scraper blocks twice

Missing information stays missing. Conflicting or ambiguous price, currency, option, media or physical facts → stop and explain the conflict. Preserve every source size value in the Ondine option set, including source sizes that are currently unavailable; source stock status is not copied.

Source availability is audit evidence only. Do not copy it into Ondine inventory or availability.

### 1b. Register this product's reviewed facts

Follow [product evidence registration](references/product-evidence-registration.md) for a new product. The runtime now accepts a separately hash-pinned run registry, so no edit to a historical lock or test fixture is needed. The assistant checks this product's facts against its captured evidence and records an `ASSISTANT_SELF_CHECK`, then registers and validates them. A separate reviewer, reviewer plugin or human fact-approval step is not required for a normal listing. Never describe this check as independent approval, reuse Calloway evidence, or use test mode. Registration is internal work, not an extra input from the operator. Resolve actual conflicting or missing facts before the affected write; reviewer availability must never block the listing.

### 2. Create the Ondine version

For runs that include original images, choose the hero avatar during product analysis. Select the adult model and styling that best present this garment's silhouette, colour, print and occasion; confirm image quality during generation QA. Make a fresh choice for each product, with no fixed ethnicity order or automatic carry-over from the previous listing. Record the choice and reason in the styling brief using §7.0 of `references/gallery-workflow.md`; select a distinct second model to add variety. This selection is the agent's decision and needs no separate user approval.

Use the loaded profile plus:

- `references/copy-templates.md`
- `references/compliance-checklist.md`

Create original customer-facing content:

- one shared Shopify/GMC title and a handle built from it; use researched buyer language plus verified attributes from the active profile, while keeping size at variant level
- original five-part description
- `custom.fit_details` and `custom.fabric_care` rich-text metafields (theme block `Product info accordion` renders them as the PDP rows "Fit & size" and "Fabric & care"; format in `references/copy-templates.md`); these replace any Details / Size & Fit / care list inside the description
- the live fit note `Model is [height] and wears UK [size]` when the source provides both model height and worn size; convert the worn size to UK only through a verified size mapping
- **no** Delivery or Returns and Refunds text in the description: since 2026-09-03 the Ondine theme renders both from the live policy pages through a `Policy accordion` block on the product template (custom block `blocks/policy-page.liquid`), so the copy lives once on the pages and never in product HTML
- exact mapped options and real combinations, with a `Colour` option always first even for a single colour; the Size option is created linked to `shopify.size` with single UK numeric values only when verified by product-specific evidence; never expand a source size into two variants. Explicit product-specific size-label approvals override the default numeric presentation
- Ondine price using the profile rule
- Ondine vendor, Shopify taxonomy category, applicable Shopify category metafields, collections, tags, SEO and custom metafields
- own SKU and MPN per variant
- `taxable=false` on every variant
- no invented barcode or GTIN

Before any Shopify write, perform a hard five-slot copy check against the loaded
store profile and `references/copy-templates.md`. Every slot must do its assigned
job, not merely exist:

1. opening starts with the silhouette and then states a verified fabric or
   coverage benefit;
2. occasion clearly says who it is for, when to wear it, or the verified/editorial
   occasion;
3. detail states one verified product fact in prose;
4. styling gives exactly one clearly editorial suggestion;
5. close is a quiet brand line with no CTA, urgency, guarantee, or new claim.

Also reject repetition between slots, vague filler that adds no customer meaning,
and any sentence whose factual wording is not supported by the reviewed facts.
**This is pass/fail: one weak or incomplete slot stops the Shopify write until the
copy is corrected and checked again.** Originality PASS does not override a failed
slot check.

Competitor title, prose, brand, handle, SKU, barcode, policies, source tags and images must not enter customer-facing fields.

The Shopify taxonomy category is resolved separately for every product from its verified product type and facts. Never reuse or hardcode the category or attribute set from a previous listing. After selecting the most specific supported category, read that category's available standardized attributes through the Shopify connector and populate only the applicable ones.

Resolve standardized colour from both the source label and the actual garment imagery. A retailer label such as `Blush` must not force `Pink` when the garment is visibly multicoloured. Use the closest supported Shopify taxonomy value for the complete product appearance, keep finer customer-facing colour wording separate, and never guess from the label alone.

For Ondine pricing, use the verified current customer-paid source price as the input and apply the profile's strict-below `.95` rule. The competitor's struck price remains evidence only and is not copied as compare-at pricing.

### 3. Preflight Shopify through the existing connector

Use the available Shopify connector—not browser automation and not a new API client. The connector's MCP server may be named by an opaque id; find its tools with ToolSearch for `get-shop-info`, `graphql_query` and `graphql_mutation`, and if none exist the user must attach it. Then:

1. Read and verify the connected shop identity.
2. Search the private source-key and canonical-source-URL metafields.
3. Search the proposed Ondine title and handle.
4. Search for a manually imported copy of the same garment: query the source style code, the source product title words and the source description's first sentence across all products. Haider's manual drafts carry no ownership metafields, so metafield search alone misses them (found this way on 2026-09-02: product 10603416158474).

If a dedicated search returns unexpectedly empty results, verify the query through the same connector’s GraphQL tools and inspect a paginated product catalogue before concluding no duplicate exists. An unsupported metafield search or empty tool response is not proof of absence.

No verified match → create one new DRAFT.

Exactly one matching owned DRAFT → update that same DRAFT.

Multiple matches, an unmanaged match, or any ACTIVE/ARCHIVED match → stop. Never create a duplicate and never downgrade or seize an existing product.

If the connector is unavailable in the current session, stop with `SHOPIFY_CONNECTOR_UNAVAILABLE`. Do not build another connection.

### 4. Write one DRAFT

When the user's request explicitly says to list, import, create, or update the product, that authorizes one DRAFT write for that exact URL. Otherwise show the proposed listing and ask before writing.

The first Shopify write must include:

- `status=DRAFT`
- original Ondine content and SEO
- exact option/variant structure, always with a `Colour` option first (single value allowed; the Google channel reads colour only from that option, profile "Variants")
- Ondine SKU/MPN values
- `taxable=false` on every variant
- the product-specific Shopify taxonomy category and every applicable attribute exposed by that category, supported by verified facts and written with Shopify's standardized values; never reuse a previous product's category or attribute set, and leave unknown or irrelevant attributes blank
- private source-key, source-URL and ownership metafields; never expose these values as Shopify tags
- `custom.fit_details` and `custom.fabric_care` rich-text metafields (format in `references/copy-templates.md`); the description carries prose only
- no media
- no stock quantities, inventory policy or availability fields; explicitly set `inventoryItem.tracked=false`
- keep `status=DRAFT`; then select the store-profile default sales channels through the existing connector before completing the draft

Connector mechanics that cost failed writes on 2026-09-03, use them as written:
- `productCreate` with linked options (`shopify.size`, `shopify.color-pattern`, `shopify.size-type`) must pass each option value as `{name, linkedMetafieldValue: <metaobject gid>}` **and** set the matching product list metafield with exactly those metaobject gids in the same call, or it fails with "metafield has no values".
- Request `options { id optionValues { id name } }` back from `productCreate`; `productVariantsBulkCreate` on linked options accepts only `optionValues: [{optionName, id}]` (never `name`, never `linkedMetafieldValue`), with `strategy: REMOVE_STANDALONE_VARIANT`.
- Category attributes: `TaxonomyAttribute` has no `name`; query `... on TaxonomyChoiceListAttribute { id name values { nodes { id name } } }`.

After each connector write, immediately read the product again. If the write outcome is unclear, read before retrying; never blind-create a second product.

Media upload is also idempotent. Before uploading, read the existing media IDs, filenames and order. Upload each approved file once, attach it once, then read back before any retry. If a prior attempt actually succeeded, resume from the existing media instead of uploading again. If a duplicate is created, record its exact later media ID and hold completion for authorized cleanup; do not delete retained media as an automatic retry step.

### 4b. Select default sales channels while keeping DRAFT

Resolve the exact Online Store and Google & YouTube publication IDs from the connected Ondine store; never reuse IDs from another store or guess from a legacy channel name. Schema-inspect and validate `publishablePublish` through the existing connector, then assign only these two defaults to the same owned DRAFT. Do not change its status. Read back DRAFT status and verify the pending channel selections using draft-aware publication data or the admin publishing selector; currently-published fields may be empty for a draft. Record the channel IDs and verification in the run. A missing channel or insufficient connector permissions is a concrete setup gap to report, not a reason to silently finish with channels off.

Haider's later activation should make the product available to those selected channels. Google processing and eligibility still apply; channel selection does not guarantee instant feed approval. Do not enable Point of Sale, Shop, legacy headless or other channels by default.

### 5. Verify the data-ready DRAFT

The run passes only when the connector read-back proves:

- the expected Ondine store
- exactly one product ID
- `status=DRAFT`
- product remains DRAFT and the store-profile default sales channels are selected for availability after Haider activates it; an empty currently-published connection alone is not proof that draft channel assignments are missing
- title, handle, description, options, variants, prices, tags, SEO, collections, identifiers, custom metafields (including `fit_details` and `fabric_care`) and applicable Shopify category metafields match the intended listing
- the description contains no bullet lists, Details / Size & Fit / care sections, size ranges, model lines or Delivery / Returns text
- all five description slots still pass the hard slot-by-slot copy check after read-back; a structurally complete but semantically weak description is a failure
- every variant has `taxable=false`
- no stock quantities, inventory policy, availability fields or competitor media were written; every variant has `inventoryItem.tracked=false`. Draft storefront availability is not an activation test

Return the Shopify product ID/admin URL, a short summary of what was created, and any missing optional facts. The data-ready phase is now complete. Continue to Step 7 only through the approvals below. Publication remains separate and human-only.

## Step 7 — Original Ondine gallery

For a complete listing run, read and follow [references/gallery-workflow.md](references/gallery-workflow.md) after the data-ready DRAFT passes. It starts with the styling brief (§7.0: season on sale, occasion, UK buyer context, garment facts, competitor styling as evidence → footwear, accessories, setting, movement, light), then internal reference/template QA, followed by internal slot 01 QA and the remaining Ilias gates: second-model preview, complete gallery, and connector-only Shopify upload. Do not begin Step 7 when only a data-ready DRAFT was requested.

## Immediate stop conditions

Stop before writing if any of these is true:

- Shopify connector unavailable or wrong store connected
- missing or ambiguous current price/currency
- extraction final URL/market differs from the requested market and exact-market verification is unavailable
- incomplete option dimensions, values or real combinations
- a size cannot be mapped without invention, or the source has more than three option dimensions
- invented physical fact, weight, barcode or GTIN
- duplicate, unmanaged, ACTIVE or ARCHIVED match
- any request or payload includes stock quantities, inventory policy, availability fields, competitor media, product activation, non-profile channel assignments, or changes to GMC/Ads settings
- any variant is missing `taxable=false` or attempts to set `taxable=true`
- a Step 7 approval is missing, a generated image fails its slot JSON, or competitor media appears in the upload set
- DRAFT status or final read-back cannot be proven

## Learnings log (mandatory)

Every run is a learning run. Whenever the skill is unclear, wrong, missing a case, needs a retry, or needs Ilias to step in, append one line to `<operator-state>/LEARNINGS.md` under `## Open` (create the heading if absent; resolve the external state folder using operator readiness), at the moment it happens:

`- YYYY-MM-DD · <product> · <what the skill got wrong, missed or left unclear> → <fix>`

Append only; never rewrite other entries; never edit the skill from a run. This file is skill-specific and is not the OS-level learnings file. The manager merges Open entries into the skill and moves them to `## Merged` with the pack version. A run is not complete until its entries are logged.

## Done

Learnings logged. One reference URL produced one original Ondine Shopify DRAFT; the existing Shopify connector read it back as DRAFT with the store-profile default sales channels selected; and, when the complete listing workflow was requested, Step 7 produced and verified the approved seven-image-per-colour Ondine galleries without publishing the product.

## Seven-image gallery update — approved 2026-09-08

Display order is **1 front (lead model), 2 front (second model), 3 back, 4 movement, 5 detail, 6 lifestyle, 7 garment-only**. Stable template IDs are `01`, `01b`, `02`, `03`, `04`, `05`, `06`; IDs are not display positions. This update overrides older six-view examples and any single-model continuity wording. Use `01b-second-model.json` for the additional view. Record `product.second_model` and `product.pose_second_model` with reasons in the styling brief; keep these separate from the lead model. Choose the hero avatar during product analysis and record its product-specific rationale under §7.0 of the gallery workflow. The second model must be a different adult person who adds variety. Neither slot has a fixed ethnicity; a previous product's model order is not a default for the next listing.

Generate and internally validate the lead portrait and its separate square without requesting user approval, then obtain approval of the second-model preview before producing remaining views. Preserve the lead model in back, movement and lifestyle shots. Use the approved lead as garment/style reference for the second model, explicitly changing identity; all other views retain their original reference rules. Match garment, lighting and background across the two front views. For additional colours, preserve each shot's corresponding approved model identity, including the second-model front. The GMC square is separate and the lead remains featured and assigned to variants. Show all seven images for gallery approval and require explicit upload approval.

New colour manifests use `schema_version: 2`, the complete canonical shot order is `front, second-model, back, side-movement, detail, lifestyle, ghost-flat`, numbered 1–7. Legacy version-1 six-view manifests remain valid historical records; do not silently add media to existing approved products.
