---
name: discord-read-dm
description: >
  Read Discord DM/group conversations using agent-browser controlling Discord web
  in a persistent browser profile. Use when the user asks to read/extract Discord
  DMs with a specific creator or contact, when /creator-update is invoked with --dm,
  or when another skill needs Discord conversation content as source material.
  Triggers on: (1) "read my Discord DMs with @CreatorName", (2) "/creator-update
  creatorname --dm", (3) "extract the Discord conversation with X", (4) "update
  CreatorName from Discord". Outputs `/tmp/discord-dm-<slug>.txt` for downstream skills.
allowed-tools: Bash(agent-browser:*), Bash(python3:*), Bash(curl:*)
---

# Discord Read DM

Extract Discord conversations via agent-browser driving **Discord web** (`https://discord.com`)
in a persistent browser profile (`~/.agent-browser/profiles/discord-web`). The user logs in
once (QR code from mobile app); the profile keeps the session forever.

## Why web (not Electron)

Earlier versions used the Discord desktop app over CDP on port 9224. Web is simpler:
- No CDP launch script
- No window-targeting issues
- Same skill works headless or headed
- Snapshots include richer ARIA content (timestamps in proper format)

## Phase 1 — Open Discord web

Always pass `--profile ~/.agent-browser/profiles/discord-web --session discord-web` for
session isolation and persistence.

```bash
agent-browser --profile ~/.agent-browser/profiles/discord-web --session discord-web get url
```

If the result is `about:blank` or fails, the session is fresh. Open Discord:

```bash
agent-browser --headed --profile ~/.agent-browser/profiles/discord-web \
  --session discord-web open "https://discord.com/login"
```

Then check login state:

```bash
agent-browser --session discord-web snapshot 2>&1 | head -20
```

If you see `heading "Welcome back!"`, ask the user to log in via the open window
(QR code is fastest), then wait for them to confirm. Once logged in, Discord redirects
to a channel URL like `https://discord.com/channels/.../...`.

## Phase 2 — Resolve the conversation URL

**Priority 1: direct URL from creator profile.**
Read `creators-management/creators/<slug>/profile.md` and look for the **Discord Group**
field. It contains a markdown link like:

```
| **Discord Group** | [BushRod x MFL](https://discord.com/channels/@me/1488485267370278922) |
```

If found, navigate directly:

```bash
agent-browser --session discord-web open "https://discord.com/channels/@me/<id>"
agent-browser --session discord-web wait 2000
```

**Priority 2: search by name.**
If no Discord Group link is in the profile, navigate to `https://discord.com/channels/@me`,
press `Control+k` to open the Quick Switcher, type `<CreatorName> x MFL` (the standard
group naming convention) — fall back to just `<CreatorName>` if no match. Click the
result and verify the channel header.

```bash
agent-browser --session discord-web open "https://discord.com/channels/@me"
agent-browser --session discord-web wait 1500
agent-browser --session discord-web press "Control+k"
agent-browser --session discord-web wait 500
agent-browser --session discord-web keyboard type "CreatorName x MFL"
agent-browser --session discord-web wait 1000
agent-browser --session discord-web snapshot 2>&1 | grep -i "creatorname"
# click the matching ref
```

## Phase 3 — Determine the cutoff date

1. If the caller passed an explicit `since` date, use it.
2. If `--full` is set, no cutoff.
3. Otherwise read `creators-management/creators/<slug>/touchpoints.md`, find the most
   recent `### YYYY-MM-DD` header, and subtract **14 days** for overlap (catches
   messages partially captured last time).
4. If touchpoints.md is empty or only template content, no cutoff.

## Phase 4 — Capture messages

Take an initial snapshot:

```bash
agent-browser --session discord-web snapshot 2>&1 > /tmp/discord-snap-<slug>.txt
grep -nE 'separator "' /tmp/discord-snap-<slug>.txt
```

The `separator` lines are date dividers (`separator "23 March 2026"`). If the earliest
visible separator is **after** the cutoff, scroll up to load older messages by scrolling
the earliest separator into view (this triggers Discord's lazy load):

```bash
agent-browser --session discord-web scrollintoview '[aria-label="<earliest separator label>"]'
agent-browser --session discord-web wait 1500
agent-browser --session discord-web snapshot 2>&1 > /tmp/discord-snap-<slug>.txt
```

Repeat until the earliest separator is at or before the cutoff date (or you reach the
beginning of the conversation — the same separator stops moving).

**Important:** use `scrollintoview` with the exact aria-label of the *earliest* visible
separator. Plain `scroll up` does not target Discord's virtualized message list reliably.

## Phase 5 — Parse to chronological text

Run the bundled parser:

```bash
python3 .claude/skills/discord-read-dm/scripts/parse_snapshot.py \
  /tmp/discord-snap-<slug>.txt --since YYYY-MM-DD \
  > /tmp/discord-dm-<slug>.txt
```

Output format:
```
[YYYY-MM-DD HH:MM] Sender: message text
```

The parser handles:
- Full-date and time-only timestamps (grouped consecutive messages)
- Reply messages (strips the `replying to X` suffix from sender)
- System messages like `Mathurin added Bastien to the group` (sender = `(system)`)
- Emoji and special characters in message bodies

Known limitations:
- Embed/preview cards leak some metadata into message text (e.g., link preview titles)
- Image attachments show as `Image Remove Message Attachment Delete` (UI buttons)

These are non-critical for `/creator-update` consumption.

## Phase 6 — Report

Tell the user:
- Number of messages captured
- Date range covered
- Path: `/tmp/discord-dm-<slug>.txt`
- Any blockers or partial extraction warnings

## Error handling

- **Login page persists** → ask user to scan the QR code in the headed window
- **Direct URL navigates to a 404 / "channel not found"** → group DM was deleted or you're
  not a member; fall back to Phase 2 Priority 2 (search)
- **`scrollintoview` finds 0 elements** → conversation has no date separators yet; you're
  at the very beginning, stop scrolling
- **Profile dir locked** ("Browser is already running") → another agent has the session;
  call `agent-browser --session discord-web close` first
