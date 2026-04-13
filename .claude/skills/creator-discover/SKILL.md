---
name: creator-discover
description: >
  Discover new content creators for MFL outreach. Searches for creators by niche/platform/audience size,
  verifies they are active, collects channel metrics, and adds them to the CRM.
  Use when the user runs /creator-discover or asks to find new creators to contact.
argument-hint: "[niche, e.g. 'Football Manager Twitch'] [audience size, e.g. '10-100 viewers'] [count, e.g. '5']"
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*), Bash(yt-dlp:*), Bash(python3:*), Bash(cp:*)
---

# Creator Discovery Skill

Find new content creators matching specific criteria, verify they are active, collect their channel info and metrics, and add them to the CRM pipeline.

## Invocation

- `/creator-discover Football Manager Twitch 10-100 viewers 5` — find 5 FM Twitch streamers with 10-100 avg viewers
- `/creator-discover Sorare YouTube 1K-50K subs 3` — find 3 Sorare YouTubers
- `/creator-discover` — user will be prompted for criteria

## Web Navigation: Use agent-browser

**All web page navigation in this skill MUST use `agent-browser` CLI** (the `agent-browser` skill is installed separately with full docs). Do NOT use WebFetch for pages — it gets blocked by most directory sites. WebSearch is OK for search-engine queries only.

**Pattern:** `agent-browser --session web open <url>` → `agent-browser --session web wait 2000` → `agent-browser --session web snapshot -i` → read output → `agent-browser --session web scroll down 600` → re-snapshot as needed.

> **Session Isolation:** Always use `--session web` for standalone browsing commands. Batch sub-agents use `--session batch{N}`. This prevents conflicts with other skills (e.g., `/discord-read-dm` using `--session discord`).

Key URLs to browse:
- **TwitchMetrics**: `https://www.twitchmetrics.net/channels/viewership?game=Football+Manager+26&lang=fr` (adjust `game=` and `lang=`)
- **SullyGnome**: `https://sullygnome.com/game/Football_Manager_2024/365/watched`
- **TwitchTracker**: `https://twitchtracker.com/[handle]` (per-creator stats)
- **Twitch directory**: `https://www.twitch.tv/directory/category/football-manager-26`
- **Twitch about page**: `https://www.twitch.tv/[handle]/about` (find social links)

## Critical Rules

- **NEVER start with WebSearch for directory data** — use agent-browser on TwitchMetrics/SullyGnome directly
- **NEVER use WebFetch** — it gets blocked by every analytics site (403, 520 errors)
- **NEVER trust TwitchTracker alone for activity** — always cross-check by visiting the actual Twitch channel /videos page
- **WebSearch is ONLY for**: Reddit threads, X handle lookups, community blog posts
- **NEVER mark email as "Not found" without checking ALL discovered channels** (Twitch about page, X bio, YouTube About tab, Instagram bio, etc.) — creators put contact email on different platforms

## Workflow

### Phase 1: Parse Search Criteria

1. Extract from arguments or ask the user:
   - **Niche / Game**: e.g., "Football Manager", "Sorare", "FIFA", "fantasy football"
   - **Primary Platform**: Twitch, YouTube, X, or "any"
   - **Audience Range**: e.g., "10-100 concurrent viewers", "1K-50K subscribers"
   - **Language**: default "English"
   - **Count**: how many creators to find (default: 5)
   - **Ecosystem**: classify as `FM`, `Sorare`, `Fantasy Football`, `Football`, or `Other` — this goes in the dashboard

### Phase 2: Check Existing CRM

2. Read `creators-management/dashboard.md` to build a list of **all known creators** (across all pipeline tables: Active, Negotiation, Outreach, To Contact, etc.)
3. Extract all known X handles, Twitch channels, and YouTube channels from the dashboard
4. Also scan `creators-management/creators/` folder names to catch any creator not yet in the dashboard
5. This list is used later to deduplicate — never suggest a creator already in the CRM

### Phase 3: Search for Candidates

