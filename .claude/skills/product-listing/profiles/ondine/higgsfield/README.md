---
type: reference
status: candidate
brand: ondine-london
owner: mira
pack_id: ondine-higgsfield-six-slot-v1
version: 3.0.0
---

# Ondine seven-view template pack

Current execution uses ChatGPT built-in image generation. The JSON `runtime_override_2026_09_13` and shared gallery workflow supersede historical provider commands, fixed resolution claims and sample-first approval requirements below. Retained identifiers and older prose are historical composition references. Do not execute legacy Higgsfield commands.

This directory contains the executable Ondine templates for direct Higgsfield GPT Image 2 gallery generation. Each slot JSON contains the fixed Higgsfield request parameters, a deterministic prompt template, reference bindings, layout rules and QA conditions. Product facts and approved private reference files are inserted at run time; they are never hardcoded into the shared template.

## Fixed order

| Slot | Template ID | Spec | Generation mode |
|---:|---|---|---|
| 01 | `ondine-hf-01-front-gmc-v1` | [Front / GMC](01-front-gmc.md) | `model_worn_product_image` |
| 02 | `ondine-hf-02-back-v1` | [Back](02-back.md) | `model_worn_product_image` |
| 03 | `ondine-hf-03-side-movement-v1` | [Side / movement](03-side-movement.md) | `model_worn_product_image` |
| 04 | `ondine-hf-04-detail-v1` | [Detail](04-detail.md) | `worn_product_detail` |
| 05 | `ondine-hf-05-lifestyle-v1` | [Lifestyle](05-lifestyle.md) | `model_worn_product_image` |
| 06 | `ondine-hf-06-ghost-flat-v1` | [Ghost flat](06-ghost-flat.md) | `model_free_product_image` |

The machine-verifiable order and file hashes live in `pack-manifest.json`. Slot 01 is always the first and only sample. Ilias must approve that sample before slots 02–06 may be submitted.

## Standards hierarchy

AB is the floor: each image must be high-quality, clearly focused on the item for sale, accurate, clean and free from logos, watermarks, text, badges, collages and confusing secondary products. [AB 7.2 @ 01:26–03:16 → `/Users/ilias/Documents/TanjaiOS/Skool-AB-Inner-Circle/02-Google-Ads-Masterclass/7.2-Compliant-Product-Import.md`]

Ondine adds the fixed seven-view sequence, original-media requirement, coherent warm-neutral studio, cross-slot garment/model continuity, clean-image rule, slot-01 GMC bar, evidence-bound fidelity and sample-first Ilias gate. These additions are brand rules, not AB course claims.

## Intent/backend separation

An approved product instantiation supplies structured intent only:

- `template_id` and slot;
- `generation_mode` from this pack;
- one short `intent_summary` derived from approved fields;
- `reference_assignments`, each with an approved asset binding and one role from the taxonomy below;
- `aspect_ratio`, `count=1` and `resolution=2k`;
- garment fidelity values, missing-fact stops and acceptance checks.

At generation time the prompt is `generation_request.prompt_json`, one JSON object sent verbatim. Fixed Ondine blocks (output, layout, shot, studio, continuity, fidelity_rules, prohibited) never change. Every `{{product.*}}` string is replaced by the matching key of the run's `product_reference_facts.json` (`garment`, `model` including footwear and styling, `movement`, `detail_focus`, `lifestyle_setting`, `ghost_flat_presentation`); values may be objects. Attach only the files matching `reference_bindings`, submit the declared command and parameters, and keep the filled JSON in the run folder. No free-text prompt is written.

## Reference-role taxonomy

| Role | May establish | Must never establish |
|---|---|---|
| `GARMENT_FRONT_IDENTITY` | Front silhouette, neckline, sleeve geometry, hem proportion, colour/print family | Source model identity, pose, set, accessories, exact print placement |
| `GARMENT_BACK_EVIDENCE` | Verified rear silhouette and visible construction | Hidden closure, seam, fastening, vent or hardware |
| `MATERIAL_SURFACE_DETAIL` | Texture, sheen, weave and print scale supported by evidence | Composition/provenance copy, embellishment or construction not visible |
| `CONSTRUCTION_SUPPORT` | A specifically verified garment feature from another view | Any feature outside its approved fact scope |
| `APPROVED_SLOT_01_CONTINUITY` | The accepted Ondine model, garment rendering, studio and colour baseline for later slots | New product facts or permission to change the garment |
| `APPROVED_TARGET_MODEL` | Model identity continuity when a separate approved target-model record exists | Height, worn size or live PDP claims unless that record supplies and approves both |

Competitor references are evidence for the garment only. They are never likeness, pose, crop, styling, set, lighting or sequence references. Every generated frame must be a newly composed Ondine image.

