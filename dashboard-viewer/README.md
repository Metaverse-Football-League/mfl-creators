# Creator Dashboard Viewer

Interactive HTML dashboard for the MFL creator pipeline. Parses all creator markdown profiles and generates a single self-contained HTML file.

## Quick Start

**Double-click `open-dashboard.command`** in Finder. That's it.

It rebuilds the data from your latest markdown files and opens the dashboard in your browser.

## What You Get

- **Workflow view** — Action Needed, Waiting On Response, Upcoming Renewals
- **Kanban view** — creators grouped by stage (Prospect through Churned)
- **Table view** — sortable columns, click any row for details
- **Stats view** — bar charts for stage/ecosystem/platform breakdowns

All views have global filters (stage, ecosystem, platform, email, search) and a detail panel that shows the full profile + touchpoints when you click a creator.

## Manual Usage

```sh
cd creators-management/dashboard-viewer
python3 build.py
open index.html
```

## Files

| File | Purpose |
|------|---------|
| `build.py` | Python script that parses markdown and generates HTML |
| `index.html` | Generated dashboard (gitignored, ~500 KB) |
| `open-dashboard.command` | Double-click launcher for macOS |
| `README.md` | This file |
