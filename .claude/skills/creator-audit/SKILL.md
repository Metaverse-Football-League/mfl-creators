---
name: creator-audit
description: Audit content creator deliverables across X, YouTube, and Twitch. Use when the user runs /creator-audit or asks to check a creator's content output.
argument-hint: "[handle] [time range, e.g. 'last 3 weeks' or '2026-01-20 to 2026-02-10']"
---

# Content Creator Audit Skill

Audit content creator deliverables against their contracts by checking X (Twitter), YouTube, and Twitch for MFL-related content. Results are written into the creator's `content-audit.md` file.

## Invocation

- `/creator-audit MookieBarbu last 3 weeks`
- `/creator-audit all 2026-01-20 to 2026-02-25`
- `/creator-audit` (defaults to all active creators, last 4 weeks)

## Creator File Structure

Each creator has a folder under `creators-management/creators/`:

```
creators-management/creators/royalivi/
├── profile.md          # Bio, channels, deal, next actions, notes
├── content-audit.md    # Observations, summary table, week details
└── touchpoints.md      # Chronological interaction log
```

Key fields in `profile.md`:
- **Info table**: `| **Last Audit Week** | 2026-W08 |` — tracks what's already audited
- **Channels table**: URLs for X, YouTube, Twitch
- **Deal table**: `**Deliverables**` row with contract terms

## Workflow

### Phase 1: Parse Arguments

1. Extract the **handle** (or "all") and **time range** from arguments
2. Defaults: handle = "all", time range = "last 4 weeks"
3. Resolve relative dates ("last N weeks") to absolute Monday-aligned start/end dates
   - "last 3 weeks" → 3 full Mon–Sun weeks ending on the most recent completed Sunday (or the current incomplete week if today is not Monday)
   - Always include the current incomplete week as the final week, marked as incomplete
4. For absolute date ranges ("2026-01-20 to 2026-02-10"), expand to full weeks:
   - Start date → previous Monday (or same day if already Monday)
   - End date → next Sunday (or same day if already Sunday)

### Phase 2: Identify Creators

5. Read `creators-management/CLAUDE.md` to understand the creator file structure.
6. If handle is "all":
   - Read `creators-management/dashboard.md`
   - Parse the `### Active` table — each row is an active creator
   - Extract the X handle from the Profile column (e.g., `[@MookieBarbu](https://x.com/MookieBarbu)` → `MookieBarbu`)
   - For each active creator, find and read their profile: `creators-management/creators/<slug>/profile.md`
   - Skip creators whose Deal > Deliverables is "TBD" or empty (no contract to audit against)
7. If a specific handle:
   - First check the dashboard `### Active` table for a matching handle in the Profile column
   - If found, read the corresponding `creators-management/creators/<slug>/profile.md`
   - If not in the Active table, fall back to folder name matching (e.g., "MookieBarbu" → `creators-management/creators/mookie-barbu/profile.md`)

### Phase 3: Extract Parameters (Main Agent)

8. For each creator to audit, read their `profile.md` and extract:
   - **X Handle**: Extract from the profile header `# Name (@Handle)` using regex, or from the Channels table X row (`https://x.com/<handle>`)
   - **YouTube Channel URL**: Extract from Channels table, YouTube row, Link column
   - **Twitch Channel URL**: Extract from Channels table, Twitch row, Link column
   - **Deliverables**: Read from Deal table, Deliverables row (free text — interpret for "vs expected" comparison)
   - **Last Audit Week**: Read from the info table `| **Last Audit Week** | 2026-Wxx |`
   - **Transcript Language**: Use `en` by default. For French-language creators (e.g., Le Poulain), use `fr`

   Note: MFL keywords are hardcoded in the script (X: `MFL OR playmfl OR playMFL`, YouTube: `mfl, playmfl, metaverse football league, playmfl.com`). No per-creator keyword config needed.

