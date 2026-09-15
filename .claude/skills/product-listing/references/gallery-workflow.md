# Original Gallery Workflow

Read this reference only after the product data-ready DRAFT passes and the requested scope includes original Ondine images. The seven-image update below, active store profile and its pinned media-pack manifest are the authority for slot order, dimensions, composition and QA.

For Ondine, use **ChatGPT’s built-in image generation**. The legacy `../profiles/ondine/higgsfield/pack-manifest.json` and seven shot templates remain composition references, not instructions to use Higgsfield. Request high-quality 3:4 images, save native originals and record their actual dimensions. Never claim 4K output when the tool returned a smaller image. Use the image tool for edits; do not recolour pixels with scripts.

For a multi-colour product, generate and approve the full seven-shot lead-colour gallery first. Adapt these same approved shots to every other selected colour, changing only the garment and its matching fabric belt. Preserve the approved model, pose, construction, crop, background, lighting and styling. These are fidelity requirements to inspect, not a guarantee that AI edits leave every other pixel unchanged.

## Approval handling and progress

Before enforcing a review gate, read the user's current scope and prior instructions. The user can explicitly waive intermediate gates or authorize a batch through upload; record that authorization and do not ask for it again. Scope changes apply only to the named work. Visual approval alone does not invent upload permission; reuse upload permission already granted for that scope.

Keep internal QA findings, user visual approval and upload authorization as separate records. When Ilias reviews previously held candidates and approves their appearance, retain the original QA notes as history, record who approved which reviewed files and when, and select the approved candidates. Do not re-reject them for the same disclosed visual concern, erase the original finding, or claim a technical QA pass or Haider review that did not happen. New files still require their applicable checks. Missing roles, corrupt files, wrong product/store identity and mismatched media IDs remain concrete completion gaps; approval cannot make absent files exist.

Update checkpoints at phase entry and completion, not only at the end: generating, ready for review, approved, uploading, uploaded/pending verification, verified, or blocked with exact next action. Record selected colour/shot counts separately from reviewed, uploaded and verified counts. An approved lead may still have six missing roles. Reuse approved files; do not regenerate them merely to rename or remove already-reviewed cosmetic variation.

Existing ACTIVE-product media updates require the separately installed product-image-set skill (not included in this listing package), which reuses this generation guidance and provides a separate ACTIVE-safe upload route. All DRAFT-only steps below remain limited to new listings and owned DRAFTs.

## 7.0 Styling brief (before any prompt is rendered)

**Hero avatar selection:** carry forward the choice made during product analysis. Choose the adult model whose styling, hair, pose and overall presentation best show this garment's silhouette, colour, print and occasion. During image QA, confirm garment fidelity, unobstructed details, natural presentation and image quality. There is no fixed ethnicity order, automatic model reuse or required alternation between products. Ethnicity does not determine which shoppers can connect with an image. The second model is a distinct adult person who adds variety to the gallery; choose both without a separate model-selection approval request.

Record `model_selection.hero` and `model_selection.second_model` in `styling_brief.json`, each with a model specification in `value` and a product-specific reason in `because`. Keep this structured selection outside the flat `decisions` map. Use these specifications for `product.model` and `product.second_model` in `product_reference_facts.json` before applying the styling brief. The selected hero occupies slot 01, supplies the separate square rendition and remains the continuity model for back, movement and lifestyle views. Existing image-review and upload gates still apply.

Write `<run>/styling_brief.json`, then run `python3 scripts/apply_styling_brief.py <run> --recent <operator-state>/recent-settings.json`. The brief answers the same five questions for every product, each decision carrying a `because`:

1. **Season on sale** — listing date plus the UK calendar (early September sells through autumn). Decides light, footwear and setting.
2. **Occasion** — the editorial classification already recorded for the product (wedding guest, holiday, daywear, evening, occasion). Decides the kind of place shown.
3. **UK buyer context** — where a UK customer actually wears it in that season (autumn wedding, city lunch, October sun holiday). Rules out settings that read as high-summer resort for a September launch.
4. **Garment facts** — length decides footwear visibility, neckline decides whether a necklace is allowed, print density decides how plain the backdrop must be.
5. **Competitor styling, evidence only** — what the source paired it with sets the register; the Ondine choice must differ in composition and setting.

