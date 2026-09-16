# Ondine composition contract — Phase 2

Status: **current verification rule updated 2026-09-15**. Normal listings use assistant source verification with no separate reviewer. Historical examples below remain test references, not runtime defaults or authority for live actions. Current profile and gallery workflow govern the five prose paragraphs, seven images, internal QA and direct DRAFT uploads; human review happens before activation.

## 1. Boundary and authority

The composer turns a `FactPacket` whose complete ordered binding projection is supplied by a verified, product-specific manifest into one original Ondine `ListingPlan`. It may also bind a current `StorePolicySnapshot` and, when one later exists, an approved target-model record. It never reads customer-facing wording, identifiers, availability or media from a competitor into the target.

Authority order:

1. A verified, product-specific FactPacket projection manifest establishes the complete allowed atomic binding set, including physical-product truth, exact option structure, eligibility and the verified customer-paid price.
2. The Ondine profile supplies brand rules and named transforms.
3. A current `StorePolicySnapshot` supplies Delivery and Returns and Refunds content.
4. Complete source fit evidence may supply the conditional live model line; an approved Ondine target-model record is an alternative source.
5. The `ListingPlan` records original customer copy, target fields, evidence links, omissions and stops.

AB is the floor: change imported competitor title and description before any later activation [AB 7.2 @ 03:59–04:48 → `02-Google-Ads-Masterclass/7.2-Compliant-Product-Import.md`], keep the product in DRAFT while edits remain [AB FAQ-13.13 @ 00:24–01:41 → `02-Google-Ads-Masterclass/FAQ-13.13-Setup-Metafields-Product-Imports.md`], use clear high-quality imagery without promotional text or watermarks [AB 7.2 @ 01:34–03:16 → `02-Google-Ads-Masterclass/7.2-Compliant-Product-Import.md`], and keep titles descriptive without keyword stuffing [AB 7.3 @ 05:58–06:13 → `02-Google-Ads-Masterclass/7.3-Optimized-Product-Titles.md`]. The five-slot copy system, fixed Ondine PDP hierarchy, evidence lanes, originality guard, conditional live fit note and six-slot original-media gate are the stronger Ondine layer **[NOT IN AB COURSE]**.

## 2. Required input envelope

Every input fact used by the plan must expose:

- `fact_id`, atomic value and unit where relevant;
- evidence locator, capture time, market, locale and currency;
- product/variant/colour scope;
- conflict state;
- `publishable_as_claim`;
- `usable_as_policy_input`;
- `allowed_transform_ids`.

Phase 1 `SourceCapture` remains immutable and provider-neutral. The Phase 2 `FactPacket` is a deterministic projection: it pins the SourceCapture output hash, SourceCapture determinism hash and final Ondine profile hash; retains the locked source fact ID or path, exact value and evidence; and adds only the brand-authorized claim/transform eligibility defined here. It must not rewrite SourceCapture. Price, options and section blocks that have no authorized Phase 2 projection cannot be used merely because their raw values exist; a missing projection is a stop.

Normal validation requires a verified, product-specific FactPacket projection manifest. The ListingPlan must carry `evidence.fact_packet_projection_manifest_id` and `evidence.fact_packet_projection_manifest_sha256`, plus identical `fact_packet_projection.manifest_id` and `fact_packet_projection.manifest_sha256` values. The manifest ID resolves through the separately hash-pinned run registry (or the historical registry for fixtures); a plan-supplied filesystem path or URL is never accepted. The validator recomputes the artifact SHA-256 and requires exact equality to both pins, then requires the manifest's product and SourceCapture binding to equal both ListingPlan SourceCapture pins.

Normal listings record `ASSISTANT_SELF_CHECK`: the same assistant prepares and verifies the source facts, records per-fact evidence and notes, and registers a verification record pinned to the final manifest. No separate reviewer or routine human fact approval is required. Follow references/product-evidence-registration.md for the normal command and record fields. Missing checks, changed evidence or a mismatched hash still stop the write. Genuine independent reviews remain supported as an optional separate method; that method must still have distinct identities and actual approval. Never call a self-check independent review.

