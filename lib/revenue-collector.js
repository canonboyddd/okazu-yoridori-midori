const CENTRAL='https://factory-career-site.pages.dev/api/central/collect';
const BOT=/bot|crawler|spider|slurp|inspection|lighthouse|pagespeed|headless|phantom|selenium|puppeteer|playwright|preview|uptime|pingdom|monitor|revenueqa/i;
const EVENTS=new Set(['page_view','cta_impression','cta_click','download_click','beta_apply_start','beta_apply_attempt','beta_apply_error','beta_capacity_view','beta_key_issued','beta_waitlisted','beta_duplicate','beta_key_copy','affiliate_impression','affiliate_click','scroll_90','sale_click','ranking_click','review_click','subscription_click','product_open','product_detail_view','catalog_list_view','internal_cta_click','catalog_search']);
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const safe=(value,max=100)=>{const s=String(value||'');return /@|CM-[A-F0-9]{48}|eyJ[A-Za-z0-9_-]+\./i.test(s)?'':s.replace(/[^a-zA-Z0-9_.:/|+-]/g,'-').slice(0,max)};
function path(value){try{return new URL(String(value||'/'),'https://local.invalid').pathname.slice(0,300)}catch{return '/'}}
function host(value){try{return new URL(String(value||'')).hostname.slice(0,200)}catch{return /^[a-z0-9.-]+$/i.test(value||'')?value:''}}
async function boundedJson(request){
 const reader=request.body?.getReader();if(!reader)throw Error('json');let size=0;const chunks=[];
 while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>16384){await reader.cancel();throw Error('large')}chunks.push(value)}
 const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength}return JSON.parse(new TextDecoder().decode(bytes));
}
export async function collect({request},siteKey){
 const q=new URL(request.url).searchParams;
 if(request.headers.get('x-ops-qa')==='1'||q.get('ops_qa')==='1'||q.get('qa')==='1'||/(?:^|;\s*)ops_owner_excluded=1(?:;|$)/.test(request.headers.get('cookie')||''))return json({ok:true,excluded:true});
 if(BOT.test(request.headers.get('user-agent')||''))return json({ok:true,filtered:'automated'});
 const origin=request.headers.get('origin');if(origin&&origin!==new URL(request.url).origin)return json({ok:false,error:'forbidden'},403);
 let b;try{b=await boundedJson(request)}catch(e){return json({ok:false,error:e.message==='large'?'payload_too_large':'invalid_json'},e.message==='large'?413:400)}
 if(!b||!EVENTS.has(b.event_name)||!/^[-a-zA-Z0-9_]{8,100}$/.test(b.browser_id||'')||!/^[-a-zA-Z0-9_]{8,100}$/.test(b.session_id||''))return json({ok:false,error:'invalid_event'},400);
 // Explicit fields prevent form inputs, keys, tokens and arbitrary query strings entering analytics.
 const body={site_key:siteKey,event_name:b.event_name,browser_id:b.browser_id,session_id:b.session_id,page_path:path(b.page_path),referrer:host(b.referrer),device_type:['mobile','tablet','desktop'].includes(b.device_type)?b.device_type:'unknown'};
 for(const field of ['provider','program','placement','variant','cta_position','page_type','product_id','outbound_domain'])body[field]=safe(b[field],field==='placement'?160:100);
 for(const field of ['origin_page_path'])body[field]=path(b[field]||'/');
 body.origin_page_type=safe(b.origin_page_type);
 if(Number.isSafeInteger(b.result_count)&&b.result_count>=0)body.result_count=b.result_count;
 try{const r=await fetch(CENTRAL,{method:'POST',headers:{'content-type':'application/json','user-agent':request.headers.get('user-agent')||''},body:JSON.stringify(body)});return json({ok:r.ok},r.ok?200:502)}catch{return json({ok:false,error:'central_unreachable'},502)}
}
