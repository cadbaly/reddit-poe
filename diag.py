#!/usr/bin/env python3
"""クラウド実行環境から各エンドポイントに到達できるか診断する。

結果を標準出力に書く（ルーティンが data/diag.txt にリダイレクト＆commitして
ローカルから読めるようにする）。Reddit がデータセンターIPをブロックしているか等の
切り分け用。本番ロジック(fetch.py)には影響しない。
"""
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
           "Accept-Encoding": "gzip, deflate"}

TARGETS = [
    ("flair-RSS", "https://www.reddit.com/r/PathOfExile2/search.rss?q=flair_name%3A%22Information%22&restrict_sr=1&sort=new&limit=5"),
    ("old.reddit-search", "https://old.reddit.com/r/PathOfExile2/search?q=flair_name%3A%22Information%22&restrict_sr=1&sort=new&include_over_18=on&limit=5"),
    ("old.reddit-comments", "https://old.reddit.com/comments/1u84u81/?sort=top&limit=5"),
    ("control-example", "https://example.com"),
]


def probe(name, url):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read()
            ms = int((time.time() - t0) * 1000)
            return f"{name}: HTTP {r.status}  {len(body)}B  {ms}ms  {url}"
    except urllib.error.HTTPError as e:
        ms = int((time.time() - t0) * 1000)
        return f"{name}: HTTPError {e.code} {e.reason}  {ms}ms  {url}"
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        return f"{name}: ERROR {type(e).__name__}: {e}  {ms}ms  {url}"


def main():
    print(f"# diag at {datetime.now(timezone.utc).isoformat()}")
    print(f"# python {sys.version.split()[0]}")
    # 送信元IPを確認(Redditブロック切り分け用)
    print(probe("egress-ip", "https://api.ipify.org?format=json"))
    try:
        with urllib.request.urlopen(
                urllib.request.Request("https://api.ipify.org?format=json", headers=HEADERS),
                timeout=15) as r:
            print("egress-ip-value:", json.loads(r.read()).get("ip"))
    except Exception as e:
        print("egress-ip-value: ERROR", e)
    for name, url in TARGETS:
        print(probe(name, url))
        time.sleep(2)


if __name__ == "__main__":
    main()
