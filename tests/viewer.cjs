/* Run with a static server serving web/ on BASE_URL (default :8765).
 * Uses installed Google Chrome by default; CHROME_PATH overrides it.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8765/';
const out = path.resolve(process.env.QA_DIR || '/tmp/padang-viewer-qa');
fs.mkdirSync(out, {recursive:true});

async function input(page,id,value) {
  await page.locator('#'+id).evaluate((el,value)=>{el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));},String(value));
}
async function ready(page) {
  await page.goto(baseURL);
  await page.waitForFunction(()=>window.gunungPadang?.state.ready);
  await page.waitForFunction(()=>window.gunungPadang.renderer.info.render.frame>2);
}
async function run() {
  const browser=await chromium.launch({executablePath:process.env.CHROME_PATH || '/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const errors=[];
  try {
    const context=await browser.newContext({viewport:{width:1440,height:1100},permissions:['clipboard-read','clipboard-write']});
    const page=await context.newPage();
    page.on('pageerror',e=>errors.push(e.message));
    page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
    await ready(page);
    assert.equal(await page.locator('#shot-count').textContent(),'117');
    assert.deepEqual(await page.evaluate(()=>({rows:gunungPadang.terrain.rows,cols:gunungPadang.terrain.columns,shots:gunungPadang.shots.length})),{rows:66,cols:66,shots:117});
    await page.locator('#date-filter').selectOption('2024-10-07');
    assert.equal(await page.locator('#shot-count').textContent(),'87');
    assert.equal(await page.evaluate(()=>gunungPadang.shotObjects.filter(o=>o.visible).length),87);
    await page.locator('#shots-toggle').uncheck();assert.equal(await page.locator('#shot-count').textContent(),'0');
    await page.locator('#shots-toggle').check();await page.locator('#date-filter').selectOption('all');
    await page.locator('#terrain-toggle').uncheck();assert.equal(await page.evaluate(()=>gunungPadang.landscape.children[0].visible),false);await page.locator('#terrain-toggle').check();
    await input(page,'opacity',45);assert.equal(await page.evaluate(()=>gunungPadang.landscape.children[0].children[0].material.opacity),.45);await input(page,'opacity',100);
    await input(page,'exaggeration',2);assert.equal(await page.evaluate(()=>gunungPadang.landscape.scale.y),2);assert.match(await page.locator('#scale-badge').textContent(),/2×/);await input(page,'exaggeration',1);
    await page.locator('#top-view').click();
    await page.waitForTimeout(300);
    // Project a real footprint to screen and use the normal pointer-selection path.
    const xy=await page.evaluate(()=>{
      const g=gunungPadang,o=g.shotObjects[25],s=o.userData.shot;
      const v=g.camera.position.clone().set(s.east_m,g.heightAt(s.east_m,s.north_m)+3,-s.north_m).project(g.camera);
      const r=document.getElementById('canvas-host').getBoundingClientRect();return {x:r.left+(v.x+1)*r.width/2,y:r.top+(1-v.y)*r.height/2};
    });
    await page.mouse.click(xy.x,xy.y);
    await page.locator('#shot-inspector').waitFor({state:'visible'});
    assert.match(await page.locator('#inspector-data').textContent(),/ellipsoid/);
    await page.locator('#inspector-close').click();
    await page.locator('#reset-view').click();
    await page.waitForTimeout(300);
    await page.screenshot({path:path.join(out,'desktop-landscape.png'),fullPage:true});
    await page.getByRole('tab',{name:'Underground hypothesis'}).click();
    assert.equal(await page.evaluate(()=>gunungPadang.hypothesis.visible),true);
    assert.match(await page.locator('#scene-tag').textContent(),/SCHEMATIC/);
    for(let i=1;i<=4;i++){
      await page.locator(`#unit${i}-toggle`).uncheck();assert.equal(await page.evaluate(i=>gunungPadang.unitGroups[i-1].visible,i),false);
      await page.locator(`#unit${i}-toggle`).check();
    }
    await input(page,'cut',35);
    assert.equal(await page.evaluate(()=>gunungPadang.unitGroups[0].children[0].material.clippingPlanes[0].constant),35);
    await page.locator('#cut-toggle').uncheck();assert.equal(await page.evaluate(()=>gunungPadang.unitGroups[0].children[0].material.clippingPlanes.length),0);await page.locator('#cut-toggle').check();
    await input(page,'explode',60);assert.equal(await page.evaluate(()=>gunungPadang.unitGroups[0].position.y),32.4);
    await input(page,'model-opacity',65);assert.equal(await page.evaluate(()=>gunungPadang.unitGroups[2].children[0].material.opacity),.65);
    await page.locator('#anomaly-toggle').check();
    await page.locator('#share-view').click();
    const shareURL=page.url();assert(shareURL.includes('#view='));
    const saved=await context.newPage();await saved.goto(shareURL);await saved.waitForFunction(()=>window.gunungPadang?.state.ready);
    assert.equal(await saved.evaluate(()=>gunungPadang.state.view),'underground');
    assert.equal(await saved.locator('#explode').inputValue(),'60');assert.equal(await saved.locator('#cut').inputValue(),'35');
    assert.equal(await saved.locator('#anomaly-toggle').isChecked(),true);
    await saved.close();
    await input(page,'explode',0);await input(page,'cut',0);await input(page,'model-opacity',100);await page.locator('#anomaly-toggle').uncheck();
    await page.waitForTimeout(300);await page.locator('.workspace').screenshot({path:path.join(out,'desktop-underground.png')});
    for(const key of ['radar','resistivity','seismic']){
      await page.locator(`[data-figure="${key}"]`).click();await page.locator('#figure-dialog').waitFor({state:'visible'});
      assert(await page.locator('#figure-image').evaluate(img=>img.complete&&img.naturalWidth>500));await page.keyboard.press('Escape');
    }
    await page.locator('#figure14-open').click();assert.match(await page.locator('#figure-title').textContent(),/four units/);await page.keyboard.press('Escape');
    await page.locator('#sources-open').click();assert(await page.locator('#method-dialog').isVisible());await page.keyboard.press('Escape');
    // Every downloadable data artifact is served, not just its UI link.
    for(const file of ['terrain.json','shots.json','provenance.json','gedi-footprints.csv','copernicus-surface-crop.tif'])assert.equal((await page.request.get(new URL('data/'+file,baseURL).href)).status(),200);
    for(const width of [390,768]){
      await page.setViewportSize({width,height:844});await page.evaluate(()=>scrollTo(0,0));await page.waitForTimeout(300);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.getByRole('tab',{name:'Underground hypothesis'}).click();await page.locator('#reset-view').click();
      await page.waitForTimeout(200);await page.screenshot({path:path.join(out,`width-${width}.png`)});
      assert(await page.locator('#canvas-host canvas').isVisible());
    }
    // Accessible fallback if graphics initialization fails.
    const fallback=await context.newPage();
    await fallback.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){if(type.startsWith('webgl'))return null;return original.call(this,type,...args);};});
    await fallback.goto(baseURL);await fallback.locator('#viewer-error').waitFor({state:'visible'});
    assert(await fallback.locator('.figure-card').first().isVisible());await fallback.close();
    assert.deepEqual(errors,[]);
    console.log('PASS: desktop/mobile render, native data, all layers, filters, cutaway, separation, opacity, shot picking, share restore, figures, downloads, and WebGL fallback.');
    console.log('Screenshots:',out);
  } finally {await browser.close();}
}
run().catch(e=>{console.error(e);process.exit(1);});
