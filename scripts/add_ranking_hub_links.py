from pathlib import Path
import re

INDEX = Path("public/index.html")

START = "<!-- FANZA_RANKING_HUBS_START -->"
END = "<!-- FANZA_RANKING_HUBS_END -->"

BLOCK = '''<!-- FANZA_RANKING_HUBS_START -->
<section class="section"><div class="wrap">
<div style="display:flex;justify-content:space-between;gap:16px;align-items:end;flex-wrap:wrap">
<div><span class="update-badge">FANZA API 自動更新</span><h2>人気ランキングから探す</h2></div>
<a href="/ranking/">総合ランキングを見る →</a>
</div>
<p>総合ランキングだけでなく、女優・ジャンル・メーカー別に人気作品を比較できます。</p>
<div class="intent-grid">
<a class="intent-card content-card" href="/ranking/actress/"><strong>女優別ランキング</strong><span>人気作品から候補を自動抽出し、女優ごとの作品を人気順で掲載します。</span></a>
<a class="intent-card content-card" href="/ranking/genre/"><strong>ジャンル別ランキング</strong><span>ジャンルごとに人気作品を画像・価格・レビュー付きで比較できます。</span></a>
<a class="intent-card content-card" href="/ranking/maker/"><strong>メーカー別ランキング</strong><span>メーカーごとの人気作品をFANZA APIから自動取得して掲載します。</span></a>
<a class="intent-card content-card" href="/ranking/"><strong>総合ランキング</strong><span>人気・新着・高評価・セール候補をまとめて比較できます。</span></a>
</div>
</div></section>
<!-- FANZA_RANKING_HUBS_END -->'''


def main() -> None:
    if not INDEX.exists():
        print("Homepage missing; ranking hub link enhancement skipped.")
        return
    text = INDEX.read_text(encoding="utf-8")
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), "", text, flags=re.S)
    marker = '<section class="section" id="articles">'
    if marker not in text:
        raise RuntimeError("Homepage article section marker not found")
    text = text.replace(marker, BLOCK + "\n\n" + marker, 1)
    INDEX.write_text(text, encoding="utf-8")
    print("Added homepage internal links to actress, genre and maker ranking hubs")


if __name__ == "__main__":
    main()
