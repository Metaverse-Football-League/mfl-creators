---
name: creator-outreach
description: >
  Send first outreach to all "To Contact" creators. Reads profiles, crafts personalized messages
  (email/X DM/Twitch/Discord), creates Gmail drafts for email contacts, sends X DMs via API
  (with batch confirmation), and saves all messages to file.
  Use when the user runs /creator-outreach or asks to contact creators in the "To Contact" pipeline.
argument-hint: "[optional: creator slug, comma-separated slugs, or 'all' (default)] [--no-email-search] [--no-x-send]"
---

# Creator Outreach Skill

Read all "To Contact" creators from the dashboard, craft personalized outreach messages per language and platform, create Gmail drafts for email contacts, check X DM availability and send DMs via API, and save everything to a single output file. Optionally update the CRM to move creators to "Outreach" stage.

## Invocation

- `/creator-outreach` — outreach to ALL "To Contact" creators
- `/creator-outreach clayts, bracodu88` — outreach to specific creators only
- `/creator-outreach --no-email-search` — skip searching for missing emails
- `/creator-outreach --no-x-send` — skip X API sending (text-only mode, save messages to file)
- "Contact all the To Contact creators" / "Send outreach to the To Contact pipeline"

## Prerequisites

- Creator profiles must exist at `creators-management/creators/<slug>/profile.md`
- `gws` CLI installed and authenticated (`gws auth status` — must have `gmail.modify` scope)
- `messaging-style.md` must exist (tone and formatting rules)
- X API credentials in `.env`: `X_BEARER_TOKEN`, `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- X API app must have **Read, Write, and Direct Messages** permissions
- Authenticated X account: @playMFL (user ID: `1461790540249419777`)

## X API OAuth 1.0a Helper

All X API calls that require user context (DMs, follows, friendship checks) use OAuth 1.0a signing. Use this inline Python pattern throughout:

```python
import os, json, hmac, hashlib, base64, time, urllib.parse, uuid, subprocess

def load_env():
    """Load .env from repo root."""
    env = {}
    for path in ['../../.env', '../../../.env', os.path.expanduser('~/MFL/mfl-knowledge-base/.env')]:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env[k.strip()] = v.strip()
            break
    return env