6. **Pose and attitude** — how a real person in this register stands and moves (casual daywear is loose and mid-step; occasionwear is composed but never rigid). Written as **one sentence per model slot** into `decisions.poses` under the keys `01`, `02`, `03` and `05`, each with its own `because`; the pack adds a fixed realism block (weight on one leg, one hand engaged, gaze just off the lens, caught between movements) so no slot reads as a mannequin.

   Every slide has to communicate a different feeling (Ilias 2026-09-03). Give each its own body axis, hand job and gaze: 01 the straight front record, 02 the back, 03 the movement, 05 the room. `apply_styling_brief.py` refuses two poses whose wording overlaps by 45% or more, and the GMC square reuses `pose_01` because it is the same look recomposed square.

Outputs: `footwear`, `accessories`, `lifestyle_setting`, `movement`, `light`, each `{value, because}`, plus `poses` holding one `{value, because}` per model slot (`01`, `02`, `03`, `05`) written into `product.pose_01/02/03/05`. The script writes them into `product_reference_facts.json` (slot 01, the GMC square and slot 06 keep `accessories: none`) and refuses a lifestyle setting, footwear type or accessory set that repeats any of the last three products in `recent-settings.json` (Ilias 2026-09-03: the same tan sandal appeared on two products in a row). Footwear and jewellery are chosen from the product's season, occasion and register, never carried over. Keep the brief in the run folder so a bad image can be traced to a bad reason.

Executable loop per slot:

1. Write `product_reference_facts.json` in the run folder (`product.garment`, `product.model` incl. footwear, `product.movement`, `product.detail_focus`, `product.lifestyle_setting`, `product.ghost_flat_presentation`).
2. `python3 scripts/render_slot_prompt.py <slot> <template.json> <run-folder>` fills the product placeholders and writes `prompts/<slot>.prompt.json`. Send its JSON content to the built-in image tool with the inspected local reference images in the declared order. Save the exact submitted prompt and returned original path immediately. For colour adaptations, use the reference mapping in §7.3b. After an uncertain result, inspect the run and returned assets before retrying; never assume a failed response created no image.
3. Download the result and run `python3 scripts/measure_framing.py <preview.jpg>`; compare against the slot's `layout` bounds. Reject and resubmit the identical request once on a framing miss; a second miss is a template gap, not a retry case. When both attempts miss, keep the one whose garment is uncropped and treat a marginal occupancy overshoot as acceptable. A left/right reading near 0 with a sane height means the backdrop gradient tripped the heuristic; judge that slot by eye. The script is meaningless on slots 04 and 05 (no plain backdrop); check those visually only.
   Show Ilias a usable preview at every gate; retain the native original for approved upload. Framing measurements are heuristic: inspect garment boundaries separately from cast shadows, especially for ghost shots. Log remaining deviations rather than silently calling them a pass.
4. Slots 02–06 attach the approved slot 01 image as the first reference. The GMC square uses `gmc_feed_rendition.generation_request`.

Baseline from the 2026-09-03 run: 3/7 first-pass, 7/7 after one retry. Record each run's numbers in `APPROVALS.txt` so template changes are judged on pass rate.

Reference preparation and template mapping are internal team QA. Ilias reviews visual outputs, not internal evidence documents. His approval at one visual gate authorizes only the stated next action.

## 7.1 Internal reference and template QA

Use competitor images privately to identify verified garment colour, print, construction, silhouette and details. A back photo of another colourway is valid back evidence: the role establishes construction only, never colour. Every drape, tie, sash or panel is recorded from visible evidence as attached, free, or unknown. Describe its actual attachment points; do not default unknown to attached or prohibit a real cuff-attached hanging panel. Record conflicts. Never copy competitor pixels, model identity, styling, watermark, background or pose sequence.

Load the pinned manifest and its seven executable JSON templates. Map verified garment evidence to each slot without changing the template rules.

The assigned specialist checks the reference pack and mapping. Do not ask Ilias to review these files. If the evidence is complete and the mapping passes, proceed directly to the slot 01 generation gate.

## 7.2 Generate and internally validate slot 01

Generate only slot 01 through ChatGPT’s built-in image generation and create its separate square GMC rendition. Validate both against the slot JSON and manifest. Inspect both internally and continue without a first-image or GMC-square approval request. Record QA results; do not record user approval that was not given. Include both in the later gallery review.

## 7.3 Generate and approve the second model and remaining views

After slot 01 passes internal QA, generate and approve `01b` using the second-model template, then generate slots 02–06 from their matching JSON files. Preserve the approved garment, model, colour and visual system. Reject any asset that fails its slot checks.

