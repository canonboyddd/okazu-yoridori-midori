from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("public")
CSS = "/assets/benchmark-upgrade-v1.css?v=20260926-2238"
CSS_LINK = f'<link rel="stylesheet" href="{CSS}">'

MOBILE_NAV = '''<nav class="benchmark-mobile-nav" aria-label="スマホ固定メニュー">
<a href="/">ホーム</a><a href="/ranking/">ランキング</a><a href="/sale/">セール</a><a href="/search/">検索</a><a href="/fc2-adult/">FC2</a>
</nav>'''

HOME_QUICK = '''<section class="benchmark-quick-wrap" aria-label="目的から探す">
<div class="benchmark-quick-head"><div><h2>目的からすぐ探す</h2><p>人気・女優・ジャンル・セール・見放題から最短で探せます。</p></div></div>
<div class="benchmark-quick-grid">
<a class="benchmark-quick-card" href="/ranking/"><strong>人気ランキング</strong><span>いま人気の作品から探す</span></a>
<a class="benchmark-quick-card" href="/ranking/actress/popular/"><strong>人気女優</strong><span>DMM/FANZA人気作品データから集計</span></a>
<a class="benchmark-quick-card" href="/ranking/actress/"><strong>女優50音検索</strong><span>名前・読み・50音から探す</span></a>
<a class="benchmark-quick-card" href="/ranking/genre/"><strong>ジャンルから探す</strong><span>好みのジャンルへすぐ移動</span></a>
<a class="benchmark-quick-card" href="/ranking/maker/"><strong>メーカーから探す</strong><span>メーカー別の人気作品を見る</span></a>
<a class="benchmark-quick-card" href="/sale/"><strong>セール作品</strong><span>値引き率と価格をまとめて確認</span></a>
<a class="benchmark-quick-card" href="/subscription/"><strong>見放題を比較</strong><span>月額・対象範囲・条件を比較</span></a>
<a class="benchmark-quick-card" href="/fc2-adult/"><strong>FC2アダルト</strong><span>FC2系サービス・商品への入口</span></a>
</div></section>
<div class="benchmark-status"><span class="benchmark-dot"></span><b>データ更新型サイト</b><span>ランキング・商品・価格は定期更新。購入前はリンク先の公式情報を最終確認してください。</span></div>'''

HOME_FAQ = '''<section class="benchmark-faq" aria-label="よくある質問"><h2>迷ったときの探し方</h2><div class="benchmark-faq-grid">
<details><summary>まず何から見ればいい？</summary><p>迷ったら人気ランキングから入り、女優・ジャンル・メーカーで絞ると探しやすくなります。</p></details>
<details><summary>安い作品だけ探せる？</summary><p>セールページで値引き候補を確認できます。価格と販売条件は購入前に公式ページで確認してください。</p></details>
<details><summary>作品名が分からないときは？</summary><p>サイト内検索、女優50音検索、ジャンル別ランキングを使うと候補を絞り込めます。</p></details>
</div></section>'''

RANKING_NAV = '''<div class="benchmark-ranking-nav" aria-label="ランキング検索メニュー">
<a href="/ranking/">総合</a><a href="/ranking/actress/popular/">人気女優</a><a href="/ranking/actress/">女優50音</a><a href="/ranking/genre/">ジャンル</a><a href="/ranking/maker/">メーカー</a><a href="/sale/">セール</a>
</div>'''


def strip_existing(text: str) -> str:
    text = re.sub(r'<link\s+rel="stylesheet"\s+href="/assets/benchmark-upgrade-v1\.css(?:\?v=[^"]*)?"\s*/?>', '', text, flags=re.I)
    text = re.sub(r'<nav class="benchmark-mobile-nav".*?</nav>', '', text, flags=re.S)
    text = re.sub(r'<section class="benchmark-quick-wrap".*?</section>\s*<div class="benchmark-status">.*?</div>', '', text, flags=re.S)
    text = re.sub(r'<section class="benchmark-faq".*?</section>', '', text, flags=re.S)
    text = re.sub(r'<div class="benchmark-ranking-nav".*?</div>', '', text, flags=re.S)
    return text


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    before = text
    text = strip_existing(text)

    if '</head>' in text:
        text = text.replace('</head>', CSS_LINK + '</head>', 1)

    rel = path.relative_to(ROOT).as_posix()

    if rel == 'index.html':
        # Competitor-style discovery: high-intent routes immediately after the hero.
        hero_end = text.find('</section>', text.find('<section class="hero"'))
        if hero_end != -1:
            pos = hero_end + len('</section>')
            text = text[:pos] + HOME_QUICK + text[pos:]

        # Remove internal/revenue-facing wording from the public homepage.
        text = text.replace('月100万円を狙うためのサイト導線', '迷わず選ぶための3ステップ')
        text = text.replace('検索流入を「情報を知りたい人」だけで終わらせず、比較・ランキング・セール・レビューへ内部リンクして、購入判断まで迷わない構造にしています。', 'まず候補を見つけ、条件を比較し、最後に公式ページで価格・販売条件を確認できる順番に整理しています。')
        text = text.replace('<div class="revenue-step"><b>集客</b>初心者・使い方</div>', '<div class="revenue-step"><b>1. 探す</b>人気・女優・ジャンル</div>')
        text = text.replace('<div class="revenue-step"><b>比較</b>月額・ランキング</div>', '<div class="revenue-step"><b>2. 比べる</b>価格・レビュー・見放題</div>')
        text = text.replace('<div class="revenue-step"><b>購入意図</b>セール・レビュー</div>', '<div class="revenue-step"><b>3. 確認</b>セール・販売条件</div>')
        text = text.replace('<div class="revenue-step"><b>成約</b>広告・商品導線</div>', '<div class="revenue-step"><b>公式へ</b>最新条件を最終確認</div>')

        main_close = text.rfind('</main>')
        if main_close != -1:
            text = text[:main_close] + HOME_FAQ + text[main_close:]

    if rel == 'ranking/index.html' or rel.startswith('ranking/actress/popular/'):
        hero_end = text.find('</section>', text.find('<section class="hub-hero"'))
        if hero_end != -1:
            pos = hero_end + len('</section>')
            text = text[:pos] + RANKING_NAV + text[pos:]

    if '</body>' in text:
        text = text.replace('</body>', MOBILE_NAV + '</body>', 1)

    if text != before:
        path.write_text(text, encoding='utf-8')
        return True
    return False


def main() -> None:
    changed = 0
    total = 0
    for path in ROOT.rglob('*.html'):
        total += 1
        if patch(path):
            changed += 1
    print(f'Competitor benchmark UX applied: {changed}/{total} HTML files')


if __name__ == '__main__':
    main()
