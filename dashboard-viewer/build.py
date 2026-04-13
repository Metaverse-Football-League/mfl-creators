#!/usr/bin/env python3
"""
Build a self-contained HTML dashboard from creator markdown profiles.

Usage:
    cd creators-management/dashboard-viewer && python3 build.py
    open index.html
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent  # creators-management/
CREATORS_DIR = BASE_DIR / "creators"
DASHBOARD_MD = BASE_DIR / "dashboard.md"
OUTPUT_HTML = SCRIPT_DIR / "index.html"


# ---------------------------------------------------------------------------
# Markdown parsing helpers
# ---------------------------------------------------------------------------

def parse_followers_numeric(text: str) -> int:
    """Convert '~223K', '~1.96M', '109K', '~500' etc. to integer."""
    if not text:
        return 0
    text = text.strip().lstrip("~").replace(",", "")
    # Remove trailing descriptors like " subs", " (YT)", etc.
    text = re.split(r'\s', text)[0]
    m = re.match(r'^([\d.]+)\s*([KkMm])?', text)
    if not m:
        return 0
    num = float(m.group(1))
    suffix = (m.group(2) or "").upper()
    if suffix == "K":
        return int(num * 1_000)
    elif suffix == "M":
        return int(num * 1_000_000)
    return int(num)


def parse_profile(path: Path) -> dict | None:
    """Parse a creator profile.md into a dict."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    data = {
        "slug": path.parent.name,
        "name": "",
        "handle": "",
        "stage": "Prospect",
        "ecosystem": "",
        "language": "",
        "updated": "",
        "mainPlatform": "",
        "email": "",
        "hasEmail": False,
        "location": "",
        "discord": "",
        "mflWallet": "",
        "mflProfile": "",
        "realName": "",
        "lastAuditWeek": "",
        "channels": [],
        "deal": {},
        "hasDeal": False,
        "nextActions": [],
        "notes": "",
        "dashboardAction": "",
        "dashboardDue": "",
    }

    lines = text.split("\n")

    # --- Header: # Name (@Handle) ---
    for line in lines:
        m = re.match(r'^#\s+(.+?)(?:\s+\((@[\w_.]+)\))?\s*$', line)
        if m:
            data["name"] = m.group(1).strip()
            data["handle"] = m.group(2) or ""
            break

    # --- Subtitle: > **Stage** | Ecosystem | Language | Updated: date ---
    for line in lines:
        m = re.match(r'^>\s+\*\*(\w[\w\s]*?)\*\*\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*Updated:\s*(.+)$', line)
        if m:
            data["stage"] = m.group(1).strip()
            data["ecosystem"] = m.group(2).strip()
            data["language"] = m.group(3).strip()
            data["updated"] = m.group(4).strip()
            break

    # --- Info table: | **Key** | Value | ---
    info_map = {}
    for line in lines:
        m = re.match(r'^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|?\s*$', line)
        if m:
            info_map[m.group(1).strip()] = m.group(2).strip()

    data["mainPlatform"] = info_map.get("Main Platform", "")
    data["email"] = info_map.get("Email", "")
    data["hasEmail"] = bool(data["email"] and data["email"] not in ("", "TBD", "—"))
    data["location"] = info_map.get("Location", "")
    data["discord"] = info_map.get("Discord", "")
    data["mflWallet"] = info_map.get("MFL Wallet", "")
    data["realName"] = info_map.get("Real Name", "")
    data["lastAuditWeek"] = info_map.get("Last Audit Week", "")

    mfl_profile_raw = info_map.get("MFL Profile", "")
    # Extract URL from markdown link
    link_m = re.search(r'\[.*?\]\((https?://[^\)]+)\)', mfl_profile_raw)
    if link_m:
        data["mflProfile"] = link_m.group(1)
    elif mfl_profile_raw.startswith("http"):
        data["mflProfile"] = mfl_profile_raw

    # --- Channels table ---
    in_channels = False
    header_seen = False
    for line in lines:
        if re.match(r'^##\s+Channels', line):
            in_channels = True
            header_seen = False
            continue
        if in_channels and re.match(r'^##\s+', line):
            break
        if in_channels:
            if re.match(r'^\|[\s-]+\|', line):
                header_seen = True
                continue
            if re.match(r'^\|\s*Platform\s*\|', line):
                continue
            if header_seen:
                cols = [c.strip() for c in line.split("|")]
                cols = [c for c in cols if c != ""]
                if len(cols) >= 2:
                    platform = cols[0]
                    link = cols[1] if len(cols) > 1 else ""
                    followers = cols[2] if len(cols) > 2 else ""
                    engagement = cols[3] if len(cols) > 3 else ""
                    # Extract URL from markdown link or raw
                    link_m2 = re.search(r'https?://[^\s\)]+', link)
                    link_url = link_m2.group(0) if link_m2 else link
                    ch = {
                        "platform": platform,
                        "link": link_url,
                        "followers": followers,
                        "followersNumeric": parse_followers_numeric(followers),
                        "engagement": engagement,
                    }
                    if platform and platform not in ("", "—"):
                        data["channels"].append(ch)

    # --- Deal table ---
    in_deal = False
    deal_header_seen = False
    deal = {}
    for line in lines:
        if re.match(r'^##\s+Deal', line):
            in_deal = True
            deal_header_seen = False
            continue
        if in_deal and re.match(r'^##\s+', line):
            break
        if in_deal:
            m = re.match(r'^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|?\s*$', line)
            if m:
                deal[m.group(1).strip().lower()] = m.group(2).strip()

    data["deal"] = deal
    deal_type = deal.get("type", "None yet")
    data["hasDeal"] = bool(deal_type and deal_type not in ("None yet", "None", "", "[Affiliate / Paid / None yet]"))

    # --- Next Actions ---
    in_actions = False
    for line in lines:
        if re.match(r'^##\s+Next Actions', line):
            in_actions = True
            continue
        if in_actions and re.match(r'^##\s+', line):
            break
        if in_actions:
            m = re.match(r'^-\s+\[([ xX])\]\s+(.+)$', line)
            if m:
                done = m.group(1).lower() == "x"
                task_text = m.group(2).strip()
                due_m = re.search(r'\(due:\s*(.+?)\)', task_text)
                due = due_m.group(1) if due_m else ""
                data["nextActions"].append({"task": task_text, "done": done, "due": due})

    # --- Notes ---
    in_notes = False
    notes_lines = []
    for line in lines:
        if re.match(r'^##\s+Notes', line):
            in_notes = True
            continue
        if in_notes and re.match(r'^##\s+', line) and not re.match(r'^###', line):
            break
        if in_notes:
            notes_lines.append(line)
    data["notes"] = "\n".join(notes_lines).strip()

    return data


