# r/PathOfExile2 Information まとめ(日本語化)

r/PathOfExile2 の **Information フレア** かつ **upvote 10 以上** の投稿を取得し、
日本語化して **Notion データベースに1投稿1ページ**で保存するツール。

保存先 Notion DB: **r/PathOfExile2 Information まとめ**
(data source: `bc65a10a-e5bf-45ae-b3d2-aaa9fe768643`)

> ローカルHTML出力(`render.py` → `output/`)もレガシーとして残してあるが、
> 現行の運用先は Notion。

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
fetch.py            取得+絞り込み → data/pending.json を生成
render.py           pending.json + translated.json → output/*.html を生成
data/
  pending.json      未処理の該当投稿(原文)        … fetch.py が生成
  translated.json   日本語訳(id/title_ja/body_ja_html) … 翻訳者が作成
  processed.json    処理済みID台帳(重複出力防止)   … render.py が更新
output/
  <id>.html         各投稿の日本語ページ
  index.html        一覧(スコア順)
```

## 運用フロー(Notion・1サイクル)

1. `python3 fetch.py` — 該当投稿を取得 → `data/pending.json`
2. 各投稿を **Claude が日本語化** → `data/translated.json`
   形式: `[{"id": "...", "title_ja": "...", "body_ja_html": "<p>...</p>"}, ...]`
3. Notion DB(data source `bc65a10a-...`)に1投稿1ページで作成
   - プロパティ: タイトル / スコア / 投稿者 / 投稿日 / 元URL / Reddit ID
   - 本文は翻訳テキスト(Notion Markdown)
4. `python3 mark_processed.py` — `data/processed.json` を更新(重複防止)
5. `data/` の変更を git commit & push

`processed.json` で処理済みを記録するため、繰り返し実行しても**新規投稿だけ**が
Notion に追加される。低負荷の観点から **1日1回**を推奨。

## 定期実行(クラウドルーティン)

毎日 09:00 JST に上記サイクルをクラウドで自動実行する Claude ルーティンを登録済み。
クラウド側で fetch → 翻訳(Opus) → Notion作成 → `mark_processed.py` → commit/push する。

## レガシー: ローカルHTML出力

`python3 render.py` で `output/<id>.html` と `output/index.html` を生成できる
(Notion移行前の機能。`pending.json` + `translated.json` から生成)。
