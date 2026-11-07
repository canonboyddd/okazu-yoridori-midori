import {createRequire} from 'node:module';import {execFileSync} from 'node:child_process';import {readFile,writeFile} from 'node:fs/promises';import assert from 'node:assert/strict';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const chooser=execFileSync('python',['-c',"import runpy; print(runpy.run_path('scripts/optimize_home_for_immediate_discovery.py')['CHOOSER_JS'])"],{encoding:'utf8',env:{...process.env,PYTHONIOENCODING:'utf-8'}});
const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})}),ctx=await browser.newContext({userAgent:'Mozilla/5.0 Chrome/130 Safari/537.36'});
await ctx.addInitScript(()=>{Object.defineProperty(navigator,'webdriver',{get:()=>false});window.GA4_CONFIG={measurementId:'G-QAONLY123'}});
const events=[];let allowedExternal=0;
await ctx.route('**/*',r=>{
 const u=new URL(r.request().url());
 if(u.hostname!=='qa.invalid')return r.abort();
 if(u.pathname==='/api/ops-collect'){events.push(r.request().postDataJSON());return r.fulfill({json:{ok:true}})}
 if(u.pathname==='/data/fanza-products.json')return r.fulfill({json:{ranking:[{contentId:'qa001',title:'Neutral QA item',price:1000,imageURL:'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==',affiliateURL:'https://al.fanza.co.jp/?af_id=fixture&ch=api&lurl=https%3A%2F%2Fvideo.dmm.co.jp%2Fav%2Fcontent%2F%3Fid%3Dqa001'}]}});
 return r.fulfill({contentType:'text/html',body:'<body><main><h1>Neutral QA page</h1><div id="instantChooser"><button id="instantDecide">Choose</button><div id="instantPicks"><div id="instantPickGrid"></div><button id="instantShuffle">Shuffle</button></div></div></main><script>document.addEventListener("click",e=>{if(e.target.closest("a"))e.preventDefault()},true)</script>'+chooser+'</body>'});
});
const page=await ctx.newPage();await page.goto('https://qa.invalid/');await page.addScriptTag({content:await readFile(new URL('../public/assets/ga4.js',import.meta.url),'utf8')});
await page.locator('#instantDecide').click();await page.locator('[data-direct-fanza]').waitFor();await page.locator('[data-direct-fanza]').click();await page.waitForTimeout(200);
assert.equal(events.filter(e=>e.event_name==='affiliate_click').length,1);assert.equal(events.find(e=>e.event_name==='affiliate_click').placement,'home-chooser-1');
assert.equal(await page.evaluate(()=>window.dataLayer.filter(x=>x[0]==='event'&&x[1]==='affiliate_click').length),1,'generated homepage must not add a second GA4 affiliate listener');
await browser.close();const result={passed:true,generatedHomepage:true,nativeClicks:1,centralAffiliateEvents:1,ga4AffiliateEvents:1,externalRequestsAllowed:allowedExternal};await writeFile(new URL('../reports/evidence/home-chooser-tests.json',import.meta.url),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