Binding equality is exact and ordered: `RFC8785(fact_packet_projection.bindings) == RFC8785(manifest.bindings)`. Counts, order, unique `fact_packet_fact_id` values, JSON types and every field must match one to one, including optional unit/currency, source fact/path, locator, capture time, market, locale, scope, conflict state, `publishable_as_claim`, `usable_as_policy_input` and ordered `allowed_transform_ids`. Subsets, supersets, normalization, coercion, regeneration from raw sections and unverified fallback are forbidden. Normal CLI validation has no bypass; validator tests use explicitly synthetic evidence or historical fixtures, never production approvals.

The boundary is closed: every ListingPlan input first exists as an atomic `fp.*` binding carrying exact value, source fact/path, locator, capture time, market, locale, scope, conflict state, claim eligibility, policy-input eligibility and allowed transform IDs. ListingPlan and derived facts may reference only `fp.*`, `df.*`, approved profile facts, a current policy record, an approved target-model record or the Store Contract. Direct `sections.*`, `structured_product.*`, `source_capture.*` or other raw-source references are forbidden outside the FactPacket bindings themselves.

The locked Calloway example pins `source_capture_sha256=279d3d4170cf62c02a140bd190aefe1fc1cded754041ad92ca0c2f88c802b660`, `source_capture_determinism_sha256=b39a7394ac9f66f2189b82acb121da8f2c878313a9bf63f1ac5a05723a3f7535` and `ondine_profile_sha256=3563e59bc0798b6ea92d568df8ae74382c07781f25a61b2007198aebafe905c9`. Any mismatch is a stop.

For the Calloway golden fixture only, the product-specific projection manifest is ID `nobodys-child-calloway-fact-packet-projection-oracle-v2`, path `.claude/skills/product-listing/tests/oracles/fact-packets/nobodys-child-calloway.fact-packet-projection-v2.expected.json`, SHA-256 `c588b0757be6acae56ff2e883432c281e1716b506a3050a905c526278a3e23ca`. Its distinct Atlas approval is the detached lock at `.claude/skills/product-listing/tests/oracles/fact-packets/nobodys-child-calloway.fact-packet-projection-v2.atlas-lock.json`, SHA-256 `cc4a4eb0f8e302d520b0e4b28679ff3351d3f791646de75befeb4a61fb0bf761`. The manifest and detached lock are one validation dependency pair; neither path, ID nor hash is a runtime default for another product.

Source facts and target wording are separate lanes:

| Exact source fact lane | Newly authored target lane |
|---|---|
| Current customer-paid price, option names/values, real variant combinations, colour, composition, care, construction, measurements, country of manufacture and weight remain exact. | Title, five description slots, benefit phrasing, styling suggestion, SEO copy, tags, filenames and alt text are authored for Ondine. |
| A source price is never customer copy; it is input only to the allowed price transform. | The derived Ondine price is target data with both input and transform provenance. |
| Source model height and worn size are eligible product fit evidence when both are explicit and any UK conversion is verified. They never identify or describe the generated Ondine gallery model. | The live model line may be generated from complete source fit evidence or from an approved target-model record; otherwise it is omitted and flagged. |
| Source title, prose, SEO, policies, identifiers, availability, programmes and media remain evidence only. | None of those expressions or assets may enter title, handle, description, SEO, target variants or `shopify_target_state`. |

Missing values stay absent and become flags. A conflict blocks only the affected claim or transform unless it prevents a complete required target.

### Runtime genericity gate

The adjacent Calloway document is a golden fixture only. Its pinned manifest ID/SHA, 33 FactPacket bindings, 16 Size×Length combinations and private ownership values are assertions for that fixture, never composer constants, defaults or target templates. Every real run derives its own FactPacket, evidence pins, canonical source identity, private source key and variant matrix and supplies its own author-attested product manifest with a distinct reviewer lock. A different SourceCapture must reject the Calloway manifest before any claim validation.

The generic Ondine composer accepts an incoming Size dimension plus zero, one or two additional non-colour selector dimensions in captured source order; Length is optional and has no reserved position. It preserves the exact real combination set and never manufactures a Cartesian product. More than three total source option dimensions is a stop. Colour renders first; when Colour is represented as a source option it consumes one of those three dimensions and reduces the remaining non-colour capacity accordingly. Every verified source size remains intact; an explicitly stated single UK numeric source label may retain that numeric target identity with no upper-limit or per-product-chart gate. The shared BODY guide covers UK 4–28 for customer guidance only and never creates a source-label conversion. Historical explicit product-specific label approvals remain bound to their original source and provenance.

