---
template_id: ondine-hf-03-side-movement-v1
slot: "03"
role: SIDE_MOVEMENT
generation_mode: model_worn_product_image
renderer_compatibility: [higgsfield_gpt_image_2]
aspect_ratio: "3:4"
resolution: 4k
quality: high
prompt_format: json_object
status: candidate
---

# 03 — Side / movement

## Purpose

Show the garment profile from the side, with restrained movement that reveals drape without hiding its true silhouette, length or construction.

## Composition

- Use the approved slot-01 Ondine model, garment and studio.
- Capture a side or three-quarter-side stance, optionally with one subtle step; keep the garment profile legible.
- Movement should read primarily in fabric and hem, not in theatrical body action.
- Keep the complete garment visible and avoid hands covering key construction or print areas.

## Garment fidelity invariants

- Movement amplitude follows the approved fabric weight and silhouette; light fabric may lift softly, heavier fabric may only sway.
- Neckline, sleeves, waist/hip line, length and hem construction cannot change under motion.
- Do not turn ordinary drape into a train, slit, ruffle, tier, pleat, flare or extra volume unless that feature is verified.
- Print scale/palette remain fixed; exact placement may vary naturally and must not clone the source.

## Reference roles

- Required: `APPROVED_SLOT_01_CONTINUITY`.
- Add `MATERIAL_SURFACE_DETAIL` for evidenced drape, sheen or texture.
- Add `CONSTRUCTION_SUPPORT` for a verified movement-critical feature only.
- Source movement/side views are fabric-behaviour evidence only, not choreography or pose references.

## Framing, background and lighting

- Portrait `3:4`; `1500×2000`; full garment and moving hem remain inside frame.
- Center the motion arc so a square crop retains the garment and its movement cue.
- Same warm-neutral seamless studio and lighting direction as slots 01–02; shutter effect stays crisp enough for product detail.

## Prohibited elements

No fan-blown spectacle, jumping, running, dance pose, flying fabric detached from gravity, fake slit/train/tier/ruffle, props, accessories, extra products, motion text, duplicated limbs or collage.

## Clean-image rule

The movement is communicated only through body and fabric. No arrows, captions, badges, model facts or graphic effects.

## Acceptance checklist

- [ ] Same approved model, garment and studio as slots 01–02.
- [ ] Motion is subtle, believable and newly composed.
- [ ] Fabric response matches approved weight/surface evidence.
- [ ] Garment remains complete, recognisable and structurally unchanged.
- [ ] No invented volume, slit, train, trim or construction.
- [ ] Zero text, logo, watermark, overlay, badge or collage.

## Failure conditions

Reject for dramatic or physically impossible motion, altered silhouette/construction, cropped hem, blurred product, anatomy errors, source-pose copying, accessory obstruction or any global pack failure.
