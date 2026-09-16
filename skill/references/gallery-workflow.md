# Original Gallery Workflow

Read this reference only after the product data-ready DRAFT passes and the requested scope includes original Ondine images. The seven-image update below, active store profile and its pinned media-pack manifest are the authority for slot order, dimensions, composition and QA.

For Ondine, use **ChatGPT’s built-in image generation**. The legacy `../profiles/ondine/higgsfield/pack-manifest.json` and seven shot templates remain composition references, not instructions to use Higgsfield. Request high-quality 3:4 images, save native originals and record their actual dimensions. Never claim 4K output when the tool returned a smaller image. Use the image tool for edits; do not recolour pixels with scripts.

For a multi-colour product, generate and internally check the full seven-shot lead-colour gallery first. Adapt these same accepted shots to every other selected colour, changing only the garment and its matching fabric belt. Preserve the approved model, pose, construction, crop, background, lighting and styling. These are fidelity requirements to inspect, not a guarantee that AI edits leave every other pixel unchanged.

## Direct DRAFT upload and progress

Ilias removed intermediate image, colour-front, full-gallery and upload approval pauses on 2026-09-15. This is standing authorization for current and future listing runs: generate original images, perform internal QA and upload accepted assets directly to the owned Shopify DRAFT. Do not wait for another approval or demand a human-reviewed image flag. Final human review occurs on the completed draft before the operator activates it. Respect a later explicit hold or narrower scope; this rule never authorizes ACTIVE-product edits.

Keep internal QA findings, any actual user review and standing upload authorization separate. Never mark an unreviewed image as approved by Ilias or Haider just to pass a checker. Retain earlier QA findings and actual human approvals honestly; do not re-reject an image for the same disclosed concern the user already accepted. New files still require their applicable checks. Missing roles, corrupt files, wrong product/store identity and mismatched media IDs remain concrete completion gaps.

Update checkpoints at phase entry and completion: generating, internal QA, ready for upload, uploading, uploaded/pending verification, verified, or blocked with the exact technical or evidence issue. Record selected, internally accepted, actually human-reviewed, uploaded and verified counts separately. Reuse accepted files; do not regenerate them merely to rename them or remove already-reviewed cosmetic variation.

Existing ACTIVE-product media updates require the separately installed product-image-set skill (not included in this listing package), which reuses this generation guidance and provides a separate ACTIVE-safe upload route. All DRAFT-only steps below remain limited to new listings and owned DRAFTs.

## 7.0 Styling brief (before any prompt is rendered)

**Hero avatar selection:** carry forward the choice made during product analysis. Choose the adult model whose styling, hair, pose and overall presentation best show this garment's silhouette, colour, print and occasion. During image QA, confirm garment fidelity, unobstructed details, natural presentation and image quality. There is no fixed ethnicity order, automatic model reuse or required alternation between products. Ethnicity does not determine which shoppers can connect with an image. The second model is a distinct adult person who adds variety to the gallery; choose both without a separate model-selection approval request.

Record `model_selection.hero` and `model_selection.second_model` in `styling_brief.json`, each with a model specification in `value` and a product-specific reason in `because`. Keep this structured selection outside the flat `decisions` map. Use these specifications for `product.model` and `product.second_model` in `product_reference_facts.json` before applying the styling brief. The selected hero occupies slot 01, supplies the separate square rendition and remains the continuity model for back, movement and lifestyle views. Internal image QA, direct DRAFT upload and final human review before activation apply.

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
   Keep a usable preview for the final review and upload the internally accepted native original without pausing. Framing measurements are heuristic: inspect garment boundaries separately from cast shadows, especially for ghost shots. Log remaining deviations rather than silently calling them a pass.
4. Slots 02–06 attach the approved slot 01 image as the first reference. The GMC square uses `gmc_feed_rendition.generation_request`.

Baseline from the 2026-09-03 run: 3/7 first-pass, 7/7 after one retry. Record each run's numbers in `APPROVALS.txt` so template changes are judged on pass rate.

Reference preparation and template mapping are internal QA. Complete them without asking Ilias to review internal documents. Keep visual outputs available for the final draft review.

## 7.1 Internal reference and template QA