6. **Use agent-browser to browse TwitchMetrics directly.** Do NOT start with WebSearch — go straight to the directory site.

   **TwitchMetrics extraction recipe (tested):**

   ```bash
   # Step 1: Open TwitchMetrics with game + language filter
   agent-browser --session web open "https://www.twitchmetrics.net/channels/viewership?game=Football+Manager+26&lang=fr"
   agent-browser --session web wait --load networkidle

   # Step 2: Dismiss cookie popup (always appears on first visit)
   agent-browser --session web snapshot -i
   # Find and click the "Accept" / "Got it" button in the consent popup
   agent-browser --session web click @eXXX  # the Accept button ref from snapshot

   # Step 3: Extract all channels with viewer hours via JS
   agent-browser --session web eval --stdin <<'EVALEOF'
   var results = [];
   var allLinks = document.querySelectorAll('a');
   var seen = [];
   for(var i=0;i<allLinks.length;i++){
     var href = allLinks[i].href;
     if(href && href.match(/\/c\/\d+-/)){
       var name = allLinks[i].textContent.trim();
       if(name && name.length > 1 && !seen.includes(name)){
         seen.push(name);
         var p = allLinks[i];
         for(var j=0;j<8;j++){if(p.parentElement)p=p.parentElement;}
         var text = p.textContent.replace(/\s+/g,' ').trim();
         var vh = text.match(/([\d,]+)\s*viewer hours/);
         var rank = text.match(/#(\d+)/);
         results.push({
           rank: rank ? parseInt(rank[1]) : null,
           name: name,
           viewerHours: vh ? vh[1] : null,
           twitch: 'https://www.twitch.tv/' + name.toLowerCase()
         });
       }
     }
   }
   JSON.stringify(results);
   EVALEOF

   # Step 4: If page has pagination, click "Next" and repeat extraction
   ```

   - If TwitchMetrics returns empty → try SullyGnome or the Twitch directory as alternatives
   - **Supplement with WebSearch** only for Reddit/community threads, blog posts, or X handle lookups

7. For each candidate found, collect **preliminary info**:
   - Name / handle
   - Twitch URL (from the extraction above)
   - Approximate viewer hours (from directory data)

8. Build a long list of candidates (aim for 2-3x the requested count to account for filtering).

### Phase 4: Verify Each Candidate

For each candidate, verify they are **active and real**. Launch verification in parallel using sub-agents when checking multiple creators.

#### Batch Size Guidance

For large discovery runs (>10 profiles):
- **Max 5-6 candidates per sub-agent** (keeps agent context manageable)
- Use named browser sessions: `--session batch1`, `--session batch2`, etc.
- Each sub-agent handles ALL steps below for its batch of candidates

#### Sub-Agent Verification Template

When launching sub-agents for parallel verification, give each this instruction set:

```
For each channel in your batch, do ALL of these steps using agent-browser:

1. TwitchTracker stats:
   agent-browser --session batch{N} open "https://twitchtracker.com/{handle}"
   agent-browser --session batch{N} wait --load networkidle
   agent-browser --session batch{N} snapshot -i
   → Extract: avg viewers, peak viewers, followers, hours streamed

2. Direct Twitch activity check (MANDATORY — do NOT skip):
   agent-browser --session batch{N} open "https://www.twitch.tv/{handle}/videos"
   agent-browser --session batch{N} wait --load networkidle
   agent-browser --session batch{N} snapshot -i
   → Confirm last VOD exists and is within 30 days
   → If "No Videos Found" or last VOD > 30 days → mark INACTIVE, discard

3. Social links & email from Twitch about page:
   agent-browser --session batch{N} open "https://www.twitch.tv/{handle}/about"
   agent-browser --session batch{N} wait --load networkidle
   agent-browser --session batch{N} snapshot -i
   → Extract: X/Twitter, YouTube, Discord, Instagram, TikTok, email, Linktree from channel panels

4. Linktree shortcut (if found in step 3):
   agent-browser --session batch{N} open "{linktree_url}"
   agent-browser --session batch{N} wait --load networkidle
   agent-browser --session batch{N} snapshot -i
   → Extract ALL social links — this usually gives everything in one page

5. Discover missing platforms (for each NOT yet found):
   a) Try same handle: visit x.com/{handle}, youtube.com/@{handle}, tiktok.com/@{handle}, instagram.com/{handle}
   b) Read the bio/description to CONFIRM it's the same person (same game/niche, cross-links)
   c) If handle doesn't match → search Google: "{handle}" site:x.com, try variations (underscores, TV/Live suffixes)
   d) Cross-check: read X bio for YT/TikTok links, read YouTube About for social links — keep snowballing

6. Fetch metrics for EACH discovered channel:
   - YouTube: use yt-dlp (see YouTube recipe below) → subs + avg views
   - X/Twitter: visit profile with agent-browser → extract follower count from header + email/contact info from bio
   - Instagram: visit profile with agent-browser → extract follower count (if login-walled, record URL only)
   - TikTok: visit profile with agent-browser → extract follower count + total likes
   - If metrics unavailable for any platform → still record the URL

7. Close session when done:
   agent-browser --session batch{N} close
```

