from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"
BASE_URL = "https://okazu-yoridori-midori.pages.dev"
CIRCLE_NAME = os.environ.get("OWN_DOUJIN_CIRCLE_NAME", "桃色ラボ").strip() or "桃色ラボ"
OUT_DIR = Path("public/momoiro-lab")
OUT_JSON = Path("public/data/momoiro-lab-works.json")
HOME = Path("public/index.html")
SITEMAP = Path("public/sitemap.xml")


def _entities(iteminfo: dict, key: str) -> list[dict]:
    rows = iteminfo.get(key) or []
    return [x for x in rows if isinstance(x, dict)]


def _circle_names(item: dict) -> list[str]:
    iteminfo = item.get("iteminfo") or {}
    names: list[str] = []
    for key in ("maker", "series"):
        for row in _entities(iteminfo, key):
            name = str(row.get("name") or "").strip()
            if name:
                names.append(name)
    return names


def _normalize(item: dict) -> dict:
    image = item.get("imageURL") or {}
    prices = item.get("prices") or {}
    review = item.get("review") or {}
    iteminfo = item.get("iteminfo") or {}
    maker_rows = _entities(iteminfo, "maker")
    maker = str(maker_rows[0].get("name") or "").strip() if maker_rows else ""
    return {
        "contentId": str(item.get("content_id") or "").strip(),
        "title": str(item.get("title") or "").strip(),
        "affiliateURL": str(item.get("affiliateURL") or "").strip(),
        "officialURL": str(item.get("URL") or "").strip(),
        "imageURL": str(image.get("large") or image.get("small") or image.get("list") or "").strip(),
        "price": str(prices.get("price") or "").strip(),
        "date": str(item.get("date") or "").strip(),
        "reviewAverage": str(review.get("average") or "").strip(),
        "reviewCount": int(review.get("count") or 0),
        "maker": maker,
    }


def fetch_works(api_id: str, affiliate_id: str) -> list[dict]:
    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "doujin",
        "floor": "digital_doujin",
        "hits": "100",
        "offset": "1",
        "sort": "date",
        "keyword": CIRCLE_NAME,
        "output": "json",
    }
    req = Request(API_URL + "?" + urlencode(params), headers={"User-Agent": "okazu-yoridori-midori-own-works/1.0"})
    with urlopen(req, timeout=30) as res:
        payload = json.loads(res.read().decode("utf-8"))
    result = payload.get("result") or {}
    status = result.get("status")
    if status not in (200, "200"):
        raise RuntimeError(f"DMM API error: status={status!r}")

    exact: list[dict] = []
    fallback: list[dict] = []
    for raw in result.get("items") or []:
        names = _circle_names(raw)
        row = _normalize(raw)
        if any(name == CIRCLE_NAME for name in names):
            exact.append(row)
        elif CIRCLE_NAME in row.get("title", ""):
            fallback.append(row)
    rows = exact or fallback
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        key = row.get("contentId") or row.get("affiliateURL") or row.get("officialURL")
        if not key or key in seen:
            continue
        seen.add(str(key))
        out.append(row)
    return out


def _card(item: dict) -> str:
    title = html.escape(item.get("title") or "FANZA同人作品")
    image = html.escape(item.get("imageURL") or "", quote=True)
    url = item.get("affiliateURL") or item.get("officialURL") or "#"
    url_e = html.escape(url, quote=True)
    price = html.escape(item.get("price") or "公式で確認")
    date = html.escape(item.get("date") or "")
    affiliate = bool(item.get("affiliateURL"))
    badge = "PR / アフィリエイトリンク" if affiliate else "公式リンク"
    image_html = f'<img src="{image}" alt="{title}" loading="lazy" decoding="async">' if image else '<div class="placeholder">画像準備中</div>'
    return f'''<article class="work-card"><a href="{url_e}" target="_blank" rel="{'sponsored nofollow ' if affiliate else ''}noopener noreferrer">{image_html}<div class="work-body"><span class="ad-badge">{badge}</span><h2>{title}</h2><div class="meta"><strong>{price}</strong>{f'<span>{date}</span>' if date else ''}</div><span class="cta">FANZAで確認する →</span></div></a></article>'''