Use competitor images privately to identify verified garment colour, print, construction, silhouette and details. A back photo of another colourway is valid back evidence: the role establishes construction only, never colour. Every drape, tie, sash or panel is recorded from visible evidence as attached, free, or unknown. Describe its actual attachment points; do not default unknown to attached or prohibit a real cuff-attached hanging panel. Record conflicts. Never copy competitor pixels, model identity, styling, watermark, background or pose sequence.

**Missing source view fallback — Ilias, 2026-09-15.** Generate every required view from the available inspected reference images even when the competitor has no photograph of that angle. This is standing authorization: do not ask again, leave the view pending, reduce the seven-view set or make a matching-angle photograph a prerequisite. Use all relevant existing views, including another colour's construction reference when it depicts the same garment; preserve the target colour's actual print and visible construction.

Infer only the unseen geometry needed to complete the requested view. Carry through the visible silhouette, neckline, sleeves, waist, length, fabric appearance and print. Where construction is not shown, choose the simplest consistent continuation; do not add decorative cutouts, zips, lacing, ties, capes, pockets, trim or hardware without evidence. For a detail view, enlarge a detail visible in the available photos instead of inventing a new feature. Actual conflicting evidence must still be resolved; a missing angle alone is not a conflict.

In `product_reference_facts.json`, describe which source views exist and which surfaces are inferred (for example `product.garment.back_evidence`). Save the actual reference mapping with the rendered prompt, and mark each affected QA/manifest asset `INFERRED_FROM_AVAILABLE_REFERENCES`; explain the inference briefly in the private gallery preview, never as text on the product image. A generated image does not establish product facts and must not become evidence for copy, fabric, sizing, closure or other metafield claims.

When a template calls for a missing view, bind the best available inspected garment reference instead and label its role `AVAILABLE_GARMENT_REFERENCE`. State what that photograph actually shows; never label a front photo as verified back evidence. One photo may serve several reference roles, but repeating it is not additional evidence. Preserve the slot's model/pose/layout rules, internal QA and DRAFT-only upload boundary.

Load the pinned manifest and its seven executable JSON templates. Map garment evidence and the missing-view fallback above to each slot. The fallback overrides older matching-angle requirements and any separate non-assertive-treatment approval gate.

The assistant checks the reference pack and mapping. Do not ask Ilias to review these files. When the available references are mapped and any inferred view is documented, proceed directly to slot 01 generation and internal QA.

## 7.2 Generate and internally validate slot 01

Generate only slot 01 through ChatGPT’s built-in image generation and create its separate square GMC rendition. Validate both against the slot JSON and manifest. Inspect both internally and continue without a first-image or GMC-square approval request. Record QA results; do not record user approval that was not given. Keep both available for the final draft review.

## 7.3 Internally check the second model and continue the gallery

After slot 01 and its square pass internal QA, generate and internally check `01b` using the second-model template, then generate slots 02–06 from their matching JSON files without a standalone second-model approval request. Include the second-model image in the completed draft gallery. Preserve the approved garment, model, colour and visual system. Reject any asset that fails its slot checks.

After internal QA, upload accepted images directly under §7.4 and continue to additional colourways. Do not stop for gallery approval. The final review takes place on the finished draft.

## 7.3b Additional colourways

The selected colourways are settled before the DRAFT write. Default to **seven shots per selected colour**, in this fixed order: front, second-model front, back, side/movement, detail, lifestyle, ghost flat. A narrower set requires an explicit user scope decision.

1. Inspect the existing run and approval records. Reuse approved fronts and completed views; generate only missing colour × shot combinations. Do not regenerate an approved front to regularise its filename.
2. After internal QA of the full lead-colour gallery, create each missing colour front from the accepted lead front plus the actual source photograph for that colour. Take the source URL from verified product data, never an invented CDN path. Match the photograph, not the retailer’s colour label. Internally check colour/print fidelity before propagating a new colour through the remaining views; no user colour-front approval is needed.
3. For the additional-colour `01b` shot, use the approved matching lead-colour second-model image for identity/composition plus the actual source colour reference; preserve the second model, not the lead model. Record `product.second_model` and `product.pose_second_model` explicitly; the styling helper only fills the original model-slot poses. For each missing shot 02–06, attach the **approved target-colour front** for colour/model identity and the **approved matching lead-colour shot** for composition and construction. Save a per-colour/per-shot prompt derived from that shot’s template, with explicit reference roles and target colour. Change only garment fabric and the matching belt; preserve everything else. If source colourways differ in print or construction, stop the colour-only adaptation and resolve that evidence rather than repainting a different garment.
4. Inspect each result against both references: hue, model identity, neckline, cuffs, belt, pleats, length, pose, crop, background and lighting. Reject introduced changes, leftover lead-colour fabric, missing details or clipped hems. Keep the original attempts and record selected retries. Do not promise pixel-identical edits or perfect results.
5. Internally inspect each complete seven-image colour set in order, alongside its preserved front, and upload accepted originals directly. Keep the ordered previews for the final draft review.