def parse_touchpoints(path: Path) -> list[dict]:
    """Parse a touchpoints.md file into a list of touchpoint dicts."""
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []

    touchpoints = []
    current = None

    for line in text.split("\n"):
        m = re.match(r'^###\s+(\d{4}-\d{2}-\d{2})\s*-\s*(.+)$', line)
        if not m:
            # Also match [YYYY-MM-DD] template format
            m = re.match(r'^###\s+\[(\d{4}-\d{2}-\d{2})\]\s*-\s*(.+)$', line)
        if m:
            if current:
                current["content"] = current["content"].strip()
                if current["date"] != "YYYY-MM-DD":
                    touchpoints.append(current)
            current = {
                "date": m.group(1),
                "type": m.group(2).strip().split("(")[0].strip().rstrip(":"),
                "content": "",
            }
        elif line.startswith("### [YYYY-MM-DD]"):
            current = None
        elif current:
            current["content"] += line + "\n"

    if current and current.get("date") and current["date"] != "YYYY-MM-DD":
        current["content"] = current["content"].strip()
        touchpoints.append(current)

    return touchpoints


def parse_workflow_sections(path: Path) -> dict:
    """Parse the Action Needed / Waiting / Renewals sections from dashboard.md."""
    if not path.exists():
        return {"actionNeeded": [], "waitingOn": []}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {"actionNeeded": [], "waitingOn": []}

    result = {"actionNeeded": [], "waitingOn": []}

    def parse_table_rows(section_text: str) -> list[dict]:
        rows = []
        header_cols = []
        in_header = False
        for line in section_text.split("\n"):
            if re.match(r'^\|.*\|$', line):
                cols = [c.strip() for c in line.split("|")]
                cols = [c for c in cols if c != ""]
                if not header_cols:
                    header_cols = [c.lower().replace(" ", "_") for c in cols]
                    continue
                if re.match(r'^[\s\-|]+$', line):
                    continue
                if all(c in ("-", "—", "") for c in cols):
                    continue
                row = {}
                for i, col in enumerate(cols):
                    if i < len(header_cols):
                        row[header_cols[i]] = col
                if row:
                    rows.append(row)
        return rows

    sections = re.split(r'^##\s+', text, flags=re.MULTILINE)
    for section in sections:
        if section.startswith("Action Needed Today"):
            result["actionNeeded"] = parse_table_rows(section)
        elif section.startswith("Waiting On Response"):
            result["waitingOn"] = parse_table_rows(section)
    return result


