# Product listing handoff

The app works with images already uploaded to Shopify. The listing process remains responsible for generating photos with ChatGPT’s built-in image generation, obtaining the required image approval, uploading them to the correct draft product, and recording the resulting Shopify IDs. This app does not generate or upload photos and does not publish products.

The canonical product-listing reference calls this compiler after approved media upload and verification. The 7 September dress run completed this handoff with 24 images, six for each of four colours. Saved product configuration and storefront embed activation are separate states.

## Handoff sequence

1. Read the product and all media pages with the validated `PRODUCT_QUERY` in `src/shopify.ts`. Include current options and `ondine_gallery.configuration` with its `compareDigest`.
2. Use the listing run’s `colour-gallery-manifest.json`, with upload approval recorded and all selected assets approved, uploaded and carrying verified Shopify MediaImage IDs. The compiler maps exact colour names to current option-value IDs. It also accepts the lower-level version-1 manifest below. Never guess colour from image position or translate arbitrary filenames.
3. Compile the snapshot and manifest. The command accepts a normalized product object or a complete GraphQL `{data:{product:...}}` response. If media pagination is incomplete, it stops; collect all pages into the normalized product first.
4. Execute the resulting `metafieldsSet` operation with the listing workflow’s existing authenticated Shopify connector, following that connector’s schema/validation workflow. The compiler itself has no credentials and performs no network writes.
5. Re-read the metafield and compare the returned value with the compiled value. If the compare digest is stale, reload and recompile; do not force an overwrite. If a response is uncertain, read back before retrying.
6. Record the handoff in the listing run’s own record. Existing sheet statuses should follow the existing workflow; a saved gallery is not evidence that a product has been published.

```sh
node scripts/listing-handoff.ts PRODUCT_SNAPSHOT.json APPROVED_MEDIA_MANIFEST.json > REVIEWABLE_GRAPHQL_PAYLOAD.json
```

The examples in `tests/fixtures/ondine-product.json` and `ondine-listing.json` capture the nine existing photos read on 7 September 2026. They are test fixtures, not a fresh snapshot for a production write.

## Canonical listing manifest

The normal workflow supplies `schema_version: 1`, `product_id`, exact `option_name`, `upload_approved: true` and `assets`. Each asset must have `product_id`, exact `colour`, `shot`, `shot_order` from 1 to 6, `approval_status: "approved"`, `uploaded: true` and the full `shopify_media_id`. Preserve the run’s paths, dimensions, hashes, approval record and other evidence; the converter ignores those extra fields.

Every current colour must contain all six unique shots. `side-movement` maps to `movement`; `ghost-flat` maps to `ghost`. Missing, duplicate, unapproved, unuploaded, foreign-product or unfinished media causes the compiler to stop before producing a write payload.

New complete configurations are enabled automatically. A previously staged listing configuration is also enabled when complete. Existing manual assignments and ordering are retained. An explicit manual disable remains disabled across repeated handoffs, so automation does not undo a merchant decision.

The embed must still be installed and enabled on the intended theme. Product-level `enabled: true` does not mean the storefront is live.

The optional Horizon loading integration reads this same metafield while rendering the selected colour. Once installed and enabled on a product template, future listings using that template require no extra grouping or image-management step. Its **Load selected colour photos first** setting and the app embed are enabled on unpublished test theme `193873969418` only. Live activation remains separate. See `../theme-integration/README.md` for theme installation and rollback.

## Lower-level manifest format

```json
{
  "version": 1,
  "productId": "gid://shopify/Product/10613327364362",
  "optionId": "gid://shopify/ProductOption/13356538167562",
  "assets": [
    {
      "mediaId": "gid://shopify/MediaImage/50990765211914",
      "valueId": "gid://shopify/ProductOptionValue/9202456887562",
      "shot": "front"
    }
  ],
  "sharedMediaIds": []
}
```

Supported shot names and initial ordering are `front`, `back`, `movement`, `detail`, `lifestyle`, `ghost`. Six photos per colour is a target, not an assertion that those photos already exist. A one-photo group displays one photo plus shared images.

The compiler accepts DRAFT products only, checks every new photo against ready images on that product, and rejects duplicate photo IDs or duplicate colour/shot slots in one manifest. It preserves existing assignments and manual ordering; repeated media IDs already owned by any saved group stay where the merchant put them. New approved photos are appended in shot order. To intentionally reassign an existing photo, use the manager.

The lower-level format supports partial image sets and does not assert approval or six-shot completion. New configurations from this format start disabled. A merchant can enable the gallery after reviewing groups with at least one ready image per colour; this format preserves existing enablement.

New listings use colour-manifest schema_version 2 with seven ordered shots: front, second-model, back, side-movement, detail, lifestyle, ghost-flat. Version 1 continues accepting the historical six-shot sequence. Existing manual gallery configurations remain unchanged.
