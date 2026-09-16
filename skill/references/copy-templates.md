# Copy templates

Fixed frameworks. Only the product facts change between runs — never the shape.

Sources: AB 7.2 (product listing SOP) · AB "import → improve" method @39:31 title priority, @25:36 clean description · Haider's prompt doc (ClickUp 08-26) · the store profile's voice.

These are the brand-neutral shapes: slot counts, limits, banned content. **The formulas that fill them live in the store's profile** (`profiles/<store>.md` → "Voice and copy formulas"), because a title formula that names a silhouette only makes sense for a brand that sells garments.

## Title

**Formula: the loaded profile's current formula.** Do not restate or override a brand formula in this shared reference.

Rules that hold for every brand:
- Use one shared Shopify/GMC title until the store has a separately managed feed title.
- Start with current product/keyword research, then combine only useful verified attributes into a natural buyer-facing title. Do not follow a rigid keyword stack or stuff terms.
- Gender and colour may appear when relevant and verified. For a product with multiple sizes, keep size in variant data rather than the shared title.
- Target ≤70 characters, hard cap 150 [AB 7.2]
- Include the keywords a buyer actually searches ("floral summer dress", not "dress") — the title is the #1 visible element on a Shopping ad
- Unique across the catalog. Check before writing.
- Normal capitalization, no ALL CAPS · no promo words ("Free Shipping", "50% Off") · no symbols, emojis, trademark marks · no claims without proof
- Generate 2 options, pick the descriptive/SEO one

## Description — 5 fixed slots

1. **Opening** — the profile's opening pattern, in the store's voice. Two sentences maximum.
2. **Who it's for and when to use it** — occasion, season, context.
3. **Verified product detail in prose** — a short sentence based on captured facts. No bullet lists in the description. Detailed construction, fit and care belong in the dedicated metafields. Missing facts are flagged internally and omitted from customer copy.
4. **One usage or styling suggestion** — a single line.
5. **Soft close** — a brand line, no call to action.

### Hard description gate

All five slots must pass before a Shopify write. Presence alone is not enough.
Reject the description when the opening does not follow the loaded profile's
sequence, the occasion line does not express a real who/when/occasion use case,
the product-detail line is not fact-backed, the styling line contains more than
one suggestion, or the close introduces a CTA, urgency, guarantee or new claim.
Reject repeated ideas across slots and vague filler that adds no customer meaning.
Correct the copy and run this gate again. There is no partial pass, and an
originality PASS cannot compensate for a failed slot.

Delivery and Returns and Refunds are **not** written into the description. The theme renders them from the live policy pages (Ondine: `Policy accordion` block on the product template, Ilias 2026-09-03). A profile that lacks that theme block must say so explicitly before any policy text enters a product.

**Banned in descriptions** [AB 7.2]: images or embedded media · external links or URLs · CTA phrases ("Buy Now", "Click Here") · urgency ("limited stock", "last pieces", "flash sale") · medical or health claims · checkmark characters (no decorative substitutes).

## SEO fields

| Field | Rule |
|---|---|
| URL handle | Built from the NEW title. Lowercase, hyphenated, 5–6 words, no stop words, no brand name, never the competitor's handle or `dress-231` [AB 7.2 @7:10]. |
| Page title | 50–60 characters, main keyword natural. |
| Meta description | 150–160 characters. Generate 3 options, pick one. |
| Tags | 10–15 descriptive tags, lowercase: category, style, occasion, colour, fabric, fit. Source URLs and ownership markers belong only in private metafields; never create system tags such as `source:`. |

## One resolved conflict

Haider's prompt ends the description with a call to action; AB 7.2 bans CTA phrases inside descriptions. **AB wins** — slot 5 is a soft brand line, not a CTA.

## Fit & size / Fabric & care metafields (theme accordion rows)

Write both as `rich_text_field` on `custom.fit_details` and `custom.fabric_care` in the same `metafieldsSet` call as the category metafields. Never repeat this content in the description. Only verified facts; drop any bullet without a source.

Ondine's shared BODY size guide is customer guidance outside these product-specific metafields. Do not present its body values as garment measurements, fit facts or supplier-to-UK equivalence. Keep verified product length, fit and model facts here when available.

Structure (bold paragraph heading, then an unordered list):

- `fit_details`: **Fit** → silhouette / waist / pockets / where the hem falls (length in cm if the source states it) / lining; **Details** → every construction bullet that would otherwise be a Details list in the description (neckline, closure, sleeves, skirt, hem); **Model wears** → the live fit note `Model is [height] and wears UK [size]` (omit the whole heading when the fit note is not verifiable).
- `fabric_care`: **Composition** → `Main: …`, plus lining if stated; **Fabric** → belt, trims, notable construction; **Care** → the source care line.

Rich text JSON skeleton:

```json
{"type":"root","children":[
  {"type":"paragraph","children":[{"type":"text","value":"Fit","bold":true}]},
  {"type":"list","listType":"unordered","children":[
    {"type":"list-item","children":[{"type":"text","value":"…"}]}
  ]}
]}
```
