import {createRequire} from 'node:module';import {readFile,writeFile} from 'node:fs/promises';import assert from 'node:assert/strict';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})}),results=[];
for(const path of ['/search/','/guide/','/about.html','/privacy.html','/sale/']){
 const ctx=await browser.newContext();let attempted=0;
 await ctx.route('**/*',r=>{if(!r.request().url().startsWith('https://qa.invalid/')){attempted++;return r.abort()}return r.fulfill({contentType:'text/html',body:'<body><main><h1>QA fixture</h1></main></body>'})});
 const page=await ctx.newPage();await page.goto('https://qa.invalid'+path);await page.addScriptTag({content:await readFile(new URL('../public/assets/fc2-affiliate-banners.js',import.meta.url),'utf8')});await page.waitForTimeout(250);
 if(path==='/sale/'){assert.equal(await page.locator('[data-fc2-affiliate]').count(),1)}else{assert.equal(attempted,0);assert.equal(await page.locator('[data-fc2-affiliate]').count(),0)}
 results.push({path,passed:true,interceptedExternalRequests:attempted,externalRequestsAllowed:0});await ctx.close();
}
await browser.close();await writeFile(new URL('../reports/evidence/fc2-browser-tests.json',import.meta.url),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