#### 4a. TwitchTracker Stats

9. Use agent-browser (NOT WebFetch) to get detailed stats from TwitchTracker:
    ```bash
    agent-browser --session web open "https://twitchtracker.com/[handle]"
    agent-browser --session web wait --load networkidle
    agent-browser --session web snapshot -i
    ```
    Extract avg viewers, peak viewers, followers, hours streamed from the snapshot output.

    **Warning:** TwitchTracker data can be stale or wrong. It is NOT sufficient on its own to confirm a creator is active. You MUST also do step 4a-bis.

#### 4a-bis. Direct Twitch Activity Confirmation (MANDATORY)

10. After collecting TwitchTracker stats, you **MUST** confirm activity by visiting the actual channel:

    ```bash
    agent-browser --session web open "https://www.twitch.tv/[handle]/videos"
    agent-browser --session web wait --load networkidle
    agent-browser --session web snapshot -i
    ```

    Check for:
    - **"No Videos Found"** or **"This channel has no videos"** → INACTIVE, discard immediately
    - Last VOD date visible in the snapshot → must be within 30 days
    - If channel page doesn't load or redirects → channel deleted, discard

    **This step catches false positives from TwitchTracker stale data. Do NOT skip it. It is the ground truth.**

#### 4b. Cross-Platform Channel Discovery & Metrics

This phase finds ALL of a creator's channels across platforms and fetches metrics for each. Handles often differ across platforms — never assume they match.

##### Step 1: Collect initial links from primary platform bio

11. Visit the Twitch about page to collect all social links:
    ```bash
    agent-browser --session web open "https://www.twitch.tv/[handle]/about"
    agent-browser --session web wait --load networkidle
    agent-browser --session web snapshot -i
    ```
    Extract from channel panels and description:
    - **X/Twitter** link and handle
    - **YouTube** channel URL
    - **Discord** server invite
    - **Instagram** profile
    - **TikTok** profile
    - **Email** (business email in description or panels)
    - **Linktree / link aggregator** (linktr.ee, beacons.ai, carrd.co, etc.)

##### Step 2: Linktree shortcut (if found)

12. If any link points to a Linktree or similar aggregator → visit it immediately:
    ```bash
    agent-browser --session web open "https://linktr.ee/[handle]"
    agent-browser --session web wait --load networkidle
    agent-browser --session web snapshot -i
    ```
    Extract ALL links — this typically gives YouTube, X, Instagram, TikTok, Discord, email in one page. Skip the search fallbacks below for any platform already found via Linktree.

##### Step 3: Discover missing platforms

13. For each platform NOT yet found, follow this priority order:

    **a) Try the same handle first:**
    - Visit `x.com/[twitch_handle]`, `youtube.com/@[twitch_handle]`, `tiktok.com/@[twitch_handle]`, `instagram.com/[twitch_handle]`
    - **Always read the bio/description to confirm identity** — the handle may belong to someone else. Check for: same game/niche, mentions streaming, same profile photo, cross-links back to the known platform.

    **b) If handle doesn't match or doesn't exist → search Google:**
    - `"[twitch handle]" site:x.com`
    - `"[creator name]" [game] twitter`
    - `"[creator name]" [game] youtube`
    - Try variations: underscores, "TV"/"Live"/"Gaming" suffixes, abbreviations (e.g., "MckinsFM" → "mckins_fm", "McKinsTV")
    - When a candidate result is found, **visit the profile and read the bio** to confirm it's the same person before recording

    **c) Cross-check discovered profiles for more links:**
    - When you find their **X profile** → read the bio for YouTube/TikTok/Instagram/Linktree links
    - When you find their **YouTube channel** → check the About tab and banner links for social links
    - When you find their **Instagram** → check bio for other links
    - Each new profile may reveal platforms not found elsewhere — keep snowballing until no new channels are discovered

    - If no X found → note as "Not found" (not a disqualifier, but less useful for outreach)
    - If no email found → note as "Not found" (X DM is the fallback contact method)

