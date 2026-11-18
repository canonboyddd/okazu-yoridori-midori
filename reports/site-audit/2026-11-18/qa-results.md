# 検証結果の詳細（おかずよりどりみどり）

## 検証環境と安全対策

- ブラウザ: Playwright 1.65.0 / Chromium（ヘッドレス）。375×812 / 768×1024 / 1440×900。
- 計測: `navigator.webdriver`・除外 Cookie・計測エンドポイントの模擬応答で、本番計測への書き込みは 0 件。
- 広告: `al.fanza.co.jp` / `*.dmm.co.jp` / `*.fc2.com` などへの通信はすべて遮断。実トラッキング URL への到達は 0 件。
- 年齢確認: 「18歳以上です」は押していません。ダイアログが出た状態のまま、ページの HTTP 応答・タイトル・リンク属性のみを確認しました。
- スクリーンショット: 文章ページ（記事・about・privacy・ガイド一覧）のみ保存。

## 1. ページが開かずダウンロードされる不具合

### 再現（修正前・本番）

- `/articles/sale-guide`、`/about`、`/privacy` を開くと、ブラウザが「ダウンロードを開始」と判断しページが表示されない（3 画面幅とも）。応答ヘッダーは `Content-Type: application/octet-stream`。
- ガイド一覧からのリンク先 `/articles/<記事>.html` は 404。

### 原因

`public/articles/` の 30 ファイルと `public/about`、`public/privacy` が拡張子なしで保存されていました（2026-09-25 の初期コミットから）。`.html` 付きの `about.html` / `privacy.html` も別に存在し、canonical は `.html` 付き URL を指していましたが、その URL は拡張子なしの URL へ転送され、転送先がダウンロードになる状態でした。

### 対応

- 30 記事を `<記事>.html` に改名、拡張子なしの `about` / `privacy` を削除、canonical をクリーン URL（`/about`、`/privacy`、`/articles/<記事>`）に統一。
- `scripts/normalize_public_routes.py` を追加。デプロイ時に復元される本番スナップショットに拡張子なしの HTML が残っていても自動で修復します。全デプロイ経路が通る `scripts/run_home_optimizer_safe.py` から実行。
- `scripts/enhance_fanza_seo.py`: サイトマップに編集ページ（記事・ガイド等、noindex 以外）を追加。
- `.github/workflows/pages-deployment.yml` / `daily-data-deploy.yml`: デプロイ前に「拡張子なしの HTML が 0 件」「記事ファイルとサイトマップの記事 URL が存在」を検査。

### 確認（修正後・本番）

| 確認 | 結果 |
|---|---|
| 18 パス × 3 画面幅の表示 | すべて `text/html` で表示（404 確認用の 1 パスは 404） |
| `/about.html`、`/articles/sale-guide.html` | クリーン URL へ転送され表示 |
| サイトマップ | 16,038 URL。全件 200・HTML・canonical 一致・noindex なし・タイトル重複 0 |
| 存在しない URL | 404 |

## 2. 年齢確認

| ページ種別 | ダイアログ |
|---|---|
| トップ、セール、ランキング、作品一覧、作品詳細、検索、FC2、ガイド一覧、記事 | 表示（背後はスクロール固定・リンク操作不可） |
| `/about`、`/privacy`、`/editorial-policy/` | 表示なし（既存の仕様。今回は変更していません） |

## 3. 広告リンクの静的確認

11 ページ種別 × 2 画面幅でリンク属性を集計しました（年齢確認の背後・クリックなし）。

| リンク先 | 確認内容 |
|---|---|
| `al.fanza.co.jp`（作品リンク） | すべて `af_id=okazumidori-990`、`ch=api`、`rel` に sponsored と nofollow、新規タブ。作品詳細 2 ページで作品 ID とリンク先 ID が一致 |
| `cnt.affiliate.fc2.com` | `rel="sponsored nofollow noopener noreferrer"`、新規タブ |
| `affiliate.dmm.com` | DMM Web サービスのクレジット表記リンク |
| `adult.contents.fc2.com`（`/fc2-adult/` の 11 本） | アフィリエイトパラメータなしの通常リンク |

PR 表記は確認した全ページ種別にありました。

## 4. テスト

| テスト | 結果 |
|---|---|
| `python -m unittest tests/test_public_routes.py`（今回追加） | 8/8 合格 |
| `node --test tests/revenue-collector.test.mjs`（既存） | 合格 |
| 既存のブラウザテスト（フィクスチャ使用） | 4/4 合格 |
| デプロイ後検査の本番再生（`production-qa.yml` 内のページ検査をそのまま実行） | 18 ページ種別すべて合格 |

`tests/test_public_routes.py` の内容: 拡張子なし HTML が 0 件、記事リンクの実体が存在、canonical がクリーン URL、スナップショット残骸の修復、サイトマップへの編集ページ追加、Production QA の埋め込みスクリプトが文法的に正しく現在の URL と一致すること。

## 5. GitHub Actions

| コミット | ワークフロー | 結果 |
|---|---|---|
| `03dd18e` | Fast Cloudflare Pages deploy（run 44337491343） | 成功 |
| `03dd18e` | Production QA（run 44337991197） | **失敗**（検査側が旧 canonical `/about.html` を期待していたため） |
| `f2bac30` | Fast Cloudflare Pages deploy（run 44351358558） | 成功 |
| `f2bac30` | Production QA（run 44351935780） | 成功 |

Production QA の失敗は私の修正に検査が追随していなかったことが原因で、サイト側の不具合ではありません。検査を現在の URL に合わせたうえで、`Content-Type` の検査とガイド記事 1 本を対象に追加したので、今後「ページがダウンロードになる」状態はこの検査で検出されます。

## 6. 変更していないもの

年齢確認の仕組み、FANZA のアフィリエイト ID、作品データ、D1・計測の設定、`fanza-link-hotfix.yml` と `product-description-enrich.yml`（どちらも `run_home_optimizer_safe.py` を通るため自動修復の対象）。
