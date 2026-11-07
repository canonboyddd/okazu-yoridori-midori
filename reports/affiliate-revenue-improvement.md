# おかずよりどりみどり 広告導線・計測改善

監査日: 2026-11-08（JST）。最新main `3060771b25b9c56c08720073cc8586caf363fc27`、本番Cloudflareの配布コミット `f00d1d0f3b339a0e4adf87618854f1d6a007e775` を別々に確認。カタログはGitHub Actionsの生成データsnapshotを復元する既存経路を維持。

## 現状の広告・問題と重要度

- FANZA/DMMは既存設定の一般リンク用IDとAPI用IDを保持。作品詳細上下、ランキング/セール/月額比較の公式リンク、FC2関連バナーがある。設定上のapprovedを確認したがASP管理画面での現在の承認・広告条件は未取得。
- P1: `ga4.js` と共通central-trackerが並行送信。FANZA/FC2バナーにも個別GAクリックlistenerがあり、1操作が重複し得る。
- P1: 画面内到達の共通分母がない。FC2は既存ga4.jsの公式クリック検出対象外。
- P1: GA4はbot/owner/QA除外前に起動。ページクエリ・参照元URL・リンクURL・任意検索入力が計測へ入り得る。
- P2: 作品詳細CTAが「見る」「公式で確認」のみで販売ページと月額等の違いを把握しにくい。
- P1（追加点検）: 人気女優・別名義・検索の生成ページに年齢確認HTMLがなく、直接流入でダイアログが出ない。共通app.jsで欠落を補完し、確認前の背景操作をinertで制限。情報/プライバシーページは閲覧可能なまま維持。
- P1（追加点検）: catalog-search.jsが検索入力をplacementへ埋め込み、GA4へ渡していた。検索語等を送らず固定placementと件数だけへ変更し、GA4でも許可項目/値を検査する。
- カタログ原本、別名義統合、ランキング根拠、商品APIのID、既存affiliateURLは変更/削除していない。販売終了を推測して商品を削除しない。

## 修正した導線と理由

| ファイル | 変更前→変更後 | 意図 |
|---|---|---|
| `public/assets/app.js` | central-tracker追加起動→削除、ga4.jsを唯一の計測担当へ | 二重PV/クリックを防止 |
| `public/assets/fanza-products.js`, `fc2-affiliate-banners.js` | バナー専用GAクリック→共通委任listener | FANZA/FC2とも1操作=各collectorに1イベント |
| `public/assets/ga4.js` | クリック中心→50%以上1秒の画面内広告表示、native click/中クリックのみ、listing/detail表示、FC2判別 | 一覧→詳細→公式クリックの離脱箇所を分析可能にする |
| 同上 | GA4だけbot除外なし→GA4と中央で共通のbot/QA/owner除外。生URL/クエリ/自由入力を除外 | 巡回による水増しと不要な入力情報送信を防ぐ |
| `public/assets/dynamic-product.js` | 汎用ボタン→価格・配信条件/この作品の販売ページを明示 | 月額・販売・セールを混同せず判断できる |
| `lib/revenue-collector.js`, `functions/api/ops-collect.js` | 任意JSON転送→項目/イベント許可リスト、16KiB制限、QA/UA除外、参照元ホスト名のみ | サーバーでも個人情報と自動操作の混入を抑制 |

年齢確認を維持し、そのモーダルが画面上を覆っている間は広告表示イベントを発生させない。PR/sponsored/nofollowと既存のデザインを保持する。広告報酬による順位変更・架空評価・新規ASPリンク作成は行っていない。

snapshot復元型の別deployにもapp.js/ga4.js/FC2 runtimeを同時overlayするよう、既存hotfix/alias/description workflowsを整合させた。自動QAがASPクリックURLを実際にGETしていたため、URLのホスト・ID・channel・公式遷移先の厳密なローカル検証へ変更した。ライブASP承認/リンク生存確認は未実施と明示し、外部クリックをテスト成果として発生させない。