Show the ordered seven-image PDP gallery to Ilias and stop for approval.

## 7.3b Additional colourways

The selected colourways are settled before the DRAFT write. Default to **seven shots per selected colour**, in this fixed order: front, second-model front, back, side/movement, detail, lifestyle, ghost flat. A narrower set requires an explicit user scope decision.

1. Inspect the existing run and approval records. Reuse approved fronts and completed views; generate only missing colour × shot combinations. Do not regenerate an approved front to regularise its filename.
2. After approval of the full lead-colour gallery, create each missing colour front from the approved lead front plus the actual source photograph for that colour. Take the source URL from verified product data, never an invented CDN path. Match the photograph, not the retailer’s colour label. Show the colour fronts for approval before propagating a new colour through the remaining views.
3. For the additional-colour `01b` shot, use the approved matching lead-colour second-model image for identity/composition plus the actual source colour reference; preserve the second model, not the lead model. Record `product.second_model` and `product.pose_second_model` explicitly; the styling helper only fills the original model-slot poses. For each missing shot 02–06, attach the **approved target-colour front** for colour/model identity and the **approved matching lead-colour shot** for composition and construction. Save a per-colour/per-shot prompt derived from that shot’s template, with explicit reference roles and target colour. Change only garment fabric and the matching belt; preserve everything else. If source colourways differ in print or construction, stop the colour-only adaptation and resolve that evidence rather than repainting a different garment.
4. Inspect each result against both references: hue, model identity, neckline, cuffs, belt, pleats, length, pose, crop, background and lighting. Reject introduced changes, leftover lead-colour fabric, missing details or clipped hems. Keep the original attempts and record selected retries. Do not promise pixel-identical edits or perfect results.
5. Show each complete seven-image colour set in order, alongside its preserved front, for visual approval. Generation approval does not authorise upload. Keep Ilias’s visual gates until he explicitly changes them.

Maintain `<run>/colour-gallery-manifest.json` as the handoff for gallery tooling. Include `schema_version: 2`, `product_id`, `option_name: "Colour"`, `shot_order`, `upload_approved` and an `assets` array. Each selected asset records its `product_id`, the exact Shopify `colour`, a stable `colour_key`, `shot`, `shot_order` (1–7), filename, absolute local path, actual width/height, SHA-256, `approval_status`, `uploaded` flag and `shopify_media_id` when known. Record the actual user instruction authorizing upload. Require one selected asset per colour/shot; keep rejected attempts outside that selection. Group by exact option value and sort by shot order, never by colour guessed from pixels or filename alone.

Record first-pass results, retries, residual framing deviations and Ilias’s corrections in `APPROVALS.txt`. Add recurring failures to `<operator-state>/LEARNINGS.md` for the next listing. A manifest supports grouping; it does not install or activate a gallery app or theme integration.

## 7.4 Upload and verify

Only after explicit upload approval, use the existing Shopify connector to upload the selected approved assets once. Read existing media first. Prefer its local-file upload tool when available, then attach those existing file IDs through a schema-validated `fileUpdate` with `referencesToAdd` to avoid duplicate file creation. Record returned IDs immediately and read back before retrying an uncertain write. Keep the lead-colour seven shots first, followed by each additional colour’s seven shots in manifest order. Expected PDP count is **7 × selected colour count**, unless Ilias explicitly approved a narrower manifest.

Assign each colour’s front to every variant of that colour using `productVariantsBulkUpdate` (`mediaId`), then read back `variants.media`. The lead front remains the product’s featured image. Store the separate square rendition as a store file; exclude it from the PDP gallery. Record each selected asset’s full `gid://shopify/MediaImage/...` in `shopify_media_id`, and set `uploaded: true` only after verifying it is a READY image attached to this product. Do not change GMC fields or install apps or activate theme embeds as part of media upload. Save this product’s Ondine Gallery grouping through §7.4b after media verification.
Do not upload competitor media or change inventory, availability, tax, product status, GMC or Ads. Preserve the default sales-channel assignments established during draft preparation; do not remove them or add other channels as a media-upload side effect. Read Shopify back and verify:

- the same owned product remains DRAFT
- exactly the manifest’s approved PDP assets exist, with seven per selected colour in the approved order
- filenames and alt text match
- the featured asset is the approved lead-colour slot 01 and all variant front assignments match their colours
- no competitor or duplicate media exists

If a retry produces duplicates, record the exact later duplicate media IDs and hold completion for authorized cleanup. Preserve older material; do not silently delete retained assets. Read back after authorized cleanup.

