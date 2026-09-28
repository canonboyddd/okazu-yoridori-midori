const SITE_KEY='okazu';
const CENTRAL='https://factory-career-site.pages.dev/api/central/collect';
function json(data,status=200){return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}})}
function sameOrigin(request){const o=request.headers.get('origin');if(!o)return true;try{return new URL(o).host===new URL(request.url).host}catch{return false}}
function ownerExcluded(request){return /(?:^|;\s*)ops_owner_excluded=1(?:;|$)/.test(request.headers.get('cookie')||'')}
export async function onRequestPost({request}){if(ownerExcluded(request))return json({ok:true,excluded:true});if(!sameOrigin(request))return json({ok:false,error:'forbidden'},403);let body={};try{body=await request.json()}catch{return json({ok:false,error:'invalid_json'},400)};body.site_key=SITE_KEY;try{const r=await fetch(CENTRAL,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});return json({ok:r.ok},r.ok?200:502)}catch{return json({ok:false,error:'central_unreachable'},502)}}
