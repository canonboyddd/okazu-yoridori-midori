function safeNext(v){const s=String(v||'/');return s.startsWith('/')&&!s.startsWith('//')?s:'/'}
export async function onRequestGet({request}){const u=new URL(request.url);const next=safeNext(u.searchParams.get('next'));return new Response(null,{status:302,headers:{location:next,'set-cookie':'ops_owner_excluded=1; Max-Age=31536000; Path=/; SameSite=Lax; Secure','cache-control':'no-store'}})}
