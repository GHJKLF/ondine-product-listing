import { SHOP, parseGallery, saveInput, type Product, type Gallery, type Media } from './gallery.ts';

export const PRODUCTS_QUERY = "query GalleryProducts($query: String, $after: String) { shop { name myshopifyDomain } products(first: 30, after: $after, query: $query, sortKey: UPDATED_AT, reverse: true) { nodes { id title status featuredMedia { preview { image { url altText } } } metafield(namespace: \"ondine_gallery\", key: \"configuration\") { value compareDigest } } pageInfo { hasNextPage endCursor } } }";
export const PRODUCT_QUERY = "query GalleryProduct($id: ID!, $after: String) { product(id: $id) { id title handle status options { id name position optionValues { id name } } media(first: 100, after: $after) { nodes { id mediaContentType status alt preview { image { url width height altText } } ... on MediaImage { image { url width height altText } } } pageInfo { hasNextPage endCursor } } metafield(namespace: \"ondine_gallery\", key: \"configuration\") { id value compareDigest } } }";
export const SAVE_MUTATION = "mutation SaveGallery($metafields: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $metafields) { metafields { id namespace key value compareDigest } userErrors { field message code } } }";
const SHOP_QUERY = 'query GalleryShop { shop { name myshopifyDomain } }';

type Result<T> = { data?: T; errors?: { message: string }[] };
export type Query = <T>(document: string, options?: { variables?: Record<string, unknown> }) => Promise<Result<T>>;
type ProductResponse = Omit<Product, 'media'> & { media: { nodes: Media[]; pageInfo: { hasNextPage: boolean; endCursor: string | null } } };
export type ProductRow = { id: string; title: string; status: string; featuredMedia: { preview: { image: { url: string; altText: string | null } | null } | null } | null;
  metafield: { value: string; compareDigest: string } | null };

export function createShopifyClient(query: Query) {
  async function request<T>(document: string, variables: Record<string, unknown> = {}): Promise<T> {
    const response = await query<T>(document, { variables });
    if (response.errors?.length) throw new Error(response.errors.map(e => e.message).join(' '));
    if (!response.data) throw new Error('Shopify returned no data. Try reloading.');
    return response.data;
  }
  async function verifyShop() {
    const { shop } = await request<{ shop: { name: string; myshopifyDomain: string } }>(SHOP_QUERY);
    if (shop.myshopifyDomain !== SHOP) throw new Error('This internal app is configured for Ondine London only.');
  }
  async function listProducts(search = '', after: string | null = null) {
    const result = await request<{ shop: { myshopifyDomain: string }; products: { nodes: ProductRow[]; pageInfo: { hasNextPage: boolean; endCursor: string | null } } }>(PRODUCTS_QUERY, { query: search || null, after });
    if (result.shop.myshopifyDomain !== SHOP) throw new Error('This internal app is configured for Ondine London only.');
    return result.products;
  }
  async function loadProduct(id: string): Promise<Product> {
    if (!/^gid:\/\/shopify\/Product\/\d+$/.test(id)) throw new Error('Choose a valid Shopify product.');
    await verifyShop();
    let after: string | null = null;
    let product: Product | null = null;
    let snapshot = '';
    const cursors = new Set<string>();
    do {
      const result: { product: ProductResponse | null } = await request(PRODUCT_QUERY, { id, after });
      if (!result.product) throw new Error('This product is no longer available.');
      const page = result.product;
      const fingerprint = JSON.stringify([page.options, page.metafield?.compareDigest ?? null]);
      if (product && fingerprint !== snapshot) throw new Error('The product changed while loading. Reload to get the latest version.');
      if (!product) { product = { ...page, media: [] }; snapshot = fingerprint; }
      product.media.push(...page.media.nodes);
      after = page.media.pageInfo.hasNextPage ? page.media.pageInfo.endCursor : null;
      if (page.media.pageInfo.hasNextPage && (!after || cursors.has(after))) throw new Error('Shopify media pagination did not advance.');
      if (after) cursors.add(after);
      if (product.media.length > 3000) throw new Error('This product exceeds the supported media limit.');
    } while (after);
    return product!;
  }
  async function saveGallery(gallery: Gallery, digest: string | null): Promise<Product> {
    const product = await loadProduct(gallery.productId);
    if ((product.metafield?.compareDigest ?? null) !== digest) throw new Error('Someone changed this gallery. Reload it before saving; your edits have not overwritten theirs.');
    const input = saveInput(gallery, product, digest);
    let failure: unknown;
    try {
      const result = await request<{ metafieldsSet: { userErrors: { message: string; code: string }[] } }>(SAVE_MUTATION, { metafields: [input] });
      if (result.metafieldsSet.userErrors.length) throw new Error(result.metafieldsSet.userErrors.map(e => e.message).join(' '));
    } catch (error) { failure = error; }
    const verified = await loadProduct(product.id);
    if (verified.metafield?.value !== input.value) {
      if (failure) throw failure;
      throw new Error('The saved gallery could not be verified. Reload before retrying.');
    }
    parseGallery(verified.metafield.value);
    return verified;
  }
  return { listProducts, loadProduct, saveGallery };
}