9. Determine which weeks to audit using `Last Audit Week`:
   - If the requested range starts **after** `Last Audit Week`, skip reading `content-audit.md` — just append new weeks
   - If overlap or redo is needed, read `content-audit.md` to get existing data
   - A week is "complete" if it's a past full Mon–Sun week with audit data
   - A week is "incomplete" if it's the current (in-progress) week
   - **Skip** already-audited complete weeks (unless user explicitly requests redo)
   - **Always re-audit** incomplete weeks
   - If complete weeks overlap with the request, ask the user: "Weeks X, Y, Z are already audited. Redo them?"

### Phase 4: Dispatch Sub-Agents

10. **When auditing multiple creators ("all")**: Launch one **Task sub-agent per creator** in parallel. Each sub-agent handles the full audit cycle for a single creator independently.

    **When auditing a single creator**: Skip the sub-agent and run directly in the main context (follow the same steps as the sub-agent prompt below).

11. For each creator, launch a Task sub-agent with `subagent_type: "general-purpose"` and the following prompt (fill in the bracketed values):

    ```
    You are auditing content creator [NAME] for MFL-related deliverables.

    ## Creator Info
    - Profile path: creators-management/creators/[slug]/profile.md
    - Content audit path: creators-management/creators/[slug]/content-audit.md
    - X Handle: [handle or "none"]
    - YouTube Channel: [url or "none"]
    - Twitch Channel: [url or "none"]
    - Deliverables: [deliverables text from profile]
    - Date range: [start_date] to [end_date]
    - Weeks to audit: [comma-separated week labels, e.g. "2026-W06, 2026-W07, 2026-W08"]
    - Last Audit Week: [week or "none"]
    - Transcript language: [en or fr]

    ## Steps

    ### Step 1: Run the Python script
    Run:
    ```
    python3 creators-management/scripts/creator-audit.py \
      --x-handle [handle] \
      --youtube-channel "[url]" \
      --twitch-channel "[url]" \
      --start-date [start] --end-date [end] \
      --fetch-transcripts \
      --transcript-language [lang]
    ```
    Omit any --x-handle, --youtube-channel, or --twitch-channel flags if the creator doesn't have that channel.

    ### Step 2: Parse JSON output
    Parse the JSON output from stdout. The script outputs structured data with weekly breakdowns.

    ### Step 3: Read existing content-audit.md
    If appending (weeks are after Last Audit Week), read the existing file to preserve prior data.
    If creating from scratch or redoing all weeks, start fresh.

    ### Step 4: Generate the markdown report

    Follow this exact output format for content-audit.md:

    ```markdown
    # Content Audit

    **Expected weekly content:** [Summarize deliverables, e.g. "X: 3 posts | YouTube: 1 video"]

    ## Observations

    [High-level patterns across ALL audited weeks — overwritten each audit run.
    Note trends in frequency, engagement, topics covered, platform distribution.
    Flag any concerns (missed weeks, declining engagement, etc.).]

    ## Summary

    | Week | X Posts | YT Dedicated | YT Integrations | YT Desc-Only | Streams | Twitch | Total | vs Expected | Notes |
    |------|---------|--------------|-----------------|--------------|---------|--------|-------|-------------|-------|
    | 2026-W04 (Jan 19–25) | 2 posts | 1 | — | — | — | — | 3 | On track | Strong engagement |

    ## Week Details

    ### 2026-W04 (Jan 19–25)

    **Weekly Summary**: 1 dedicated YT video and 2 X posts. Dedicated video covers Season 11
    preparation with 154 views. X posts about progression and transfers. Meets YouTube target
    (1/1 dedicated). X slightly below (2/3 posts). Overall: on track.

    **YouTube:**

    | Date | Type | Title (excerpt) | Views | Likes | Link |
    |------|------|-----------------|-------|-------|------|
    | 2026-01-19 | Dedicated | "PREPARING FOR THE NEW MFL SEASON!" | 154 | 10 | [link](url) |

    > **Summary**: Creator walks through squad preparation for Season 11, highlighting
    > key player signings and formation choice. Discusses the progression system and
    > how player development influenced transfer strategy. Covers league placement goals
    > and rivalry with a neighboring division club. Ends with transfer market plans.

    | 2026-01-22 | Integration @8:56 | "SORARE DRAFT WEEK 3" | 1,230 | 45 | [link](url?t=536) |
    | 2026-01-24 | Dedicated (Live) | "MFL LIVE - Season 11 Day 1!" | 89 | 12 | [link](url) |

    > **Summary**: Livestream VOD covering the first matchday of Season 11...

    **X/Twitter:**

    | Date | Type | Text (excerpt) | Impr | Likes | RT | Link |
    |------|------|----------------|------|-------|----|------|
    | 2026-01-21 | Post | "Season 11 is here! My squad..." | 85,930 | 102 | 22 | [link](url) |

    ### 2026-W05 (Jan 26–Feb 1)

    **Weekly Summary**: No MFL content detected across any platform. Below expectations
    for 1 YT video + 3 X posts.

    No MFL content this week.
    ```

    #### Type column values for YouTube:
    - `Dedicated` — MFL keyword in title (a full MFL video)
    - `Dedicated (Live)` — Dedicated MFL livestream
    - `Integration @MM:SS` — MFL keyword in description AND confirmed in transcript. The `@MM:SS` shows when MFL is first mentioned (from `integration_timestamp` field in JSON). Also append `?t=<seconds>` to the YouTube link so it jumps to the integration moment. Example: `Integration @8:56` with link `url?t=536`
    - `Integration (Live) @MM:SS` — Integration in a livestream (same timestamp rules)
    - `Desc-Only` — MFL in description but NOT confirmed in transcript (likely affiliate link only)
    - If `integration_timestamp` is missing or null, just use `Integration` without the timestamp

    #### Reclassifying integrations as dedicated:
    Some videos are classified as `integration` by the script because MFL isn't in the title, but they are actually **entirely about MFL**. When an integration video has a `transcript` field in the JSON:
    - Read the transcript and determine if MFL is the **main topic** of the entire video (e.g., the creator is playing MFL throughout, discussing MFL strategy, showing MFL gameplay) or just a brief mention/segment
    - If MFL is the main topic → reclassify as `Dedicated` in the Type column and write a summary blockquote (same as other dedicated videos)
    - If MFL is just one segment among other topics → keep as `Integration @MM:SS`

    #### Video summaries:
    For **dedicated** MFL videos that have a `transcript` field in the JSON:
    - Write a 4-6 line blockquote summary below the video's table row
    - Focus on: MFL topics covered, strategies/tactics discussed, notable gameplay moments
    - If multiple dedicated videos in one week, summarize each separately
    - If no transcript is available, skip the summary silently
    - Do NOT summarize integration or description-only videos

    #### Weekly Summary format:
    For each week, write a `**Weekly Summary**:` line BEFORE the content tables:
    - **Content count**: How many items on each platform (e.g., "2 YT videos + 3 X posts")
    - **Topics**: Brief mention of MFL topics covered (e.g., "progression, transfers, match recap")
    - **Frequency assessment**: Compare against deliverables (e.g., "Meets weekly YT target, X slightly below")
    - Keep to 2-4 lines
    - For weeks with no content: "No MFL content detected across any platform. Below expectations for [deliverables]."

    #### Incomplete weeks:
    For incomplete (current) weeks, add this note after the week heading:
    ```
    *(Incomplete week — audited on YYYY-MM-DD, week still in progress)*
    ```

    ### Step 5: Write content-audit.md
    - If appending new weeks only: read existing file, add new week rows to Summary table,
      add new Week Details sections, then overwrite `## Observations` based on ALL data
    - If replacing/merging weeks: keep existing weeks that aren't being redone, replace/add
      newly audited weeks, sort chronologically, then overwrite `## Observations`
    - Use the Edit tool to update content-audit.md

    ### Step 6: Update profile.md
    Update `Last Audit Week` in profile.md to the last **complete** week audited.

    ### Step 7: Return summary
    Return a single line:
    "[NAME]: [N] X posts, [N] YT dedicated, [N] YT integrations, [N] desc-only, [N] streams, [N] Twitch | [total] vs [expected] | [status]"
    Where status is: "On track", "Above", "Below", or "Miss"
    ```

12. Wait for all sub-agents to complete.

### Phase 5: Aggregate and Summarize

13. Collect the one-line summary from each sub-agent.
14. Print a summary table to the user:

```
Creator Audit Summary (2026-W04 to 2026-W08)

