---
name: creator-activate
description: >
  Activate a content creator partnership after contract signing. Automates the full post-signature workflow:
  contract parsing, profile update, dashboard move, Discord kickoff message, and payment spreadsheet entry.
  Use when the user runs /creator-activate, says "activate [creator]", "contract is signed", "move [creator]
  to Active", "kick off the partnership with [creator]", "onboard [creator]", or any variant indicating a
  creator has signed and needs to be moved from Negotiation to Active. Also triggers on "set up [creator]
  after signing", "creator signed the contract", or "start the partnership".
---

# Activate Creator Skill

Move a creator from Negotiation to Active after contract signing.

## Invocation

- `/creator-activate trequinho` — activate a specific creator
- `/creator-activate trequinho /path/to/contract.pdf` — with explicit contract path
- `/creator-activate trequinho --notes "He requested affiliate link ASAP"` — with custom notes
- "Activate Trequinho, contract is signed" / "Move Trequinho to Active"

## Prerequisites

- Creator folder must exist at `creators-management/creators/<slug>/`
- Creator should be in **Negotiation** stage (warn if not, but allow override)
- Signed contract PDF should be available (skill will ask for path if not provided)

## Workflow

### Phase 1: Read Existing Files

Read in parallel:
- `creators-management/creators/<slug>/profile.md`
- `creators-management/creators/<slug>/touchpoints.md`
- `creators-management/dashboard.md`
- `creators-management/messaging-style.md`

Also read the contract PDF if a path was provided.

### Phase 2: Extract & Confirm Contract Terms

If a contract PDF was provided, extract: Contract Start, Guarantee, Commission, Deliverables, Exclusivity, Duration, Signed Date, Payment terms.

For commission tiers and standard contract terms, consult `references/commission-tiers.md`.

If no PDF: check profile.md for existing deal terms from negotiation, or ask user for manual input.

**Present a terms summary table to the user and ask for confirmation before writing anything.** This is the checkpoint. No files are modified until the user approves. This matters because contract terms drive everything downstream (profile, dashboard deal column, kickoff message deliverables list).

### Phases 3–5: Update Files, Dashboard & Kickoff Message

**Do these in parallel.** Profile.md, touchpoints.md, dashboard.md, and the kickoff message are all independent files. Edit them all in one turn, not sequentially.

### Phase 3: Update Creator Files

#### 3a. Copy Contract PDF

```bash
cp "/path/to/contract.pdf" "creators-management/creators/<slug>/MFL_x_<Name>_-_Affiliate_Contract.pdf"
```

#### 3a-bis. Upload Contract to Google Drive

Upload the signed contract PDF to the creator's folder in the shared Affiliates Google Drive.

**Parent folder:** `23-AFFILIATES` (shared drive, ID: `1aLBZr6BDsIm5Yx1Y49gbBHarK523YooE`)

1. List subfolders to find the creator's folder:
   ```bash
   gws drive files list --params '{"q": "\"1aLBZr6BDsIm5Yx1Y49gbBHarK523YooE\" in parents and mimeType = \"application/vnd.google-apps.folder\"", "supportsAllDrives": true, "includeItemsFromAllDrives": true, "corpora": "allDrives", "fields": "files(id,name)"}' --format json
   ```

2. If the creator's folder does **not** exist, create it. Folder naming convention: `<slug> - <Real Name>` (e.g., `trequinho - Matthew Hood`, `nepenthez - Craig Douglas`):
   ```bash
   gws drive files create --params '{"supportsAllDrives": true}' \
     --json '{"name": "<slug> - <Real Name>", "mimeType": "application/vnd.google-apps.folder", "parents": ["1aLBZr6BDsIm5Yx1Y49gbBHarK523YooE"]}' --format json
   ```

3. Upload the contract PDF to the creator's folder:
   ```bash
   gws drive files create --params '{"supportsAllDrives": true}' \
     --json '{"name": "MFL x <Name> - Affiliate Contract (<Month Year>).pdf", "parents": ["<CREATOR_FOLDER_ID>"]}' \
     --upload "/path/to/contract.pdf" --format json
   ```

Note: This is a shared drive — always pass `supportsAllDrives: true` in params.

#### 3b. Update `profile.md`

- **Header**: Change stage to `Active`, update date to today
- **Deal section**: Full deal table. Format:

```markdown
## Deal

| | |
|---|---|
| **Type** | Affiliate + Guarantee |
| **Guarantee** | €[amount]/month minimum |
| **Commission** | 5–20% of Net Revenue (tiered: 0 users = 5%, 1–2 = 10%, 3–5 = 12%, 6–20 = 15%, 21+ = 20%) |
| **Deliverables** | [exact quantities and frequencies from contract] |
| **Exclusivity** | [None — no competition clause / Yes — describe] |
| **Contract Start** | [date] |
| **Contract Duration** | Indefinite, 1-month written notice to terminate |
| **Contract Signed** | [YYYY-MM-DD] (both parties) |
| **Contract File** | [MFL_x_<Name>_-_Affiliate_Contract.pdf](MFL_x_<Name>_-_Affiliate_Contract.pdf) |
| **Payment** | Monthly, within 30 days of invoice receipt. Invoice to mathurin@playmfl.com + finance@playmfl.com |
```

