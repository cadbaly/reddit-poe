#!/usr/bin/env bash
# ローカルcron用: 両サブレディットの該当投稿を取得し pending.json を更新する。
# 翻訳・Notion投稿は行わない（Claudeセッションで「更新して」と頼んだ時に実施する半自動運用）。
# cron は最小環境なので PATH を明示。
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
set -u
cd "$(dirname "$0")" || exit 1

LOG=data/cron.log
ts() { date "+%Y-%m-%d %H:%M:%S %Z"; }
echo "[$(ts)] refresh start" >> "$LOG"

for sub in PathOfExile2 PathOfExile; do
  out=$(python3 fetch.py "$sub" 2>&1)
  echo "[$(ts)] $sub: $(echo "$out" | grep -E '条件合致|ERR|Error|Forbidden' | head -1)" >> "$LOG"
  sleep 15   # サブレディット間でレート制限回避のため待機
done

# pending.json に差分があれば commit → pull --rebase → push（best-effort、失敗しても継続）
if ! git diff --quiet -- 'data/*/pending.json' 2>/dev/null; then
  git add data/*/pending.json 2>>"$LOG"
  git commit -q -m "cron: refresh pending posts ($(date +%F))" 2>>"$LOG"
  GIT_TERMINAL_PROMPT=0 git pull --rebase -q origin master 2>>"$LOG"
  if GIT_TERMINAL_PROMPT=0 git push -q origin master 2>>"$LOG"; then
    echo "[$(ts)] pushed pending updates" >> "$LOG"
  else
    echo "[$(ts)] push failed (commit kept locally)" >> "$LOG"
  fi
else
  echo "[$(ts)] no pending changes" >> "$LOG"
fi
echo "[$(ts)] refresh done" >> "$LOG"
