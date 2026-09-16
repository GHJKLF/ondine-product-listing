# Product-listing check

Fill this once for every product. A failed product check stops the next Shopify
write. A master-sheet failure blocks only the sheet handoff and must be reported
separately; retain any verified Shopify draft for retry.

## Source

- [ ] PASS / FAIL — Available read-only extractor used (Firecrawl, browser or public-source helper); actual method, requested URL, final URL and capture time recorded
- [ ] PASS / FAIL — UK market/locale and currency cross-checked against source page and same-session commerce data; rendered-page verification completed when HTML is incomplete or market state is uncertain; redirects or mismatches resolved
- [ ] PASS / FAIL — exact reference URL and capture time recorded
- [ ] PASS / FAIL — current price, struck price and currency verified
- [ ] PASS / FAIL — every option dimension, ordered value and real combination captured
- [ ] PASS / FLAG — physical facts, care, fit, measurements and model facts captured or explicitly missing
- [ ] PASS / FAIL — product-only gallery identity/order verified; recommendation, navigation, service, size-guide and app assets excluded
- [ ] PASS / FAIL — repeated extraction blocks deduplicated without losing distinct source sections or facts
- [ ] PASS / FAIL — conflicts resolved without guessing

## Original Ondine listing

- [ ] PASS / FAIL — new title and handle; competitor name and wording absent
- [ ] PASS / FAIL — five-part description uses only captured facts
- [ ] PASS / FAIL — Details & Care and Size & Fit use only supported facts
- [ ] PASS / FAIL — Delivery and Returns and Refunds use the current live Ondine policy pages
- [ ] PASS / FAIL — no shared competitor sentence or copied bullet order
- [ ] PASS / FAIL — Ondine pricing rule applied to the verified current source price
- [ ] PASS / FAIL — every option and real variant combination is present
- [ ] PASS / FAIL — own SKU and MPN; no invented barcode or GTIN
- [ ] PASS / FLAG — supplier weight captured; otherwise left unset and flagged
- [ ] PASS / FAIL — category, applicable real collection, descriptive tags and SEO verified; supported Ondine metafields populated, unknown facts omitted and flagged; unresolved required fields prevent activation readiness
- [ ] PASS / FAIL — every applicable standardized Shopify category metafield is populated and connector read-back resolves the intended display values; irrelevant fields remain blank
- [ ] PASS / FAIL — standardized colour reflects the actual garment imagery as well as the retailer label; multicolour products are not reduced to one label-derived colour

## Shopify connector

- [ ] PASS / FAIL — existing Shopify connector is available
- [ ] PASS / FAIL — connected shop matches Ondine London
- [ ] PASS / FAIL — private source-key/source-URL metafields, proposed title and handle duplicate checks return zero or one owned DRAFT
- [ ] PASS / FAIL — Shopify tags contain descriptive merchandising terms only; no source URL, competitor identity, ownership marker or `managed-by` value
- [ ] PASS / FAIL — first write explicitly uses `status=DRAFT`
- [ ] PASS / FAIL — no media, stock quantities, inventory policy or availability fields written during product-data creation; tracking explicitly disabled and tax off on every variant; only profile-default channel assignments allowed afterward while preserving DRAFT
- [ ] PASS / FAIL — immediate connector read-back returns the same product ID and `status=DRAFT`
- [ ] PASS / FAIL — product remains DRAFT; Online Store and Google & YouTube are selected for Haider activation, verified with draft-aware channel evidence
- [ ] PASS / FAIL — final fields match the intended listing
- [ ] PASS / FAIL — media was read before upload and after every attempt; exactly seven internally accepted PDP assets per selected colour remain in manifest order, unless an explicit narrower scope was approved; the separate GMC square is excluded; no duplicate media IDs or filenames

## Handoff

- [ ] PASS / FAIL / NOT REQUESTED — Master-sheet task uses the operator's own Google connection; exact sheet, tab, row and columns are verified through live reads
- [ ] PASS / FAIL / NOT REQUESTED — After the requested listing scope passes, only the matched row's existing Draft status and draft-link cells are updated and read back; an Active row is never downgraded
- [ ] PASS / FAIL / NOT REQUESTED — A failed sheet update is reported separately with the preserved Shopify draft link; no duplicate product or row is created on retry

- [ ] PASS / FAIL — Shopify product ID and admin URL recorded
- [ ] PASS / FLAG — missing optional facts listed for Ilias
- [ ] PASS — images and publication remain separate work

- [ ] Description is prose only: no bullet lists, no Details / Size & Fit / Delivery / Returns sections, no size ranges or model lines (those live in `custom.fit_details` / `custom.fabric_care` and the theme rows)
- [ ] Populate `fit_details` and `fabric_care` only with verified source facts; omit empty sections and flag missing optional facts. Do not invent content to satisfy field completeness.
