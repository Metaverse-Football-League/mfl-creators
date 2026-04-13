#!/usr/bin/env python3
"""Parse an agent-browser Discord snapshot into a chronological message log.

Usage: parse_discord_snapshot.py <snapshot.txt> [--since YYYY-MM-DD]

Output:
  [YYYY-MM-DD HH:MM] Sender: message text
"""
import re
import sys
from datetime import datetime

SEPARATOR_RE = re.compile(r'separator "(\d{1,2} \w+ \d{4})"')
ARTICLE_LABEL_RE = re.compile(
    r'article "([^"]+)"\s*(?:\[ref=|:)'
    r"|article '([^']+)'\s*(?:\[ref=|:)"
)
HEADING_RE = re.compile(
    r'heading "(.+?) (\d{2}/\d{2}/\d{4}, \d{2}:\d{2}|\d{2}:\d{2})"'
)
TEXT_RE = re.compile(r"^(\s*)-\s*text:\s*(.*)$")
LISTITEM_RE = re.compile(r"^(\s*)-\s*listitem:")
DATETIME_FULL_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4}), (\d{2}:\d{2})")
TIME_ONLY_RE = re.compile(r"(?<!\d)(\d{2}:\d{2})(?!\d)")

NOISE_PATTERNS = [
    re.compile(r"^[A-Za-z]+day, \d{1,2} \w+ \d{4} at "),  # tooltip date
    re.compile(r"^Add Reaction$"),
    re.compile(r"^Remove all embeds$"),
    re.compile(r"^Delete$"),
    re.compile(r"^Send GIF$"),
    re.compile(r"^Upgrade your friends"),
    re.compile(r"^Remove Message Attachment$"),
    re.compile(r"^Image$"),
    re.compile(r"^\"\d+\"$"),  # "1" reaction count
    re.compile(r"^\d+$"),  # bare number reactions
]


def is_noise(text: str) -> bool:
    text = text.strip()
    if not text:
        return True
    for p in NOISE_PATTERNS:
        if p.match(text):
            return True
    return False


def parse_separator(label: str) -> datetime:
    return datetime.strptime(label, "%d %B %Y")


def parse_listitem_block(lines, current_date, last_sender):
    """Parse a single listitem block. Returns (sender, ts, text) or None."""
    sender = None
    ts = None
    body_parts = []

    # First pass: try article aria-label
    for line in lines:
        m = ARTICLE_LABEL_RE.search(line)
        if m:
            content = m.group(1) or m.group(2)
            # Extract timestamp (full or time-only)
            dt_full = list(DATETIME_FULL_RE.finditer(content))
            if dt_full:
                last = dt_full[-1]
                dd, mm, yyyy, hhmm = last.groups()
                ts = datetime.strptime(f"{yyyy}-{mm}-{dd} {hhmm}", "%Y-%m-%d %H:%M")
                content_wo_ts = content[: last.start()].rstrip(" ,")
            else:
                # Try plain HH:MM at end
                tm = TIME_ONLY_RE.search(content)
                if tm and current_date:
                    hhmm = tm.group(1)
                    ts = datetime.strptime(
                        current_date.strftime("%Y-%m-%d") + " " + hhmm,
                        "%Y-%m-%d %H:%M",
                    )
                    content_wo_ts = content[: tm.start()].rstrip(" ,")
                else:
                    content_wo_ts = content
            # Sender is first comma-separated chunk
            parts = content_wo_ts.split(" , ")
            if len(parts) >= 2:
                sender = parts[0].strip()
                # Strip "replying to X" suffix from sender
                sender = re.sub(r"\s+replying to .+$", "", sender)
                body_parts = [" ".join(parts[1:]).strip()]
            else:
                # System message ("X added Y to the group")
                sender = "(system)"
                body_parts = [content_wo_ts.strip()]
            break

    # Fallback: parse from heading + text children
    if sender is None or ts is None:
        for line in lines:
            hm = HEADING_RE.search(line)
            if hm:
                sender = hm.group(1).strip()
                stamp = hm.group(2)
                if "/" in stamp:
                    ts = datetime.strptime(stamp, "%d/%m/%Y, %H:%M")
                elif current_date:
                    ts = datetime.strptime(
                        current_date.strftime("%Y-%m-%d") + " " + stamp,
                        "%Y-%m-%d %H:%M",
                    )
                break
        # Body from direct text: lines (only at the top indent of the article)
        if sender:
            collected = []
            base_indent = None
            for line in lines:
                tm = TEXT_RE.match(line)
                if not tm:
                    continue
                indent = len(tm.group(1))
                if base_indent is None:
                    base_indent = indent
                # Only top-level text under the article
                if indent <= base_indent + 2:
                    txt = tm.group(2).strip()
                    if not is_noise(txt):
                        collected.append(txt)
            if collected:
                body_parts = collected

    if not sender or not ts:
        return None

    # If sender is "(unknown)" but body has only HH:MM, inherit last_sender
    if sender == "(unknown)" and last_sender:
        sender = last_sender

    body = " ".join(body_parts).strip()
    body = re.sub(r"\s+", " ", body)
    if not body:
        return None
    return sender, ts, body


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    since = None
    if "--since" in sys.argv:
        i = sys.argv.index("--since")
        since = datetime.strptime(sys.argv[i + 1], "%Y-%m-%d")

    with open(path) as f:
        all_lines = f.readlines()

    # Walk lines, tracking date separator and listitem boundaries.
    current_date = None
    messages = []
    last_sender = None

    i = 0
    n = len(all_lines)
    while i < n:
        line = all_lines[i]
        sm = SEPARATOR_RE.search(line)
        if sm:
            current_date = parse_separator(sm.group(1))
            i += 1
            continue
        lim = LISTITEM_RE.match(line)
        if lim:
            base_indent = len(lim.group(1))
            block = [line]
            j = i + 1
            while j < n:
                nxt = all_lines[j]
                nxt_lim = LISTITEM_RE.match(nxt)
                # Stop at next listitem at same or lower indent, or at separator,
                # or at lines that de-indent below base_indent (end of list scope)
                if nxt_lim and len(nxt_lim.group(1)) <= base_indent:
                    break
                if SEPARATOR_RE.search(nxt):
                    break
                stripped_indent = len(nxt) - len(nxt.lstrip())
                if nxt.strip() and stripped_indent <= base_indent:
                    break
                block.append(nxt)
                j += 1
            parsed = parse_listitem_block(block, current_date, last_sender)
            if parsed:
                sender, ts, body = parsed
                if sender != "(system)":
                    last_sender = sender
                messages.append((ts, sender, body))
            i = j
            continue
        i += 1

    # Dedupe and filter by since
    seen = set()
    out = []
    for ts, sender, body in messages:
        key = (ts.isoformat(), sender, body)
        if key in seen:
            continue
        seen.add(key)
        if since and ts < since:
            continue
        out.append((ts, sender, body))
    out.sort(key=lambda x: x[0])

    for ts, sender, body in out:
        print(f"[{ts:%Y-%m-%d %H:%M}] {sender}: {body}")


if __name__ == "__main__":
    main()
