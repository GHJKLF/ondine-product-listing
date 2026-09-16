# Ondine seven-view image templates

Use ChatGPT's built-in image generation. The directory name and template IDs are retained for compatibility; Higgsfield is not required. Render each JSON prompt with this product's inspected references and styling brief. Save native originals and their actual dimensions; the requested 1500×2000 is a composition target, not a guaranteed output size.

| Display order | Template | Purpose |
|---|---|---|
| 1 | 01-front-gmc.json | Lead front; separate square rendition for Google |
| 2 | 01b-second-model.json | Same garment on a distinct adult model |
| 3 | 02-back.json | Rear construction and silhouette |
| 4 | 03-side-movement.json | Side profile and natural movement |
| 5 | 04-detail.json | One visible garment detail |
| 6 | 05-lifestyle.json | Garment in a suitable original setting |
| 7 | 06-ghost-flat.json | Garment only |

The separate square is not an eighth PDP image. Generate seven views for every selected colour. Preserve each colour's garment facts and the appropriate lead/second-model identity.

Choose models, footwear, accessories, setting and distinct poses for the actual garment. Keep supplier people, poses, branding and styling out of generated images. Source photographs are private garment evidence only. If a camera view is missing, use inspected available references and infer unseen geometry conservatively; record that inference privately and never use it as a product fact.

For later views, `APPROVED_SLOT_01_CONTINUITY` means the internally accepted lead. The second model uses that image for garment/studio continuity while changing the person. No standalone model, gallery or upload approval is required. Internally check fidelity, image quality and framing, then upload accepted originals directly to the owned Shopify DRAFT. Final human review precedes activation.

The executable `generation_request.prompt_json.layout` supplies each slot's bounds; top-level layout mirrors it. Do not apply front-view thresholds to movement or ghost shots. On a framing miss, make at most one identical retry, then handle residual deviations as specified in the gallery workflow. A heuristic miss is not permission to crop away garment parts or falsely report a pass.

See [gallery workflow](../../../references/gallery-workflow.md) for the full generation, QA, upload and verification procedure. `pack-manifest.json` pins the current files; signed historical fixtures elsewhere remain test evidence only.
