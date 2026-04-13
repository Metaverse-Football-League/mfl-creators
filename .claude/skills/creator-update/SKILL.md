---
name: creator-update
description: >
  Update a content creator's profile and touchpoints from source materials (meeting transcripts,
  Discord logs, notes). Use when the user runs /creator-update or asks to update a creator's info,
  add meeting notes, or incorporate new information about a content creator partnership. Triggers on:
  (1) User provides meeting transcripts or Discord conversations about a creator,
  (2) User asks to update a specific creator's profile or touchpoints,
  (3) User runs /creator-update with a creator name and source material.
  (4) User asks to refresh or fetch channel metrics/stats for a creator.
  NOT for auditing content output (use /creator-audit instead).
---

# Update Creator Skill

Update a content creator's `profile.md` and `touchpoints.md` from source materials — meeting transcripts, Discord logs, or notes provided by the user.

## Invocation

- `/creator-update workthespace` + pasted transcript/Discord text
- `/creator-update nepenthez` + pasted meeting notes
- User pastes source material and says "update WorkTheSpace info based on this"
- `/creator-update workthespace --dm` — read Discord DMs directly via agent-browser (no paste needed)

## Creator File Structure

Each creator lives under `creators-management/creators/<slug>/`:

```
creators-management/creators/<slug>/
├── profile.md          # Bio, channels, deal, MFL engagement, notes
├── content-audit.md    # Deliverable tracking (managed by /creator-audit)
└── touchpoints.md      # Chronological interaction log
```

## Workflow

### Phase 1: Identify Creator and Read Existing Files

1. Determine the creator slug from arguments or context (e.g., "workthespace", "nepenthez")
2. Read these files in parallel:
   - `creators-management/creators/<slug>/profile.md`
   - `creators-management/creators/<slug>/touchpoints.md`
   - `creators-management/CLAUDE.md` (writing rules for creator files)

If the creator folder doesn't exist, ask the user to confirm, then create it and copy template files:
    ```bash
    mkdir -p creators-management/creators/<slug>
    cp creators-management/_template/*.md creators-management/creators/<slug>/
    ```
    Then fill in the profile with available information.

### Phase 2: Analyze Source Material

3. Read all source material provided by the user. **If the source includes screenshots of conversations**, read `creators-management/platform-identification.md` and use it to correctly identify the messaging platform (X DM, WhatsApp, Discord, Telegram, etc.) before logging touchpoints. Do not guess — match visual indicators from the guide.

   Sources can be:
   - Meeting transcripts (pasted inline or file paths under `sources/transcripts/`)
   - Discord conversation logs (pasted inline or file paths under `sources/discord/`)
   - Notes or bullet points from the user
   - **Discord DMs via agent-browser** — if the user uses the `--dm` flag or asks to read DMs directly, invoke the `/discord-read-dm` skill first. It will extract the conversation to `/tmp/discord-dm-<slug>.txt`, then use that file as the source material for the remaining phases. The extraction automatically limits to messages since the last touchpoint date in `touchpoints.md` (minus a 14-day overlap). To fetch the full conversation history instead, use `--dm --full`.

4. Extract information into these categories:

   **Profile updates** (long-term facts for `profile.md`):
   - Channel metrics (subscribers, views, concurrent viewers)
   - Deal changes (guarantee, commission, deliverables, contract terms)
   - MFL engagement (teams owned, agency size, activity level, discovery story)
   - Background facts (career history, other partnerships, achievements)
   - Relationship context (how they discovered MFL, what they enjoy, content preferences)
   - Product ideas or feedback contributed
   - Creator referrals made (other creators they introduced)

   **Touchpoint entries** (interactions for `touchpoints.md`):
   - Each distinct meeting, call, or significant Discord exchange = one touchpoint
   - Extract: date, type (Call/X DM/Discord/Email/WhatsApp/In-Person), summary, key points, action items, next step

   **Skip** (not for creator files):
   - MFL internal strategy discussions not directly about the creator
   - General game mechanics explanations
   - Small talk / personal chat without business relevance

### Phase 3: Update Profile

5. Update `profile.md` sections as needed. Preserve existing content — add to it, don't replace unless correcting errors.

   **Sections to update:**

   | Section | What to add |
   |---------|------------|
   | **Channels** | New metrics, engagement data, platform notes |
   | **MFL Engagement** | Teams, agency, playing habits, alliance participation |
   | **Deal** | Contract changes, guarantee, commission, deliverables, branding, IP terms |
   | **Notes > Background** | Career facts, achievements, other brand deals |
   | **Notes > MFL Relationship** | Discovery story, referrals made, events attended, content preferences, feedback given |
   | **Notes > Product Ideas Contributed** | Feature suggestions with enough detail to understand the proposal |
   | **Next Actions** | New action items; check off completed ones. Dashboard Next Actions must be concrete one-off tasks only — never invoice/payment processing (handled via finance), never generic "await content" or implicit ongoing activities. When all actions are done, set dashboard Next Action and Due to `-` |

   **Due Date enforcement:** When adding or changing a Next Action on the dashboard, always set a Due date per the **Due Date Policy** in `creators-management/CLAUDE.md`. Classify the action text by keyword to determine our-side (next business day) vs their-side (today + 7 days). If unclear, default to our-side. **Never leave Due as `—` or `-` when Next Action is populated.**

   **Rules:**
   - Apply the long-term test: "Will this still be accurate and relevant in one year?" If not, it belongs in touchpoints only, not profile
   - No quotes or attributions — present as established facts
   - No specific dates/timelines in profile (those go in touchpoints)
   - No operational statuses or temporary states
   - Deal section: include both the structured table AND prose explanation of non-obvious terms
   - Deliverables: must include **exact quantities and frequencies** as specified in the contract (e.g., "2 dedicated videos/month + 4 tweets/week"). Never write vague deliverables like "tweets" or "integrations" without quantity and cadence.
   - Product ideas: summarize the concept, not the full conversation. Include enough for someone to understand the proposal without reading the source
   - Historical performance data (e.g., referral counts, revenue generated) is acceptable — it's factual record

