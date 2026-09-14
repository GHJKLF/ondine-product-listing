export const NAMESPACE = 'ondine_gallery';
export const KEY = 'configuration';
export const SHOP = 'zfrbm1-y6.myshopify.com';
export const SHOTS = ['front', 'second-model', 'back', 'movement', 'detail', 'lifestyle', 'ghost'] as const;
export type Shot = typeof SHOTS[number];
export type OptionValue = { id: string; name: string };
export type Option = { id: string; name: string; position: number; optionValues: OptionValue[] };
export type Media = { id: string; mediaContentType: string; status: string; alt: string | null;
  preview: { image: { url: string; altText?: string | null; width?: number; height?: number } | null } | null };
export type Product = { id: string; title: string; handle: string; status: string; options: Option[]; media: Media[];
  metafield: { id?: string; value: string; compareDigest: string } | null };
export type Group = { valueId: string; name: string; mediaIds: string[] };
export type Gallery = { version: 1; productId: string; optionId: string; optionName: string; optionPosition: number;
  enabled: boolean; hideUnassigned: boolean; groups: Group[]; sharedMediaIds: string[];
  revision: number; updatedAt: string; source: 'manual' | 'listing' };
export type ListingManifest = { version: 1; productId: string; optionId: string;
  assets: { mediaId: string; valueId: string; shot: Shot }[]; sharedMediaIds?: string[] };

export function numericId(id: string): string {
  if (typeof id !== 'string' || !/^(?:gid:\/\/shopify\/(?:MediaImage|ProductOptionValue|Product)\/)?\d+$/.test(id)) {
    throw new Error('Invalid Shopify identifier.');
  }
  return id.split('/').pop()!;
}

export function newGallery(product: Product, optionId?: string): Gallery {
  const option = optionId ? product.options.find(o => o.id === optionId)
    : product.options.find(o => /^(colour|color)$/i.test(o.name));
  if (!option) throw new Error('Choose the product option that identifies its image groups.');
  return { version: 1, productId: product.id, optionId: option.id, optionName: option.name,
    optionPosition: option.position, enabled: false, hideUnassigned: true,
    groups: option.optionValues.map(v => ({ valueId: v.id, name: v.name, mediaIds: [] })),
    sharedMediaIds: [], revision: 0, updatedAt: '', source: 'manual' };
}

export function parseGallery(raw: string): Gallery {
  let value: Gallery;
  try { value = JSON.parse(raw); } catch { throw new Error('The saved gallery is unreadable. Its data has been preserved.'); }
  if (!value || value.version !== 1 || typeof value.productId !== 'string' || typeof value.optionId !== 'string'
    || typeof value.optionName !== 'string' || !Number.isInteger(value.optionPosition) || value.optionPosition < 1
    || value.optionPosition > 3 || typeof value.enabled !== 'boolean' || typeof value.hideUnassigned !== 'boolean'
    || !Number.isInteger(value.revision) || value.revision < 0 || typeof value.updatedAt !== 'string'
    || !['manual', 'listing'].includes(value.source) || !Array.isArray(value.groups)
    || !Array.isArray(value.sharedMediaIds) || value.groups.length > 1000
    || value.groups.some(g => !g || typeof g.valueId !== 'string' || !/^gid:\/\/shopify\/ProductOptionValue\/\d+$/.test(g.valueId) || typeof g.name !== 'string'
      || !Array.isArray(g.mediaIds) || g.mediaIds.some(id => typeof id !== 'string'))
    || value.sharedMediaIds.some(id => typeof id !== 'string')) {
    throw new Error('Unsupported gallery configuration. Its data has been preserved.');
  }
  return value;
}