Check the PDP gallery and mobile presentation against the bundled Ondine profile, seven JSON shot templates and this run's approved images. Verify garment fidelity, framing, image order, colour grouping and the profile's product-page layout. Figma is not used by this skill: do not request a Figma plugin, links or exports, or block a listing because they are absent. A mismatch returns to the affected gate. Keep the existing visual approvals and upload authorization; never claim a visual check that was not performed.

## 7.4b Automatic Ondine Gallery handoff

For Ondine listings with a complete approved seven-shot set for every selected colour, perform this handoff after §7.4. The listing process saves the colour groups automatically; opening the image manager is only needed for corrections. The app and its theme embed are installed separately. A saved, enabled product configuration does not prove storefront activation.

1. Read the owned draft product afresh using `PRODUCT_QUERY` from `projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/src/shopify.ts`. Collect every media page, current option-value IDs and `ondine_gallery.configuration` including `compareDigest`. Save the complete snapshot in this run.
2. Pass that snapshot and this run’s `colour-gallery-manifest.json` to the app’s compiler, from the workspace root:

   ```sh
   node projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/scripts/listing-handoff.ts PRODUCT_SNAPSHOT.json COLOUR_GALLERY_MANIFEST.json > REVIEWABLE_GRAPHQL_PAYLOAD.json
   ```

   The compiler checks approval, upload verification, attached READY media, product identity, exact Shopify colour names, unique colour/shot slots and all seven shots per colour. It accepts `side-movement` and `ghost-flat` from this manifest. Resolve any failed check before writing; never fabricate approvals or missing media IDs.
3. Schema-validate the returned `metafieldsSet` operation, then execute its query and variables through the existing authenticated Shopify connector. The compiler itself performs no network writes. Complete approved manifests enable new gallery configurations automatically. Existing manual assignments, ordering and explicit manual disablement are preserved.
4. Re-read and compare the saved metafield with the compiled value. A stale digest requires a fresh snapshot and recompilation. An uncertain response requires readback before retrying. Verify the product is still DRAFT and its approved media order, featured image and variant fronts are unchanged by this handoff.
5. Record the saved configuration and readback in this run. If the app is not installed or its intended theme embed is inactive, report that separately; do not install, activate a live theme, publish the product or change research-sheet status as a side effect.

Implementation contract and supported formats: `projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery/docs/listing-handoff.md`.

## Seven-image gallery update — approved 2026-09-08

Display order is **1 front (lead model), 2 front (second model), 3 back, 4 movement, 5 detail, 6 lifestyle, 7 garment-only**. Stable template IDs are `01`, `01b`, `02`, `03`, `04`, `05`, `06`; IDs are not display positions. This update overrides older six-view examples and any single-model continuity wording. Use `01b-second-model.json` for the additional view. Record `product.second_model` and `product.pose_second_model` with reasons in the styling brief; keep these separate from the lead model. Choose the hero avatar during product analysis and record its product-specific rationale under §7.0 of the gallery workflow. The second model must be a different adult person who adds variety. Neither slot has a fixed ethnicity; a previous product's model order is not a default for the next listing.

Generate and internally validate the lead portrait and its separate square without requesting user approval, then obtain approval of the second-model preview before producing remaining views. Preserve the lead model in back, movement and lifestyle shots. Use the approved lead as garment/style reference for the second model, explicitly changing identity; all other views retain their original reference rules. Match garment, lighting and background across the two front views. For additional colours, preserve each shot's corresponding approved model identity, including the second-model front. The GMC square is separate and the lead remains featured and assigned to variants. Show all seven images for gallery approval and require explicit upload approval.

New colour manifests use `schema_version: 2`, the complete canonical shot order is `front, second-model, back, side-movement, detail, lifestyle, ghost-flat`, numbered 1–7. Legacy version-1 six-view manifests remain valid historical records; do not silently add media to existing approved products.

## First-image gate removed — Ilias, 2026-09-08

The lead portrait and separate GMC square no longer require individual user approval. Internal fidelity and framing QA still applies. Legacy template fields such as `requires_approved_slot_01` mean an internally QA-accepted continuity reference during generation; they do not impose a user approval pause. Final manifest approval remains actual gallery approval by Ilias. This overrides sample-first user-gate wording in older composition/template references. The second-model preview, additional-colour front review, full galleries and explicit upload approval remain unchanged.
