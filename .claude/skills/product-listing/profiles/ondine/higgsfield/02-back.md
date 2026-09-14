---
template_id: ondine-hf-02-back-v1
slot: "02"
role: BACK
generation_mode: model_worn_product_image
renderer_compatibility: [higgsfield_gpt_image_2]
aspect_ratio: "3:4"
resolution: 4k
quality: high
prompt_format: json_object
status: candidate
---

# 02 — Back

## Purpose

Show the complete rear silhouette and only the back construction that verified evidence permits.

## Composition

- Use the approved slot-01 Ondine model, garment and studio in a straight or restrained three-quarter rear stance.
- Full garment and complete hem visible; both sleeves clear enough to read.
- Hair is moved away from the upper back when it would hide the neckline or approved construction.
- Arms and hands must not cover the centre back, waist/hip line or closure area.

## Garment fidelity invariants

- Preserve the approved rear neckline, sleeve/cuff, body line, print/surface, length and hem.
- Render a closure, seam, fastening, vent or hardware only when a verified back-specific fact authorizes it.
- When back construction is unknown, the product instantiation must name an Ilias-approved non-assertive treatment; otherwise stop.
- Back treatment must stay consistent with any verified pull-on or closure construction.

## Reference roles

- Required: `APPROVED_SLOT_01_CONTINUITY`.
- Use `GARMENT_BACK_EVIDENCE` when it clearly proves rear silhouette or construction.
- `GARMENT_FRONT_IDENTITY` may support print/sleeve/length continuity but cannot authorize hidden back features.
- Source rear imagery is garment evidence only, never model, hair, pose, accessory or set direction.

## Framing, background and lighting

- Portrait `3:4`; `1500×2000`; full rear garment uncropped and centered.
- Preserve a safe central silhouette for square gallery cropping.
- Same warm-neutral seamless studio, camera character, lighting direction and colour as earlier model slots.

## Prohibited elements

No invented zip, buttons, keyhole, tie, hook, seam, vent, label or hardware; no obscuring hair, bag, jewellery, outer layer, hand placement, text, badge, collage or competitor back pose.

## Clean-image rule

Construction is shown only through evidence-safe pixels. No callout arrows, closure labels, measurements or model facts.

## Acceptance checklist

- [ ] Same approved model, garment and studio as slot 01.
- [ ] Complete rear silhouette, hem and both sleeves are visible.
- [ ] Hair, hands and styling do not conceal the back.
- [ ] Every visible back feature is verified or follows the approved non-assertive treatment.
- [ ] No copied competitor pose, accessory, styling or crop.
- [ ] Zero text, logo, watermark, overlay, badge or collage.

## Failure conditions

Reject for any invented/contradictory closure or hardware, obscured centre back, changed silhouette/length/print, different model, source-pose copying, crop failure or any global pack failure.
