const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium}=require('playwright');
const base=process.env.BASE_URL||'http://127.0.0.1:8766/';
const out=process.env.QA_DIR||'/tmp/padang-unified-qa';fs.mkdirSync(out,{recursive:true});
async function range(p,id,value){await p.locator('#'+id).evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));},String(value));}
async function main(){
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const errors=[];
 try{
  const ctx=await browser.newContext({viewport:{width:1440,height:900},permissions:['clipboard-read','clipboard-write']});
  const p=await ctx.newPage();p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()}: ${r.url()}`);});
  await p.goto(base);await p.waitForFunction(()=>window.gunungPadang?.state.ready);
  assert.equal(await p.locator('canvas').count(),1);assert.equal(await p.getByRole('tab').count(),0);
  assert(await p.evaluate(()=>document.body.scrollHeight===innerHeight));
  assert.deepEqual(await p.evaluate(()=>{const g=gunungPadang;return [g.terrainGroup.visible,g.gediGroup.visible,g.structureGroup.visible,g.shotObjects.length];}),[true,true,true,117]);
  assert(await p.evaluate(()=>{const g=gunungPadang;return g.shots.every(s=>Math.abs(s.elev_lowestmode_ellipsoid_m-s.geoid_undulation_m-s.ground_egm2008_m)<.000002)&&g.shotObjects.every(o=>Math.abs(o.geometry.attributes.position.getY(0)-(o.userData.shot.ground_egm2008_m-g.datum))<.0001);}));
  // Terrain and structures use the very same world-space clipping plane.
  assert(await p.evaluate(()=>gunungPadang.terrainGroup.children[0].material.clippingPlanes[0]===gunungPadang.unitGroups[0].children[0].material.clippingPlanes[0]));
  assert(await p.evaluate(()=>{const g=gunungPadang;g.scene.updateMatrixWorld(true);return Math.abs(g.structureGroup.position.y+56-g.anchor)<.00001&&g.structureGroup.parent===g.terrainGroup.parent;}));
  for(const [id,key] of [['terrain-toggle','terrainGroup'],['shots-toggle','gediGroup'],['chamber-toggle','chamberGroup']]){
   await p.locator('#'+id).uncheck();assert.equal(await p.evaluate(k=>gunungPadang[k].visible,key),false);await p.locator('#'+id).check();
  }
  for(let i=1;i<=4;i++){await p.locator(`#unit${i}-toggle`).uncheck();assert.equal(await p.evaluate(i=>gunungPadang.unitGroups[i-1].visible,i),false);await p.locator(`#unit${i}-toggle`).check();}
  await range(p,'cut',42);assert.equal(await p.evaluate(()=>gunungPadang.clip.constant),42);
  await p.locator('#cut-toggle').uncheck();assert.equal(await p.evaluate(()=>gunungPadang.terrainGroup.children[0].material.clippingPlanes.length),0);assert.equal(await p.evaluate(()=>gunungPadang.unitGroups[0].children[0].material.clippingPlanes.length),0);
  await p.locator('#cut-toggle').check();await range(p,'cut',0);
  await range(p,'opacity',25);assert.equal(await p.evaluate(()=>gunungPadang.terrainGroup.children[0].material.opacity),.25);await range(p,'opacity',100);
  await range(p,'explode',55);assert.equal(await p.evaluate(()=>gunungPadang.unitGroups[0].position.y),29.7);
  await p.locator('#share-view').click();const shared=p.url();assert(shared.includes('#view='));
  const q=await ctx.newPage();await q.goto(shared);await q.waitForFunction(()=>window.gunungPadang?.state.ready);assert.equal(await q.locator('#explode').inputValue(),'55');assert.equal(await q.locator('canvas').count(),1);await q.close();await range(p,'explode',0);
  await p.locator('#top-view').click();await p.waitForTimeout(200);
  const xy=await p.evaluate(()=>{const g=gunungPadang,s=g.shots[26],v=g.camera.position.clone().set(s.east_m,s.ground_egm2008_m-g.datum,-s.north_m).project(g.camera),r=document.getElementById('canvas-host').getBoundingClientRect();return {x:r.left+(v.x+1)*r.width/2,y:r.top+(1-v.y)*r.height/2};});
  await p.mouse.click(xy.x,xy.y);await p.locator('#shot-inspector').waitFor({state:'visible'});assert.match(await p.locator('#shot-data').textContent(),/EGM2008/);await p.locator('#inspector-close').click();
  await p.locator('#site-view').click();await p.waitForTimeout(300);await p.screenshot({path:path.join(out,'desktop.png')});
  await p.locator('#info-open').click();await p.locator('#sources').waitFor({state:'visible'});
  for(const key of ['reconstruction','resistivity','seismic','radar']){await p.locator(`[data-figure="${key}"]`).click();await p.locator('#figure-dialog').waitFor({state:'visible'});await p.waitForFunction(()=>document.getElementById('figure-image').complete&&document.getElementById('figure-image').naturalWidth>500);await p.locator('[data-close="figure-dialog"]').click();}
  await p.locator('[data-close="sources"]').click();
  for(const file of ['terrain.json','shots.json','provenance.json','gedi-footprints.csv','copernicus-surface-crop.tif','egm2008-local.tif'])assert.equal((await p.request.get(new URL('data/'+file,base).href)).status(),200);
  for(const size of [{width:390,height:844},{width:768,height:1024},{width:844,height:390}]){await p.setViewportSize(size);await p.locator('#site-view').click();await p.waitForTimeout(250);assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.body.scrollHeight===innerHeight));await p.screenshot({path:path.join(out,`${size.width}x${size.height}.png`)});assert(await p.locator('#cut-toggle').isVisible());assert(await p.locator('#unit4-toggle').isVisible());}
  const fallback=await ctx.newPage();await fallback.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type.startsWith('webgl')?null:original.call(this,type,...args);};});await fallback.goto(base);await fallback.locator('#viewer-error').waitFor({state:'visible'});await fallback.locator('#info-open').click();assert(await fallback.locator('#sources').isVisible());await fallback.close();
  assert.deepEqual(errors,[]);console.log('PASS: one viewport; merged terrain, GEDI and structures; common cut plane; converted heights; all controls; picking; sharing; source figures; downloads; desktop/mobile; WebGL fallback.');console.log('Screenshots:',out);
 }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exit(1);});