def parse_pipeline_actions(path: Path) -> list[dict]:
    """Parse Next Action + Due from all pipeline tables in dashboard.md."""
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []

    results = []
    sections = re.split(r'^##\s+', text, flags=re.MULTILINE)

    for section in sections:
        lines = section.split("\n")
        # Find header row with "Next Action" and "Due" columns
        col_indices = {}
        header_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'^\|.*Next Action.*\|.*Due.*\|', line):
                cols = [c.strip() for c in line.split("|")]
                cols = [c for c in cols if c != ""]
                for j, col in enumerate(cols):
                    col_lower = col.lower().strip()
                    if col_lower == "name":
                        col_indices["name"] = j
                    elif col_lower == "next action":
                        col_indices["action"] = j
                    elif col_lower == "due":
                        col_indices["due"] = j
                header_idx = i
                break

        if header_idx < 0 or "name" not in col_indices:
            continue

        # Parse data rows (skip separator and blank lines)
        for line in lines[header_idx + 1:]:
            if line.strip() == '':
                continue  # skip blank lines within tables
            if not re.match(r'^\|', line):
                break
            if re.match(r'^\|[\s\-|]+$', line):
                continue
            cols = [c.strip() for c in line.split("|")]
            cols = [c for c in cols if c != ""]

            name = cols[col_indices["name"]] if col_indices["name"] < len(cols) else ""
            action = cols[col_indices.get("action", -1)] if col_indices.get("action", -1) >= 0 and col_indices.get("action", -1) < len(cols) else ""
            due = cols[col_indices.get("due", -1)] if col_indices.get("due", -1) >= 0 and col_indices.get("due", -1) < len(cols) else ""

            # Strip markdown links from name
            name = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', name).strip()

            if name and name not in ("-", "—"):
                results.append({"name": name, "action": action, "due": due})

    return results


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build():
    print("Building MFL Creator Dashboard...")

    if not CREATORS_DIR.exists():
        print(f"Error: {CREATORS_DIR} not found. Run from creators-management/.", file=sys.stderr)
        sys.exit(1)

    # Parse all creator profiles
    creators = []
    slugs = sorted([d.name for d in CREATORS_DIR.iterdir() if d.is_dir() and (d / "profile.md").exists()])

    for slug in slugs:
        profile_path = CREATORS_DIR / slug / "profile.md"
        data = parse_profile(profile_path)
        if not data:
            continue

        # Parse touchpoints
        tp_path = CREATORS_DIR / slug / "touchpoints.md"
        data["touchpoints"] = parse_touchpoints(tp_path)
        data["lastTouchpoint"] = data["touchpoints"][0]["date"] if data["touchpoints"] else ""

        creators.append(data)

    # Merge pipeline actions/due dates from dashboard tables
    pipeline_actions = parse_pipeline_actions(DASHBOARD_MD)
    creator_idx = {}
    for i, c in enumerate(creators):
        creator_idx[c["name"].lower().strip()] = i
        creator_idx[c["slug"]] = i
        creator_idx[c["name"].lower().strip().replace(" ", "-")] = i
    for pa in pipeline_actions:
        name_lower = pa["name"].lower().strip()
        idx = creator_idx.get(name_lower)
        if idx is None:
            idx = creator_idx.get(name_lower.replace(" ", "-"))
        if idx is not None:
            creators[idx]["dashboardAction"] = pa["action"]
            creators[idx]["dashboardDue"] = pa["due"]

    # Parse workflow sections
    workflow = parse_workflow_sections(DASHBOARD_MD)

    print(f"Parsed {len(creators)} creator profiles")

    # Build the data payload
    payload = {
        "creators": creators,
        "workflow": workflow,
        "buildDate": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    json_data = json.dumps(payload, ensure_ascii=False)

    html = generate_html(json_data)

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {OUTPUT_HTML}")
    print(f"File size: {OUTPUT_HTML.stat().st_size / 1024:.0f} KB")


def generate_html(json_data: str) -> str:
    """Generate the complete self-contained HTML dashboard."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MFL Creator Dashboard</title>
<style>
{CSS}
</style>
</head>
<body>
<div id="app">
  <header id="topbar">
    <div class="topbar-left">
      <h1>MFL Creator Dashboard</h1>
      <span class="build-date" id="buildDate"></span>
    </div>
    <nav class="tabs" id="tabs">
      <button class="tab active" data-tab="workflow">Workflow</button>
      <button class="tab" data-tab="kanban">Kanban</button>
      <button class="tab" data-tab="table">Table</button>
      <button class="tab" data-tab="stats">Stats</button>
    </nav>
  </header>
  <div id="filters" class="filters">
    <div class="filter-group">
      <label>Stage</label><button class="filter-clear" data-filter="stage">Clear</button>
      <div class="filter-chips" id="filterStage"></div>
    </div>
    <div class="filter-group">
      <label>Ecosystem</label><button class="filter-clear" data-filter="ecosystem">Clear</button>
      <div class="filter-chips" id="filterEcosystem"></div>
    </div>
    <div class="filter-group">
      <label>Platform</label><button class="filter-clear" data-filter="platform">Clear</button>
      <div class="filter-chips" id="filterPlatform"></div>
    </div>
    <div class="filter-group">
      <label>Email</label>
      <select id="filterEmail"><option value="all">All</option><option value="yes">Has Email</option><option value="no">No Email</option></select>
    </div>
    <div class="filter-group">
      <input type="text" id="filterSearch" placeholder="Search name or handle...">
    </div>
  </div>
  <main id="main">
    <div id="view-workflow" class="view active"></div>
    <div id="view-kanban" class="view"></div>
    <div id="view-table" class="view"></div>
    <div id="view-stats" class="view"></div>
  </main>
</div>
<div id="overlay" class="overlay hidden"></div>
<div id="detail" class="detail-panel hidden">
  <button id="detailClose" class="detail-close">&times;</button>
  <div id="detailContent"></div>
</div>
<script>
const DATA = {json_data};
{JS}
</script>
</body>
</html>'''


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = r"""
* { margin:0; padding:0; box-sizing:border-box; }
:root {
  --bg: #1e1e2e; --bg2: #27273a; --bg3: #313147; --bg4: #3b3b55;
  --fg: #cdd6f4; --fg2: #a6adc8; --fg3: #7f849c;
  --accent: #89b4fa; --green: #a6e3a1; --orange: #fab387; --red: #f38ba8;
  --yellow: #f9e2af; --purple: #cba6f7; --teal: #94e2d5; --pink: #f5c2e7;
  --border: #45475a; --radius: 6px;
}
body { background:var(--bg); color:var(--fg); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; font-size:14px; overflow-x:hidden; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }

/* Topbar */
#topbar { display:flex; align-items:center; justify-content:space-between; padding:12px 20px; background:var(--bg2); border-bottom:1px solid var(--border); position:sticky; top:0; z-index:100; }
.topbar-left { display:flex; align-items:center; gap:16px; }
.topbar-left h1 { font-size:18px; font-weight:600; }
.build-date { color:var(--fg3); font-size:12px; }
.tabs { display:flex; gap:4px; }
.tab { background:none; border:1px solid transparent; color:var(--fg2); padding:6px 16px; border-radius:var(--radius); cursor:pointer; font-size:13px; transition:all .15s; }
.tab:hover { background:var(--bg3); color:var(--fg); }
.tab.active { background:var(--accent); color:var(--bg); font-weight:600; border-color:var(--accent); }

/* Filters */
.filters { display:flex; align-items:center; gap:16px; padding:10px 20px; background:var(--bg2); border-bottom:1px solid var(--border); flex-wrap:wrap; position:sticky; top:52px; z-index:99; }
.filter-group { display:flex; align-items:center; gap:6px; }
.filter-group label { color:var(--fg3); font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.5px; white-space:nowrap; }
.filter-chips { display:flex; gap:3px; flex-wrap:wrap; }
.chip { padding:3px 10px; border-radius:12px; font-size:12px; cursor:pointer; border:1px solid var(--border); background:var(--bg3); color:var(--fg2); transition:all .15s; user-select:none; }
.chip.active { background:var(--accent); color:var(--bg); border-color:var(--accent); }
.chip:hover { border-color:var(--fg3); }
.filter-clear { background:none; border:none; color:var(--fg3); font-size:11px; cursor:pointer; padding:2px 4px; text-decoration:underline; text-underline-offset:2px; }
.filter-clear:hover { color:var(--red); }
select { background:var(--bg3); color:var(--fg); border:1px solid var(--border); border-radius:var(--radius); padding:4px 8px; font-size:12px; }
#filterSearch { background:var(--bg3); color:var(--fg); border:1px solid var(--border); border-radius:var(--radius); padding:6px 12px; font-size:13px; width:200px; }
#filterSearch::placeholder { color:var(--fg3); }

/* Main */
#main { padding:20px; min-height:calc(100vh - 120px); }
.view { display:none; }
.view.active { display:block; }

/* Workflow */
.workflow-cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:16px; }
.wf-card { background:var(--bg2); border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }
.wf-card-header { padding:12px 16px; font-weight:600; font-size:14px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:8px; }
.wf-card-header .dot { width:8px; height:8px; border-radius:50%; }
.wf-card-body { padding:8px 0; }
.wf-col-headers { display:flex; padding:6px 16px; border-bottom:1px solid var(--border); font-size:10px; color:var(--fg3); text-transform:uppercase; letter-spacing:.5px; user-select:none; gap:8px; align-items:center; }
.wf-col-headers span { cursor:pointer; transition:color .1s; }
.wf-col-headers span:hover { color:var(--fg); }
.wf-col-headers span.active { color:var(--accent); }
.wf-col-headers .col-name { width:22%; flex-shrink:0; }
.wf-col-headers .col-stage { width:80px; flex-shrink:0; }
.wf-col-headers .col-action { flex:1; min-width:0; }
.wf-col-headers .col-due { width:60px; flex-shrink:0; text-align:center; }
.wf-row { padding:8px 16px; display:flex; align-items:center; cursor:pointer; transition:background .1s; gap:8px; }
.wf-row:hover { background:var(--bg3); }
.wf-row .name { font-weight:500; width:22%; flex-shrink:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.wf-row .wf-stage { width:80px; flex-shrink:0; }
.wf-row .wf-stage .stage-badge { font-size:9px; padding:1px 6px; }
.wf-row .meta { color:var(--fg3); font-size:12px; }
.wf-empty { padding:16px; color:var(--fg3); text-align:center; font-style:italic; }
.wf-row .wf-action { flex:1; color:var(--fg2); font-size:12px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.wf-due { font-size:11px; font-weight:600; white-space:nowrap; padding:2px 6px; border-radius:3px; background:var(--bg4); width:60px; flex-shrink:0; text-align:center; }
.wf-due.overdue { color:var(--red); }
.wf-due.this-week { color:var(--orange); }
.wf-due.waiting { color:var(--yellow); }

/* Kanban */
.kanban { display:flex; gap:12px; overflow-x:auto; padding-bottom:12px; align-items:flex-start; }
.kanban-col { min-width:220px; max-width:260px; flex:1; background:var(--bg2); border-radius:var(--radius); border:1px solid var(--border); display:flex; flex-direction:column; max-height:calc(100vh - 180px); }
.kanban-col-header { padding:10px 12px; font-weight:600; font-size:13px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; background:var(--bg2); z-index:1; border-radius:var(--radius) var(--radius) 0 0; cursor:pointer; }
.kanban-col-header .count { background:var(--bg4); padding:2px 8px; border-radius:10px; font-size:11px; color:var(--fg2); }
.kanban-col-body { overflow-y:auto; padding:8px; flex:1; }
.kanban-card { background:var(--bg3); border:1px solid var(--border); border-radius:var(--radius); padding:10px; margin-bottom:6px; cursor:pointer; transition:border-color .15s; }
.kanban-card:hover { border-color:var(--accent); }
.kanban-card .card-name { font-weight:500; font-size:13px; margin-bottom:4px; }
.kanban-card .card-handle { color:var(--fg3); font-size:11px; }
.kanban-card .card-badges { display:flex; gap:4px; margin-top:6px; flex-wrap:wrap; }
.badge { padding:1px 6px; border-radius:3px; font-size:10px; font-weight:600; text-transform:uppercase; }
.badge-eco { background:var(--purple); color:var(--bg); }
.badge-plat { background:var(--teal); color:var(--bg); }
.kanban-col.collapsed .kanban-col-body { display:none; }
.kanban-col.collapsed { max-height:none; }
.kanban-col.collapsed .kanban-col-header::after { content:" (click to expand)"; font-weight:400; font-size:11px; color:var(--fg3); }
.load-more { padding:8px; text-align:center; cursor:pointer; color:var(--accent); font-size:12px; border:1px dashed var(--border); border-radius:var(--radius); margin-top:4px; }
.load-more:hover { background:var(--bg4); }

/* Table */
.table-wrap { overflow-x:auto; }
table.data-table { width:100%; border-collapse:collapse; }
table.data-table th { background:var(--bg2); padding:10px 12px; text-align:left; font-size:12px; color:var(--fg3); text-transform:uppercase; letter-spacing:.5px; border-bottom:2px solid var(--border); cursor:pointer; user-select:none; white-space:nowrap; position:sticky; top:0; }
table.data-table th:hover { color:var(--fg); }
table.data-table th .sort-arrow { margin-left:4px; font-size:10px; }
table.data-table td { padding:8px 12px; border-bottom:1px solid var(--border); font-size:13px; }
table.data-table tr { cursor:pointer; transition:background .1s; }
table.data-table tr:hover { background:var(--bg3); }
.table-count { color:var(--fg3); font-size:12px; margin-bottom:8px; }

/* Stats */
.stats-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; }
.stat-card { background:var(--bg2); border:1px solid var(--border); border-radius:var(--radius); padding:16px; }
.stat-card h3 { font-size:14px; margin-bottom:12px; color:var(--fg2); }
.stat-number { font-size:28px; font-weight:700; color:var(--accent); }
.stat-sub { color:var(--fg3); font-size:12px; margin-top:4px; }
.bar-chart { display:flex; flex-direction:column; gap:6px; }
.bar-row { display:flex; align-items:center; gap:8px; }
.bar-label { width:100px; font-size:12px; color:var(--fg2); text-align:right; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex-shrink:0; }
.bar-track { flex:1; background:var(--bg4); border-radius:3px; height:18px; position:relative; overflow:hidden; }
.bar-fill { height:100%; border-radius:3px; transition:width .3s; display:flex; align-items:center; padding-left:6px; font-size:10px; font-weight:600; color:var(--bg); min-width:fit-content; }
.bar-value { font-size:11px; color:var(--fg3); width:40px; text-align:right; flex-shrink:0; }

/* Stage colors */
.stage-prospect { background:var(--fg3); color:var(--bg); }
.stage-to-contact { background:var(--yellow); color:var(--bg); }
.stage-outreach { background:var(--orange); color:var(--bg); }
.stage-negotiation { background:var(--purple); color:var(--bg); }
.stage-signed { background:var(--teal); color:var(--bg); }
.stage-active { background:var(--green); color:var(--bg); }
.stage-paused { background:var(--yellow); color:var(--bg); }
.stage-churned { background:var(--red); color:var(--bg); }

.stage-badge { padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; display:inline-block; }

/* Detail panel */
.overlay { position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,.5); z-index:200; }
.overlay.hidden { display:none; }
.detail-panel { position:fixed; top:0; right:0; width:min(480px,90vw); height:100vh; background:var(--bg); border-left:1px solid var(--border); z-index:201; overflow-y:auto; padding:20px; transition:transform .2s; }
.detail-panel.hidden { transform:translateX(100%); }
.detail-close { position:sticky; top:0; float:right; background:var(--bg3); border:none; color:var(--fg); font-size:20px; width:32px; height:32px; border-radius:50%; cursor:pointer; display:flex; align-items:center; justify-content:center; z-index:1; }
.detail-close:hover { background:var(--red); }
.detail-panel h2 { font-size:20px; margin-bottom:4px; }
.detail-panel .detail-handle { color:var(--fg3); font-size:14px; margin-bottom:12px; }
.detail-section { margin-top:16px; }
.detail-section h3 { font-size:13px; color:var(--fg3); text-transform:uppercase; letter-spacing:.5px; margin-bottom:8px; border-bottom:1px solid var(--border); padding-bottom:4px; }
.detail-table { width:100%; }
.detail-table td { padding:4px 0; font-size:13px; vertical-align:top; }
.detail-table td:first-child { color:var(--fg3); width:120px; font-weight:500; }
.tp-item { margin-bottom:12px; padding-left:12px; border-left:2px solid var(--border); }
.tp-date { font-weight:600; font-size:12px; color:var(--accent); }
.tp-type { color:var(--fg3); font-size:11px; margin-left:8px; }
.tp-content { font-size:13px; margin-top:4px; color:var(--fg2); white-space:pre-wrap; line-height:1.5; }
.action-item { padding:4px 0; font-size:13px; }
.action-done { text-decoration:line-through; color:var(--fg3); }
.notes-text { font-size:13px; line-height:1.6; color:var(--fg2); white-space:pre-wrap; }
.notes-text strong, .notes-text b { color:var(--fg); }
.ch-list { list-style:none; }
.ch-list li { padding:4px 0; font-size:13px; display:flex; justify-content:space-between; }
.ch-list .ch-plat { color:var(--fg); font-weight:500; }
.ch-list .ch-fol { color:var(--fg3); }
"""

# ---------------------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------------------

JS = r"""
(function() {
  const creators = DATA.creators;
  const workflow = DATA.workflow;
  document.getElementById('buildDate').textContent = 'Built: ' + DATA.buildDate;

  // --- Stage order ---
  const STAGES = ['Prospect','To Contact','Outreach','Negotiation','Signed','Active','Paused','Churned'];
  const stageClass = s => 'stage-' + s.toLowerCase().replace(/\s+/g, '-');

  // --- Collect unique values ---
  const uniqueVals = (arr, key) => [...new Set(arr.map(c => c[key]).filter(Boolean))].sort();
  const ecosystems = uniqueVals(creators, 'ecosystem');
  const platforms = uniqueVals(creators, 'mainPlatform');
  const stages = STAGES.filter(s => creators.some(c => c.stage === s));

  // --- Filter state (empty = show all) ---
  let filterState = { stages: new Set(), ecosystems: new Set(), platforms: new Set(), email: 'all', search: '' };

  function buildChips(containerId, values, stateSet) {
    const el = document.getElementById(containerId);
    values.forEach(v => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = v;
      chip.onclick = () => {
        if (stateSet.has(v)) { stateSet.delete(v); chip.classList.remove('active'); }
        else { stateSet.add(v); chip.classList.add('active'); }
        applyFilters();
      };
      el.appendChild(chip);
    });
  }
  buildChips('filterStage', stages, filterState.stages);
  buildChips('filterEcosystem', ecosystems, filterState.ecosystems);
  buildChips('filterPlatform', platforms, filterState.platforms);

  // Clear buttons
  document.querySelectorAll('.filter-clear').forEach(btn => {
    btn.onclick = () => {
      const key = btn.dataset.filter;
      let stateSet, containerId;
      if (key === 'stage') { stateSet = filterState.stages; containerId = 'filterStage'; }
      else if (key === 'ecosystem') { stateSet = filterState.ecosystems; containerId = 'filterEcosystem'; }
      else if (key === 'platform') { stateSet = filterState.platforms; containerId = 'filterPlatform'; }
      if (stateSet) {
        stateSet.clear();
        document.getElementById(containerId).querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        applyFilters();
      }
    };
  });

  document.getElementById('filterEmail').onchange = e => { filterState.email = e.target.value; applyFilters(); };
  document.getElementById('filterSearch').oninput = e => { filterState.search = e.target.value.toLowerCase(); applyFilters(); };

  function filtered() {
    return creators.filter(c => {
      if (filterState.stages.size > 0 && !filterState.stages.has(c.stage)) return false;
      if (filterState.ecosystems.size > 0 && c.ecosystem && !filterState.ecosystems.has(c.ecosystem)) return false;
      if (filterState.platforms.size > 0 && c.mainPlatform && !filterState.platforms.has(c.mainPlatform)) return false;
      if (filterState.email === 'yes' && !c.hasEmail) return false;
      if (filterState.email === 'no' && c.hasEmail) return false;
      if (filterState.search) {
        const q = filterState.search;
        if (!c.name.toLowerCase().includes(q) && !c.handle.toLowerCase().includes(q) && !c.slug.includes(q)) return false;
      }
      return true;
    });
  }

  // --- Tabs ---
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(t => t.onclick = () => {
    tabs.forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + t.dataset.tab).classList.add('active');
  });

  // --- Detail panel ---
  const overlay = document.getElementById('overlay');
  const detailPanel = document.getElementById('detail');
  const detailContent = document.getElementById('detailContent');
  document.getElementById('detailClose').onclick = closeDetail;
  overlay.onclick = closeDetail;

  function closeDetail() {
    detailPanel.classList.add('hidden');
    overlay.classList.add('hidden');
  }

  function openDetail(slug) {
    const c = creators.find(x => x.slug === slug);
    if (!c) return;
    let html = '';
    html += '<h2>' + esc(c.name) + '</h2>';
    if (c.handle) html += '<div class="detail-handle">' + esc(c.handle) + '</div>';
    html += '<span class="stage-badge ' + stageClass(c.stage) + '">' + esc(c.stage) + '</span>';

    // Info
    html += '<div class="detail-section"><h3>Info</h3><table class="detail-table">';
    const infoRows = [
      ['Ecosystem', c.ecosystem], ['Language', c.language], ['Main Platform', c.mainPlatform],
      ['Email', c.email || '—'], ['Location', c.location || '—'], ['Discord', c.discord || '—'],
      ['MFL Wallet', c.mflWallet || '—'], ['Real Name', c.realName || '—'], ['Updated', c.updated || '—'],
    ];
    infoRows.forEach(([k,v]) => {
      if (v && v !== '—') html += '<tr><td>' + esc(k) + '</td><td>' + esc(v) + '</td></tr>';
    });
    if (c.mflProfile) html += '<tr><td>MFL Profile</td><td><a href="' + esc(c.mflProfile) + '" target="_blank">View</a></td></tr>';
    html += '</table></div>';

    // Channels
    if (c.channels.length) {
      html += '<div class="detail-section"><h3>Channels</h3><ul class="ch-list">';
      c.channels.forEach(ch => {
        html += '<li><span class="ch-plat">' + esc(ch.platform) + '</span>';
        if (ch.link) html += ' <a href="' + esc(ch.link) + '" target="_blank">link</a>';
        html += '<span class="ch-fol">' + esc(ch.followers) + '</span></li>';
      });
      html += '</ul></div>';
    }

    // Deal
    if (c.hasDeal && Object.keys(c.deal).length) {
      html += '<div class="detail-section"><h3>Deal</h3><table class="detail-table">';
      Object.entries(c.deal).forEach(([k,v]) => {
        if (v) html += '<tr><td>' + esc(k) + '</td><td>' + esc(v) + '</td></tr>';
      });
      html += '</table></div>';
    }

    // Next Actions
    if (c.nextActions.length) {
      html += '<div class="detail-section"><h3>Next Actions</h3>';
      c.nextActions.forEach(a => {
        const cls = a.done ? 'action-item action-done' : 'action-item';
        html += '<div class="' + cls + '">' + (a.done ? '&#9745; ' : '&#9744; ') + esc(a.task) + '</div>';
      });
      html += '</div>';
    }

    // Notes
    if (c.notes) {
      html += '<div class="detail-section"><h3>Notes</h3><div class="notes-text">' + renderMd(c.notes) + '</div></div>';
    }

    // Touchpoints
    if (c.touchpoints && c.touchpoints.length) {
      html += '<div class="detail-section"><h3>Touchpoints (' + c.touchpoints.length + ')</h3>';
      c.touchpoints.forEach(tp => {
        html += '<div class="tp-item"><span class="tp-date">' + esc(tp.date) + '</span><span class="tp-type">' + esc(tp.type) + '</span>';
        html += '<div class="tp-content">' + esc(tp.content) + '</div></div>';
      });
      html += '</div>';
    } else {
      html += '<div class="detail-section"><h3>Touchpoints</h3><p style="color:var(--fg3);font-style:italic">No touchpoints recorded</p></div>';
    }

    detailContent.innerHTML = html;
    detailPanel.classList.remove('hidden');
    overlay.classList.remove('hidden');
    detailPanel.scrollTop = 0;
  }

  function esc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function renderMd(s) {
    let h = esc(s);
    h = h.replace(/^### (.+)$/gm, '<strong style="font-size:14px;display:block;margin-top:8px">$1</strong>');
    h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    h = h.replace(/^- (.+)$/gm, '&bull; $1');
    return h;
  }

  // === WORKFLOW VIEW ===
  function fmtDate(d) {
    if (!d) return '';
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const parts = d.split('-');
    if (parts.length !== 3) return d;
    return months[parseInt(parts[1],10)-1] + ' ' + parseInt(parts[2],10);
  }

  // Stage priority: Active most important, Churned least
  const STAGE_PRIORITY = {Active:0, Signed:1, Negotiation:2, Outreach:3, 'To Contact':4, Prospect:5, Paused:6, Churned:7};

  function wfSort(arr, col, asc) {
    return arr.slice().sort((a,b) => {
      let v = 0;
      switch(col) {
        case 'stage': v = (STAGE_PRIORITY[a.stage]??99) - (STAGE_PRIORITY[b.stage]??99); break;
        case 'name': v = a.name.localeCompare(b.name); break;
        case 'action': v = (a.dashboardAction||'').localeCompare(b.dashboardAction||''); break;
        case 'due': v = (a.dashboardDue||'9999').localeCompare(b.dashboardDue||'9999'); break;
      }
      if (v !== 0) return asc ? v : -v;
      // secondary: stage priority then due date
      const sp = (STAGE_PRIORITY[a.stage]??99) - (STAGE_PRIORITY[b.stage]??99);
      if (sp !== 0) return sp;
      return (a.dashboardDue||'9999').localeCompare(b.dashboardDue||'9999');
    });
  }

  // Per-card sort state: {col, asc}
  const wfSortState = { 0: {col:'stage',asc:true}, 1: {col:'stage',asc:true}, 2: {col:'stage',asc:true} };

  function wfColHeaders(cardIdx) {
    const st = wfSortState[cardIdx];
    function arrow(col) { return st.col === col ? (st.asc ? ' ▲' : ' ▼') : ''; }
    function cls(col) { return st.col === col ? 'active' : ''; }
    return '<div class="wf-col-headers">' +
      '<span class="col-name ' + cls('name') + '" onclick="event.stopPropagation();wfToggleSort(' + cardIdx + ',\'name\')">Name' + arrow('name') + '</span>' +
      '<span class="col-stage ' + cls('stage') + '" onclick="event.stopPropagation();wfToggleSort(' + cardIdx + ',\'stage\')">Stage' + arrow('stage') + '</span>' +
      '<span class="col-action ' + cls('action') + '" onclick="event.stopPropagation();wfToggleSort(' + cardIdx + ',\'action\')">Action' + arrow('action') + '</span>' +
      '<span class="col-due ' + cls('due') + '" onclick="event.stopPropagation();wfToggleSort(' + cardIdx + ',\'due\')">Due' + arrow('due') + '</span>' +
      '</div>';
  }

  function wfRowHtml(c, dueClass) {
    let h = '<div class="wf-row" onclick="openDetail(\'' + esc(c.slug) + '\')">';
    h += '<span class="name">' + esc(c.name) + '</span>';
    h += '<span class="wf-stage"><span class="stage-badge ' + stageClass(c.stage) + '">' + esc(c.stage) + '</span></span>';
    h += '<span class="wf-action">' + esc(c.dashboardAction) + '</span>';
    if (c.dashboardDue && c.dashboardDue !== '-' && c.dashboardDue !== '—') {
      h += '<span class="wf-due ' + (dueClass||'') + '">' + fmtDate(c.dashboardDue) + '</span>';
    } else {
      h += '<span class="wf-due"></span>';
    }
    h += '</div>';
    return h;
  }

  // Store card data for re-sorting
  let wfCardData = {};

  function renderWorkflow() {
    const el = document.getElementById('view-workflow');
    const today = new Date(); today.setHours(0,0,0,0);
    const todayStr = today.getFullYear() + '-' + String(today.getMonth()+1).padStart(2,'0') + '-' + String(today.getDate()).padStart(2,'0');

    // Compute end of week (Sunday)
    const dayOfWeek = today.getDay(); // 0=Sun
    const daysUntilSunday = dayOfWeek === 0 ? 0 : 7 - dayOfWeek;
    const endOfWeek = new Date(today);
    endOfWeek.setDate(endOfWeek.getDate() + daysUntilSunday);
    const endOfWeekStr = endOfWeek.getFullYear() + '-' + String(endOfWeek.getMonth()+1).padStart(2,'0') + '-' + String(endOfWeek.getDate()).padStart(2,'0');

    // Filter creators with due dates
    const withDue = creators.filter(c => c.dashboardDue && c.dashboardDue !== '—' && c.dashboardDue !== '-');
    const overdue = withDue.filter(c => c.dashboardDue <= todayStr);
    const dueThisWeek = withDue.filter(c => c.dashboardDue > todayStr && c.dashboardDue <= endOfWeekStr);

    // Card 3: Active & Negotiation not already shown
    const shownSlugs = new Set([...overdue, ...dueThisWeek].map(c => c.slug));
    const activeNeg = creators.filter(c =>
      (c.stage === 'Active' || c.stage === 'Negotiation') &&
      c.dashboardAction && c.dashboardAction !== '-' && c.dashboardAction !== '—' &&
      !shownSlugs.has(c.slug)
    );

    wfCardData = { 0: overdue, 1: dueThisWeek, 2: activeNeg };

    let html = '<div class="workflow-cards">';

    // Card 1: Urgent / Overdue
    html += '<div class="wf-card"><div class="wf-card-header"><span class="dot" style="background:var(--red)"></span>Urgent / Overdue (' + overdue.length + ')</div>';
    html += wfColHeaders(0);
    html += '<div class="wf-card-body" id="wf-body-0">';
    html += wfRenderCardBody(0, 'overdue');
    html += '</div></div>';

    // Card 2: Due This Week
    html += '<div class="wf-card"><div class="wf-card-header"><span class="dot" style="background:var(--orange)"></span>Due This Week (' + dueThisWeek.length + ')</div>';
    html += wfColHeaders(1);
    html += '<div class="wf-card-body" id="wf-body-1">';
    html += wfRenderCardBody(1, 'this-week');
    html += '</div></div>';

    // Card 3: Active & Negotiation Actions
    html += '<div class="wf-card"><div class="wf-card-header"><span class="dot" style="background:var(--green)"></span>Active & Negotiation Actions (' + activeNeg.length + ')</div>';
    html += wfColHeaders(2);
    html += '<div class="wf-card-body" id="wf-body-2">';
    html += wfRenderCardBody(2, '');
    html += '</div></div>';

    html += '</div>';
    el.innerHTML = html;
  }

  function wfRenderCardBody(cardIdx, dueClass) {
    const st = wfSortState[cardIdx];
    const items = wfSort(wfCardData[cardIdx] || [], st.col, st.asc);
    const emptyMsg = cardIdx === 0 ? 'Nothing overdue' : cardIdx === 1 ? 'Nothing due this week' : 'No pending actions';
    if (!items.length) return '<div class="wf-empty">' + emptyMsg + '</div>';
    return items.map(c => wfRowHtml(c, dueClass)).join('');
  }

  // Expose globally for onclick handlers in column headers
  window.wfToggleSort = function(cardIdx, col) {
    const st = wfSortState[cardIdx];
    if (st.col === col) { st.asc = !st.asc; } else { st.col = col; st.asc = true; }
    const dueClass = cardIdx === 0 ? 'overdue' : cardIdx === 1 ? 'this-week' : '';
    // Re-render just the body and column headers
    const body = document.getElementById('wf-body-' + cardIdx);
    if (body) body.innerHTML = wfRenderCardBody(cardIdx, dueClass);
    // Update column headers (sibling before body)
    const headerRow = body ? body.previousElementSibling : null;
    if (headerRow && headerRow.classList.contains('wf-col-headers')) {
      const tmp = document.createElement('div');
      tmp.innerHTML = wfColHeaders(cardIdx);
      headerRow.replaceWith(tmp.firstElementChild);
    }
  };

  function findSlug(name) {
    if (!name) return '';
    const n = name.toLowerCase().trim();
    const c = creators.find(x => x.name.toLowerCase() === n || x.slug === n || x.slug === n.replace(/\s+/g, '-'));
    return c ? c.slug : '';
  }

  // === KANBAN VIEW ===
  let kanbanLimits = {};
  const KANBAN_PAGE = 50;

  function renderKanban() {
    const el = document.getElementById('view-kanban');
    const data = filtered();
    let html = '<div class="kanban">';

    STAGES.forEach(stage => {
      const items = data.filter(c => c.stage === stage);
      const isProspect = stage === 'Prospect';
      const collapsed = isProspect && items.length > 50;
      const limit = kanbanLimits[stage] || KANBAN_PAGE;
      const shown = items.slice(0, limit);

      html += '<div class="kanban-col' + (collapsed && !(kanbanLimits[stage]) ? ' collapsed' : '') + '" data-stage="' + stage + '">';
      html += '<div class="kanban-col-header" onclick="toggleKanbanCol(this)"><span>' + esc(stage) + '</span><span class="count">' + items.length + '</span></div>';
      html += '<div class="kanban-col-body">';
      shown.forEach(c => {
        html += '<div class="kanban-card" onclick="openDetail(\'' + esc(c.slug) + '\')">';
        html += '<div class="card-name">' + esc(c.name) + '</div>';
        if (c.handle) html += '<div class="card-handle">' + esc(c.handle) + '</div>';
        html += '<div class="card-badges">';
        if (c.ecosystem) html += '<span class="badge badge-eco">' + esc(c.ecosystem) + '</span>';
        if (c.mainPlatform) html += '<span class="badge badge-plat">' + esc(c.mainPlatform) + '</span>';
        html += '</div></div>';
      });
      if (items.length > limit) {
        html += '<div class="load-more" onclick="loadMoreKanban(\'' + stage + '\')">Show more (' + (items.length - limit) + ' remaining)</div>';
      }
      html += '</div></div>';
    });

    html += '</div>';
    el.innerHTML = html;
  }

  window.toggleKanbanCol = function(header) {
    const col = header.parentElement;
    const stage = col.dataset.stage;
    if (col.classList.contains('collapsed')) {
      col.classList.remove('collapsed');
      if (!kanbanLimits[stage]) kanbanLimits[stage] = KANBAN_PAGE;
    } else if (stage === 'Prospect') {
      col.classList.add('collapsed');
      kanbanLimits[stage] = 0;
    }
  };

  window.loadMoreKanban = function(stage) {
    kanbanLimits[stage] = (kanbanLimits[stage] || KANBAN_PAGE) + KANBAN_PAGE;
    renderKanban();
  };

  // === TABLE VIEW ===
  let sortCol = 'name';
  let sortDir = 1;

  function renderTable() {
    const el = document.getElementById('view-table');
    const data = filtered();

    data.sort((a, b) => {
      let va, vb;
      switch (sortCol) {
        case 'name': va = a.name.toLowerCase(); vb = b.name.toLowerCase(); break;
        case 'stage': va = STAGES.indexOf(a.stage); vb = STAGES.indexOf(b.stage); break;
        case 'ecosystem': va = a.ecosystem.toLowerCase(); vb = b.ecosystem.toLowerCase(); break;
        case 'platform': va = a.mainPlatform.toLowerCase(); vb = b.mainPlatform.toLowerCase(); break;
        case 'followers': va = maxFollowers(a); vb = maxFollowers(b); break;
        case 'email': va = a.hasEmail ? 1 : 0; vb = b.hasEmail ? 1 : 0; break;
        case 'deal': va = a.hasDeal ? (a.deal.type || '') : ''; vb = b.hasDeal ? (b.deal.type || '') : ''; break;
        case 'updated': va = a.updated || ''; vb = b.updated || ''; break;
        default: va = ''; vb = '';
      }
      if (va < vb) return -sortDir;
      if (va > vb) return sortDir;
      return 0;
    });

    const arrow = col => col === sortCol ? (sortDir === 1 ? ' &#9650;' : ' &#9660;') : '';

    let html = '<div class="table-count">' + data.length + ' creators</div>';
    html += '<div class="table-wrap"><table class="data-table"><thead><tr>';
    const cols = [['name','Name'],['stage','Stage'],['ecosystem','Ecosystem'],['platform','Platform'],['followers','Followers'],['email','Email'],['deal','Deal'],['updated','Updated']];
    cols.forEach(([key, label]) => {
      html += '<th onclick="sortTable(\'' + key + '\')">' + label + '<span class="sort-arrow">' + arrow(key) + '</span></th>';
    });
    html += '</tr></thead><tbody>';

    data.forEach(c => {
      html += '<tr onclick="openDetail(\'' + esc(c.slug) + '\')">';
      html += '<td><strong>' + esc(c.name) + '</strong>' + (c.handle ? ' <span style="color:var(--fg3)">' + esc(c.handle) + '</span>' : '') + '</td>';
      html += '<td><span class="stage-badge ' + stageClass(c.stage) + '">' + esc(c.stage) + '</span></td>';
      html += '<td>' + esc(c.ecosystem) + '</td>';
      html += '<td>' + esc(c.mainPlatform) + '</td>';
      html += '<td>' + esc(topFollowers(c)) + '</td>';
      html += '<td>' + (c.hasEmail ? '&#9989;' : '') + '</td>';
      html += '<td>' + (c.hasDeal ? esc(c.deal.type || 'Yes') : '') + '</td>';
      html += '<td style="color:var(--fg3);font-size:12px">' + esc(c.updated) + '</td>';
      html += '</tr>';
    });

    html += '</tbody></table></div>';
    el.innerHTML = html;
  }

  function maxFollowers(c) {
    if (!c.channels.length) return 0;
    return Math.max(...c.channels.map(ch => ch.followersNumeric || 0));
  }
  function topFollowers(c) {
    if (!c.channels.length) return '';
    const top = c.channels.reduce((a, b) => (a.followersNumeric || 0) > (b.followersNumeric || 0) ? a : b);
    return top.followers || '';
  }

  window.sortTable = function(col) {
    if (sortCol === col) sortDir *= -1;
    else { sortCol = col; sortDir = 1; }
    renderTable();
  };

  // === STATS VIEW ===
  function renderStats() {
    const el = document.getElementById('view-stats');
    const data = filtered();

    let html = '<div class="stats-grid">';

    // Total
    html += '<div class="stat-card"><h3>Total Creators</h3><div class="stat-number">' + data.length + '</div>';
    html += '<div class="stat-sub">of ' + creators.length + ' total</div></div>';

    // Email coverage
    const withEmail = data.filter(c => c.hasEmail).length;
    const pct = data.length ? Math.round(withEmail / data.length * 100) : 0;
    html += '<div class="stat-card"><h3>Email Coverage</h3><div class="stat-number">' + pct + '%</div>';
    html += '<div class="stat-sub">' + withEmail + ' of ' + data.length + ' have email</div></div>';

    // Deals
    const withDeal = data.filter(c => c.hasDeal).length;
    html += '<div class="stat-card"><h3>Active Deals</h3><div class="stat-number">' + withDeal + '</div>';
    const dealTypes = {};
    data.filter(c => c.hasDeal).forEach(c => { const t = c.deal.type || 'Other'; dealTypes[t] = (dealTypes[t]||0) + 1; });
    html += '<div class="stat-sub">' + Object.entries(dealTypes).map(([k,v]) => k + ': ' + v).join(', ') + '</div></div>';

    // With touchpoints
    const withTP = data.filter(c => c.touchpoints && c.touchpoints.length > 0).length;
    html += '<div class="stat-card"><h3>Have Touchpoints</h3><div class="stat-number">' + withTP + '</div>';
    html += '<div class="stat-sub">creators with interaction history</div></div>';

    // Bar: stages
    html += '<div class="stat-card"><h3>Creators by Stage</h3>' + barChart(countBy(data, 'stage'), STAGES, [
      'var(--fg3)','var(--yellow)','var(--orange)','var(--purple)','var(--teal)','var(--green)','var(--yellow)','var(--red)'
    ]) + '</div>';

    // Bar: ecosystems (top 10)
    const ecoCounts = countBy(data, 'ecosystem');
    const ecoSorted = Object.entries(ecoCounts).sort((a,b) => b[1] - a[1]);
    const ecoTop = ecoSorted.slice(0, 10);
    const ecoOther = ecoSorted.slice(10).reduce((s, [,v]) => s + v, 0);
    if (ecoOther > 0) ecoTop.push(['Other', ecoOther]);
    html += '<div class="stat-card"><h3>Creators by Ecosystem</h3>' + barChartFromEntries(ecoTop, 'var(--purple)') + '</div>';

    // Bar: platforms
    const platCounts = countBy(data, 'mainPlatform');
    const platSorted = Object.entries(platCounts).sort((a,b) => b[1] - a[1]);
    html += '<div class="stat-card"><h3>Creators by Platform</h3>' + barChartFromEntries(platSorted, 'var(--teal)') + '</div>';

    html += '</div>';
    el.innerHTML = html;
  }

  function countBy(arr, key) {
    const m = {};
    arr.forEach(c => { const v = c[key] || '(none)'; m[v] = (m[v]||0) + 1; });
    return m;
  }

  function barChart(counts, orderedKeys, colors) {
    const max = Math.max(...Object.values(counts), 1);
    let html = '<div class="bar-chart">';
    orderedKeys.forEach((k, i) => {
      const v = counts[k] || 0;
      const pct = Math.max(v / max * 100, 0);
      const color = colors[i % colors.length];
      html += '<div class="bar-row"><span class="bar-label">' + esc(k) + '</span><div class="bar-track"><div class="bar-fill" style="width:' + pct + '%;background:' + color + '">' + (pct > 15 ? v : '') + '</div></div><span class="bar-value">' + v + '</span></div>';
    });
    html += '</div>';
    return html;
  }

  function barChartFromEntries(entries, color) {
    const max = entries.length ? Math.max(...entries.map(e => e[1]), 1) : 1;
    let html = '<div class="bar-chart">';
    entries.forEach(([k, v]) => {
      const pct = Math.max(v / max * 100, 0);
      html += '<div class="bar-row"><span class="bar-label">' + esc(k) + '</span><div class="bar-track"><div class="bar-fill" style="width:' + pct + '%;background:' + color + '">' + (pct > 15 ? v : '') + '</div></div><span class="bar-value">' + v + '</span></div>';
    });
    html += '</div>';
    return html;
  }

  // === APPLY FILTERS ===
  function applyFilters() {
    renderKanban();
    renderTable();
    renderStats();
  }

  // Expose openDetail globally
  window.openDetail = openDetail;

  // Initial render
  renderWorkflow();
  renderKanban();
  renderTable();
  renderStats();
})();
"""


if __name__ == "__main__":
    build()
