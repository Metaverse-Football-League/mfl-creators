# Creator Agent

> Domain-specific instructions for the creator/influencer management agent. The root `../CLAUDE.md` provides shared context.

---

## Purpose

Manage content creator relationships and outreach for MFL. Track deliverables, update profiles, maintain CRM records. This is an operational/CRM system, not documentation.

---

## Writing Rules (Different from KB!)

Creator files follow **different rules** than knowledge base files:

- **Dates, quotes, and attributions are OK** — these are CRM records, not evergreen documentation
- **Operational data is expected**: contract dates, deal amounts, next actions, status updates
- **No "long-term test"** — CRM data includes ephemeral operational info by design
- **Accuracy matters**, but style is practical, not documentary
- **Always update `dashboard.md`** when creator status, deal, or next-action changes

---

## File Structure

```
mfl-creators/
├── CLAUDE.md         ← This file
├── dashboard.md      ← Pipeline tracking (Active, Paused, Negotiation, Outreach, To Contact)
├── community-partners.md ← Lightweight contact list for small creators (news distribution)
├── messaging-style.md ← Mathurin's tone, formatting & scheduling preferences
├── partnership-guidelines.md ← Partnership philosophy, pitch talking points & deal framing
├── platform-identification.md ← Visual guide for identifying messaging platforms in screenshots
├── _template/        ← Onboarding kit for new creators
│   ├── profile.md
│   ├── content-audit.md
│   ├── touchpoints.md
│   └── message-templates.md
├── creators/         ← All creator profile folders
│   └── <slug>/       ← One folder per creator
│       ├── profile.md
│       ├── content-audit.md
│       └── touchpoints.md
└── scripts/
    ├── audit-creator.py
    ├── extract-x-dms.js
    └── discord-cdp.sh
```

---

## Dashboard

`dashboard.md` is the **source of truth** for the creator pipeline. It shows only actionable stages:

- **Active** — producing content
- **Paused** — relationship stopped, retry date set
- **Negotiation** — deal discussions in progress
- **Outreach** — contacted, waiting for response
- **To Contact** — reviewed and interesting, ready to contact

**Prospect** and **Archived** creators do NOT appear on the dashboard — they only exist in their `profile.md`.

**Community partners** (small creators we share news with) are tracked separately in `community-partners.md` — they do NOT appear on the dashboard or have individual `creators/` folders.

Columns: Name, Profile, MFL Profile, Main Platform, Followers, Status, Deal, Next Action, Due.