## Cross-slot invariants

1. One coherent garment identity across all seven slots: colour/print family, fabric appearance, neckline, sleeve form, silhouette, length, hem and every verified construction feature remain stable.
2. Exact print placement may vary naturally; copying a source image's placement is forbidden. Print scale, density, palette and distribution character must remain consistent.
3. Slots 01, 02, 03 and 05 use the same accepted Ondine model and the same garment rendering. Slots 01–04 share the warm-neutral studio; slot 05 uses the approved warm lifestyle setting. Slot 04 uses the same model when a person is visible. Slot 06 is model-free.
4. One calm warm-neutral studio system: seamless light neutral background, soft directional light, restrained contrast, faithful colour and realistic fabric response.
5. Every image contains zero text, letters, numbers, logos, labels, watermarks, promotional overlays, badges or UI. Model height and worn size remain live PDP text only when separately eligible.
6. No competitor accessory, pose, model likeness, set, crop sequence or brand expression may survive into the result.
7. Missing or ambiguous physical facts remain unrendered. The instantiation must choose an evidence-safe treatment or stop for Ilias; it may not silently invent.
8. Each slot is one clean image, never a collage, contact sheet, split view or before/after.

## Global delivery contract

- File stem: `ondine-<approved-product-handle>-<slot>`; no competitor brand, product name, ID or source filename.
- Slot 01 PDP slide: `3:4`, `1500×2000`; its separate GMC rendition is independently composed at `1:1`, square-safe 1200×1200 or larger.
- All six PDP slides: `3:4`, 1500×2000 target. Slot 01 also produces a separate 1:1 GMC rendition outside the PDP gallery.
- Output count: exactly one candidate per submitted slot unless Ilias separately authorizes variants.
- Metadata/alt text is authored outside the pixels and must be original Ondine wording.
- Generated URLs and files do not become Shopify target media until all seven pass the customer-ready media gate and Ilias approves the set.

## Pack-level failure conditions

Stop the slot or reject its output when any of these occurs:

- missing or unapproved reference binding;
- unresolved fact conflict affecting visible garment identity;
- garment drift between slots;
- copied competitor likeness, pose, styling, set, crop or print placement;
- invented closure, hardware, pocket, slit, tier, seam, trim, lining, opacity, stretch or measurement;
- text, logo, watermark, badge, collage, extra product or distracting accessory;
- wrong aspect ratio, low resolution, crop failure, distorted anatomy or visibly synthetic compositing;
- slot 01 misses any GMC criterion;
- slots 02–06 are attempted before Ilias approves slot 01;
- any renderer other than direct Higgsfield GPT Image 2 is used.

## Gate

This pack is specification-only. A product-specific instantiation and Ilias approval are required before slot 01; a second Ilias approval of slot 01 is required before the remaining five slots.


## Accessories (v4.3.0)

Slots 02–05 render `model` from `product.model_styled`: the same model block as `product.model` with `accessories` set per product (a fine chain, small hoops, a plain belt only when the garment has none; unbranded, never over the neckline or the detail the slot sells). Slot 01, the GMC square and slot 06 keep `accessories: none` because the feed image must show only the product.


## Pose realism (v4.4.0)

Slots 01, the GMC square, 02, 03 and 05 carry a fixed `pose_realism` block. The retired wording ("calm neutral standing pose, shoulders level", "balanced rear stance") produced mannequins.

## One pose per slot (v4.5.0)

Each model slot takes its own `shot.pose`: slot 01 reads `{{product.pose_01}}`, slot 02 `{{product.pose_02}}`, slot 03 `{{product.pose_03}}`, slot 05 `{{product.pose_05}}`. The GMC square reuses `pose_01` because it is the same look recomposed square; slots 04 and 06 carry no full-body pose.

Ilias 2026-09-03: "if two slides communicate the same feeling then we lost, each one should be unique". The single shared `{{product.pose}}` of v4.4.0 made slots 01, 02, 03 and 05 converge on one stance, and each run had to patch it by hand. The styling brief now writes four stances in `decisions.poses` and `scripts/apply_styling_brief.py` refuses any pair whose wording overlaps by 45% or more, so the gallery cannot reach a visual gate with two slots telling the same story.

Give each slot a different job: 01 the straight front record, 02 the back, 03 the movement, 05 the room. Vary the body axis, what the hands do and where the gaze goes, not only the words.

## First-image approval override — 2026-09-08

Ilias removed the standalone slot 01 portrait and GMC-square approval gate. Generate and internally validate them, then continue without requesting first-image approval. Older sample-first approval wording in this document is superseded by references/gallery-workflow.md. Continuity references must pass internal QA; full-gallery and upload approval remain required, as do the separate second-model and colour-front review gates.
