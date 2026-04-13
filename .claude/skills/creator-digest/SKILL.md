---
name: creator-digest
description: >
  Parse the creator dashboard and produce a prioritized daily action summary.
  Categorizes items as OVERDUE, TODAY, THIS WEEK, or STALE. Optionally drafts
  follow-up messages for overdue items. Use when the user runs /creator-digest,
  asks "what do I need to do today", or wants a morning briefing on creator pipeline status.
  Also suitable for cron scheduling.
argument-hint: "[optional: --no-drafts]"
---

# Creator Digest Skill

Parse `creators-management/dashboard.md` and produce a prioritized, scannable action summary. Designed to answer "what do I need to do right now?" in 30 seconds.

## Invocation

- `/creator-digest` — full digest with follow-up drafts for overdue items
- `/creator-digest --no-drafts` — digest only, skip follow-up message drafting
- "What's on my plate today?" / "Morning briefing" / "Creator pipeline status"
- Schedulable via Claude Code cron (daily at 8:00 AM with `--no-drafts`)

## Workflow

### Phase 1: Read Dashboard and References

1. Read these files in parallel:
   - `creators-management/dashboard.md` — source of truth for pipeline
   - `creators-management/messaging-style.md` — needed if drafting follow-ups

2. Determine today's date from the system.

### Phase 2: Parse Dashboard Tables

3. Parse each dashboard section that has a **Due** column: **Active**, **Negotiation**, **Outreach**. Skip **Paused** and **To Contact**.

4. For each row, extract:
   - **Name** (column 1)
   - **Profile** (column 2 — parse the markdown link for handle and URL)
   - **Main Platform** (column 4)
   - **Stage** (which table section the row is in)
   - **Next Action** (the action text column)
   - **Due** (the date string)

5. Skip rows where **both** Due and Next Action are `-`, empty, or missing (nothing to do).

6. Collect rows where **Next Action is populated but Due is missing/empty/`—`/`-`**. These are **Due Date Policy violations** (see `creators-management/CLAUDE.md`). Do NOT skip them — they go into a dedicated `MISSING DUE DATE` section. For each, compute a **Suggested Due** by classifying the action text:
   - Our-side keywords (reply, send, create, schedule, set up, draft, follow up, propose, check in, review, reschedule, bump, share, prepare) → next business day
   - Their-side keywords (await response, await booking, await signature, await invoice, await feedback, await follow-back) → today + 7 days
   - Default → next business day

### Phase 3: Categorize Items

6. Classify each extracted item into exactly one category:

   | Category | Rule | Priority |
   |----------|------|----------|
   | **OVERDUE** | Due date < today | 1 (highest) |
   | **TODAY** | Due date = today | 2 |
   | **THIS WEEK** | Due date is within the next 7 days (today+1 through today+7) | 3 |

7. Tag items as `[STALE]` if: stage is Outreach AND Next Action contains "Await response" AND due date < today. These appear in the OVERDUE section with the tag to signal "this person probably isn't responding."

8. Within each category, sort by:
   - Stage priority: Negotiation > Active > Outreach (higher-value relationships first)
   - Then by due date (earliest first)

### Phase 4: Count Pipeline

9. Count the number of rows in each dashboard table:
   - Active, Negotiation, Outreach, To Contact, Paused

### Phase 5: Generate Digest Output

10. Print the digest directly to the terminal in this exact format:

