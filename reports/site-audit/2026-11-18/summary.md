# おかずよりどりみどり サイト監査サマリー

- 監査日: 2026-11-18〜19（JST）
- 本番URL: https://okazu-yoridori-midori.pages.dev/ （canonicalホスト: 同じ）
- リポジトリ: `canonboyddd/okazu-yoridori-midori`（public）
- main: 監査開始時 `608cb06` → 監査後 `f2bac30`
- デプロイ: GitHub Actions（`Fast Cloudflare Pages deploy` / `Daily FANZA data refresh`）から `wrangler pages deploy`
- 収益化: DMM/FANZA アフィリエイト（`af_id=okazumidori-990`、`ch=api`）、FC2 アフィリエイト

## 結論

重大な不具合を 1 件確認し、修正して本番で再検証しました。年齢確認は変更していません。

| 重要度 | 見つかった問題（本番で再現） | 対応 | 本番確認 |
|---|---|---|---|
| P1 | **ガイド記事 30 本と `/about` `/privacy` が、ページとして表示されずファイルとしてダウンロードされていた**（`Content-Type: application/octet-stream`）。サイト内リンク先の `/articles/<記事>.html` は 404 | ファイルに `.html` を付けてクリーン URL で配信。全デプロイ経路で自動修復する処理とテストを追加 | 済 |
| P2 | 上記 30 記事など編集ページ 40 本がサイトマップに入っていなかった | サイトマップ生成に編集ページを追加（15,998 → 16,038 URL） | 済 |
| CI | 修正後、デプロイ後検査（Production QA）が旧 canonical（`/about.html`）を期待して失敗 | 検査を現在の URL に合わせ、Content-Type の検査を追加 | 済（成功） |

原因は、2026-09-25 の初期コミット以来、これらのページが拡張子なしのファイル名で保存されていたことです。Cloudflare Pages は拡張子のないファイルを HTML として配信しません。

## 主要な検証結果（本番）

| 検証 | 修正前 | 修正後 |
|---|---|---|
| 記事・about・privacy の表示（375/768/1440px） | ダウンロード開始（表示されない） | 200・`text/html`・タイトルと本文を表示 |
| `/articles/sale-guide.html` などの旧リンク | 404 | 308 でクリーン URL へ転送 |
| サイトマップ全 URL | 15,998 件すべて 200 | 16,038 件すべて 200・HTML・canonical 一致・noindex なし |
| 年齢確認ダイアログ | 作品系・ガイド系ページで表示 | 変更なし（記事ページでも表示されることを確認） |
| GitHub Actions | — | Fast deploy 成功、Production QA 成功（run 44351935780） |

## 年齢確認と広告リンク

- 年齢確認ダイアログは**一度も代行で通過していません**。そのため広告リンクのクリック試験は行わず、リンク属性の確認のみです（`static_only`）。
- ダイアログ表示中は背後のリンクが操作不可（inert）であることを確認しました。
- FANZA の作品リンクはすべて `af_id=okazumidori-990`・`ch=api`・`rel="sponsored nofollow noopener noreferrer"`・新規タブ。作品ページでは作品 ID とリンク先 ID が一致（確認した 2 作品で不一致 0）。
- `/fc2-adult/` の `adult.contents.fc2.com` への 11 本はアフィリエイトパラメータのない通常リンクです（`rel="noopener noreferrer"`）。
- 成人向け画像を含むスクリーンショットは保存していません（[screenshots/](screenshots/) は文章ページのみ）。

明細は [affiliate-links-audit.csv](affiliate-links-audit.csv)、数値は [browser-results.json](browser-results.json)、テストは [qa-results.md](qa-results.md)、残課題は [next-actions.md](next-actions.md) を参照してください。

## 確認できていないこと

- 年齢確認後の画面でのクリック動作（許可が必要）。
- 監査の終盤（2026-11-18 17:30 UTC ごろ〜）、`/api/*` が一時的に応答しない状態になりました（ページ表示は可能。復旧見込み: 2026-11-19 09:00 JST ごろ）。経緯はオーナー向けの全体報告に記載しています。
- DMM/FANZA・FC2 の管理画面（承認状態・成果・クリック数）。**未取得**です。
- 約 16,000 ページの大半を占める作品ページの個別の表示確認（HTTP とメタ情報は全件、ブラウザ表示は代表テンプレートのみ）。