## 3. Named rules and transforms

These IDs are the complete Phase 2 vocabulary Dex should encode later:

| ID | Rule |
|---|---|
| `ondine_original_title_v1` | Author one shared Shopify/GMC title using current buyer-search language and eligible `fp.*` facts. Prefer gender, colour and the strongest verified high-intent attributes with the required product type, arranged naturally rather than as a rigid keyword stack. Multi-size values stay in variant data. Target ≤70 characters; hard stop >150. Do not reuse source product names, brands or title syntax. |
| `ondine_original_five_slot_copy_v1` | Author the five slots in §4. Every product claim carries fact refs. Styling language is a recommendation, not a physical claim. |
| `ondine_price_nearest_95_below_v1` | From a verified current customer-paid GBP amount, output the greatest two-decimal price ending `.95` that is **strictly less** than the input. Exact boundaries: `59.00→58.95`, `59.40→58.95`, `59.95→58.95`, `59.96→59.95`; therefore `55.00→54.95`. The result is the regular target price; source compare-at and promotion are not copied. |
| `ondine_uk_numeric_size_identity_v1` | Preserve an explicitly stated single UK numeric source label as the same numeric target size after market/size-system proof. Letter-only, other-market and ambiguous labels remain unresolved: the shared BODY guide does not convert them. A historical explicit product-specific label exception remains valid only with its original approval trace and source provenance. |
| `ondine_option_identity_v1` | Preserve every non-colour, non-size option name/value exactly after customer-facing capitalization; retain source position for selector placement. |
| `ondine_variant_matrix_preserve_real_v1` | Preserve source dimension order, values and real combinations. Never invent a Cartesian product and never remove a combination based on source stock state. |
| `ondine_style_code_v1` | Normalize the approved new title into ASCII word tokens and concatenate the uppercase first character of every token in order. `Navy Embroidered Cotton Midi Day Dress → NECMDD`. Collision against any existing or planned Ondine style is a STOP; never append a random suffix. |
| `ondine_colour_code_v1` | Resolve colour through the approved Ondine colour-code table (`Navy→NVY` in the example). Missing mapping or collision is a STOP. |
| `ondine_sku_mpn_v3` | Create Ondine-owned `OND-<style>-<COLOUR>-<size>` codes; zero-pad numeric size to three digits and append approved three-letter codes for additional options in source-dimension order (`Regular→REG`, `Petite→PET`). SKU and MPN match per variant and are unique. Source IDs, SKU and barcode are forbidden inputs. |
| `ondine_occasion_from_end_use_v1` | Map a conflict-free source end-use value to the Ondine occasion list. When the source states none, the composer assigns one or more values from `daywear · evening · occasion · wedding guest · holiday` as an editorial classification derived from length, fabric, print and construction, recorded with its reasoning. It is metadata, never customer-facing claim copy (Ilias 2026-09-03). |
| `ondine_adult_womenswear_defaults_v1` | Apply Ondine’s brand-scoped adult womenswear taxonomy defaults (`age_group=adult`, `gender=female`) only when the product is an eligible Ondine womenswear garment and no source fact conflicts. This is classification metadata, not customer-facing copy. |
| `ondine_dress_taxonomy_v1` | Map eligible `Dresses` product type to the approved dresses product category and Ondine collection; no guessed taxonomy ID/GID. |
| `ondine_handle_slug_v1` | Slug the new Ondine title, lowercase and hyphenated, in 5–6 words. Source handles, brands and product names are forbidden inputs. |
| `ondine_seo_copy_v1` | Author page title 50–60 characters and meta description 150–160 characters from eligible facts; no promotion, urgency or unverified claim. |
| `ondine_tags_v1` | Produce 10–15 lowercase descriptive tags from eligible target facts. Strip source operational, promotion, collaboration and season/import tags. |
| `ondine_media_plan_v1` | Build only the planning six-slot shot requirements, filenames and alt-text plan from eligible `fp.*` garment facts; it never imports a source asset or pose sequence. |
| `ondine_weight_identity_v1` | Preserve one exact eligible source weight per real variant; disagreement across variants requires variant-scoped values or a STOP. |
| `ondine_canonical_source_identity_v1` | Private-only: normalize the final lowercase source host and use the stable source product ID when present, otherwise normalized pathname. |
| `ondine_source_key_v1` | Emit a stable source key from the canonical source identity into a private product metafield only. It must never become a Shopify tag or customer-facing value. |
| `ondine_source_key_v1` | Private-only: emit `SHA256(expected_shop_gid + canonical_source_identity)` after the Store Contract resolves `expected_shop_gid`; before then the ListingPlan carries the required value ref, never a guessed hash. |