def oauth1_header(method, url, query_params=None):
    """Generate OAuth 1.0a Authorization header. query_params must be included for GET requests with query strings."""
    env = load_env()
    oauth_params = {
        'oauth_consumer_key': env['X_API_KEY'],
        'oauth_nonce': uuid.uuid4().hex,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': env['X_ACCESS_TOKEN'],
        'oauth_version': '1.0',
    }
    all_params = {**oauth_params, **(query_params or {})}
    param_string = '&'.join(f'{urllib.parse.quote(k, safe="")}={urllib.parse.quote(str(v), safe="")}'
                            for k, v in sorted(all_params.items()))
    base_string = f'{method}&{urllib.parse.quote(url, safe="")}&{urllib.parse.quote(param_string, safe="")}'
    signing_key = f'{urllib.parse.quote(env["X_API_SECRET"], safe="")}&{urllib.parse.quote(env["X_ACCESS_TOKEN_SECRET"], safe="")}'
    signature = base64.b64encode(hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()).decode()
    oauth_params['oauth_signature'] = signature
    return 'OAuth ' + ', '.join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(str(v), safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
```

**API endpoints used:**
- User lookup: `GET https://api.twitter.com/2/users/by/username/{handle}` (Bearer token)
- Friendship/DM status: `GET https://api.twitter.com/1.1/friendships/show.json?source_screen_name=playMFL&target_screen_name={handle}` (OAuth 1.0a — include query params in signature)
- DM conversation history: `GET https://api.twitter.com/2/dm_conversations/with/{user_id}/dm_events` (OAuth 1.0a)
- Send DM: `POST https://api.twitter.com/2/dm_conversations/with/{user_id}/messages` (OAuth 1.0a, body: `{"text": "..."}`)
- Follow user: `POST https://api.twitter.com/2/users/1461790540249419777/following` (OAuth 1.0a, body: `{"target_user_id": "..."}`)

## Workflow

### Phase 1: Parse Arguments & Read Pipeline

1. Parse arguments:
   - No args or `all` → process every creator in the "To Contact" dashboard table
   - Comma-separated slugs → process only those creators
   - `--no-email-search` flag → skip Phase 3
   - `--no-x-send` flag → skip X API interactions (DM check, send, follow). Just generate message text.

2. Read these files in parallel:
   - `creators-management/dashboard.md` — extract the "To Contact" table rows
   - `creators-management/messaging-style.md` — tone, formatting, structure rules

3. From the dashboard "To Contact" table, extract for each row:
   - **Name** (column 1)
   - **Profile link / X handle** (column 2 — parse the markdown link)
   - **Main Platform** (column 3)
   - **Followers** (column 4)
   - **Ecosystem** (column 5 — FM, Sorare, etc.)
   - **Next Action** (column 6 — may contain X follow-back tracking status)
   - **Due** (column 7 — check-back date for follow-back tracking)

4. Build the list of creator slugs to process. Derive slug from the name:
   - Lowercase, hyphenated (e.g., "TheOfficialFNG" → look for `theofficialfng/` or `the-official-fng/`)
   - Check if folder exists at `creators-management/creators/<slug>/`
   - If folder not found, try common slug variations

### Phase 2: Read Creator Profiles

5. For each creator, read `creators-management/creators/<slug>/profile.md`. Read profiles in parallel (batch of 5-10 at a time).

6. Extract from each profile:

   | Field | Source | Used For |
   |-------|--------|----------|
   | **Name** | Header `# Name (@Handle)` | Message greeting |
   | **X Handle** | Header or Channels table, X row | X DM link, social proof context |
   | **Email** | Info table, Email row | Contact method selection |
   | **Language** | Header tagline (after vertical) | EN vs FR message template |
   | **Main Platform** | Info table | Contact method fallback |
   | **Channels** | Channels table | Follower counts for context |
   | **Ecosystem** | Dashboard or header tagline | Social proof selection |
   | **Discord** | Info table or Notes | Fallback contact method |
   | **Notes > Background** | Notes section | Personalization hooks (content style, connections) |
   | **Notes > Discovery** | Notes section | How they were found, referral info |
   | **Notes > X Outreach** | Notes section | Prior follow tracking (date, status) |

7. Determine **contact method** per creator (priority order):
   1. **Email** — if email field is populated and not "Not found"
   2. **X DM** — if X handle exists
   3. **Twitch whisper** — if main platform is Twitch and no X handle
   4. **Discord DM** — if Discord link exists and no other method

### Phase 3: Search for Missing Emails (Optional)

> Skip this phase if `--no-email-search` was passed.

8. For each creator where email is missing or "Not found":

   **Method A: Twitch GraphQL API** (most reliable for Twitch streamers)
   ```bash
   curl -s -X POST 'https://gql.twitch.tv/gql' \
     -H 'Client-Id: kimne78kx3ncx6brgo4mv6wki5h1ko' \
     -H 'Content-Type: application/json' \
     -d '[{"query":"{ user(login: \"HANDLE_HERE\") { id displayName description channel { socialMedias { name title url } } } }"}]'
   ```
   Extract email patterns from `description` field and social media URLs.

   **Method B: WebSearch**
   ```
   "[creator name]" "[handle]" email
   ```
   Check first few results for publicly listed business emails.

   **Method C: yt-dlp** (if creator has a YouTube channel)
   ```bash
   yt-dlp --dump-json --playlist-items 1 "https://www.youtube.com/@HANDLE/videos" 2>/dev/null | python3 -c "
   import sys,json
   d=json.loads(sys.stdin.readline())
   desc=d.get('description','')
   ch_desc=d.get('channel_description','')
   print('VIDEO DESC:', desc[:500])
   print('CHANNEL DESC:', ch_desc[:500])
   "
   ```

9. If an email is found, update the creator's `profile.md` info table with the email.

10. Re-evaluate contact method for creators where email was found (upgrade from X DM → Email).

### Phase 4: X DM Status Check

> Skip this phase if `--no-x-send` was passed. All X DM creators get status "ready_to_send" and messages are saved to file only.

For each creator where contact method is **X DM**:

11. **Resolve X user ID:**
    ```
    GET https://api.twitter.com/2/users/by/username/{handle}
    ```
    Extract `data.id`. If user not found, mark as "skipped" (handle may have changed).

12. **Check DM status and friendship:**
    ```
    GET https://api.twitter.com/1.1/friendships/show.json?source_screen_name=playMFL&target_screen_name={handle}
    ```
    Extract:
    - `relationship.source.can_dm` — can we DM them?
    - `relationship.source.following` — does @playMFL follow them?
    - `relationship.source.followed_by` — do they follow @playMFL?

13. **Check for prior follow tracking in profile.md:**
    - Look for `### X Outreach` section in Notes
    - Parse follow date if present (format: `- YYYY-MM-DD: Followed @handle from @playMFL...`)
    - Calculate days elapsed since follow

14. **Branch based on status:**

    | DMs | Following? | Followed by? | Prior follow | Action |
    |-----|-----------|-------------|--------------|--------|
    | Open | any | any | any | → **ready_to_send** |
    | Closed | No | No | None | → **followed_awaiting** (follow + track) |
    | Closed | Yes | No | < 10 days | → **still_waiting** |
    | Closed | Yes | No | >= 10 days | → **manual_action_needed** |
    | Closed | Yes | Yes | any | Re-check can_dm. If open → ready_to_send. If closed → manual_action_needed |

    **For "ready_to_send":**
    - Read DM conversation history: `GET /2/dm_conversations/with/{user_id}/dm_events?max_results=10`
    - If conversation exists: summarize last messages (sender, snippet) — include in output file
    - If no conversation: note "No prior conversation"
    - Proceed to Phase 5 (Craft Messages)

    **For "followed_awaiting":**
    - Follow the user: `POST /2/users/1461790540249419777/following` with body `{"target_user_id": "{uid}"}`
    - Update creator's `profile.md`:
      - In Notes section, add or append to `### X Outreach`:
        ```
        - {today}: Followed @{handle} from @playMFL. DMs closed. Waiting for follow-back.
        ```
      - In Next Actions section, add:
        ```
        - [ ] Check if @{handle} followed back (due: {today + 3 days})
        ```
    - Update **dashboard.md** To Contact row for this creator:
      - Set Next Action to: `Followed @playMFL ({date}). Check follow-back`
      - Set Due to: `{today + 3 days}`
    - Do NOT craft a message. Do NOT move to Outreach. Keep in To Contact.

    **For "still_waiting":**
    - Update **dashboard.md** To Contact row:
      - Set Due to `{today + 3 days}` (push forward)
    - Report: "Waiting for follow-back. {X} days since follow, check again in {10-X} days."

    **For "manual_action_needed":**
    - Update **dashboard.md** To Contact row:
      - Set Next Action to: `No follow-back (10+ days). Find email or manual DM`
      - Clear Due to `-`
    - Report: "No follow-back after {X} days. Manual action needed: find email, DM from personal account, or tweet at them."

    Rate limit: process in batches of 15 with 1s delay between requests. If 429 error, wait for `x-rate-limit-reset`.

### Phase 5: Craft Messages

15. For each creator marked as **"ready_to_send"** (email contacts + X DM with open DMs), generate an outreach message following the templates and rules in `creators-management/messaging-style.md`:

> Skip creators in "followed_awaiting", "still_waiting", or "manual_action_needed" states.

#### Template Source

- **Read `creators-management/messaging-style.md`** for the current message templates, tone rules, and formatting rules
- **Email (EN):** Use the "Cold outreach to FM creator (Email)" example from the Example Messages section. Add a personalization line after the self-introduction.
- **Email (FR):** Translate the EN email template following the FR tone rules in the same file (use "Hello" not "Salut", add social proof descriptors)
- **DMs (EN):** Adapt the email template to DM format: no signature block, no markdown, use "Looking forward to it!" instead of "I'm looking forward to it!", shorter CTA with just the Calendly link
- **DMs (FR):** Same adaptation as EN DMs, following FR tone rules
- **Subject line (EN):** "MFL x [CreatorName]: Collab opportunity, let's chat?"
- **Subject line (FR):** "MFL x [CreatorName]: Opportunite de collab"

#### Personalization Rules

- **Reference mutual connections** if Notes mention them (e.g., "Referred by WorkTheSpace" → "Jack from WorkTheSpace mentioned you")
- **Use first name** if known from profile Notes (e.g., "Hey Kevin!", "Hey Kev!")
- **Add social proof descriptors for FR creators**: WorkTheSpace needs "(l'un des plus gros createurs FM au UK)", Nepenthez needs "(createur FIFA, 2M d'abonnes)"
- **For non-FM ecosystems** (Sorare, FIFA): adjust social proof to reference relevant partners. E.g., for Sorare creators mention "createurs dans l'ecosysteme Sorare et gaming foot"
- **For creators with distinctive content**: add one brief, factual observation (e.g., "I saw you play FM regularly alongside your darts content and thought there could be a cool fit")
- **For re-contacts** (previous outreach that went cold): "I reached out a while back but I think the timing might not have been right"
- **Never pitch content angles** — save that for the call. The message is just to get the call.
- **Never oversell or flatter** — keep compliments simple and factual

#### Message Formatting Rules (from messaging-style.md)

- **No em dashes ( — )** — use periods to separate sentences
- **Generous line breaks** between paragraphs
- **Short sentences**, one idea per sentence
- **Email signature** on all emails (Mathurin Blouin / CEO, MFL / mathurin@playmfl.com)
- **"I'm looking forward to it!"** in emails, **"Looking forward to it!"** in DMs
- **Calendly always included**: https://calendly.com/mathurin-mfl/30min
- **Self-identify**: "I'm Mathurin, CEO at MFL" (first outreach to someone who doesn't know you)

### Phase 6: Create Gmail Drafts & Send X DMs

#### Gmail Drafts

> Uses the same draft-creation method as the `/email draft` skill. See `email/SKILL.md` for full details.

16. For each creator where the contact method is **Email**, create a Gmail draft using the `/email` skill's draft creation method (see `email/SKILL.md`). This handles RFC 2047 encoding for non-ASCII subjects (e.g., FR "Opportunité").

17. Store the returned `id` (draft ID) and `message.id` (message ID) from the response. Build the compose URL:
    - URL pattern: `https://mail.google.com/mail/u/0/#drafts?compose=[message.id]`

#### Send X DMs

> Skip this sub-phase if `--no-x-send` was passed.

18. Write ALL "ready_to_send" X DM messages to the output temp file with conversation history summaries (see Phase 7 for file structure).

19. Print terminal summary:
    ```
    [N] X DMs ready to send. Review messages at /tmp/msg-outreach-to-contact.md
    ```

20. Ask user ONCE: **"Send all [N] X DMs? (yes / no / edit file first)"**
    - **yes** → batch-send all DMs
    - **no** → skip sending, messages remain in file for manual copy-paste
    - **edit** → user edits the file, then re-confirm

21. If confirmed, batch-send all DMs:
    ```python
    # For each ready_to_send creator:
    url = f"https://api.twitter.com/2/dm_conversations/with/{user_id}/messages"
    # OAuth 1.0a signed POST, body: {"text": message}
    ```
    - 1-second delay between sends for rate limiting
    - Record success (dm_event_id) or failure for each
    - Print results: `[X] sent, [Y] failed`

### Phase 7: Generate Output File

22. Save all messages and status to `/tmp/msg-outreach-to-contact.md` with this structure:

```markdown
# Outreach Messages — "To Contact" Batch ([today's date])

> [N] creators processed. [A] X DMs sent, [B] Gmail drafts created, [C] followed (awaiting follow-back), [D] still waiting, [E] manual action needed, [F] skipped.

---

## X DMs Sent ([count])

### 1. [Name] (@[Handle]) — [Followers] — [Language]

- **DM Event ID:** [id]
- **Conversation History:** [summary or "No prior conversation"]

\```
[Full message text]
\```

---

## X DMs Ready (not yet sent) ([count])

> Review and confirm to send. Plain text only.

### [N]. [Name] (@[Handle]) — [Followers] — [Language]

- **DM Status:** Open
- **Conversation History:** [summary or "No prior conversation"]

\```
[Full message text]
\```

---

## Email Outreach ([count] Gmail drafts)

### [N]. [Name] — [Followers] — [Language]

- **Email:** [email]
- **Gmail Draft:** [Open draft](compose URL)

\```
[Full message text]
\```

---

## Followed — Awaiting Follow-back ([count])

| # | Name | X Handle | Followed On | Check Back |
|---|------|----------|-------------|------------|
| 1 | [Name] | @[handle] | [date] | [date + 3 days] |

---

## Still Waiting for Follow-back ([count])

| # | Name | X Handle | Followed On | Days Waiting | Recommendation |
|---|------|----------|-------------|-------------|----------------|
| 1 | [Name] | @[handle] | [date] | [N] | Check again in [10-N] days |

---

## Manual Action Needed ([count])

| # | Name | X Handle | Followed On | Days Waiting | Suggestion |
|---|------|----------|-------------|-------------|------------|
| 1 | [Name] | @[handle] | [date] | [N] | Find email, DM from personal account, or tweet |

---

## Skipped ([count])

[Creators with no X handle, API errors, user not found, no contact method]

---

## Summary

| # | Creator | Followers | Language | Contact Method | Status | Action Taken |
|---|---------|-----------|----------|----------------|--------|--------------|
[rows for all creators]
```

23. Print terminal summary:
```
## Outreach Batch ([today's date])

[A] X DMs sent
[B] Gmail drafts created — review and send from Gmail
[C] Followed on X — awaiting follow-back (check in 3 days)
[D] Still waiting for follow-back
[E] Manual action needed — see /tmp/msg-outreach-to-contact.md
[F] Skipped

File saved: /tmp/msg-outreach-to-contact.md
```

### Phase 8: Update CRM (After User Confirmation)

24. Ask the user: **"Should I update profiles and dashboard to move contacted creators to Outreach?"**

25. If the user confirms:

    **For creators where X DM was SENT or Email draft was created:**

    **a. Update `profile.md`:**
    - Change stage in header tagline from `To Contact` to `Outreach`
    - Update the date to today

    **b. Add touchpoint to `touchpoints.md`:**
    ```markdown
    ### [today's date] - [Email/X DM]
    First outreach sent. Mathurin introduced MFL, mentioned active creator partners (WorkTheSpace, Nepenthez), and proposed a call.
    - Key points: Initial partnership outreach; MFL pitch (football management sim, real opponents, no AI); social proof (active FM creator partners)
    - Action items: Await response
    - Next step: Follow up in 7 days if no response
    ```

    **c. Move on dashboard:**
    - Remove creator's row from the **To Contact** table
    - Add a new row to the **Outreach** table:
      ```
      | [Name] | [@Handle](https://x.com/Handle) | [Main Platform] | [Followers] | [Ecosystem] | Await response to outreach [email/DM] ([date]) | [today + 7 days] |
      ```
    - Update the **Status Summary** counts: To Contact -N, Outreach +N

    **For creators in "followed_awaiting" state:**
    - Do NOT move to Outreach. Keep in To Contact.
    - Profile.md already updated in Phase 4 (Notes + Next Actions).
    - No dashboard change.

    **For creators in "still_waiting" or "manual_action_needed" states:**
    - No CRM changes. Report only.

26. Print a summary of CRM changes:
```
## CRM Updated

[N] creators moved: To Contact → Outreach
- [Name] — X DM sent, profile updated, touchpoint added, dashboard moved
- [Name] — Email draft created, profile updated, touchpoint added, dashboard moved

[M] creators followed (still in To Contact)
- [Name] (@handle) — followed from @playMFL, check back [date]

[P] creators unchanged
- [Name] — still waiting for follow-back ([X] days)
- [Name] — manual action needed (10+ days, no follow-back)

Dashboard counts: To Contact [new count], Outreach [new count]
```

## Error Handling

- **Profile folder not found**: Skip creator, warn in output ("Skipped [Name]: no profile folder found at creators/[slug]/")
- **No contact method available** (no email, no X, no Twitch, no Discord): Skip creator, flag in output
- **gws Gmail auth failed**: Skip draft creation, save email text to file only, warn user to run `gws auth login`
- **Email search fails** (network error, API blocked): Continue without email, fall back to next contact method
- **Dashboard parse error**: Stop and warn — dashboard format may have changed
- **Creator already in Outreach/Negotiation/Active**: Skip — they've already been contacted
- **Empty "To Contact" table**: Report "No creators in To Contact pipeline" and exit
- **X API rate limit (429)**: Pause until `x-rate-limit-reset`, then retry. For large batches, process 15 at a time with 1-minute cooldowns.
- **X API auth failure (401/403)**: Skip X sending, save message text to file only, warn user to check `.env` credentials
- **X user not found (404)**: Skip creator, note "X handle not found — may have changed username"
- **X DM send failure**: Log error, keep message in output file for manual sending, do not mark as sent
- **X follow request failed**: Log error, suggest manual follow
- **X DM conversation read failure**: Proceed without history, note "Could not retrieve DM history"

## Personalization Data Sources

| Source | What to Extract | Used For |
|--------|----------------|----------|
| `profile.md` > Notes > Background | Content style, niche focus | Brief observation in message |
| `profile.md` > Notes > Discovery | Referral source, discovery date | "Jack mentioned you" or "I came across your content" |
| `profile.md` > Notes > X Outreach | Prior follow date, DM status | Follow-back tracking |
| `profile.md` > Channels | Platform presence, follower counts | Context for social proof level |
| `profile.md` > Info table | Email, Discord, location | Contact method, language hints |
| `dashboard.md` > Active table | Current active partners | Social proof references |

## Social Proof Reference

Use these active partners as social proof (adjust per creator's ecosystem and language):

**For FM creators (EN):**
> "We work with several FM creators already including WorkTheSpace and Nepenthez."
> "Jack's been streaming MFL weekly and the community has been really engaged."

**For FM creators (FR):**
> "On travaille deja avec plusieurs createurs FM comme WorkTheSpace (l'un des plus gros createurs FM au UK) et Nepenthez (createur FIFA, 2M d'abonnes)."

**For Sorare creators (FR):**
> "On travaille deja avec plusieurs createurs dans l'ecosysteme Sorare et gaming foot."

**For Sorare creators (EN):**
> "We already work with several creators in the Sorare and football gaming space."

## Notes

- This skill creates Gmail drafts for email contacts and **sends X DMs directly via the X API** (with batch confirmation before sending). Twitch/Discord messages are saved to file for manual sending.
- The output file at `/tmp/msg-outreach-to-contact.md` overwrites any previous file at that path.
- X/Twitter DMs must be plain text — no markdown formatting of any kind.
- French messages use accents where possible but plain ASCII is acceptable (X DMs may strip special characters).
- Calendly link is always `https://calendly.com/mathurin-mfl/30min`.
- Email signature is always: Mathurin Blouin / CEO, MFL / mathurin@playmfl.com
- X API calls use OAuth 1.0a signing (inline Python helper, no external dependencies).
- The @playMFL account ID is hardcoded: `1461790540249419777`.
- When DMs are closed, the skill follows the creator and tracks follow-back status in `profile.md` under `### X Outreach` in Notes.
- Re-invoking the skill for a previously-followed creator checks follow-back status and attempts DM if now available.
- X API rate limits: ~15 requests per 15 minutes for DM and friendship endpoints. The skill paces requests with 1s delays.
- Never display API credentials or tokens in terminal output or temp files.
