import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { convertColourManifest, type ColourManifest } from '../src/listing-manifest.ts';
import { compileHandoff } from '../scripts/listing-handoff.ts';
import { newGallery, SHOTS, type Product } from '../src/gallery.ts';
function complete(version: 1 | 2 = 2) {
 const product:Product=JSON.parse(readFileSync(new URL('./fixtures/ondine-product.json',import.meta.url),'utf8'));
 product.media=[];
 const source:ColourManifest={schema_version:version,product_id:product.id.split('/').pop()!,option_name:'Colour',upload_approved:true,assets:[]};
 for(const [colourIndex,colour] of product.options[0].optionValues.entries()) for(const [i,shot] of (version === 1 ? SHOTS.filter(shot => shot !== 'second-model') : SHOTS).entries()){
  const id=`gid://shopify/MediaImage/${1000+colourIndex*7+i}`;
  product.media.push({id,mediaContentType:'IMAGE',status:'READY',alt:null,preview:null});
  source.assets.push({product_id:source.product_id,colour:colour.name,shot:shot==='movement'?'side-movement':shot==='ghost'?'ghost-flat':shot,shot_order:i+1,approval_status:'approved',uploaded:true,shopify_media_id:id});
 }
 return {product,source};
}
test('real listing format converts exact colours and shot aliases, then auto-enables all four groups',()=>{
 const {product,source}=complete();source.assets.reverse();const converted=convertColourManifest(product,source);
 assert.equal(converted.assets.length,28);assert.equal(converted.optionId,product.options[0].id);
 const payload=compileHandoff(product,source);const gallery=JSON.parse(payload.variables.metafields[0].value);
 assert.equal(gallery.enabled,true);assert.deepEqual(gallery.groups.map((g:any)=>g.mediaIds.length),[7,7,7,7]);
 assert.deepEqual(gallery.groups[0].mediaIds,['1000','1001','1002','1003','1004','1005','1006']);assert.equal(payload.variables.metafields[0].compareDigest,null);
});
test('pending approval, pending upload and absent media IDs never enable a gallery',()=>{
 for(const change of [(s:ColourManifest)=>s.upload_approved=false,(s:ColourManifest)=>s.assets[0].approval_status='pending_visual_review',(s:ColourManifest)=>s.assets[0].uploaded=false,(s:ColourManifest)=>delete s.assets[0].shopify_media_id]){
  const {product,source}=complete();change(source);assert.throws(()=>compileHandoff(product,source));
 }
});
test('missing, duplicate, foreign, not-ready and wrong-order images are rejected',()=>{
 const changes=[(p:Product,s:ColourManifest)=>s.assets.pop(),(p:Product,s:ColourManifest)=>s.assets[1]={...s.assets[0]},(p:Product,s:ColourManifest)=>s.assets[0].product_id='123',(p:Product,s:ColourManifest)=>p.media[0].status='PROCESSING',(p:Product,s:ColourManifest)=>s.assets[0].shot_order=2,(p:Product,s:ColourManifest)=>s.assets[0].colour='Guess Blue'];
 for(const change of changes){const {product,source}=complete();change(product,source);assert.throws(()=>compileHandoff(product,source));}
});
test('repeat complete handoff preserves manual order and explicit manual disable',()=>{
 const {product,source}=complete();let saved=JSON.parse(compileHandoff(product,source).variables.metafields[0].value);
 saved.groups[0].mediaIds.reverse();saved.enabled=false;saved.source='manual';product.metafield={value:JSON.stringify(saved),compareDigest:'current'};
 const field=compileHandoff(product,source).variables.metafields[0];const next=JSON.parse(field.value);
 assert.equal(next.enabled,false);assert.deepEqual(next.groups,saved.groups);assert.equal(field.compareDigest,'current');
 product.metafield={value:field.value,compareDigest:'next'};assert.equal(JSON.parse(compileHandoff(product,source).variables.metafields[0].value).enabled,false);
});
test('a previously staged listing gallery becomes enabled when its complete approved set arrives',()=>{
 const {product,source}=complete();const staged={...newGallery(product),source:'listing'};product.metafield={value:JSON.stringify(staged),compareDigest:'staged'};
 assert.equal(JSON.parse(compileHandoff(product,source).variables.metafields[0].value).enabled,true);
});

test('legacy six-shot manifests remain supported without adding a second model',()=>{
 const {product,source}=complete(1);const result=convertColourManifest(product,source);assert.equal(result.assets.length,24);assert.ok(result.assets.every(asset=>asset.shot !== 'second-model'));
});