##### Step 4: Fetch metrics for EACH discovered channel

14. Collect audience metrics for every platform found:

    **Twitch** (already collected in step 4a via TwitchTracker):
    - Followers, avg concurrent viewers, peak viewers

    **YouTube** — use `yt-dlp`:
    ```bash
    yt-dlp --dump-json --playlist-items 1-5 "https://www.youtube.com/@[handle]/videos" 2>/dev/null | python3 -c "
    import sys,json
    views=[]; subs=None; ch=None; dates=[]
    for line in sys.stdin:
        d=json.loads(line)
        ch=d.get('channel','?')
        subs=d.get('channel_follower_count','?')
        views.append(d.get('view_count',0))
        dates.append(d.get('upload_date','?'))
    avg=sum(views)//len(views) if views else 0
    print(f'Channel: {ch}\nSubscribers: {subs}\nAvg views (last {len(views)} vids): {avg}\nViews: {views}\nDates: {dates}')
    "
    ```
    - **Active check**: Last upload within 60 days
    - If no videos or channel doesn't exist → mark YouTube as inactive (may still be valid via Twitch)
    - YouTube handles often differ from Twitch handles — try alternates if first attempt returns <50 subs

    **X/Twitter** — use `agent-browser`:
    ```bash
    agent-browser --session web open "https://x.com/[handle]"
    agent-browser --session web wait --load networkidle
    agent-browser --session web snapshot -i
    ```
    Extract from the profile:
    - **Follower count** from the header
    - **Email** from the bio (look for "contact:", "business:", "📧", or raw email addresses)
    - **Other social links** mentioned in the bio (YouTube, Twitch, Discord links)
    - **Location** if shown

    **Instagram** — use `agent-browser`:
    ```bash
    agent-browser --session web open "https://www.instagram.com/[handle]/"
    agent-browser --session web wait --load networkidle
    agent-browser --session web snapshot -i
    ```
    Extract follower count. If login wall blocks metrics → still record the URL with note "metrics unavailable".

    **TikTok** — use `agent-browser`:
    ```bash
    agent-browser --session web open "https://www.tiktok.com/@[handle]"
    agent-browser --session web wait --load networkidle
    agent-browser --session web snapshot -i
    ```
    Extract follower count and total likes.

    For any platform where metrics can't be fetched (login wall, private account), still record the URL in the profile and note "metrics unavailable".

#### 4c. Disqualification Criteria

**Discard** a candidate if ANY of these apply:
- Channel doesn't exist or is deleted
- No content in the last 30 days (Twitch) or 60 days (YouTube)
- Already exists in the CRM (matched by X handle, Twitch URL, YouTube URL, or name)
- Audience size is outside the requested range (allow ±30% tolerance)
- Content is not primarily in the requested language
- Content is not primarily about the requested niche

### Phase 5: Present Candidates to User

14. Present a summary table of **verified candidates** (up to the requested count) with per-platform metrics:

```
## Discovery Results: [Niche] [Platform] ([Count] found)

| # | Name | Twitch (avg viewers) | YouTube (subs) | X (followers) | Instagram | TikTok | Email | Language |
|---|------|---------------------|----------------|---------------|-----------|--------|-------|----------|
| 1 | Name | [twitch.tv/handle](url) · 45 avg | [@yt](url) · 12K | [@x](url) · 3.2K | [@ig](url) · 1.5K | — | email | FR |
```

Always include clickable links for each platform found. Use "—" for platforms not found, "URL only" if metrics unavailable.

15. For each candidate, also show a brief profile:
    - **Why they fit**: What makes them relevant for MFL outreach
    - **Content style**: What kind of content they produce
    - **Contact method**: Best way to reach them (email > X DM > Twitch chat > Discord)
    - **Risk/flag**: Any concerns (e.g., "also streams non-FM content", "very small audience")

16. Ask the user: **"Which creators should I add to the CRM? (all / numbers / none)"**

### Phase 6: Create CRM Entries

For each approved creator:

