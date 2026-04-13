#!/bin/bash
# Sends a meeting prep email via gws CLI.
# Usage: send.sh <slug> "<subject>"
# slug must match a .txt file in this directory (lykos|tony|mat).

set -euo pipefail

SLUG="${1:?usage: send.sh <slug> <subject>}"
SUBJECT="${2:?usage: send.sh <slug> <subject>}"
DIR="$(cd "$(dirname "$0")" && pwd)"
BODY="$DIR/$SLUG.txt"
LOG="$DIR/send.log"

if [[ ! -f "$BODY" ]]; then
  echo "$(date): ERROR — body file $BODY not found" >> "$LOG"
  exit 1
fi

# Ensure gws is on PATH (cron has minimal env)
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

if /opt/homebrew/bin/gws gmail +send \
    --to mathurin@playmfl.com \
    --subject "$SUBJECT" \
    --body "$(cat "$BODY")" >> "$LOG" 2>&1; then
  echo "$(date): SENT $SLUG — $SUBJECT" >> "$LOG"
else
  echo "$(date): FAILED $SLUG — $SUBJECT" >> "$LOG"
  exit 1
fi
