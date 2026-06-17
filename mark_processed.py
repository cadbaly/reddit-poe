#!/usr/bin/env python3
"""translated.json の各idを data/<sub>/processed.json に処理済みとして記録する。

Notion へページを作成した後に実行して台帳を更新し、次回 fetch.py が同じ投稿を
再取得しないようにする。対象サブレディットは fetch.py と同じく引数/環境変数で指定:
    python3 mark_processed.py PathOfExile
    SUBREDDIT=PathOfExile python3 mark_processed.py
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

SUBREDDIT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SUBREDDIT", "PathOfExile2")
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / SUBREDDIT
PENDING_FILE = DATA / "pending.json"
TRANSLATED_FILE = DATA / "translated.json"
PROCESSED_FILE = DATA / "processed.json"


def main():
    pending = {p["id"]: p for p in json.loads(PENDING_FILE.read_text())}
    translated = json.loads(TRANSLATED_FILE.read_text())
    processed = {}
    if PROCESSED_FILE.exists():
        processed = json.loads(PROCESSED_FILE.read_text())

    n = 0
    for t in translated:
        pid = t["id"]
        src = pending.get(pid, {})
        processed[pid] = {
            "title": src.get("title", ""),
            "title_ja": t.get("title_ja", ""),
            "score": src.get("score"),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        n += 1

    PROCESSED_FILE.write_text(json.dumps(processed, ensure_ascii=False, indent=2))
    print(f"processed.json を更新: {n}件追記 / 累計{len(processed)}件")


if __name__ == "__main__":
    main()
