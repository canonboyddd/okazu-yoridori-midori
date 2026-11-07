import test from 'node:test';
import assert from 'node:assert/strict';
import {collect} from '../lib/revenue-collector.js';
const event={event_name:'affiliate_click',browser_id:'browser-test-123',session_id:'session-test-123',page_path:'/products/view/?id=item1&email=private@example.test',referrer:'https://search.example.test/?q=private@example.test',provider:'FANZA',program:'FANZA',placement:'product-top',device_type:'mobile'};
const request=(body=event,headers={})=>new Request('https://example.test/api/ops-collect',{method:'POST',headers:{'content-type':'application/json','user-agent':'Mozilla/5.0',...headers},body:JSON.stringify(body)});
test('owner, QA and automated requests never forward to the revenue collector',async()=>{
 let calls=0;const old=globalThis.fetch;globalThis.fetch=async()=>{calls++;return new Response('{}')};
 try{for(const headers of [{'x-ops-qa':'1'},{cookie:'ops_owner_excluded=1'},{'user-agent':'RevenueQA Playwright'},{'user-agent':'Googlebot'}]){const r=await collect({request:request(event,headers)},'clipmade');assert.equal(r.status,200);assert.equal(calls,0)}}finally{globalThis.fetch=old}
});
test('safe dimension allowlist drops email, key, token, URLs and query strings',async()=>{
 let sent;const old=globalThis.fetch;globalThis.fetch=async(_u,init)=>{sent=JSON.parse(init.body);assert.equal(init.headers['user-agent'],'Mozilla/5.0');return new Response('{}')};
 try{const r=await collect({request:request({...event,email:'private@example.test',accessKey:'CM-'+'A'.repeat(48),token:'secret',page_title:'private@example.test',link_url:'https://example.test/?email=private@example.test'})},'clipmade');assert.equal(r.status,200);assert.equal(sent.page_path,'/products/view/');assert.equal(sent.referrer,'search.example.test');assert.equal(sent.site_key,'clipmade');assert.equal(JSON.stringify(sent).includes('private'),false);assert.equal('accessKey' in sent,false);assert.equal('token' in sent,false)}finally{globalThis.fetch=old}
});
test('cross-origin, oversized, malformed and unrecognized events fail without forwarding',async()=>{
 let calls=0;const old=globalThis.fetch;globalThis.fetch=async()=>{calls++;return new Response('{}')};
 try{assert.equal((await collect({request:request(event,{origin:'https://attacker.test'})},'okazu')).status,403);assert.equal((await collect({request:request({...event,event_name:'arbitrary'})},'okazu')).status,400);assert.equal((await collect({request:request({...event,padding:'x'.repeat(17000)})},'okazu')).status,413);assert.equal(calls,0)}finally{globalThis.fetch=old}
});
test('upstream failure remains observable instead of reporting a saved event',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async()=>new Response('{}',{status:503});
 try{assert.equal((await collect({request:request()},'okazu')).status,502)}finally{globalThis.fetch=old}
});