| Creator | X Posts | YT Dedicated | YT Integrations | Desc-Only | Streams | Twitch | Total | vs Expected | Status |
|---------|--------|--------------|-----------------|-----------|---------|--------|-------|-------------|--------|
| MookieBarbu | 2 | — | — | — | — | — | 2 | 2/15 (13%) | Below |
| SimplyAlexSR | 0 | 4 | — | — | — | — | 4 | 4/5 (80%) | On Track |
| Royalivi | 8 | 3 | 2 | 1 | — | — | 13 | 13/20 (65%) | Partial |
```

15. Report any errors or warnings from individual sub-agents.

## Script Reference

The Python audit script (`creators-management/scripts/creator-audit.py`) accepts these arguments:
- `--x-handle <handle>` — X/Twitter handle to search
- `--x-keywords <keywords>` — Override X search keywords (default: `MFL OR playmfl OR playMFL`)
- `--youtube-channel <url>` — YouTube channel URL (any tab suffix like `/videos` or `/streams` is auto-stripped; both `/videos` and `/streams` are always scanned)
- `--twitch-channel <url>` — Twitch channel URL
- `--fetch-transcripts` — Fetch auto-generated subtitles to verify integration videos and provide transcript text for dedicated video summaries
- `--transcript-language <lang>` — Language code for auto-subs (default: `en`, use `fr` for French creators)
- `--start-date <YYYY-MM-DD>` — Start of date range (Monday)
- `--end-date <YYYY-MM-DD>` — End of date range (Sunday)

The script outputs a JSON object with:
- `weeks[]` — Array of weekly data, each containing `x_posts[]`, `youtube_videos[]`, `twitch_vods[]`
- YouTube video fields include:
  - `type`: `"dedicated"`, `"integration"`, or `"description-only"`
  - `is_live`: `true` for livestream VODs
  - `transcript`: Raw transcript text (dedicated videos and transcript-verified integrations, when `--fetch-transcripts` used)
  - `transcript_available`: Whether auto-subs were available
  - `transcript_verified`: Whether MFL keywords were found in transcript (integration videos only)
  - `integration_timestamp`: Seconds into the video where MFL is first mentioned (integration videos only, when transcript-verified)

**YouTube scanning**: The script automatically normalizes the channel URL and scans both `/videos` and `/streams` tabs, deduplicating by video ID. Livestream VODs appearing under `/streams` are marked with `is_live: true`. This catches both regular uploads and live content without needing separate configuration.

**Transcript verification**: When `--fetch-transcripts` is used, "integration" videos (MFL in description only) are verified against the transcript. If the transcript doesn't mention MFL, the video is reclassified as `"description-only"` — meaning the creator likely has MFL as an affiliate link in the description but didn't actually discuss MFL in the video. This prevents false positives in the audit counts.

## Error Handling

- If `X_BEARER_TOKEN` is not set, skip X audit and warn the user
- If `yt-dlp` is not installed, skip YouTube/Twitch and warn the user
- If a creator has no Deal/Deliverables or no channels in their Channels table, skip them and warn
- If the API returns no results, record the week as "No MFL content"
- If a sub-agent fails, report the error in the summary table and continue with other creators
- Always attempt to complete as many creators as possible before stopping

## Notes

- X API rate limits: the script sleeps 1s between requests
- yt-dlp handles its own rate limiting
- TikTok is listed in Expected Weekly for some creators but not yet automated (manual check needed)
- The script requires `X_BEARER_TOKEN` environment variable for X/Twitter access
- Transcript fetching adds ~10-30s per video; this is expected
- For French-language creators, pass `--transcript-language fr` — MFL keywords are language-agnostic
