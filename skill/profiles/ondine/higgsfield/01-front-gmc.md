---
template_id: ondine-hf-01-front-gmc-v1
slot: "01"
role: FRONT_GMC
generation_mode: model_worn_product_image
renderer_compatibility: [chatgpt_builtin_image_generation]
aspect_ratio: "3:4"
resolution: native_output_dimensions_recorded
quality: high
prompt_format: json_object
status: candidate
---

# 01 — Front / GMC

`APPROVED_SLOT_01_CONTINUITY` is a legacy identifier for the internally accepted lead image, not a human approval gate. Upload accepted originals directly to DRAFT. Use the JSON prompt layout for this slot’s exact bounds.

## Purpose

Create the featured PDP image: an unmistakable, accurate front view that makes the single garment for sale immediately legible. A separate square composition from this slot supplies the future GMC feed image.

## Composition

- One adult Ondine model wearing only the garment being sold; calm neutral stance, front-facing torso and garment.
- Arms relaxed and slightly clear of the body so the sleeve line and side silhouette remain readable.
- Full garment and complete hem visible. Keep the garment centered, upright and visually dominant.
- The garment bounding area occupies 75–90% of the portrait frame while preserving breathing room around the outline.
- Compose a new Ondine stance. Do not reproduce a source pose, crop or styling arrangement.

## Garment fidelity invariants

- Match only approved product facts for colour/print family, surface, neckline, sleeve length/cuff, bodice line, skirt line, length and hem.
- Preserve realistic fabric weight, drape and opacity without adding structure or volume.
- Pattern placement must be newly distributed while its approved scale, density and palette remain stable.
- Unknown closures, seams, pockets, trims, lining, stretch and hardware remain absent or visually non-assertive.

## Reference roles

- Required: at least one `GARMENT_FRONT_IDENTITY` reference.
- Add `MATERIAL_SURFACE_DETAIL` when the front reference cannot establish texture, sheen or print scale.
- Add narrowly scoped `CONSTRUCTION_SUPPORT` only for a verified visible feature.
- A competitor reference may establish garment facts only; it may not establish model likeness, pose, accessories, set or lighting.

## Framing, background and lighting

- Portrait `3:4`; `1500×2000` composition target (record actual native dimensions). A separate independent `1:1` rendition must remain full-body and uncropped for GMC.
- Plain seamless light warm-neutral background with no horizon clutter, furniture, architecture or scenery.
- Soft directional studio light, gentle grounding shadow, controlled highlights and faithful colour.
- No aggressive editorial crop, lens distortion or depth blur that hides the garment edge.

## Prohibited elements

No text, logo, watermark, badge, price, model statistic, collage, props, handbag, jewellery focus, outer layer, visible unrelated garment, branded footwear, hanger, pedestal, décor or competitor styling cue.

## Clean-image rule

Pixels contain the model and garment only, with a neutral ground/shadow where needed. Alt text, product facts, price, height and size are never embedded.

## Acceptance checklist

- [ ] Exact one garment is clearly the subject.
- [ ] Front-facing and full garment uncropped, including hem and both sleeves.
- [ ] Product occupies 75–90% of the PDP frame; the separate GMC rendition is independently composed at `1:1` without cropping the garment.
- [ ] Approved colour/print, silhouette, neckline, sleeves and length are coherent.
- [ ] Background is plain, light and warm-neutral; colour remains faithful.
- [ ] Anatomy, garment edges, hands and fabric are realistic with no compositing artifacts.
- [ ] No source likeness/pose/set/accessory or exact print-placement copy.
- [ ] Zero text, logo, watermark, overlay, badge or collage.

## Failure conditions

Reject for any crop, side/back bias, unclear product focus, extra apparel, invented garment feature, source-composition copying, print/colour drift, low resolution, text/branding, anatomy defect or synthetic compositing. Failure of this slot blocks every later slot.