Named transforms must be explicitly listed in each input fact’s `allowed_transform_ids`; a publishable claim flag never grants transform eligibility, and transform eligibility never grants customer-copy eligibility.

## 4. Exact customer-facing structure

### Buy box

Fixed order on desktop and mobile:

1. Title
2. Colour
3. Every captured non-colour option selector in source order
4. Price
5. **Add to Bag**

When Size is present, its selector keeps the adjacent Size guide and conditional live model line nested inside that module. Every remaining captured selector renders immediately after Size according to captured option position. The example therefore renders Title → Colour → Size module → Length selector → Price → Add to Bag.

No policy strip, secondary CTA, review block or promotional interruption may appear between these elements. If the live model line is ineligible, remove it from rendered output without leaving a placeholder; keep an omission flag in the plan.

### Description — exactly five slots

1. `opening`: at most two sentences; silhouette, fabric/coverage benefit.
2. `occasion`: one short who/when or occasion line supported by an eligible occasion fact.
3. `benefits` (legacy key): one verified detail in a prose paragraph; no bullet list in the description.
4. `styling`: one clearly editorial styling suggestion.
5. `close`: one quiet closing line; no CTA, urgency or guarantee.

### Below fold

Customer-facing output is five description paragraphs, then the live Fit & size and Fabric & care accordions, followed by the theme’s Delivery and Returns and Refunds policy rows. Do not duplicate those policies in product HTML. The following ordered keys are retained only in the legacy serialized composition record, not as an instruction to create extra PDP sections:


1. Description
2. Details & Care
3. Size & Fit
4. Materials & Provenance, only when at least one claim is publishable
5. Delivery
6. Returns and Refunds

`Details & Care` holds construction and care. `Size & Fit` holds option labels, exact garment measurements with known scope, and non-duplicated fit information. `Materials & Provenance` holds exact composition and eligible country/provenance claims; it must not manufacture sustainability language. Delivery and Returns and Refunds render only from the current `StorePolicySnapshot`, using its exact approved headings and content.

### StorePolicySnapshot field contract

The snapshot carries `snapshot_id`, `profile_id=ondine-live-policy-v1`, `provenance`, `test_only`, `status=CURRENT_AT_COMPOSE`, `verified_at` and `canonical_sha256`. Each of its ordered `delivery` and `returns_and_refunds` blocks carries `requested_url`, `final_url`, `captured_at`, exact `heading`, exact `content`, `content_sha256` and the existing policy binding. The canonical snapshot hash is SHA-256 over the UTF-8 RFC 8785 canonical JSON of all snapshot fields except `canonical_sha256`.

A real plan is committable only when `provenance=LIVE_STORE_READ_ONLY`, `test_only=false`, both requested and final URLs are exactly `https://ondinelondon.co.uk/pages/shipping-policy` and `https://ondinelondon.co.uk/pages/returns-refund-policy` for their respective blocks, the profile ID matches, every hash recomputes and the headings are exactly `Delivery` and `Returns and Refunds`. Redirects to another host or path do not qualify. `provenance=SYNTHETIC_TEST_ONLY` with `test_only=true` may satisfy validation only when an explicit validator-test-mode input is true; the normal CLI never exposes that mode and must reject every synthetic snapshot.

## 5. Variants, price and target state