export function validateGallery(gallery: Gallery, product: Product): void {
  parseGallery(JSON.stringify(gallery));
  if (gallery.productId !== product.id) throw new Error('This gallery belongs to a different product.');
  const option = product.options.find(o => o.id === gallery.optionId);
  if (!option || option.position !== gallery.optionPosition) throw new Error('The grouping option changed. Reload the product.');
  const values = new Map(option.optionValues.map(v => [v.id, v.name]));
  const seen = new Set<string>();
  const media = new Map(product.media.filter(m => m.mediaContentType === 'IMAGE').map(m => [numericId(m.id), m]));
  const validateIds = (ids: string[]) => {
    if (new Set(ids).size !== ids.length) throw new Error('A group contains duplicate photos.');
    for (const id of ids) {
      if (!/^\d+$/.test(id)) throw new Error('Gallery media IDs must be numeric Shopify IDs.');
      const image = media.get(id);
      if (!image) throw new Error('An assigned photo no longer belongs to this product. Reload and review it.');
      if (image.mediaContentType !== 'IMAGE' || image.status !== 'READY') throw new Error('Only fully uploaded images can be assigned.');
    }
  };
  validateIds(gallery.sharedMediaIds);
  for (const group of gallery.groups) {
    if (!values.has(group.valueId) || seen.has(group.valueId)) throw new Error('A colour group is missing or duplicated. Reload the product.');
    seen.add(group.valueId);
    validateIds(group.mediaIds);
    if (group.mediaIds.some(id => gallery.sharedMediaIds.includes(id))) throw new Error('Shared photos must not also be assigned to a colour.');
    if (gallery.enabled && group.mediaIds.length === 0) throw new Error(`Assign at least one photo to ${group.name} before enabling the gallery.`);
  }
  if (values.size !== seen.size) throw new Error('The product has a new option value. Reload and assign its photos.');
}

export function reconcileGallery(gallery: Gallery, product: Product): { gallery: Gallery; notices: string[] } {
  if (gallery.productId !== product.id) throw new Error('This gallery belongs to a different product.');
  const option = product.options.find(o => o.id === gallery.optionId);
  if (!option) throw new Error('The saved grouping option was deleted. Review this product before changing its configuration.');
  const readyIds = new Set(product.media.filter(m => m.mediaContentType === 'IMAGE' && m.status === 'READY').map(m => numericId(m.id)));
  const notices: string[] = [];
  const clean = (ids: string[]) => ids.filter(id => readyIds.has(id));
  const groups = option.optionValues.map(v => {
    const old = gallery.groups.find(g => g.valueId === v.id);
    if (!old) notices.push(`${v.name} needs an image group.`);
    const mediaIds = clean(old?.mediaIds || []);
    if (old && old.mediaIds.length !== mediaIds.length) notices.push(`${v.name} has removed or unfinished photos.`);
    return { valueId: v.id, name: v.name, mediaIds };
  });
  if (gallery.groups.some(g => !groups.some(next => next.valueId === g.valueId))) notices.push('A removed option value was excluded.');
  const sharedMediaIds = clean(gallery.sharedMediaIds);
  if (sharedMediaIds.length !== gallery.sharedMediaIds.length) notices.push('A shared photo was removed or is unfinished.');
  return { gallery: { ...gallery, optionPosition: option.position, optionName: option.name, groups, sharedMediaIds,
    enabled: gallery.enabled && groups.every(g => g.mediaIds.length > 0) && notices.length === 0 }, notices };
}

export function assignMedia(gallery: Gallery, target: string, ids: string[], mode: 'move' | 'copy' = 'move'): Gallery {
  const next = structuredClone(gallery);
  const list = target === 'shared' ? next.sharedMediaIds : next.groups.find(g => g.valueId === target)?.mediaIds;
  if (!list) throw new Error('Choose an image group.');
  const unique = [...new Set(ids.map(numericId))];
  if (mode === 'move' || target === 'shared') for (const group of next.groups) group.mediaIds = group.mediaIds.filter(id => !unique.includes(id));
  next.sharedMediaIds = next.sharedMediaIds.filter(id => !unique.includes(id));
  const destination = target === 'shared' ? next.sharedMediaIds : next.groups.find(g => g.valueId === target)!.mediaIds;
  destination.push(...unique.filter(id => !destination.includes(id)));
  next.source = 'manual';
  return next;
}

