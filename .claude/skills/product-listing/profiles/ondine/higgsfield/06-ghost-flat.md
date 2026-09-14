---
template_id: ondine-hf-06-ghost-flat-v1
slot: "06"
role: GHOST_FLAT
generation_mode: model_free_product_image
renderer_compatibility: [higgsfield_gpt_image_2]
aspect_ratio: "3:4"
resolution: 4k
quality: high
prompt_format: json_object
status: candidate
---

# 06 — Ghost flat

## Purpose

Close the gallery with a model-free, complete front-oriented product view that confirms silhouette and construction without adding styling noise.

## Composition

- Present one complete garment front, symmetrically and naturally shaped, using a clean ghost-mannequin or careful flat presentation selected for the garment's structure.
- Both sleeves, neckline, body, full length and hem are visible and separated clearly from the background.
- No human body or body remnants. The garment retains believable volume and gravity rather than appearing pasted or inflated.
- Newly arrange the garment; do not reproduce a competitor flat/ghost composition.

## Garment fidelity invariants

- Consolidate only approved facts already proven across the gallery: colour/print, surface, neckline, sleeves/cuffs, silhouette, length, hem and visible construction.
- Preserve the same print scale/density/palette and fabric response as approved model slots; exact placement remains newly distributed.
- Do not expose or invent inner construction, lining, labels, pockets, closures, seams, fastenings, stretch or opacity.
- The view must not imply a different cut merely to make the layout symmetrical.

## Reference roles

- Required: `APPROVED_SLOT_01_CONTINUITY` for garment identity after the sample passes.
- Add `GARMENT_FRONT_IDENTITY`, `MATERIAL_SURFACE_DETAIL` and narrowly scoped `CONSTRUCTION_SUPPORT` as needed.
- A source model photo supplies garment geometry only; body shape, pose, styling and shadows must not transfer.

## Framing, background and lighting

- Portrait `3:4`; `1500×2000`; full garment centered with even margin and a square-safe central read.
- Plain light warm-neutral background consistent with the earlier studio.
- Soft even light with restrained natural shadow; enough edge contrast to separate sleeves and hem without cutout halos.

## Prohibited elements

No visible mannequin/body, hanger, hook, rail, tag, inner label, size sticker, packaging, props, footwear, accessories, collage, text, logo, watermark, badge, cutout halo or invented inside view.

## Clean-image rule

Only the garment and minimal natural grounding/shadow appear. All product information remains outside the pixels.

## Acceptance checklist

- [ ] One complete front-oriented garment with neckline, both sleeves and hem visible.
- [ ] Model-free presentation has no body/mannequin remnants or cutout artifacts.
- [ ] Shape, colour/print, fabric response and verified construction match slots 01–05.
- [ ] Garment reads naturally rather than flattened, inflated or re-cut.
- [ ] No invented inner or hidden feature and no source composition copy.
- [ ] Zero text, logo, watermark, overlay, badge, tag or collage.

## Failure conditions

Reject for missing/cropped garment parts, body remnants, hanger/tag, distorted symmetry, inconsistent fabric/print, invented internal construction, cutout artifacts, copied source arrangement or any global pack failure.