Below the table, add a prose paragraph explaining deal context from touchpoints history.

- **Next Actions**: Mark negotiation items as done. Add activation checklist:
  - `[x] Contract signed (done: [signed date])`
  - `[x] Discord group created with Bastien & Lucas (done: [today])`
  - `[x] Kickoff message sent in Discord group (done: [today])`
  - `[ ] Kickoff call with Bastien & Lucas`
  - `[ ] [Creator name] to share content schedule`

#### 3c. Update `touchpoints.md`

Add two entries at the top (most recent first):

1. **Kickoff touchpoint** (today): Discord kickoff message sent, team intros, deliverables recap, Calendly shared
2. **Contract signing touchpoint** (signed date): Contract fully executed, deal terms locked

Each entry needs: date, type, summary paragraph, key points, action items, next step.

### Phase 4: Update Dashboard

Move creator from Negotiation to Active table. **These tables have different column structures.** Read `references/dashboard-columns.md` for the exact schemas. Getting column count wrong breaks the markdown table.

Steps:
1. Remove row from Negotiation table
2. Add row to Active table (8 columns, not 7)
3. Set Due per the **Due Date Policy** in `creators-management/CLAUDE.md`. Typical activation action "Kickoff call with Bastien & Lucas" is our-side → Due = next business day. Never leave Due as `—`.
4. Update Status Summary counts

### Phase 5: Draft Discord Group Kickoff Message

Read the template from `assets/kickoff-message-template.md`. Customize with:
- Creator's name
- Deliverables from the contract
- Any custom --notes

Remind user to: (1) create Discord group with creator + Bastien + Lucas, (2) post the message.

### Phase 6: Add to Payment Spreadsheet

Run `/creator-payments add <slug>` to add the creator to the CC Details sheet. If `gws` fails, flag as manual follow-up rather than blocking activation.

### Phase 7: Summary

Print what changed: files modified, contract location, kickoff message saved path, payment spreadsheet status, deal summary. Remind that changes are NOT committed.

## Gotchas

These are real failure patterns from past activations. Check for them proactively.

- **Dashboard column mismatch**: The Negotiation table has 7 columns, Active has 8. If you copy the row directly, it creates a broken table. Always rebuild the row for the target table's schema. Read `references/dashboard-columns.md` before editing.

- **Deal section formatting**: The deal table uses `| | |` with no header row (just `|---|---|`). If you add a header row or change the separator, it won't match the standard format used by other Active creators. Check Trequinho's profile as reference.

- **Commission tiers are standard**: Don't invent custom tiers from the contract PDF. All contracts use the same 5-tier structure (5/10/12/15/20%). If the PDF shows different numbers, flag it to the user rather than writing wrong tiers.

- **Contract PDF path**: Users often provide relative paths or paths with spaces. Always quote the path in the `cp` command. If the PDF is in Downloads, it might have a name like `MFL x Creator - Affiliate Contract (1).pdf`.

- **Profile.md merge, not overwrite**: The profile already has content from the negotiation phase (channels, background, etc.). The activation adds the Deal section and updates the header/next actions. Never overwrite the whole file. Read it first, then surgically add/update sections.

- **Touchpoints ordering**: New entries go at the TOP of touchpoints.md (most recent first). Putting them at the bottom breaks chronological reading.

- **Creator not in Negotiation**: Some creators skip stages (e.g., direct from Outreach after a quick deal). Warn but don't block. The activation workflow works regardless of prior stage.

- **Missing MFL Profile/Wallet**: Many new creators don't have an MFL account yet at activation time. Use `—` in the dashboard and add "Set up MFL account" to next actions.

- **Status Summary drift**: The counts at the top of dashboard.md can drift if someone edits the tables manually without updating counts. After your edit, recount the actual table rows to verify.

- **Sequential execution is slow**: Phases 3, 4, and 5 edit different files (profile.md, touchpoints.md, dashboard.md, kickoff message). Do them all in one turn using parallel tool calls. Don't wait for one file edit to complete before starting the next.

## Error Handling

- **Folder not found**: Stop. Suggest creating the creator folder first via the template.
- **PDF unreadable**: Fall back to profile.md deal terms or ask user for manual input.
- **Already Active**: Warn, ask if re-run is intended (e.g., to update deal terms or re-draft kickoff).
- **Missing fields in PDF**: Present what was found, ask user to fill gaps.

## Reference Files

- `references/commission-tiers.md` — Standard tiers, Net Revenue definition, deal types
- `references/dashboard-columns.md` — Exact table schemas for Negotiation vs Active
- `assets/kickoff-message-template.md` — Discord kickoff message template with links and rules
- `creators-management/messaging-style.md` — Tone and formatting rules for all creator messages
