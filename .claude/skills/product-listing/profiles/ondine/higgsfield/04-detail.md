---
template_id: ondine-hf-04-detail-v1
slot: "04"
role: DETAIL
generation_mode: worn_product_detail
renderer_compatibility: [higgsfield_gpt_image_2]
aspect_ratio: "3:4"
resolution: 4k
quality: high
prompt_format: json_object
status: candidate
---

# 04 — Detail

## Purpose

Make one purchase-relevant material, print or construction detail inspectable at realistic scale without turning the frame into a collage.

## Composition

- Choose exactly one approved `detail_focus` per product: for example neckline finish, cuff, surface/print, fastening or verified construction.
- Frame a tight worn-garment crop with enough surrounding garment context to locate the detail.
- The approved Ondine model may be partially visible; hands appear only if necessary and must not cover or manipulate the detail unnaturally.
- Create a new crop and gesture rather than following a competitor detail composition.

## Garment fidelity invariants

- Match evidenced texture, sheen, weave, print scale, edge finish and construction at close range.
- Preserve true material response: no plastic smoothing, metallic sparkle, embroidery, beading or raised texture unless verified.
- Do not use composition percentages or sustainability/provenance claims as visual effects.
- Every visible adjacent feature must remain consistent with approved slots 01–03.

## Reference roles

- Required: `MATERIAL_SURFACE_DETAIL` or narrowly scoped `CONSTRUCTION_SUPPORT` matching the selected `detail_focus`.
- Add `APPROVED_SLOT_01_CONTINUITY` for colour, garment and model continuity.
- A source detail reference establishes only the approved feature; source hands, jewellery, props, crop and lighting are excluded.

## Framing, background and lighting

- Portrait `3:4`; `1500×2000`; detail fills most of the frame while remaining identifiable as part of the garment.
- Background stays softly warm-neutral and subordinate.
- Diffused directional light reveals surface and edge definition without glare, false sparkle or colour shift.

## Prohibited elements

No collage, macro abstraction without context, jewellery focus, manicure focus, clutch/bag, text, labels, care symbols, composition percentages, logos, badges, invented stitch/trim/fastening, skin artifacts or competitor crop.

## Clean-image rule

The image communicates one detail visually. Feature names, fibre content and care facts remain in live PDP copy or alt text, not pixels.

## Acceptance checklist

- [ ] Exactly one approved detail is the unambiguous subject.
- [ ] Detail scale, colour, texture and construction match evidence and earlier slots.
- [ ] Crop includes enough garment context and remains useful in a square gallery crop.
- [ ] Hands/partial model, if present, are realistic and unobtrusive.
- [ ] No source accessory, crop, gesture or lighting composition is copied.
- [ ] Zero text, logo, watermark, overlay, badge or collage.

## Failure conditions

Reject for multiple competing details, invented embellishment/construction, false material texture, over-smoothing, glare, colour drift, source-crop copying, anatomy errors or any global pack failure.
