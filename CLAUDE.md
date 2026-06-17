# CLAUDE.md

このリポジトリで作業するClaude向けのガイド。詳細な使い方は `README.md` を参照。

## 目的

**r/PathOfExile2(PoE2)** と **r/PathOfExile(PoE1)** の **Information フレア** かつ
**upvote 10 以上** の投稿を取得し、日本語化して **Notion データベースに1投稿1ページ**で保存する。
ゲームごとに別Notion DB・別ルーティンで、毎日クラウド実行。

対象サブレディットは引数で切替（既定 PathOfExile2）。データは `data/<サブレディット名>/` に分離:
```
python3 fetch.py PathOfExile          # PoE1
python3 fetch.py PathOfExile2         # PoE2（引数省略時もこれ）
python3 mark_processed.py PathOfExile # 同上、台帳更新も同じ引数で
```

## 重要な制約・前提（非自明なので必読）

- **Reddit の公開 `.json` / 通常HTML は 403 (Blocked)**。OAuth登録なしのAPIは使わない方針。
  代わりに次の経路を使う:
  - 本文・タイトル・URL・投稿日時・画像・動画 → **フレア検索RSS**
    (`https://www.reddit.com/r/PathOfExile2/search.rss?q=flair_name:"Information"&restrict_sr=1&sort=new`)
  - スコア(upvote) → **old.reddit 検索HTML** の `search-score`（RSSにスコアが無いため補完）
  - コメント → **old.reddit のコメントページ** (`https://old.reddit.com/comments/<id>/?sort=top`)
  - リクエストには**ブラウザUA + Accept-Language**が必須（無いと403/429）。`fetch.py` の `HEADERS` 参照。
- **低負荷が要件**。1サイクルのリクエストは「RSS + 検索 = 2本」＋「pending投稿数分のコメント取得」。
  各コメント取得の間に `COMMENT_DELAY` 秒の待機を入れている。むやみにリトライしない。
- **翻訳はClaudeが実施**（機械翻訳APIは使わない）。各実行時に翻訳＋コメント要約を作る。
- **画像はNotionにバイナリ保存できない**（連携にアップロード機能なし）。`i.redd.it` の安定URLを
  `![](url)` で外部埋め込み（Notion側CDNでキャッシュ表示。正本はReddit依存）。
  preview.redd.it は署名付きでhotlink不可のため `i.redd.it/<file>` に正規化している。
- **動画はダウンロード/`<video>`埋め込みしない**（重いため）。callout でリンクのみ。

## ファイルとデータフロー

```
fetch.py          取得+絞り込み(score>=10)+コメント取得 → data/<sub>/pending.json
                  （pending.json は processed.json で既処理を除外した未処理分のみ）
mark_processed.py translated.json の id を processed.json に記録（重複防止）
data/<sub>/pending.json    未処理投稿（原文・images・video・comments）        ← fetch.py が生成
data/<sub>/translated.json 日本語訳（id/title_ja/body_ja_html/comments_summary_ja） ← Claudeが作成
data/<sub>/processed.json  処理済みID台帳                                    ← mark_processed.py が更新
```
（`<sub>` は `PathOfExile` または `PathOfExile2`）

1サイクル: `python3 fetch.py <sub>` → Claudeが翻訳＋コメント要約して `data/<sub>/translated.json` 作成 →
Notion create-pages で1投稿1ページ作成 → `python3 mark_processed.py <sub>` → `data/<sub>/` を commit & push。

Notionページ本文の構成: (a)動画callout → (b)画像 `![](url)` → (c)翻訳本文＋末尾に原文リンク →
(d)`## 💬 コメントの反応`（要約）。

## Notion 保存先（ゲームごとに別DB）

プロパティはどちらも: タイトル(title) / スコア(number) / 投稿者(text) / 投稿日(date) / 元URL(url) / Reddit ID(text)。
日付は `date:投稿日:start`（ISO8601）と `date:投稿日:is_datetime=1` で設定。

- PoE2 DB「r/PathOfExile2 Information まとめ」 data_source_id: `bc65a10a-e5bf-45ae-b3d2-aaa9fe768643`
- PoE1 DB「r/PathOfExile Information まとめ」 data_source_id: `4da0435e-828a-42ce-b53a-2318a614d9d5`

## 定期実行（クラウドルーティン・2本）

- PoE2: routine_id `trig_01Wx5sup3AaYLD3hzhUa1AFm` / cron `0 0 * * *`（毎日 09:00 JST）
- PoE1: routine_id `trig_01QHAvC7PR5uzPHxWSidMht3` / cron `30 0 * * *`（毎日 09:30 JST、Reddit同時アクセス回避でずらし）
- どちらも model: `claude-opus-4-8`、Notion MCPコネクタ接続済み、source: このGitHubリポ(master)
- ルーティンのプロンプトを変える場合は `RemoteTrigger`(action=update) を使う。
  **クラウド環境はローカルマシンにアクセスできない**（出力はNotion＋GitHubのみ）。
- ⚠ クラウド実行には**GitHubの再認証が必要**（未対応だと `github_repo_access_denied` で失敗）。
  https://claude.ai/code/routines から再認証する。

## 留意

- GitHub: https://github.com/cadbaly/reddit-poe (private, master, gh account=cadbaly)
- ローカルHTML出力（旧 `render.py` / `output/`）は廃止済み。Notion一本化。
- 設定値は `fetch.py` 冒頭の定数: `MIN_SCORE=10` / `LIMIT=25` / `COMMENT_LIMIT=10` / `COMMENT_DELAY=4`。
- コミットメッセージ末尾には `Co-Authored-By: Claude <noreply@anthropic.com>` を付ける。
