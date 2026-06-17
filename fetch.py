#!/usr/bin/env python3
"""r/PathOfExile2 の Information フレア・upvote>=N 投稿を取得する。

Reddit の公開 .json は現在ブロックされるため、以下の2経路を使う:
  1) フレア検索 RSS  -> 本文(selftext HTML)・タイトル・id・URL・投稿日時
  2) old.reddit 検索 HTML -> 各投稿のスコア(N points)

両者を id で突き合わせ、score>=MIN_SCORE のものを抽出。
処理済み id は data/processed.json に記録し、未処理分のみ data/pending.json に出力する。
低負荷のため1実行あたりのリクエストは2本、間に待機を入れる。
"""
import json
import re
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

SUBREDDIT = "PathOfExile2"
FLAIR = "Information"
MIN_SCORE = 10
LIMIT = 25  # 直近件数(1ページ分)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
PROCESSED_FILE = DATA / "processed.json"
PENDING_FILE = DATA / "pending.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}
ATOM = "{http://www.w3.org/2005/Atom}"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
    return raw


def parse_media(body_html: str) -> dict:
    """body_html から画像URL・動画URLを抽出する。

    - 画像: i.redd.it / preview.redd.it のURLを元画像 i.redd.it/<file> に正規化。
            (preview はサムネ・署名付きで hotlink できないため i.redd.it に変換)
            external-preview(外部リンクのOGP画像)は壊れやすいので除外。
    - 動画: reddit.com/link/<id>/video/... または v.redd.it のURL(最初の1件)。
    """
    images = []
    seen = set()
    # i.redd.it と preview.redd.it のファイル名を拾う
    for m in re.finditer(r'https?://(?:i|preview)\.redd\.it/([\w.-]+\.(?:png|jpe?g|gif|webp))', body_html, re.I):
        fname = m.group(1)
        # preview の webp 変換などは元拡張子のまま i.redd.it へ
        url = f"https://i.redd.it/{fname}"
        if url not in seen:
            seen.add(url)
            images.append(url)
    video = None
    vm = re.search(r'https?://(?:reddit\.com/link/[\w]+/video/[\w]+|v\.redd\.it/[\w]+)[^\s"<)]*', body_html, re.I)
    if vm:
        video = vm.group(0)
    return {"images": images, "video": video}


def fetch_rss() -> dict:
    """id -> {title, link, body_html, published, images, video} (Information フレア絞り込み済み)"""
    q = urllib.parse.quote('flair_name:"%s"' % FLAIR)
    url = (f"https://www.reddit.com/r/{SUBREDDIT}/search.rss?"
           f"q={q}&restrict_sr=1&sort=new&limit={LIMIT}")
    root = ET.fromstring(get(url))
    out = {}
    for e in root.findall(f"{ATOM}entry"):
        pid = e.findtext(f"{ATOM}id", "").replace("t3_", "")
        if not pid:
            continue
        link_el = e.find(f"{ATOM}link")
        body_html = (e.findtext(f"{ATOM}content", "") or "").strip()
        media = parse_media(body_html)
        out[pid] = {
            "id": pid,
            "title": e.findtext(f"{ATOM}title", "").strip(),
            "link": link_el.get("href") if link_el is not None else "",
            "body_html": body_html,
            "published": e.findtext(f"{ATOM}published", "").strip(),
            "author": (e.find(f"{ATOM}author/{ATOM}name").text
                       if e.find(f"{ATOM}author/{ATOM}name") is not None else ""),
            "images": media["images"],
            "video": media["video"],
        }
    return out


def fetch_scores() -> dict:
    """id -> score (old.reddit 検索HTMLから)"""
    q = urllib.parse.quote('flair_name:"%s"' % FLAIR)
    url = (f"https://old.reddit.com/r/{SUBREDDIT}/search?"
           f"q={q}&restrict_sr=1&sort=new&include_over_18=on&limit={LIMIT}")
    htmltext = get(url).decode("utf-8", "replace")
    scores = {}
    # 各検索結果ブロックを data-fullname で分割し、直後の search-score を拾う
    for m in re.finditer(r'data-fullname="t3_([a-z0-9]+)"', htmltext):
        pid = m.group(1)
        tail = htmltext[m.end(): m.end() + 4000]
        sm = re.search(r'class="search-score"[^>]*>\s*([\d,]+)\s*points?', tail)
        if sm:
            scores[pid] = int(sm.group(1).replace(",", ""))
    return scores


def main():
    processed = {}
    if PROCESSED_FILE.exists():
        processed = json.loads(PROCESSED_FILE.read_text())

    rss = fetch_rss()
    time.sleep(4)  # 低負荷: リクエスト間に待機
    scores = fetch_scores()

    pending = []
    for pid, post in rss.items():
        score = scores.get(pid)
        if score is None or score < MIN_SCORE:
            continue
        if pid in processed:
            continue
        post["score"] = score
        pending.append(post)

    pending.sort(key=lambda p: p["published"])
    PENDING_FILE.write_text(json.dumps(pending, ensure_ascii=False, indent=2))

    print(f"RSS取得: {len(rss)}件 / スコア取得: {len(scores)}件")
    print(f"条件合致(score>={MIN_SCORE})かつ未処理: {len(pending)}件 -> {PENDING_FILE}")
    for p in pending:
        print(f"  [{p['score']:>4}] {p['id']}  {p['title'][:60]}")


if __name__ == "__main__":
    main()
