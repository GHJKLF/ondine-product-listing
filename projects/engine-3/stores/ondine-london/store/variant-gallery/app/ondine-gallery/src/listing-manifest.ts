import { numericId, SHOTS, type ListingManifest, type Product, type Shot } from './gallery.ts';

export type ColourManifest = {
  schema_version: 1 | 2;
  product_id: string;
  option_name: string;
  upload_approved: boolean;
  upload_authorization?: { mode: 'DIRECT_TO_DRAFT'; instruction: string };
  assets: {
    product_id: string;
    colour: string;
    shot: string;
    shot_order: number;
    approval_status: string;
    qa_status?: 'accepted' | 'pending' | 'rejected';
    uploaded: boolean;
    shopify_media_id?: string;
  }[];
};
const slotNames: Record<string, Shot> = { front:'front', 'second-model':'second-model', back:'back', 'side-movement':'movement', movement:'movement', detail:'detail', lifestyle:'lifestyle', 'ghost-flat':'ghost', ghost:'ghost' };

/** Convert checked colour/shot records into Shopify option IDs without publishing. */
export function convertColourManifest(product: Product, source: ColourManifest): ListingManifest {
  if (!source || ![1, 2].includes(source.schema_version) || typeof source.product_id !== 'string'
    || numericId(source.product_id) !== numericId(product.id)) throw new Error('The colour manifest belongs to a different product or version.');
  if (product.status !== 'DRAFT') throw new Error('The listing handoff accepts draft products only.');
  if (source.upload_approved !== true) throw new Error('The selected colour galleries need upload authorization.');
  const directToDraft = source.upload_authorization?.mode === 'DIRECT_TO_DRAFT';
  if (source.upload_authorization && (!directToDraft || typeof source.upload_authorization.instruction !== 'string' || !source.upload_authorization.instruction.trim())) {
    throw new Error('Record the user instruction authorizing direct draft uploads.');
  }
  if (directToDraft && source.schema_version !== 2) throw new Error('Direct draft uploads require the current seven-shot manifest.');
  const options = product.options.filter(option => option.name === source.option_name);
  if (options.length !== 1) throw new Error('The manifest must name exactly one current Shopify grouping option.');
  const option = options[0];
  const shots: readonly Shot[] = source.schema_version === 1 ? SHOTS.filter(shot => shot !== 'second-model') : SHOTS;
  if (!option.optionValues.length || !Array.isArray(source.assets) || source.assets.length !== option.optionValues.length * shots.length) {
    throw new Error('Automatic gallery setup requires all selected shots for the manifest version for every colour.');
  }
  const usedMedia = new Set<string>();
  const slots = new Set<string>();
  const assets = source.assets.map(asset => {
    if (!asset || (directToDraft ? asset.qa_status !== 'accepted' : asset.approval_status !== 'approved') || asset.uploaded !== true) {
      throw new Error('Every selected photo must pass the applicable internal QA or historical review, and its upload must be verified.');
    }
    if (typeof asset.product_id !== 'string' || numericId(asset.product_id) !== numericId(product.id)) throw new Error('An asset belongs to a different product.');
    const value = option.optionValues.find(value => value.name === asset.colour);
    if (!value) throw new Error(`Unknown Shopify colour: ${asset.colour}.`);
    const shot = slotNames[asset.shot];
    if (!shot || !shots.includes(shot) || asset.shot_order !== shots.indexOf(shot) + 1) throw new Error('A selected shot name and order disagree.');
    if (!asset.shopify_media_id || !/^gid:\/\/shopify\/MediaImage\/\d+$/.test(asset.shopify_media_id)) throw new Error('Record the verified Shopify MediaImage ID for every selected photo.');
    const id = numericId(asset.shopify_media_id);
    const media = product.media.find(media => media.id === asset.shopify_media_id);
    if (!media || media.status !== 'READY' || media.mediaContentType !== 'IMAGE') throw new Error('A selected photo is not a ready image attached to this product.');
    const slot = `${value.id}:${shot}`;
    if (usedMedia.has(id) || slots.has(slot)) throw new Error('The colour manifest contains a duplicate photo or colour/shot slot.');
    usedMedia.add(id); slots.add(slot);
    return { mediaId: asset.shopify_media_id, valueId: value.id, shot };
  });
  for (const value of option.optionValues) for (const shot of shots) {
    if (!slots.has(`${value.id}:${shot}`)) throw new Error(`Missing ${shot} for ${value.name}.`);
  }
  return { version:1, productId:product.id, optionId:option.id, assets };
}
