import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assignMedia, galleryMedia, mergeListing, newGallery, numericId, parseGallery, reconcileGallery, reorderMedia, saveInput, validateGallery, type Product, type ListingManifest } from '../src/gallery.ts';
import { compileHandoff, readProductSnapshot } from '../scripts/listing-handoff.ts';
const product: Product = JSON.parse(readFileSync(new URL('./fixtures/ondine-product.json', import.meta.url), 'utf8'));
const manifest: ListingManifest = JSON.parse(readFileSync(new URL('./fixtures/ondine-listing.json', import.meta.url), 'utf8'));
const all = product.media.map(m => numericId(m.id));
const mapped = () => mergeListing(newGallery(product), product, manifest);
test('approved listing maps six green photos and the three existing colour heroes', () => {
 const g = mapped(); assert.deepEqual(g.groups.map(g => g.mediaIds.length), [6,1,1,1]);
 assert.equal(g.enabled, false); validateGallery(g, product);
 for (const group of g.groups) assert.deepEqual(galleryMedia({...g,enabled:true},group.valueId,all).ids,group.mediaIds);
});
test('moves, shared images and explicit copying produce ordered deduplicated galleries', () => {
 let g=mapped();const [green,burgundy]=g.groups;
 g=assignMedia(g,'shared',[green.mediaIds[5]]);
 g=assignMedia(g,burgundy.valueId,[green.mediaIds[0]],'copy');
 assert.equal(g.groups[0].mediaIds.length,5);assert.equal(g.groups[1].mediaIds.length,2);
 validateGallery(g,product);
 assert.deepEqual(galleryMedia({...g,enabled:true},burgundy.valueId,all).ids,[all[6],all[0],all[5]]);
 g=reorderMedia(g,burgundy.valueId,1,0);assert.equal(g.groups[1].mediaIds[0],all[0]);
});
test('disabled and missing colour images retain native gallery, unassigned is opt-in',()=>{
 let g=mapped(); assert.deepEqual(galleryMedia(g,g.groups[0].valueId,all),{ids:all,fallback:true});
 g.enabled=true;g.groups[1].mediaIds=[];
 assert.equal(galleryMedia(g,g.groups[1].valueId,all).fallback,true);
 g.hideUnassigned=false;
 assert.deepEqual(galleryMedia(g,g.groups[0].valueId,all).ids,[...all.slice(0,6),all[6]]);
});
test('foreign, unfinished, duplicated and incomplete enabled assignments are rejected',()=>{
 const g=mapped();g.enabled=true;
 assert.throws(()=>validateGallery({...g,productId:'gid://shopify/Product/1'},product),/different product/);
 assert.throws(()=>validateGallery({...g,sharedMediaIds:['9']},product),/no longer belongs/);
 const pending=structuredClone(product);pending.media[0].status='PROCESSING';
 assert.throws(()=>validateGallery(g,pending),/fully uploaded/);
 const duplicate=structuredClone(g);duplicate.groups[0].mediaIds.push(all[0]);assert.throws(()=>validateGallery(duplicate,product),/duplicate/);
 const missing=structuredClone(g);missing.groups[1].mediaIds=[];assert.throws(()=>validateGallery(missing,product),/at least one/);
 const withVideo=structuredClone(product);withVideo.media.push({id:'gid://shopify/Video/123',mediaContentType:'VIDEO',status:'READY',alt:null,preview:null});
 assert.doesNotThrow(()=>validateGallery(g,withVideo));
});
test('option renames retain assignments; deleted media and new colours disable pending review',()=>{
 const g={...mapped(),enabled:true};const renamed=structuredClone(product);renamed.options[0].optionValues[0].name='Forest';
 const r=reconcileGallery(g,renamed);assert.equal(r.gallery.groups[0].name,'Forest');assert.equal(r.gallery.enabled,true);
 const changed=structuredClone(renamed);changed.media.shift();changed.options[0].optionValues.push({id:'gid://shopify/ProductOptionValue/111',name:'Rose'});
 const next=reconcileGallery(g,changed);assert.equal(next.gallery.enabled,false);assert.equal(next.gallery.groups.at(-1)?.mediaIds.length,0);assert.equal(next.notices.length,2);
});
test('listing handoff preserves manual order and is idempotent for existing photo IDs',()=>{
 let g=mapped();g=reorderMedia(g,g.groups[0].valueId,5,0);
 assert.deepEqual(mergeListing(g,product,manifest).groups,g.groups);
 const payload=compileHandoff(product,manifest);const field=payload.variables.metafields[0];
 assert.equal(field.compareDigest,null);assert.equal(field.namespace,'ondine_gallery');assert.equal(JSON.parse(field.value).enabled,false);
 assert.match(payload.query,/metafieldsSet/);assert.doesNotMatch(payload.query,/productUpdate|productSet|publish/);
});
test('listing rejects live products, wrong product, duplicate slots and unknown colours',()=>{
 assert.throws(()=>compileHandoff({...product,status:'ACTIVE'},manifest),/draft/);
 assert.throws(()=>compileHandoff(product,{...manifest,productId:'gid://shopify/Product/1'}),/does not match/);
 assert.throws(()=>compileHandoff(product,{...manifest,assets:[...manifest.assets,manifest.assets[0]]}),/duplicate/);
 assert.throws(()=>compileHandoff(product,{...manifest,assets:[{...manifest.assets[0],valueId:'unknown'}]}),/unknown colour/);
});
test('malformed saved data stays rejected and saves carry compare-and-set digest',()=>{
 assert.throws(()=>parseGallery('{'),/preserved/);assert.throws(()=>parseGallery('{"version":2}'),/preserved/);
 const field=saveInput(mapped(),product,'current-digest','2026-09-07T12:00:00Z');assert.equal(field.compareDigest,'current-digest');assert.equal(JSON.parse(field.value).revision,1);
});

test('listing accepts connector JSON and rejects incomplete media pages',()=>{
 const raw={data:{product:{...product,media:{nodes:product.media,pageInfo:{hasNextPage:false}}}}};
 assert.deepEqual(readProductSnapshot(raw),product);
 raw.data.product.media.pageInfo.hasNextPage=true;
 assert.throws(()=>readProductSnapshot(raw),/all media pages/);
});