```
# Creator Digest — [Day of week], [Month DD, YYYY]

## MISSING DUE DATE ([count])

| # | Creator | Stage | Next Action | Suggested Due |
|---|---------|-------|-------------|---------------|
| 1 | Name (@Handle) | Active | Set up dashboard link | 2026-03-13 (our-side) |
| 2 | Name (@Handle) | Negotiation | Await game feedback | 2026-03-19 (their-side) |

## OVERDUE ([count])

| # | Creator | Stage | Next Action | Due | Days Late |
|---|---------|-------|-------------|-----|-----------|
| 1 | Name (@Handle) | Negotiation | Send contract | 2026-03-10 | 2 |
| 2 | Name (@Handle) [STALE] | Outreach | Await response | 2026-03-06 | 6 |

## TODAY ([count])

| # | Creator | Stage | Next Action | Due |
|---|---------|-------|-------------|-----|
| 1 | Name (@Handle) | Negotiation | Reply to proposal | 2026-03-12 |

## THIS WEEK ([count])

| # | Creator | Stage | Next Action | Due |
|---|---------|-------|-------------|-----|
| 1 | Name (@Handle) | Active | Set up dashboard | 2026-03-14 |

## Pipeline Snapshot

| Stage | Count |
|-------|-------|
| Active | [N] |
| Negotiation | [N] |
| Outreach | [N] |
| To Contact | [N] |
| Paused | [N] |

---
[Total] items need attention. [M] are overdue. [P] items have missing due dates.
```

**Formatting rules:**
- If a category has 0 items, print the header with "(0)" and "Nothing here." underneath
- Keep the entire output concise and scannable
- Use the creator's X handle from the Profile column link (e.g., `@McBrideAce`)
- Days Late = today minus due date, in days
- MISSING DUE DATE section: show Suggested Due with classification label (our-side / their-side)
- The bottom summary line is the key takeaway

### Phase 6: Stale Outreach Recommendations

11. If there are any STALE items, append this section after the pipeline snapshot:

```
## Stale Outreach — Decision Needed

| Creator | Original Outreach | Days Since | Recommendation |
|---------|-------------------|------------|----------------|
| Name (@Handle) | 2026-03-01 | 11 | Final follow-up or Pause |
```

Recommendation logic:
- 1-7 days overdue: "Send follow-up"
- 8-14 days: "Final follow-up or Pause"
- 15+ days: "Move to Paused"

### Phase 7: Draft Follow-Up Messages (Optional)

12. **Skip this phase entirely** if `--no-drafts` was passed or if there are 0 OVERDUE items.

13. Draft for ALL OVERDUE items, regardless of the Next Action text. For "Await response" or "Check for reply" items, draft a gentle follow-up / bump message: reference the original outreach briefly, keep it to 1-2 sentences + a CTA. The tone is "just circling back" — not a new pitch.

14. For each message to draft:
    a. Read the creator's profile: `creators-management/creators/<slug>/profile.md`
    b. Read the creator's touchpoints: `creators-management/creators/<slug>/touchpoints.md` (last 2-3 entries for context)
    c. **Determine the creator's language** from the profile header line: `> **Stage** | Vertical | Language | Updated: date`. If Language is `French`, draft in French. For all other languages, draft in English. See the Language-Specific Drafting section below.
    d. Determine the message channel from the Next Action text and profile info
    e. Draft following `messaging-style.md` rules (see Quick Reference below), adapted to the creator's language
    f. **Add a direct link** so Mathurin can click and act immediately:
       - **Email**: Use the `/email search` method to find the thread:
         ```bash
         gws gmail +triage --query "to:<email> OR from:<email>" --max 5 --format json
         ```
         If triage doesn't return thread IDs, fall back to the raw API:
         ```bash
         gws gmail users messages list --params '{"userId": "me", "q": "to:<email> OR from:<email>", "maxResults": 5}' --format json
         ```
         Then get the threadId from the first result and add a `**Thread:**` line with a clickable Gmail link: `https://mail.google.com/mail/u/0/#all/<threadId>`
       - **X DM**: Add an `**X Profile:**` line with the creator's X profile URL (e.g., `https://x.com/Handle`) so Mathurin can click through to DM them
       - **Discord**: Add a `**Discord:**` line with the creator's Discord username from their profile.md info table (e.g., `**Discord:** @username`). If no Discord username is available, note "Open Discord DM directly"

15. Save all drafted messages to `/tmp/msg-daily-followups.md` with this structure:

