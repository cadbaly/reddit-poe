# r/PathOfExile2 Information まとめ(日本語化)

r/PathOfExile2 の **Information フレア** かつ **upvote 10 以上** の投稿を取得し、
日本語化して **1投稿1枚のHTML** に出力するツール。

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

## 使い方(手動・1回)

```bash
python3 fetch.py        # 1) 該当投稿を取得 → data/pending.json
#   2) data/pending.json を翻訳し data/translated.json を作成
#      形式: [{"id": "...", "title_ja": "...", "body_ja_html": "<p>...</p>"}, ...]
python3 render.py       # 3) HTML生成 + processed.json 更新
```

閲覧は `output/index.html` をブラウザで開く。

## 翻訳について

翻訳は **Claude が実施**する(本リポジトリの運用では機械翻訳APIは使わない)。
`fetch.py` 実行後、`data/pending.json` の各投稿を Claude が日本語化して
`data/translated.json` を書き出し、`render.py` でHTML化する。

## 定期実行

`processed.json` で処理済みを記録するため、繰り返し実行しても**新規投稿だけ**が
追加される。低負荷の観点から **1日1回程度**を推奨(Information+10upvoteの母数は少ない)。

定期実行の流れ(1サイクル):
1. `python3 fetch.py`
2. Claude が `data/pending.json` → `data/translated.json` を作成
3. `python3 render.py`

Claude のルーティン(スケジュール実行)に上記サイクルを登録すれば自動化できる。