- Preserve every exact source option dimension, value and real combination. Normalize `length` to customer-facing `Length` without changing values, and render it as a selector in captured order before price.
- UK numeric sizes remain `4, 6, 8, 10, 12, 14, 16, 18` when that is the locked source set.
- Do not carry source inventory, stock state, inventory policy or target availability. Those keys are absent from `shopify_target_state` and every target variant.
- Apply the price transform per real variant. Do not create compare-at prices, sale labels, savings text or countdowns.
- Generate unique Ondine SKU/MPN values through `ondine_style_code_v1`, the approved colour/option code tables and `ondine_sku_mpn_v3`. Collision is a stop. Do not reuse source product ID, item code, variant ID, SKU or barcode. Do not invent a GTIN.
- Supplier/source weight may transfer only as an eligible exact fact; otherwise omit and flag.
- `DATA_READY_DRAFT` is always Shopify `DRAFT`, with `target_media=[]` and `media_status=PENDING_GENERATION`. The media phase performs internal QA and direct DRAFT uploads without an intermediate human approval pause.
- `inventory_scope=OUT_OF_SCOPE` is plan metadata, not a target inventory field.

## 6. MediaPlan is planning, not target state

Every current plan includes an ordered seven-slot `MediaPlan` **[NOT IN AB COURSE]**:

1. Front/GMC (`01`)
2. Distinct second-model front (`01b`)
3. Back (`02`)
4. Side/movement (`03`)
5. Detail (`04`)
6. Lifestyle (`05`)
7. Ghost flat (`06`)

Each slot contains only a new Ondine filename, original shot brief, fact-bound garment requirements, clean alt-text plan and acceptance criteria. It contains no competitor URL, media ID, filename, pixel, prompt, pose/background/crop sequence or asset. All seven images specify zero text, model statistics, overlay or badge. Slot 01 additionally requires square-safe ≥1200×1200, plain light background, full garment uncropped and front-facing with 75–90% frame occupancy.

The separate media phase internally checks slot 01 and its square, then the second model and remaining views. Upload accepted originals directly to the owned DRAFT. A complete listing has seven originals per selected colour; `MediaPlan` is never part of the data-only Shopify deep-diff target. Human review occurs before activation.

## 7. Model-line gate

Render exactly `Model is [height] and wears UK [size]` when the source PDP explicitly supplies both model height and worn size for the product and the UK size is directly stated or resolved by an approved mapping. Preserve provenance for both values and the conversion rule. This is fit guidance from the reference product; it must not be presented as a measurement of the generated Ondine gallery model. An approved target-model record containing both facts remains an alternative authority. If neither route is complete, set `render=false`, omit the line and raise a specific missing-fact or unverified-size-mapping flag. Images always remain text-free.

## 8. SEO, GMC and organisation fields

The plan must contain:

- unique title ≤70 characters (≤150 hard);
- own 5–6 word handle;
- page title 50–60 and meta description 150–160;
- 10–15 lowercase descriptive tags;
- at least one real, non-empty Ondine collection;
- product type and approved Google product category binding;
- Brand and Vendor `Ondine London`; condition `new`;
- own unique per-variant SKU and MPN;
- exact target price, size, colour, URL plan and eligible weight;
- all five metafields: size, fabric, occasion, neckline and age group;
- no GTIN/barcode unless a separate authoritative Ondine record later supplies one.

GMC image binding is absent at `DATA_READY_DRAFT`; slot 01 becomes the feed image only after the separate customer-ready media gate. Feed availability is outside this workflow.

## 9. Private ownership and read-back

Customer leakage and writer ownership are separate namespaces. Source URL, host, product ID and ownership values are forbidden from title, description, public tags, metafields intended for display, SEO, GMC copy, alt text, filenames and media briefs. They are required inside `shopify_target_state.private_ownership`, marked `PRIVATE_INTERNAL_NOT_CUSTOMER_FACING`, and in the verdict-specific read-back contract.

The first-write and read-back target must resolve and exactly verify:

- `source_key`: value ref `run_state.source_key_sha256`, produced by `ondine_source_key_v1` from the Store Contract `expected_shop_gid` plus `df.canonical_source_identity`;
- private source-key and canonical-source-URL metafields;
- private `managed_by=product-listing-v2` metafield;
- descriptive merchandising tags only; source identities and management markers are forbidden in Shopify tags;
- private canonical source URL from `fp.canonical_source_url`.

Missing, duplicate or mismatched ownership state blocks creation/resume. The source-key value remains a ref until the Store Contract supplies the expected shop GID; guessing it is forbidden.

