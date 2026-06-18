# r/PathOfExile(2) Information まとめ(日本語化)

**r/PathOfExile2(PoE2)** と **r/PathOfExile(PoE1)** の **Information フレア** かつ
**upvote 10 以上** の投稿を取得し、日本語化して **Notion データベースに1投稿1ページ**で保存するツール。

対象サブレディットは引数で切替(既定 `PathOfExile2`)。データは `data/<sub>/` に分離:
```
python3 fetch.py PathOfExile     # PoE1
python3 fetch.py PathOfExile2    # PoE2
```

保存先 Notion DB(ゲームごと):
- PoE2: **r/PathOfExile2 Information まとめ** (data source `bc65a10a-e5bf-45ae-b3d2-aaa9fe768643`)
- PoE1: **r/PathOfExile Information まとめ** (data source `4da0435e-828a-42ce-b53a-2318a614d9d5`)

## なぜこの構成か(取得方法)

Reddit の公開 `.json` API は現在この環境からは 403(Blocked)になる。代わりに:

| 取得物 | 経路 | 備考 |
|---|---|---|
| 本文・タイトル・URL・投稿日時 | フレア検索 **RSS** (`search.rss?q=flair_name:"Information"`) | フレアで絞り込み済み |
| スコア(upvote) | **old.reddit** 検索HTML の `search-score` | RSSには無いため補完 |

両者を投稿IDで突き合わせ、`score >= 10` を抽出する。
**1実行あたりのリクエストは2本のみ**、間に4秒の待機を入れて負荷を抑えている。

## ファイル構成

```
fetch.py            取得+絞り込み+コメント取得 → data/pending.json を生成
mark_processed.py   translated.json の id を processed.json に記録(重複防止)
data/
  pending.json      未処理の該当投稿(原文・画像・動画・コメント) … fetch.py が生成
  translated.json   日本語訳+コメント要約                       … 翻訳者が作成
  processed.json    処理済みID台帳(重複防止)                    … mark_processed.py が更新
```

## 運用フロー(Notion・1サイクル)

1. `python3 fetch.py` — 該当投稿＋**上位コメント(最大10件)**を取得 → `data/pending.json`
   （各投稿は `comments: [{author, score, body}, ...]` を持つ。old.reddit のコメント
   ページを1投稿1リクエストで取得、間に待機を入れて低負荷）
2. 各投稿を **Claude が日本語化**、さらに**コメントの反応を日本語で要約** → `data/translated.json`
   形式: `[{"id": "...", "title_ja": "...", "body_ja_html": "<p>...</p>", "comments_summary_ja": "..."}, ...]`
3. Notion DB(data source `bc65a10a-...`)に1投稿1ページで作成
   - プロパティ: タイトル / スコア / 投稿者 / 投稿日 / 元URL / Reddit ID
   - 本文は翻訳テキスト(Notion Markdown)
   - **画像**: `pending.json` の `images`(i.redd.it の元画像URL)をページ先頭に
     `![caption](url)` で埋め込む。Notion連携にバイナリアップロードが無いため、
     Reddit側の安定URL(i.redd.it・署名なし)を指す外部埋め込みで表示する。
   - **動画**: `pending.json` の `video` は**ダウンロード/埋め込みせず**、先頭に
     callout でリンクのみ置く(重いため。サムネがあれば併記)。
   - **コメントの反応**: 本文の後に「## 💬 コメントの反応」見出しを付け、
     `comments`(上位コメント)の論調を日本語で2〜4文に要約して載せる。
4. `python3 mark_processed.py` — `data/processed.json` を更新(重複防止)
5. `data/` の変更を git commit & push

`processed.json` で処理済みを記録するため、繰り返し実行しても**新規投稿だけ**が
Notion に追加される。低負荷の観点から **1日1回**を推奨。

## 定期実行(ローカル半自動)

クラウドルーティンは外部通信不可のため廃止。現行はローカル cron + Claude セッションの半自動:

- **取得**: ローカル cron が毎日 08:50 JST に `refresh.sh` を実行 → 両サブの `pending.json` を更新・push。
  ```
  50 8 * * * /home/koezuka/reddit-poe/refresh.sh
  ```
- **翻訳＋Notion投稿**: Claude セッションで「更新して」と頼むと、Claude が pending を翻訳し
  Notion にページ作成 → `mark_processed.py <sub>` → commit/push。

> `diag.py` はクラウド等のネットワーク到達性を調べる診断用(通常運用では不要)。