Maintain `<run>/colour-gallery-manifest.json` as the handoff for gallery tooling. Include `schema_version: 2`, `product_id`, `option_name: "Colour"`, `shot_order`, `upload_approved` and an `assets` array. Each selected asset records its `product_id`, the exact Shopify `colour`, a stable `colour_key`, `shot`, `shot_order` (1–7), filename, absolute local path, actual width/height, SHA-256, `approval_status`, `uploaded` flag and `shopify_media_id` when known. Set `upload_approved: true` to record upload authorization, and add `upload_authorization: {"mode": "DIRECT_TO_DRAFT", "instruction": "Ilias: when the images generated upload them directly to shopify, the final review will be done to change status from draft"}`. For each internally accepted asset, set `qa_status: "accepted"`; keep `approval_status: "not_reviewed"` unless a human actually reviewed that asset. The compiler accepts this internal-QA path without inventing human approval. Require one selected asset per colour/shot; keep rejected attempts outside that selection. Group by exact option value and sort by shot order, never by colour guessed from pixels or filename alone.

Record first-pass results, retries, residual framing deviations and Ilias’s corrections in `APPROVALS.txt`. Add recurring failures to `<operator-state>/LEARNINGS.md` for the next listing. A manifest supports grouping; it does not install or activate a gallery app or theme integration.

## 7.4 Upload and verify

As soon as selected assets pass internal QA, use the existing Shopify connector to upload them directly to the owned DRAFT, once each. The standing instruction above supplies upload authorization; do not request another approval. Upload checked batches as they become available, then verify the full gallery when generation finishes. Read existing media first. Prefer its local-file upload tool when available, then attach those existing file IDs through a schema-validated `fileUpdate` with `referencesToAdd` to avoid duplicate file creation. Record returned IDs immediately and read back before retrying an uncertain write. Keep the lead-colour seven shots first, followed by each additional colour’s seven shots in manifest order. Expected PDP count is **7 × selected colour count**, unless Ilias explicitly approved a narrower manifest.

Assign each colour’s front to every variant of that colour using `productVariantsBulkUpdate` (`mediaId`), then read back `variants.media`. The lead front remains the product’s featured image. Store the separate square rendition as a store file; exclude it from the PDP gallery. Record each selected asset’s full `gid://shopify/MediaImage/...` in `shopify_media_id`, and set `uploaded: true` only after verifying it is a READY image attached to this product. Do not change GMC fields or install apps or activate theme embeds as part of media upload. Save this product’s Ondine Gallery grouping through §7.4b after media verification.
Do not upload competitor media or change inventory, availability, tax, product status, GMC or Ads. Preserve the default sales-channel assignments established during draft preparation; do not remove them or add other channels as a media-upload side effect. Read Shopify back and verify:

- the same owned product remains DRAFT
- exactly the manifest’s internally accepted PDP assets exist at completion, with seven per selected colour in the recorded order
- filenames and alt text match
- the featured asset is the approved lead-colour slot 01 and all variant front assignments match their colours
- no competitor or duplicate media exists

If a retry produces duplicates, record the exact later duplicate media IDs and hold completion for authorized cleanup. Preserve older material; do not silently delete retained assets. Read back after authorized cleanup.

Check the PDP gallery and mobile presentation against the bundled Ondine profile, seven JSON shot templates and this run's internally accepted images. Verify garment fidelity, framing, image order, colour grouping and the profile's product-page layout. Figma is not used by this skill: do not request a Figma plugin, links or exports, or block a listing because they are absent. Resolve a mismatch in the affected asset or mapping without adding a routine approval pause. Never claim a visual check that was not performed. Keep the product DRAFT for final human review.

## 7.4b Automatic Ondine Gallery handoff

For Ondine listings with a complete internally checked seven-shot set for every selected colour, perform this handoff after §7.4. The listing process saves the colour groups automatically; opening the image manager is only needed for corrections. The app and its theme embed are installed separately. A saved, enabled product configuration does not prove storefront activation.