export function removeMedia(gallery: Gallery, target: string, id: string): Gallery {
  const next = structuredClone(gallery);
  if (target === 'shared') next.sharedMediaIds = next.sharedMediaIds.filter(value => value !== id);
  else {
    const group = next.groups.find(g => g.valueId === target);
    if (group) group.mediaIds = group.mediaIds.filter(value => value !== id);
  }
  next.source = 'manual';
  return next;
}

export function reorderMedia(gallery: Gallery, target: string, from: number, to: number): Gallery {
  const next = structuredClone(gallery);
  const list = target === 'shared' ? next.sharedMediaIds : next.groups.find(g => g.valueId === target)?.mediaIds;
  if (!list || !Number.isInteger(from) || !Number.isInteger(to) || from < 0 || to < 0 || from >= list.length || to >= list.length) return next;
  list.splice(to, 0, list.splice(from, 1)[0]);
  next.source = 'manual';
  return next;
}

export function galleryMedia(gallery: Gallery, valueId: string, availableIds: string[]): { ids: string[]; fallback: boolean } {
  const ready = new Set(availableIds);
  const group = gallery.groups.find(g => numericId(g.valueId) === numericId(valueId));
  const assigned = group?.mediaIds.filter(id => ready.has(id)) || [];
  if (!gallery.enabled || !assigned.length) return { ids: [...availableIds], fallback: true };
  const owned = new Set([...gallery.groups.flatMap(g => g.mediaIds), ...gallery.sharedMediaIds]);
  const shared = gallery.sharedMediaIds.filter(id => ready.has(id));
  const unassigned = gallery.hideUnassigned ? [] : availableIds.filter(id => !owned.has(id));
  return { ids: [...new Set([...assigned, ...shared, ...unassigned])], fallback: false };
}

export function mergeListing(gallery: Gallery, product: Product, manifest: ListingManifest): Gallery {
  if (product.status !== 'DRAFT') throw new Error('The listing handoff accepts draft products only.');
  if (manifest.version !== 1 || manifest.productId !== product.id || manifest.optionId !== gallery.optionId || !Array.isArray(manifest.assets)) {
    throw new Error('The listing manifest does not match this product and option.');
  }
  const next = structuredClone(gallery);
  const claimed = new Set([...next.groups.flatMap(g => g.mediaIds), ...next.sharedMediaIds]);
  const manifestIds = new Set<string>();
  const manifestSlots = new Set<string>();
  const ordered = [...manifest.assets].sort((a, b) => SHOTS.indexOf(a.shot) - SHOTS.indexOf(b.shot));
  for (const asset of ordered) {
    const id = numericId(asset.mediaId);
    const slotKey = asset.valueId + ':' + asset.shot;
    if (!SHOTS.includes(asset.shot) || manifestIds.has(id) || manifestSlots.has(slotKey)) throw new Error('The listing manifest has duplicate photos or shot slots.');
    manifestIds.add(id); manifestSlots.add(slotKey);
    const group = next.groups.find(g => g.valueId === asset.valueId);
    if (!group) throw new Error('The listing manifest references an unknown colour.');
    if (claimed.has(id)) continue;
    group.mediaIds.push(id); claimed.add(id);
  }
  for (const rawId of manifest.sharedMediaIds || []) {
    const id = numericId(rawId);
    if (manifestIds.has(id)) throw new Error('A listing photo cannot be both shared and colour-specific.');
    if (!claimed.has(id)) { next.sharedMediaIds.push(id); claimed.add(id); }
  }
  next.source = 'listing';
  validateGallery(next, product);
  return next;
}

export function saveInput(gallery: Gallery, product: Product, digest: string | null, now = new Date().toISOString()) {
  validateGallery(gallery, product);
  if (digest !== null && (typeof digest !== 'string' || !digest)) throw new Error('Reload before saving this gallery.');
  const option = product.options.find(o => o.id === gallery.optionId)!;
  const next = { ...gallery, optionName: option.name, groups: gallery.groups.map(g => ({ ...g,
    name: option.optionValues.find(v => v.id === g.valueId)!.name })), revision: gallery.revision + 1, updatedAt: now };
  return { ownerId: product.id, namespace: NAMESPACE, key: KEY, type: 'json', value: JSON.stringify(next), compareDigest: digest };
}