**After every creator profile update** (any file in a creator's folder), check `dashboard.md` and update it if needed.

### Pipeline Rules

| Stage | On Dashboard | Next Actions | Description |
|-------|-------------|--------------|-------------|
| **Prospect** | No | No | Contact added, needs review before deciding to reach out |
| **To Contact** | Yes | X follow-back tracking only | Reviewed and interesting, ready to contact |
| **Outreach** | Yes | Follow-up only | Contacted, waiting for response |
| **Negotiation** | Yes | Various | Ongoing deal discussions |
| **Active** | Yes | Concrete tasks only | Active partner producing content |
| **Paused** | Yes | Retry date | Relationship stopped. Next Action = retry in ~2 months unless specified |
| **Archived** | No | No | Not pursuing. Reason documented in Notes |

- **Active Next Actions**: only concrete, one-off follow-up tasks (e.g., "Schedule call", "Await response", "Send contract"). Never use "Monitor X" — ongoing content monitoring is implicit for all Active creators. Never use invoice/payment processing (handled via email/finance). Never use generic "await content ramp-up" or similar — content production is implicit for Active creators. When all Next Actions are completed, set to `-`
- **Archived requires a reason** in the Notes section (e.g., "Archived: Inactive channel since 2025", "Archived: Not a fit — content too generic")
- **Prospect → To Contact** transition happens after manual review
- **Negotiation → Active** transition: use `/creator-activate` after contract is signed. Creates Discord group with Bastien & Lucas, sends kickoff message, schedules kickoff call
- **Archived creators can re-enter** the pipeline if circumstances change

### Due Date Policy

**Invariant:** Next Action and Due must always be in sync. Both populated or both `-`. Never leave Due as `—` or `-` when Next Action is populated.

Classify every Next Action into one of two categories to determine the due date:

| Category | Due Date | Keyword Signals |
|----------|----------|-----------------|
| **Our-side action** (ball is on us) | Next business day (tomorrow, or Monday if today is Friday) | reply, send, create, schedule, set up, draft, follow up, propose, check in, review, reschedule, bump, share, prepare |
| **Their-side action** (ball is on them) | Today + 7 days | await response, await booking, await signature, await invoice, await feedback, await follow-back |

**Rules:**
- If the action text doesn't clearly match either category, **default to our-side** (next business day). Faster is safer — we'd rather act early than lose days.
- **Never overwrite** a valid future due date that was intentionally set (e.g., a retry date for Paused creators, or a date the user explicitly chose). Only fill missing dates or update stale/past ones when the action changes.
- When an action is completed and replaced with a new action, reset Due to match the new action's category.
- When all actions are completed, set both Next Action and Due to `-`.

---

## Creator Profile Schema

Each creator folder has 3 files:

### `profile.md` — Main creator file

- **Header**: `# Name (@XHandle)` with `> **Stage** | Vertical | Language | Updated: YYYY-MM-DD`
- **Stage**: One of `Prospect`, `To Contact`, `Outreach`, `Negotiation`, `Active`, `Paused`, `Archived`
- **Info Table**: Main Platform, Email, Location, Discord, Discord Group, MFL Username, MFL Wallet, MFL Profile, Last Audit Week
- **Channels table**: Platform | Link | Followers | Avg Views / Engagement
- **Deal table**: Type, Guarantee, Commission, Contract dates, Deliverables (must include exact quantities and frequencies matching the contract — e.g., "2 videos/month + 4 tweets/week", never vague like "tweets" or "integrations")
- **Next Actions**: Checklist of pending tasks
- **Notes**: Free-form context, observations, relationship notes

Machine-readable fields:
- X handle: from header `(@Handle)` or Channels table X row
- YouTube URL: Channels table, YouTube row
- Twitch URL: Channels table, Twitch row
- Deliverables: Deal table, free text

### `content-audit.md` — Populated by `/creator-audit` skill

- Expected deliverables (from the deal)
- Observations on content patterns
- Summary table with per-week totals
- Week Details sections with individual content items

### `touchpoints.md` — Chronological interaction log

```
### YYYY-MM-DD - [Type: Email/Discord/Call/WhatsApp]
[Summary of conversation]
- Key points:
- Action items:
- Next step:
```

Most recent entries first.

---

## Available Skills

- `/creator-audit` — Audit deliverables across X, YouTube, Twitch
- `/creator-update` — Update profiles from source materials (transcripts, Discord logs)
- `/creator-payments` — Read and manage the creator payment tracking spreadsheet (requires `gws` CLI + Google Sheets auth)
- `/discord-read-dm` — Read Discord DM conversations via agent-browser web (Discord login persisted)

### Discord DM Integration

The `/discord-read-dm` skill reads DM conversations from **Discord web** via agent-browser, using a persistent profile at `~/.agent-browser/profiles/discord-web` where the user is already logged in. No copy-pasting, no desktop app, no CDP setup.

**Usage:**
- Standalone: "Read my Discord DMs with @CreatorName"
- With creator-update: `/creator-update creatorname --dm`

The extracted conversation is saved to `/tmp/discord-dm-<slug>.txt` and can be used as source material for `/creator-update`.

**Session isolation:** Always use `--profile ~/.agent-browser/profiles/discord-web --session discord-web` when invoking agent-browser for Discord. This keeps the Discord session separate from other browser-using skills (which use `--session web` or `--session batch{N}`).

---

## New Creator Onboarding

1. Copy `_template/` folder to `creators/<name-slug>/`
2. Fill in `profile.md` with the creator's information
3. Leave `content-audit.md` and `touchpoints.md` as-is (placeholder content)
4. Add the creator to `dashboard.md` only if status is **To Contact or beyond** (not Prospect)
5. Use `_template/message-templates.md` for outreach

---

## Finding Active Creators

Read `dashboard.md` → `### Active` table. Do **not** glob all folders — the dashboard is the source of truth.

---

## Cross-References

- Messaging style & tone: `messaging-style.md` (Mathurin's preferences for creator outreach)
- Partnership approach & pitch guide: `partnership-guidelines.md` (how to position MFL, deal framing, onboarding philosophy)
- Platform identification: `platform-identification.md` (visual cues for X DM vs WhatsApp vs Discord etc.)
- MFL product knowledge: `../mfl-wiki/knowledge-base/` (when you need game mechanics, strategy, etc.)
- Recent activity context: `../mfl-wiki/memory/recaps/` for Discord/meeting recaps
- Raw sources: `../mfl-wiki/sources/` for Discord exports and transcripts
- Influencer program strategy: `../mfl-wiki/knowledge-base/09-marketing/06-influencer-program.md`
- Communication guidelines: `../mfl-wiki/knowledge-base/09-marketing/10-communication-guidelines.md`
- Payment tracking spreadsheet: managed via `/creator-payments` skill (`gws` CLI → Google Sheets)
- Invoice template (for creators): https://docs.google.com/spreadsheets/d/1STAnCn-WtRtf5k6VgbipB43VqZf4Iikh5bCWANMO9qU/edit (in `23-AFFILIATES` Drive folder)
- Invoice filling guide (for creators): see "How to Fill Your Invoice" doc in `23-AFFILIATES` Drive folder
- Community partners (news distribution list): `community-partners.md`

---

## Conventions

- **Folder naming**: lowercase, hyphenated (`mookie-barbu`, `simply-alex`)
- **One folder per creator**
- **English only** for all files
- **Keep operational records up to date** — stale data is worse than no data
- **When drafting messages** (DMs, emails, outreach): always print the message in the terminal AND save it to a temp file at `/tmp/msg-<context>.md` so the user can open it and copy-paste easily