6. Update the header line `Updated: YYYY-MM-DD` to today's date.

### Phase 4: Update Touchpoints

7. Append new entries to `touchpoints.md` in chronological order. Each entry follows this format:

   ```markdown
   ### YYYY-MM-DD - [Type: Call/X DM/Discord/Email/WhatsApp/In-Person]
   [1-2 sentence summary of what was discussed/decided]
   - Key points: [bullet list of important items]
   - Action items: [what each party committed to]
   - Next step: [immediate follow-up]
   ```

   **Rules:**
   - One entry per distinct interaction (a call is one entry; a week of Discord back-and-forth can be one entry)
   - Use the actual date of the interaction, not today's date
   - Summarize — don't transcribe. Capture decisions and commitments, not conversation flow
   - Include both parties' contributions (what MFL said AND what the creator said)
   - For Discord threads spanning multiple days, use the first message date and note the range
   - Chronological order (oldest first, newest last)
   - Do NOT duplicate entries that already exist in the file

### Phase 5: Review

8. Show the user a summary of all changes made:
   - List of profile sections updated (with brief description of what changed)
   - Number of touchpoint entries added
   - Dashboard Due date set/updated: show the date and reasoning (e.g., "Due: 2026-04-10 (our-side action: 'Reply to Joe')")
   - Any information that was skipped and why (e.g., "Skipped ELO discussion details — too speculative for profile, captured in touchpoints")

9. Do NOT commit. Let the user review the changes and decide when to commit.

## Information Classification Guide

| Information Type | Where It Goes | Example |
|-----------------|---------------|---------|
| Channel subscriber count | Profile > Channels | "~223K YouTube subs" |
| Streaming concurrent viewers | Profile > Channels | "Avg concurrent ~400 Twitch" |
| Deal guarantee amount | Profile > Deal table | "600€/month" |
| Contract IP terms | Profile > Deal prose | "Non-exclusive license, 6-month wind-down" |
| Number of MFL teams owned | Profile > MFL Engagement | "7-8 clubs" |
| How they discovered MFL | Profile > MFL Relationship | "Community member mentioned in Twitch chat" |
| Feature idea pitched | Profile > Product Ideas | "Ranked ELO ladder with team-strength weighting" |
| Other creators referred | Profile > MFL Relationship | "Referred Clayts, TomFM, lollujo" |
| Event attendance | Profile > MFL Relationship + Touchpoint | Fact in profile, details in touchpoint |
| Specific referral numbers for a month | Profile > Deal prose | "64 referrals in April 2025" — factual record |
| "Contract signed on Feb 11" | Touchpoint only | Operational date |
| "Starting streams mid-February" | Touchpoint only | Temporary timeline |
| "Japan trip in March" | Touchpoint only | Personal/scheduling |
| "FM launch keeping me busy" | Touchpoint only | Temporary context |
| Discussion of MFL strategy/challenges | Touchpoint only | Internal strategy, not creator profile |

## Fetching Live Channel Metrics

When the user asks to update channel data, or when profile channel metrics are outdated/missing, use `yt-dlp` to fetch live stats directly from YouTube.

### Method

```bash
# Get subscriber count + avg views from last 5 videos
yt-dlp --dump-json --playlist-items 1-5 "https://www.youtube.com/@HANDLE/videos" 2>/dev/null | python3 -c "
import sys,json
views=[]; subs=None; ch=None
for line in sys.stdin:
    d=json.loads(line)
    ch=d.get('channel','?')
    subs=d.get('channel_follower_count','?')
    views.append(d.get('view_count',0))
avg=sum(views)//len(views) if views else 0
print(f'Channel: {ch}\nSubscribers: {subs}\nAvg views (last {len(views)} vids): {avg}\nViews: {views}')
"
```

### YouTube Handle Discovery

The YouTube handle may differ from the creator's X/Twitter handle. Common patterns:
- Same as X handle: `@WorkTheSpace`, `@Quinny3001`
- Different from X: Andrew Laird → `@sorarewithlaird` (not `@andrewmlaird`)
- Channel name variant: MrFutlovers → `@MrFutlovers` (YouTube name: Jakobsweg26)
- SimplyAlex → `/c/SimplyAlexSR` (YouTube name: SimplyAlexGaming)
- Le Poulain → `@le_poulain` (not `@LePoulainYT`)

If the first handle returns 0 results or very low subs (<50), try alternate handles or search for the creator's known channel name.

### When to Fetch

- Profile has `TBD` or missing values in the Channels table
- User explicitly asks to refresh/update channel metrics
- As part of a bulk profile update when source material doesn't include fresh metrics

### Updating the Profile

Update the **Channels** table in `profile.md` with:
- Subscriber/follower count (rounded: e.g., ~223K, ~4.99K, ~1.77K)
- Avg views per video (from last 5 videos)
- Note the date fetched in the profile header `Updated: YYYY-MM-DD`

## Error Handling

- If creator folder doesn't exist → ask user to confirm creation
- If source material is ambiguous about which creator → ask user to clarify
- If source contains info about multiple creators → process one at a time, confirm with user
- If unsure whether information is long-term or ephemeral → default to touchpoints only