```markdown
# Follow-Up Drafts — [today's date]

> [N] follow-up messages drafted for overdue items.

---

### 1. [Name] (@Handle) — [Channel: Email/X DM/Discord]

**Thread:** [Subject](https://mail.google.com/mail/u/0/#all/<threadId>)  ← for Email
**X Profile:** https://x.com/Handle  ← for X DM
**Discord:** @username  ← for Discord
**Context:** [1 line from touchpoints — what happened last]
**Action:** [The Next Action from dashboard]
**Overdue by:** [N] days

\```
[Draft message text]
\```

---
```

16. Print a summary to terminal after the digest:

```
## Follow-Up Drafts

[N] messages drafted -> /tmp/msg-daily-followups.md
- [Name]: [channel] — [1-line summary of draft]
- [Name]: [channel] — [1-line summary of draft]

```

## Language-Specific Drafting

The creator's language is in their `profile.md` header: `> **Stage** | Vertical | Language | Updated: date`.

**Mathurin only writes in French or English.** For creators whose profile language is French, draft in French. For all other languages (English, German, Dutch, Portuguese, Spanish, etc.), draft in English. Only draft in another language if the user explicitly asks for it.

| Language in profile | Draft in | Greeting | Sign-off: first outreach | Sign-off: follow-up | CTA phrasing |
|---------------------|----------|----------|--------------------------|---------------------|--------------|
| French | French | "Hello [Name] ! J'espère que tu vas bien." | "Au plaisir d'échanger !" | End with "Dis-moi !" + "Bonne journée !" | "N'hésite pas à réserver directement ici :" |
| Any other | English | "Hey [Name]! Hope you're doing well." | "I'm looking forward to it!" | End with "Let me know!" + "Have a great day!" | "Don't hesitate to find a time here directly:" |

**Sign-off rule:** "I'm looking forward to it!" / "Au plaisir d'échanger !" is for **first outreach and cold recontacts only**. Do NOT use it in follow-up/circle-back messages to someone who hasn't replied. It sounds presumptuous. For follow-ups, close with "Let me know!" + "Have a great day!" (EN) or "Dis-moi !" + "Bonne journée !" (FR).

**French-specific rules:**
- Use "Hello" not "Salut" as the opener.
- Use "tu" (informal) not "vous".
- Use proper French accents (é, è, ê, ë, à, ù, ç, etc.). Never omit accents.
- Email signature stays in English (Mathurin Blouin / CEO, MFL / mathurin@playmfl.com).
- Self-identify: "Je suis Mathurin, CEO de MFL." in cold outreach.
- Social proof: "On travaille déjà avec plusieurs créateurs FM comme WorkTheSpace et Nepenthez."

## Quick Reference: Messaging Style for Drafts

When drafting follow-up messages, apply these rules from `messaging-style.md`:

- No em dashes. Use periods.
- Generous line breaks between paragraphs.
- X DMs: plain text only, no markdown.
- Emails: include signature block (Mathurin Blouin / CEO, MFL / mathurin@playmfl.com).
- Self-identify: "It's Mathurin, CEO at MFL" (if recontacting someone who may not remember).
- CTA: Calendly link https://calendly.com/mathurin-mfl/30min
- "I'm looking forward to it!" for first outreach only. NOT for follow-ups on silent creators. For follow-ups, end with Calendly link or "Let me know!".
- Never imply watching content you haven't watched.
- Lead with concrete social proof in recontacts.
- Keep it short. 3 paragraphs max.

## Error Handling

- **Dashboard parse error** (unexpected format): Stop and warn. Don't guess at column positions.
- **No due dates found**: Report "No items with due dates on the dashboard. Pipeline is either clear or dates need to be added."
- **Creator profile not found** (for draft phase): Skip that creator's draft, warn in output.

## Notes

- This skill is **read-only**. It never modifies the dashboard or any creator files.
- The `/tmp/msg-daily-followups.md` file overwrites any previous file at that path.
- For a deeper dive into a specific creator, use `/creator-update <slug>` after reviewing the digest.
- To send batch outreach to the "To Contact" backlog, use `/creator-outreach`.
