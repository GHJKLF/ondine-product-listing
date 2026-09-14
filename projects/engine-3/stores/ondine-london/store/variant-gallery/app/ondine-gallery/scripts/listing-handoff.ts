import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mergeListing, newGallery, parseGallery, saveInput, type Product, type ListingManifest } from '../src/gallery.ts';
import { convertColourManifest, type ColourManifest } from '../src/listing-manifest.ts';
import { SAVE_MUTATION } from '../src/shopify.ts';

export function readProductSnapshot(input: unknown): Product {
  const raw = input as { data?: { product?: unknown }; product?: unknown };
  const product = (raw?.data?.product || raw?.product || raw) as Omit<Product, 'media'> & { media: Product['media'] | { nodes?: Product['media']; pageInfo?: { hasNextPage: boolean } } };
  if (!product || !Array.isArray(product.options)) throw new Error('The snapshot must contain a Shopify product and its options.');
  if (Array.isArray(product.media)) return { ...product, media: product.media };
  if (!Array.isArray(product.media?.nodes) || !product.media.pageInfo || product.media.pageInfo.hasNextPage) {
    throw new Error('Load all media pages before compiling the listing handoff.');
  }
  return { ...product, media: product.media.nodes };
}

export function compileHandoff(product: Product, input: ListingManifest | ColourManifest) {
  const completeListing = 'schema_version' in input;
  const manifest = completeListing ? convertColourManifest(product, input) : input;
  const current = product.metafield ? parseGallery(product.metafield.value) : newGallery(product, manifest.optionId);
  const gallery = mergeListing(current, product, manifest);
  // A completed approved listing enables a new gallery. Preserve an explicit manual disable.
  if (completeListing && (!product.metafield || current.enabled || current.source === 'listing')) gallery.enabled = true;
  if (completeListing && product.metafield && !current.enabled && current.source === 'manual') gallery.source = 'manual';
  return { query: SAVE_MUTATION, variables: { metafields: [saveInput(gallery, product, product.metafield?.compareDigest ?? null)] } };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [productPath, manifestPath] = process.argv.slice(2);
  if (!productPath || !manifestPath) {
    console.error('Usage: node scripts/listing-handoff.ts PRODUCT_SNAPSHOT.json APPROVED_MEDIA_MANIFEST.json');
    process.exitCode = 1;
  } else {
    try {
      const product = readProductSnapshot(JSON.parse(await readFile(productPath, 'utf8')));
      const manifest: ListingManifest | ColourManifest = JSON.parse(await readFile(manifestPath, 'utf8'));
      process.stdout.write(JSON.stringify(compileHandoff(product, manifest), null, 2) + '\n');
    } catch (error) { console.error(error instanceof Error ? error.message : 'Invalid handoff.'); process.exitCode = 1; }
  }
}
