import fs from 'node:fs';

const file='public/index.html';
let s=fs.readFileSync(file,'utf8');
const replacements=[
  ['<h2>月100万円を狙うためのサイト導線</h2>','<h2>迷わず比較して選べるサイト導線</h2>'],
  ['<p>検索流入を「情報を知りたい人」だけで終わらせず、比較・ランキング・セール・レビューへ内部リンクして、購入判断まで迷わない構造にしています。</p>','<p>初心者向け情報から、料金比較・ランキング・セール・レビューまで順番に確認できるよう整理しています。気になる条件を比べてから、公式情報で最終確認できます。</p>'],
  ['<div class="revenue-step"><b>集客</b>初心者・使い方</div>','<div class="revenue-step"><b>基本を知る</b>初心者・使い方</div>'],
  ['<div class="revenue-step"><b>比較</b>月額・ランキング</div>','<div class="revenue-step"><b>条件を比べる</b>月額・ランキング</div>'],
  ['<div class="revenue-step"><b>購入意図</b>セール・レビュー</div>','<div class="revenue-step"><b>候補を絞る</b>セール・レビュー</div>'],
  ['<div class="revenue-step"><b>成約</b>広告・商品導線</div>','<div class="revenue-step"><b>公式で確認</b>料金・作品情報</div>'],
  ['購入前の疑問から収益ページへ自然につなぐ。','初めて使う前に確認したい基本と注意点をまとめる。']
];
for(const [from,to] of replacements){
  if(!s.includes(from)) throw new Error(`expected public copy not found: ${from}`);
  s=s.replace(from,to);
}
const forbidden=['月100万円を狙うため','収益ページへ自然につなぐ','<b>成約</b>広告・商品導線'];
for(const term of forbidden) if(s.includes(term)) throw new Error(`operator-only public copy remains: ${term}`);
fs.writeFileSync(file,s);
console.log('Public homepage copy aligned with user-facing behavior.');