## 計測可能な実数値と未取得

Cloudflare D1を2026-11-08に読み取り専用で集計。過去30日raw page_view 20,975件/20,972セッション、scroll_90 19,002件/19,002セッション、affiliate_impression 3件/3セッション。多数の一見一セッション巡回が疑われ、これを実ユーザーPV/有効CTRへ変換しない。UAフィルタだけでは人間を完全識別できない。旧データは削除せず、収集仕様変更前後を分ける。

ASP成果/確定報酬とGSCは中央のインポート表にレコードなし＝未取得。実収益0円という意味ではない。ASP実申込・購入や有料アクセスを自動発生させず、広告の外部遷移試験はモック/遮断する。販売元の購入可能性・現在の価格/配信・全カタログのリンク有効性はASP/APIの実データが揃うまで保証しない。

## テストと実画面

- collector境界4テスト: QA/owner/botが送信0、クロスオリジン拒否、大きすぎるpayload拒否、メール/キー/token/queryの除去、中央障害時502を合格。
- Pythonリンク契約2テスト合格、既存別名義DB検証43 identities/94 namesが合格。生成された派生JSONは原本として追加していない。
- 年齢確認の欠落/既存あり/情報ページの5経路を中立なfixtureで検証し、全件合格。年齢ボタンを押さず、実際の年齢確認を代理で送信していない。
- `scripts/qa-revenue-browser.mjs`, `qa-age-browser.mjs`, `qa-fc2-browser.mjs` は単独repoで再実行可能（Playwrightが別の場所にある場合は `PLAYWRIGHT_MODULE` を明示）。非掲載4経路のFC2 banner通信0、掲載セール経路は表示要素あり・ASP通信は遮断を合格。本文の一覧/詳細イベントも年齢確認と非表示タブの背後では発生させない。
- 生成ホームの選択結果にも独自GA4 click listenerがあったため、生成元 `scripts/optimize_home_for_immediate_discovery.py` を共通計測用metadataだけに変更。`qa-home-chooser.mjs` は生成元の実JSと中立な商品fixtureを使い、native click1回→中央1件/GA4 1件、ASP通信0を確認した。`npm run test:browser` で4系統を実行できる。
- カタログID照合はquick4群169行＋100shard中3shardの1500行、合計1669行すべて一致。保護静的商品ページのCTA3本も一致。全カタログ保証ではなく、重複行を含み得る。現在の `video.dmm.co.jp/av/content/?id=...` と旧cid形式を区別し、URL/IDを勝手に再構成していない。
- 通信遮断したEdge実ブラウザ: 画面内広告表示のみ、画面外広告なし、合成click無計測、native click1回=1クリック、FC2 click1件、QA queryで全送信0件、クエリ非送信を合格。
- 変更前本番セールページ375/768/1440pxはHTTP200、JS例外0、横はみ出し0。年齢確認を保持。第三者画像・広告・解析は検証時に遮断。変更前後証拠は `reports/evidence/`。
- データ生成は既存GitHub Actionsの秘密設定とsnapshotを使用。Fast deploy・Production QAの成功結果とコミットを `reports/production-verification.json` に記録済み。

## 継続判定・残るブロッカー

新仕様の同一期間・同一ページ/案件/配置/端末の表示数を分母にCTR、表示到達セッション、クリックセッションを別集計する。PV・クリック・クリックセッション・ASP発生・確定報酬を合算しない。十分な表示/クリック後、ASP CSVを取り込んで発生/承認/取消を照合するまで増収達成とはしない。

GSC・ASP CSV・管理画面上の承認/規約/販売終了情報は未取得。今回の変更は計測の単一化が中心であり、大規模カタログ全件の販売元検証は未完了。重複URL/404/別名義の既存生成QAは既存経路に沿って継続する。ASP契約内容を推測したID修正や、販売終了の推測削除は行わない。

## 本番反映中に判明した既存経路の問題

