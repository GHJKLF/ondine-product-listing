---
template_id: ondine-hf-05-lifestyle-v1
slot: "05"
role: LIFESTYLE
generation_mode: model_worn_product_image
renderer_compatibility: [chatgpt_builtin_image_generation]
aspect_ratio: "3:4"
resolution: native_output_dimensions_recorded
quality: high
prompt_format: json_object
status: candidate
---

# 05 — Lifestyle

`APPROVED_SLOT_01_CONTINUITY` is a legacy identifier for the internally accepted lead image, not a human approval gate. Upload accepted originals directly to DRAFT. Use the JSON prompt layout for this slot’s exact bounds.

## Purpose

Place the approved garment and model in one calm, believable Ondine lifestyle setting while keeping the product clearly readable.

## Composition

- Use the internally accepted slot-01 Ondine model and garment identity.
- Use a quiet warm interior with soft window light and minimal architectural context.
- Keep the complete or near-complete garment, sleeves, silhouette and hem clearly readable.
- Use a calm standing or walking pose; the setting supports the garment and never becomes the subject.

## Garment fidelity invariants

- Preserve the approved relationship of garment to body, verified length class, neckline, sleeve geometry, print scale, fabric response and construction.
- Do not use a competitor model, location, pose, crop, accessory or styling as lifestyle direction.
- Do not imply an unverified event, endorsement, provenance or location.
- Do not use a competitor model's apparent body, height or size as fit data.

## Reference roles

- Required: `APPROVED_SLOT_01_CONTINUITY`.
- Add `GARMENT_FRONT_IDENTITY`, `MATERIAL_SURFACE_DETAIL` or `CONSTRUCTION_SUPPORT` only to protect verified garment identity.
- `APPROVED_TARGET_MODEL` is optional and does not authorize pixels containing height/size.
- Competitor full-body references are garment evidence only, never lifestyle, pose, body, likeness, location or prop references.

## Framing, background and lighting

- Portrait `3:4`; `1500×2000` composition target (record actual native dimensions); complete or near-complete garment clearly readable.
- Leave enough clear margin to keep the product dominant.
- Quiet warm-neutral interior, soft natural window light and restrained contrast.

## Prohibited elements

No text, measurements, size labels, arrows, collage, handbag focus, prominent jewellery, outerwear, waist-cinching props, competing footwear, busy décor, event signage or competitor pose/location/styling.

## Clean-image rule

Model height and worn size may appear only as separately eligible live PDP text. They never appear in this image, its set or a prop.

## Acceptance checklist

- [ ] Same approved model and garment as slot 01.
- [ ] Complete or near-complete garment is readable and remains the subject.
- [ ] Setting is calm, believable, original and supports the product.
- [ ] Pose is natural, new and does not distort the silhouette.
- [ ] No competitor location, pose, props, crop or styling survives.
- [ ] Zero text, logo, watermark, overlay, badge or collage.

## Failure conditions

Reject for a different model or garment, changed fit, false length, product-obscuring décor, implausible setting, copied competitor location/pose/styling, printed model facts or any global pack failure.