Resolve `<gallery-tool>` before these steps: the simplified package bundles it at `gallery/` beside `SKILL.md`. In the TanjaiOS checkout it remains at `projects/engine-3/stores/ondine-london/store/variant-gallery/app/ondine-gallery`. Use the actual absolute folder path in commands; the angle-bracket name is a placeholder.

1. Read the owned draft product afresh using `PRODUCT_QUERY` from `<gallery-tool>/src/shopify.ts`. Collect every media page, current option-value IDs and `ondine_gallery.configuration` including `compareDigest`. Save the complete snapshot in this run.
2. Pass that snapshot and this run’s `colour-gallery-manifest.json` to the app’s compiler, from the workspace root:

   ```sh
   node <gallery-tool>/scripts/listing-handoff.ts PRODUCT_SNAPSHOT.json COLOUR_GALLERY_MANIFEST.json > REVIEWABLE_GRAPHQL_PAYLOAD.json
   ```

   The compiler checks recorded direct-to-draft authorization and per-asset internal QA, upload verification, attached READY media, DRAFT status, product identity, exact Shopify colour names, unique colour/shot slots and all seven shots per colour. Historical genuinely human-approved manifests remain supported separately. It accepts `side-movement` and `ghost-flat` from this manifest. Resolve any failed check before writing; never fabricate approvals or missing media IDs.
3. Schema-validate the returned `metafieldsSet` operation, then execute its query and variables through the existing authenticated Shopify connector. The compiler itself performs no network writes. Complete checked manifests enable new gallery configurations automatically while the product remains DRAFT. Existing manual assignments, ordering and explicit manual disablement are preserved.
4. Re-read and compare the saved metafield with the compiled value. A stale digest requires a fresh snapshot and recompilation. An uncertain response requires readback before retrying. Verify the product is still DRAFT and its approved media order, featured image and variant fronts are unchanged by this handoff.
5. Record the saved configuration and readback in this run. If the app is not installed or its intended theme embed is inactive, report that separately; do not install, activate a live theme, publish the product or change research-sheet status as a side effect.

Implementation contract and supported formats: `<gallery-tool>/docs/listing-handoff.md`.

## Seven-image gallery update — approved 2026-09-08

Display order is **1 front (lead model), 2 front (second model), 3 back, 4 movement, 5 detail, 6 lifestyle, 7 garment-only**. Stable template IDs are `01`, `01b`, `02`, `03`, `04`, `05`, `06`; IDs are not display positions. This update overrides older six-view examples and any single-model continuity wording. Use `01b-second-model.json` for the additional view. Record `product.second_model` and `product.pose_second_model` with reasons in the styling brief; keep these separate from the lead model. Choose the hero avatar during product analysis and record its product-specific rationale under §7.0 of the gallery workflow. The second model must be a different adult person who adds variety. Neither slot has a fixed ethnicity; a previous product's model order is not a default for the next listing.

Generate and internally validate the lead portrait, its separate square and the second-model preview without requesting individual user approval, then continue to the remaining views. Preserve the lead model in back, movement and lifestyle shots. Use the approved lead as garment/style reference for the second model, explicitly changing identity; all other views retain their original reference rules. Match garment, lighting and background across the two front views. For additional colours, preserve each shot's corresponding approved model identity, including the second-model front. The GMC square is separate and the lead remains featured and assigned to variants. Internally check all seven images and upload accepted originals directly to the owned Shopify DRAFT. Do not pause for image, colour-front, complete-gallery or upload approval. Human review happens on the finished draft before activation.

New colour manifests use `schema_version: 2`, the complete canonical shot order is `front, second-model, back, side-movement, detail, lifestyle, ghost-flat`, numbered 1–7. Legacy version-1 six-view manifests remain valid historical records; do not silently add media to existing approved products.

## First-image gate removed — Ilias, 2026-09-08

The lead portrait and separate GMC square no longer require individual user approval. Internal fidelity and framing QA still applies. Legacy template fields such as `requires_approved_slot_01` mean an internally QA-accepted continuity reference during generation; they do not impose a user approval pause. Ilias subsequently removed all remaining gallery, colour-front and upload pauses on 2026-09-15. Every view is internally checked, accepted originals upload directly to DRAFT, and final human review occurs before activation. This overrides older user-gate wording in composition/template references without relabelling historical human reviews.