初回実装コミット `c1bec3211f3baf3050bd4be23b71bebb563622e6` のFast deployは、CI Nodeランタイムで廃止された実験フラグと、production-public artifactの期限切れで停止。正式なpackage.jsonのtype:moduleに切り替え `adf1821` で回帰合格。既存定期dispatcherはcheckoutがないのにリポジトリを省略してghを呼び、直近の更新が失敗していた。`947d519b765de93e8bfdd27527e93412f0da711c` で `--repo "$GITHUB_REPOSITORY"` を明記し、dispatcher変更時の既存更新実行、保存期間7日（二回の3日周期）へ修正。

既存dispatcher run `42392509113` とDaily FANZA refresh `42392515177` がsuccess。新規ホスティング経路・新しいASP ID・D1データ削除は追加していない。生成途中を本番へ配信せず、既存ビルド検証を満たした後に既存Cloudflare deployで反映した。

## 最終本番結果

- 最新公開実装 `58873149f2234b868c8b7dab5abad5fa3798d496`。Cloudflare production deployment `737d41b7-59bb-40d0-aaf9-f352d8d67366` がsuccess。Fast deploy `42395674069` と既存Production QA `42395879728` がともにsuccess。
- 後続の `c477d70` はreports-only変更を既存Fast deployから除外する運用設定。監査追記のmainと公開artifactのSHA差は意図的であり、public runtimeの差ではない。
- 主要ページ/ランキング/分類/月額比較/FC2/動的商品、robots、sitemap、catalog auditは200、未知URLは404。QA collectorは明示的除外応答。app/ga4/catalog-search/FC2の4JSは本番とソースのLF正規化SHA256が一致。
- 本番構造監査: catalog 50,000、重複ID0、無効ID0、形式上のaffiliate link不備0、sitemap404Risk0。これはASP管理画面や販売先の生存確認ではない。メーカー未取得0、ジャンル未取得50、出演者未取得20,033、全分類あり29,953という実データの欠損をそのまま保持し、架空補完していない。
- 既存カタログ・検索・別名義・動的商品・関連分類のProduction QAを第一者URL以外の強制遮断下でも合格。ログはUTF-8で `reports/evidence/production-qa.log` に保存。
- Android/タブレット/PC UA、375/768/1440pxの年齢確認画面でJS例外0・横はみ出し0。年齢確認を代行送信していないため、本番本文の広告クリックや年齢確認後の外部画像表示は実操作で確認していない。本文機能/イベントは中立fixtureとHTTPで検証。第三者画像・ASP・解析通信は遮断した。
- 5サイト統合QAは5tests成功、失敗/skip/flaky0。本サイトの15,954 sitemap URLと47ホーム内部リンクを含む全16,787 URL/155リンクでdirect200・canonical・noindex整合・重複なしを確認。通常PVの単一化とbot/QA送信0も確認した。`five-site-final-summary.json`参照。

## 未提供の公式商品説明と補助ジョブ

補助description enrichment `42395124831` attempt2は50,000商品すべて照合したが、今回APIで公式commentを取得できた商品は0、更新行0だった。`Verify description enrichment` が「公式説明なし」で停止し、デプロイへ進まなかった。最新Fastの配信・既存Production QA・5サイト統合QAの成功とは区別する。成功に見せるための検査削除・架空の商品説明・レビュー作成は行っていない。

公開ページは取得済み価格/日付/メーカー/分類等の事実要約と関連作品を用いる既存の代替表示で動作する。公式説明がAPI等の正規データとして取得可能になった場合のみ、この補助処理を再実行し、引用元/内容/保持済みデータとの整合と元の検証を通す。現在のASP承認・確定報酬・全販売先生存も引き続き未取得。

旧補助ジョブを停止する案は、保存済み認証情報の取得を伴うため自動承認レビューに拒否された。停止スクリプトは実行されず、認証情報も取得していない。その経路は再試行せず、既存ジョブの上記の自然終了を確認した。Computer UseもURL確認の制約で終了し、既存GitHubワークフローで作業を継続した。