def _render(works: list[dict], generated_at: str, error: str = "") -> str:
    cards = "".join(_card(x) for x in works)
    if not cards:
        cards = '''<div class="empty"><h2>公開作品のAPI反映待ちです</h2><p>桃色ラボの作品がFANZAで公開され、FANZA Webサービスの商品APIに反映されると、このページへ自動掲載します。</p></div>'''
    error_html = f'<div class="notice"><strong>更新メモ：</strong>{html.escape(error)}</div>' if error else ""
    count_text = f"{len(works)}作品" if works else "公開準備中"
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>桃色ラボ FANZA同人作品一覧 | オカズはよりどりみどり</title><meta name="description" content="桃色ラボのFANZA同人作品を一覧で紹介します。公開作品はFANZA Webサービスの商品APIから自動更新します。"><meta name="robots" content="index,follow"><link rel="canonical" href="{BASE_URL}/momoiro-lab/"><link rel="icon" type="image/png" href="/assets/favicon.png"><link rel="stylesheet" href="/assets/style-white-v2.css?v=20260922-1322"><style>.own-hero{{padding:46px 0;background:linear-gradient(135deg,#fff1f7,#fff)}}.own-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin:22px 0}}.work-card{{background:#fff;border:1px solid #eee;border-radius:18px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.06)}}.work-card a{{color:inherit;text-decoration:none;display:block}}.work-card img,.placeholder{{width:100%;aspect-ratio:4/3;object-fit:cover;background:#f6f6f6;display:block}}.placeholder{{display:grid;place-items:center;color:#777}}.work-body{{padding:14px}}.work-body h2{{font-size:1rem;line-height:1.55;margin:8px 0}}.ad-badge{{font-size:.75rem;color:#a32d60}}.meta{{display:flex;justify-content:space-between;gap:10px;font-size:.9rem}}.cta{{display:inline-block;margin-top:10px;font-weight:700;color:#b32262}}.empty{{padding:28px;border:1px dashed #d9a9bd;border-radius:16px;background:#fff9fc}}.notice{{margin-top:18px;padding:14px;border-radius:12px;background:#fff7d8}}.own-note{{font-size:.9rem;color:#666}}</style></head><body><header><div class="wrap header-inner"><a class="logo" href="/"><span>オカズはよりどりみどり</span></a><nav class="topnav"><a href="/sale/">セール</a><a href="/ranking/">ランキング</a><a href="/momoiro-lab/">桃色ラボ</a><a href="/discover/">探す</a><a href="/guide/">初心者ガイド</a></nav></div></header><main><section class="own-hero"><div class="wrap"><span class="update-badge">FANZA同人 / 自作サークル</span><h1>桃色ラボ 作品一覧</h1><p>桃色ラボのFANZA同人作品をまとめています。商品情報はFANZA Webサービスの商品APIから取得し、自動更新します。</p><div class="notice"><strong>PRについて：</strong>アフィリエイトURLが取得できる作品はPRリンクとして掲載します。取得できない場合はFANZA公式ページへの通常リンクを使用します。</div></div></section><section class="section"><div class="wrap"><div class="entity-summary"><span class="entity-chip">{count_text}</span><span class="entity-chip">毎日自動更新</span><span class="entity-chip">18歳以上</span></div>{error_html}<div class="own-grid">{cards}</div><p class="own-note">API更新: {html.escape(generated_at)} / 販売状況・価格・配信条件はリンク先のFANZA公式情報を確認してください。</p></div></section></main><footer><div class="wrap"><div class="footer-links"><a href="/about.html">サイトについて</a><a href="/editorial-policy/">編集方針</a><a href="/privacy.html">プライバシー</a></div><div>© 2026 オカズはよりどりみどり. All rights reserved.</div></div></footer><div id="ageModal" class="age-modal" aria-modal="true" role="dialog"><div class="age-box"><h2>18歳以上ですか？</h2><p>このサイトは成人向けサービスに関する情報を扱います。18歳未満の方は閲覧できません。</p><div class="age-actions"><button id="ageYes">18歳以上です</button><a class="btn-secondary" href="https://www.google.com/">退出する</a></div></div></div><script src="/assets/affiliate-config.js"></script><script src="/assets/v6.js"></script><script src="/assets/app.js"></script><script src="/assets/ga4-config.js"></script><script src="/assets/ga4.js"></script><script src="/assets/affiliate-compliance.js"></script></body></html>'''


def _inject_home_link() -> None:
    if not HOME.exists():
        return
    text = HOME.read_text(encoding="utf-8")
    text = re.sub(r'<a href="/momoiro-lab/">桃色ラボ</a>', '', text)
    text = text.replace('<a href="/ranking/">ランキング</a>', '<a href="/ranking/">ランキング</a><a href="/momoiro-lab/">桃色ラボ</a>', 1)
    marker = '<!-- MOMOIRO_LAB_HOME -->'
    block = marker + '''<section class="section"><div class="wrap"><span class="update-badge">NEW / FANZA同人</span><h2>桃色ラボの作品</h2><p>当サイト運営サークル「桃色ラボ」のFANZA同人作品をまとめる専用ページを追加しました。公開後は商品APIから自動更新します。</p><p><a class="btn" href="/momoiro-lab/">桃色ラボ作品一覧を見る →</a></p></div></section>'''
    text = re.sub(r'<!-- MOMOIRO_LAB_HOME -->.*?(?=<section class="section"><div class="wrap">\s*<h2>運営・比較方針</h2>)', '', text, flags=re.S)
    target = '<section class="section"><div class="wrap">\n<h2>運営・比較方針</h2>'
    if target in text:
        text = text.replace(target, block + '\n' + target, 1)
    elif marker not in text:
        text = text.replace('</main>', block + '</main>', 1)
    HOME.write_text(text, encoding="utf-8")


def _update_sitemap() -> None:
    if not SITEMAP.exists():
        return
    text = SITEMAP.read_text(encoding="utf-8")
    url = f"{BASE_URL}/momoiro-lab/"
    if url in text:
        return
    today = datetime.now(timezone.utc).date().isoformat()
    entry = f"  <url><loc>{url}</loc><lastmod>{today}</lastmod></url>\n"
    text = text.replace("</urlset>", entry + "</urlset>")
    SITEMAP.write_text(text, encoding="utf-8")


def main() -> None:
    api_id = os.environ.get("DMM_API_ID", "").strip()
    affiliate_id = os.environ.get("DMM_API_AFFILIATE_ID", "").strip() or "okazumidori-990"
    generated_at = datetime.now(timezone.utc).isoformat()
    works: list[dict] = []
    error = ""
    if api_id:
        try:
            works = fetch_works(api_id, affiliate_id)
        except Exception as exc:
            error = f"API取得エラーのため前回表示を更新できませんでした: {exc}"
    else:
        error = "DMM_API_IDが未設定のため商品取得をスキップしました。"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"generatedAt": generated_at, "circle": CIRCLE_NAME, "affiliateId": affiliate_id, "works": works}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT_DIR / "index.html").write_text(_render(works, generated_at, error), encoding="utf-8")
    _inject_home_link()
    _update_sitemap()
    print(f"桃色ラボ作品ページ更新: {len(works)} works -> {OUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
