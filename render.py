#!/usr/bin/env python3
"""pending.json(原文) + translated.json(日本語訳) を結合し、1投稿1HTMLを出力する。

translated.json は Claude が作成する翻訳ファイル。形式:
  [{"id": "...", "title_ja": "...", "body_ja_html": "<p>...</p>"}, ...]

出力:
  output/<id>.html      … 各投稿のページ
  output/index.html     … 一覧
  data/processed.json   … 処理済み id を追記(再実行時の重複出力防止)
"""
import json
import re
import html
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
PENDING_FILE = DATA / "pending.json"
TRANSLATED_FILE = DATA / "translated.json"
PROCESSED_FILE = DATA / "processed.json"

SUB = "r/PathOfExile2"


def extract_md(body_html: str) -> str:
    """RSSのcontentから本文の <div class="md">…</div> 部分だけを取り出す。
    画像サムネのtableや submitted by / [link] / [comments] のフッタは除去。"""
    m = re.search(r'<div class="md">(.*?)</div>', body_html, re.S)
    return m.group(1).strip() if m else ""


def fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return iso


PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_ja}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, "Segoe UI", "Hiragino Kaku Gothic ProN", "Noto Sans JP", Meiryo, sans-serif;
          line-height: 1.8; max-width: 760px; margin: 0 auto; padding: 24px 18px; }}
  h1 {{ font-size: 1.5rem; line-height: 1.4; }}
  .meta {{ color: #888; font-size: .85rem; margin-bottom: 1.5rem; }}
  .meta a {{ color: inherit; }}
  .score {{ background: #ff4500; color: #fff; padding: 1px 8px; border-radius: 10px; font-weight: bold; }}
  .body {{ font-size: 1.02rem; }}
  .body img {{ max-width: 100%; height: auto; }}
  details {{ margin-top: 2.5rem; border-top: 1px solid #ccc8; padding-top: 1rem; }}
  summary {{ cursor: pointer; color: #888; }}
  .orig {{ color: #999; font-size: .95rem; }}
  .back {{ display: inline-block; margin-bottom: 1rem; color: #888; }}
</style>
</head>
<body>
<a class="back" href="index.html">← 一覧へ</a>
<h1>{title_ja}</h1>
<div class="meta">
  <span class="score">▲ {score}</span>
  ｜ {sub} ｜ {author} ｜ {date}
  ｜ <a href="{link}" target="_blank" rel="noopener">元投稿を開く</a>
</div>
<div class="body">
{body_ja}
</div>
<details>
  <summary>原文(English)を表示</summary>
  <div class="orig"><h2 class="orig">{title_en}</h2>{body_en}</div>
</details>
</body>
</html>
"""

INDEX = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>r/PathOfExile2 Information まとめ(日本語)</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "Noto Sans JP", Meiryo, sans-serif;
          line-height: 1.7; max-width: 760px; margin: 0 auto; padding: 24px 18px; }}
  h1 {{ font-size: 1.4rem; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: 10px 0; border-bottom: 1px solid #ccc8; }}
  a {{ text-decoration: none; color: inherit; }}
  .score {{ background: #ff4500; color: #fff; padding: 1px 8px; border-radius: 10px;
            font-weight: bold; font-size: .85rem; margin-right: 8px; }}
  .d {{ color: #888; font-size: .8rem; }}
</style>
</head>
<body>
<h1>r/PathOfExile2 — Information(upvote 10+)日本語まとめ</h1>
<p class="d">生成: {now} ／ {count}件</p>
<ul>
{items}
</ul>
</body>
</html>
"""


def main():
    pending = {p["id"]: p for p in json.loads(PENDING_FILE.read_text())}
    translated = json.loads(TRANSLATED_FILE.read_text())

    processed = {}
    if PROCESSED_FILE.exists():
        processed = json.loads(PROCESSED_FILE.read_text())

    written = []
    for t in translated:
        pid = t["id"]
        src = pending.get(pid)
        if not src:
            print(f"  ! {pid}: pending.json に原文なし。スキップ")
            continue
        page = PAGE.format(
            title_ja=html.escape(t["title_ja"]),
            title_en=html.escape(src["title"]),
            score=src["score"],
            sub=SUB,
            author=html.escape(src.get("author", "")),
            date=fmt_date(src.get("published", "")),
            link=html.escape(src["link"]),
            body_ja=t["body_ja_html"],
            body_en=extract_md(src["body_html"]) or "<p>(本文なし / リンク投稿)</p>",
        )
        (OUT / f"{pid}.html").write_text(page, encoding="utf-8")
        written.append((src["published"], pid, t["title_ja"], src["score"]))
        processed[pid] = {
            "title": src["title"],
            "title_ja": t["title_ja"],
            "score": src["score"],
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

    # index: 処理済み全件を新しい順に(日本語タイトルを表示)
    all_items = sorted(
        [(v.get("processed_at", ""), pid, v.get("title_ja") or v["title"], v["score"])
         for pid, v in processed.items()],
        reverse=True,
    )
    lis = []
    for _, pid, disp, score in all_items:
        lis.append(
            f'  <li><a href="{pid}.html"><span class="score">▲ {score}</span>'
            f'{html.escape(disp)}</a></li>'
        )
    (OUT / "index.html").write_text(
        INDEX.format(now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                     count=len(processed), items="\n".join(lis)),
        encoding="utf-8",
    )

    PROCESSED_FILE.write_text(json.dumps(processed, ensure_ascii=False, indent=2))
    print(f"出力: {len(written)}ページ + index.html -> {OUT}")
    for _, pid, title, score in sorted(written, reverse=True):
        print(f"  [{score:>4}] {pid}.html  {title[:50]}")


if __name__ == "__main__":
    main()
