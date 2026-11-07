import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
const output=[];
for(const site of ['okazu-yoridori-midori']){
 const ctx=await browser.newContext({viewport:{width:375,height:900},userAgent:'Mozilla/5.0 Chrome/130 Safari/537.36'});
 await ctx.addInitScript(()=>{Object.defineProperty(navigator,'webdriver',{get:()=>false});window.GA4_CONFIG={measurementId:'G-QAONLY123'}});
 const events=[];
 await ctx.route('**/*',async route=>{
  const u=new URL(route.request().url());
  if(u.pathname==='/api/ops-collect'){events.push(route.request().postDataJSON());return route.fulfill({status:200,contentType:'application/json',body:'{"ok":true}'})}
  if(u.pathname==='/fixture')return route.fulfill({contentType:'text/html',body:'<!doctype html><html><body><main><a id="a" data-event="beta_primary" data-affiliate-target="product-top" href="https://al.dmm.co.jp/?lurl=example&af_id=existing">Official conditions</a><a id="fc2" data-affiliate-target="fc2-existing" href="https://cnt.affiliate.fc2.com/cgi-bin/click.cgi?aff_shopid=existing">FC2 conditions</a><div id="below" style="margin-top:2000px"><a data-event="below_fold" data-affiliate-target="below-fold" href="https://al.dmm.co.jp/?lurl=example2">Below fold</a></div></main><script>document.addEventListener("click",e=>e.preventDefault())</script></body></html>'});
  return route.abort(); // No analytics or affiliate request can escape the test.
 });
 const page=await ctx.newPage();
 await page.goto('https://qa.invalid/fixture?email=private@example.test');
 const src=site==='clipmade-site'?'site-analytics.js':'public/assets/ga4.js';
 await page.addScriptTag({content:await readFile(new URL(`../${src}`,import.meta.url),'utf8')});
 await page.waitForTimeout(1300);
 const impression=site==='clipmade-site'?'cta_impression':'affiliate_impression';
 assert.equal(events.filter(e=>e.event_name===impression&&e.cta_position==='below_fold').length,0);
 assert.equal(events.filter(e=>e.event_name===impression&&e.cta_position===(site==='clipmade-site'?'beta_primary':'product-top')).length,1);
 const before=events.length;
 await page.locator('#a').evaluate(a=>a.click());
 await page.waitForTimeout(150);
 assert.equal(events.length,before,'script clicks must not count');
 await page.locator('#a').click();
 await page.waitForTimeout(150);
 assert.equal(events.filter(e=>e.event_name===(site==='clipmade-site'?'cta_click':'affiliate_click')).length,1,'one native click is one event');
 if(site.startsWith('okazu')){
  await page.locator('#fc2').click();await page.waitForTimeout(150);
  assert.equal(events.filter(e=>e.event_name==='affiliate_click'&&e.provider==='FC2').length,1);
  await page.evaluate(()=>window.trackOpsEvent('catalog_search',{placement:'private@example.test',search_query:'private@example.test',result_count:1}));
  assert.equal(await page.evaluate(()=>JSON.stringify(window.dataLayer).includes('private@example.test')),false,'GA4 must not receive private query or input dimensions');
 }
 assert.equal(JSON.stringify(events).includes('private@example.test'),false);
 output.push({site,tests:'visible-only impressions, hidden CTA exclusion, synthetic-click exclusion, one native click, safe query strings'+(site.startsWith('okazu')?', FC2 click':''),passed:true});
 await ctx.close();
 // QA query suppresses every client measurement, even with a human-looking browser.
 const blocked=await browser.newContext();await blocked.addInitScript(()=>Object.defineProperty(navigator,'webdriver',{get:()=>false}));
 let sent=0;await blocked.route('**/*',async r=>{if(r.request().url().includes('/api/ops-collect'))sent++;return r.fulfill({contentType:'text/html',body:'<body><a data-event="test" href="https://example.test">Test</a></body>'})});
 const bp=await blocked.newPage();await bp.goto('https://qa.invalid/?ops_qa=1');await bp.addScriptTag({content:await readFile(new URL(`../${src}`,import.meta.url),'utf8')});await bp.waitForTimeout(1100);assert.equal(sent,0);await blocked.close();
}
await browser.close();
await mkdir(new URL('../reports/evidence/',import.meta.url),{recursive:true});await writeFile(new URL('../reports/evidence/analytics-tests.json',import.meta.url),JSON.stringify(output,null,2));console.log(JSON.stringify(output));