17. Create the creator folder by copying template files:
    ```bash
    mkdir -p creators-management/creators/[slug]
    cp creators-management/_template/*.md creators-management/creators/[slug]/
    ```
    - **Slug**: lowercase, hyphenated version of their name (e.g., "MckinsFM" → "mckins-fm")

18. Fill in `creators-management/creators/[slug]/profile.md`:

    ```markdown
    # [Name] (@[XHandle])

    > **To Contact** | [Niche] | [Language] | Updated: [today's date]

    | | |
    |---|---|
    | **Main Platform** | [Primary platform] |
    | **Email** | [email or "Not found"] |
    | **Location** | [location if known, or "Unknown"] |
    | **Discord** | |
    | **MFL Username** | |
    | **MFL Wallet** | |
    | **MFL Profile** | |
    | **Last Audit Week** | — |

    ## Channels

    | Platform | Link | Followers | Avg Views / Engagement |
    |----------|------|-----------|------------------------|
    | YouTube | [url or empty] | [subs] | [avg views/video] |
    | Twitter/X | [url or empty] | [followers if known] | |
    | Twitch | [url or empty] | [followers] | [avg concurrent viewers] |
    | TikTok | | | |
    | Instagram | | | |

    ## Deal

    | | |
    |---|---|
    | **Type** | None yet |
    | **Guarantee** | |
    | **Commission** | |
    | **Contract** | |
    | **Deliverables** | |

    ## Next Actions
    - None

    ## Notes

    ### Background
    [Brief bio from research — content style, other games covered, community involvement]

    ### Discovery
    - Found via: /creator-discover on [today's date]
    - Search criteria: [niche], [platform], [audience range]
    - Contact method: [recommended approach]
    ```

19. Leave `content-audit.md` and `touchpoints.md` as template defaults (no audit data yet).

20. Add the creator to `dashboard.md` in the **To Contact** section.

    Dashboard row format:
    ```
    | [Name] | [@Handle](https://x.com/[Handle]) | [Main Platform] | [Followers] | [Ecosystem] |
    ```

### Phase 7: Summary

21. Print a final summary:

```
## Creator Discovery Complete

Added [N] creators to CRM:
- [Name] → creators/[slug]/ (Twitch: [viewers] avg | YouTube: [subs] subs | X: [followers] | Contact: [method])
- ...

Dashboard updated with [N] new entries in To Contact pipeline.

Next step: Draft outreach messages with /creator-update or manually via messaging-style.md guidelines.
```

## Tools Used

| Tool | Purpose |
|------|---------|
| agent-browser (Bash) | **Primary navigation** — browse TwitchMetrics, SullyGnome, TwitchTracker, Twitch pages, X profiles, Instagram, TikTok, Linktree, creator profiles |
| yt-dlp (Bash) | Fetch YouTube subs, avg views, upload dates; Twitch VOD history |
| WebSearch | Supplementary only — Reddit threads, community directories, X handle lookups |
| Read | Check existing CRM entries (dashboard.md, creator folders) |
| Write | Create new profile.md files |
| Edit | Update dashboard.md with new entries |

## Error Handling

- If `agent-browser` is not installed → run `npm install -g agent-browser`
- If a page loads empty → try `agent-browser --session web wait --load networkidle`, scroll, or `agent-browser --session web reload`
- If `yt-dlp` is not installed → warn user, skip YouTube/Twitch verification (rely on agent-browser data only)
- If a candidate can't be verified → skip and note in results ("Could not verify: [reason]")
- If fewer candidates found than requested → report how many were found and suggest broadening criteria
- If all candidates are already in CRM → report this and suggest different search criteria
- If TwitchMetrics returns empty → try SullyGnome or Twitch directory as alternatives

## Notes

- **Use agent-browser for all page navigation.** Only use WebSearch for search-engine queries. Never use WebFetch — it gets blocked.
- Discovery is best-effort — public data only. Some metrics may be approximate.
- Creators are added as **To Contact** stage — reviewed and ready to contact, but no outreach made yet.
- The skill does NOT draft outreach messages. Use `messaging-style.md` or ask the agent to draft DMs after discovery.
- YouTube handles often differ from X handles — try alternates if first attempt fails (see creator-update skill for known patterns).
- For Twitch creators, TwitchTracker (`twitchtracker.com/[handle]`) is the most reliable source for avg concurrent viewers.
- Always close the browser session when done: `agent-browser --session web close`