## 10. Originality and evidence checks

`originality.copy_guard_result` is recomputed by `ondine_copy_guard_v1`; a free-text PASS assertion is forbidden. Its normalization is locked as `ondine_copy_guard_normalization_v1`:

1. Apply Unicode NFKD and casefold.
2. Replace `&` with ` and `, remove combining marks and Unicode format characters (`Cf`), then tokenize only maximal ASCII `[a-z0-9]+` runs.
3. Join tokens inside a field with one ASCII space. Empty normalized fields are omitted. Field boundaries remain distinct for three-gram comparison; ordered LCS concatenates the field token lists without adding boundary tokens.
4. Serialize corpus field records as an ordered array of `{path, normalized}` objects using UTF-8 RFC 8785 canonical JSON; its SHA-256 is the corpus hash.

The private source corpus is built from the hash-pinned SourceCapture in this exact order: source title; for every captured section in `order`, heading then `raw_text`; structured-product SEO HTML title then meta description; then one product-gallery media alt per non-excluded `rendered_media` item in media position order. When media alt is not a first-class SourceCapture field, the audit resolver reads it only from the SourceCapture's hash-pinned sanitized-render artifact, matches it to the ordered rendered-media URL and requires exactly one value per media item. Calloway therefore contributes five ordered media-alt fields. Raw source strings exist only while the audit runs and never enter the ListingPlan.

The target corpus follows the exact ordered `customer_field_paths` stored in the result and covers title; all five description slots, expanding slot-three items in order; every below-fold heading, item and policy content in rendered order; SEO page title and meta description; every public tag; and every MediaPlan filename then alt text in slot order. Private ownership and policy provenance URLs are excluded.

The guard enumerates every shared normalized contiguous three-token span within individual fields. A span is removed from `non_whitelisted_shared_three_grams` only when an exemption record repeats that exact normalized three-token span and names one exact approved rule: `EXACT_CAPTURED_MATERIAL_NAME`, `EXACT_CAPTURED_COMPOSITION_VALUE` or `EXACT_CAPTURED_MEASUREMENT_VALUE`. Broader fact, product-type or editorial exemptions are forbidden.

`source_order_lcs` records integer source, target and LCS token counts, `denominator=TARGET_TOKEN_COUNT`, the exact six-decimal ratio `lcs_token_count / target_token_count`, and `threshold=0.50`. The result is deterministically `PASS` only when all corpus hashes recompute, `non_whitelisted_shared_three_grams=[]`, every exemption matches a real shared span and approved rule, no forbidden source identity/expression family is customer-facing, and the exact integer comparison `2 × lcs_token_count < target_token_count` holds. Otherwise it is `FAIL`; equality at 0.50 fails. `report_sha256` is SHA-256 over UTF-8 RFC 8785 canonical JSON of `copy_guard_result` with only `report_sha256` omitted.

The copy guard supplements the existing claim checks: every physical claim must resolve to a conflict-free `publishable_as_claim=true` fact; every derived value must resolve to an allowed transform; source media count in target state remains zero; and every planned image remains original and text-free. Passing originality means source facts survived while source expression did not.

## 11. Flags and stops

Flags that permit a data-ready plan when the affected claim is omitted:

- `OMITTED_NO_APPROVED_TARGET_MODEL_RECORD`
- `OMITTED_AMBIGUOUS_MEASUREMENT_SCOPE`
- `OMITTED_UNPUBLISHABLE_PROVENANCE`
- `WEIGHT_MISSING`
- `MEDIA_PENDING_GENERATION` (historical fixtures retain `MEDIA_PENDING_APPROVAL`)

Stops:

- `FACT_PACKET_PROJECTION_MANIFEST_REQUIRED` when any normal-validation manifest pin or artifact is absent;
- `FACT_PACKET_PROJECTION_MANIFEST_INVALID` for unknown registry ID, hash mismatch, wrong product/SourceCapture binding or invalid verification target;
- `FACT_PACKET_PROJECTION_REVIEW_SEPARATION_INVALID` only when a record claims independent review but author/reviewer separation fails; ordinary assistant self-checks do not require separation;
- `FACT_PACKET_PROJECTION_BINDINGS_MISMATCH` when the ordered ListingPlan binding array is not exactly equal to the verified manifest array;
- verification record/hash mismatch, wrong market/currency or unresolved source conflict affecting a required output;
- SourceCapture output/determinism hash or final Ondine profile hash mismatch;
- any ListingPlan or derived-fact input that bypasses `fp.*` and points directly to raw SourceCapture/section/product paths;
- missing/invalid current customer-paid price or unauthorized price transform;
- unknown size system, unmappable size, more than three source option dimensions, missing dimension/value, invented combination or duplicate SKU/MPN;
- any source identifier/URL outside the private ownership namespace, any source media/expression/policy/stock state, target inventory field or target availability field in the target;
- incomplete five-slot description, wrong PDP order, missing required metafield, SEO length failure, empty collection or unbound category;
- Delivery/Returns copy without a current `StorePolicySnapshot`;
- live model line without either complete source height/worn-size evidence plus a verified UK mapping, or one approved target-model record containing both facts and bindings;
- non-empty `target_media`, media status other than `PENDING_GENERATION` for current plans, or any customer-facing image text at `DATA_READY_DRAFT`;
- any Shopify state other than `DRAFT` or any publication action.
- missing/mismatched private source key, private canonical source URL or private `managed_by=product-listing-v2` metafield in target/read-back state, or any of them exposed as a Shopify tag.

## 12. Example-specific decisions

The adjacent example uses the Atlas-locked positive denominator oracle SHA-256 `46dddf7976e96ccd3fe2a29b5f47a7e5423c05f984b02917b82d3225e6153646` under detached aggregate lock SHA-256 `0bf1135a067f07363b6eacb0e0e942a8e5e6a45f96b6347a3f56b7c453cccc9b`.

Stage B pins the exact Calloway manifest ID and SHA-256 in both ListingPlan evidence and `fact_packet_projection`. The manifest's Scout authorship is accepted only with the distinct detached Atlas lock named in §2; that pair approves the exact ordered 33-binding canonical SHA-256 `7b89952844b9de29083fe5ec943adff7ed1fb23ab19a52a3987e0340bf95ce95`. All four ListingPlan manifest pins are Calloway golden-fixture values only.

- Verified current GBP price `55.00` becomes regular target price `54.95` via `ondine_price_nearest_95_below_v1`.
- Eight UK sizes × two locked lengths yield the exact 16 real combinations.
- Length renders as the second captured selector after the Size module and before price.
- Approved title `Navy Embroidered Cotton Midi Day Dress` deterministically yields style code `NECMDD`; Navy resolves to `NVY`; all SKU/MPNs use the exact matrix and collision-stop rule.
- Source stock state, compare-at price, promotion, product/variant identifiers, title/prose/SEO, policies and media are absent.
- Source model facts do not authorize a target fit line; the line is omitted and flagged.
- The captured `140 cm` wearing length has no locked Regular/Petite scope, so it is omitted and flagged rather than presented ambiguously.
- The six-slot `MediaPlan` is complete, while `shopify_target_state.target_media=[]` and `media_status=PENDING_APPROVAL`.
- Private target/read-back ownership carries the source-key value ref, private source URL ref and `managed_by=product-listing-v2` solely as private metafields. Shopify tags remain descriptive merchandising terms and must never carry ownership or source identity.
- Delivery and Returns and Refunds are represented as required `StorePolicySnapshot` bindings, not copied source policy prose. A real plan cannot pass the compose gate until those bindings resolve to a current snapshot.
- The 33 bindings, 16 Size×Length rows and shown ownership values are golden-fixture expectations only; a runtime composer derives its own counts, dimensions, exact combinations and ownership, and Length may be absent.

## First-image approval override — 2026-09-08

Ilias removed the standalone slot 01 portrait and GMC-square approval gate. Generate and internally validate them, then continue without requesting first-image approval. Older sample-first approval wording in this document is superseded by references/gallery-workflow.md. Continuity references and all generated views must pass internal QA. Ilias removed the remaining full-gallery, colour-front and upload approval pauses on 2026-09-15: upload accepted images directly to DRAFT and retain the final human review before activation. Use `INTERNAL_QA_THEN_DIRECT_DRAFT_UPLOAD` for current MediaPlans; old approval-gate values belong only to historical evidence.
