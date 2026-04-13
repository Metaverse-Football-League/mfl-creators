---
name: creator-payments
description: Read and manage the creator payment tracking spreadsheet via Google Sheets. Use when the user runs /creator-payments or asks about creator payments, invoices, or the payment spreadsheet.
argument-hint: "[add|update|sync] [creator-name]"
---

# Creator Payments Skill

Manage the MFL creator payment tracking spreadsheet using the `gws` CLI (Google Workspace CLI).

## Prerequisites

- `gws` CLI installed (`brew install googleworkspace-cli`)
- Authenticated: `gws auth login` (one-time OAuth via browser)
- Check auth status: `gws auth status`

If not authenticated, tell the user to run `gws auth login` and stop.

## Configuration

```
SPREADSHEET_ID=1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME
```

The spreadsheet has 4 sheets:

| Sheet | Purpose |
|-------|---------|
| `Payments Follow up` | Monthly payment rows per creator (period, referrals, revenue, commission, amount paid, paid status) |
| `CC Details` | Creator master data (real name, contract type, active status, guarantee fee, currency, payout details) |
| `Total Payable SUM` | Summary/totals (read-only) |
| `Revenues Attributes SUM` | Revenue attribution summary (read-only) |

## Column Schemas

### `CC Details` columns (A-L):
Creator Name | Real Name | Contract Type | Active | Period Start | Period End | MFL Wallet Address | Min. Guarantee Fee | Currency | Min. Guarantee Fee ($) | Preferred Payment Method | Payout Details (IBAN / SWIFT / Wallet)

### `Payments Follow up` columns (A-P):
Creator Name | Period | Start Date | Contract Type | Min. Guarantee Fee | Currency on contract | # Referrals | Revenue Attributed ($) | Column 15 | Com. Rate (%) | Month Avg Exchange Rate to USD | Total Payable (in $) | Amount to be paid | Payment Currency | Paid? (Yes/No) | Column 1

## Commands

### `/creator-payments` — Read & display

1. Check auth: `gws auth status` — verify `auth_method` is not `"none"`
2. Read CC Details for creator overview:
   ```bash
   gws sheets +read --spreadsheet "1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME" --range "'CC Details'" --format table
   ```
3. Read Payments Follow up for payment history:
   ```bash
   gws sheets +read --spreadsheet "1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME" --range "'Payments Follow up'" --format json
   ```
4. Display a formatted summary to the user. For payment history, filter to the most recent months or a specific creator if requested.
5. Highlight any rows with missing data, unpaid entries, or anomalies.

### `/creator-payments add <creator>` — Add a creator to CC Details

1. Read the creator's `profile.md` from `creators-management/creators/<slug>/profile.md`
2. Extract: name, contract type, guarantee amount, currency, contract dates, MFL wallet, payment method
3. Show the user what will be appended and **ask for confirmation**
4. Append to CC Details:
   ```bash
   gws sheets +append --spreadsheet "1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME" \
     --json-values '[["Creator Name","Real Name","Affiliate","Active","2026-03-01","Indefinitely","","200.00","EUR","","EUR",""]]'
   ```
   Note: Use `--json-values` (not `--values`) to avoid issues with commas in values.

   **Important:** The `+append` helper does NOT support targeting a specific sheet — it always appends to the first sheet (Payments Follow up). To append to CC Details, use `spreadsheets values append` with the table range so Sheets extends the table automatically:
   ```bash
   gws sheets spreadsheets values append \
     --params '{"spreadsheetId": "1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME", "range": "CC Details\u0021A1:L1", "valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}' \
     --json '{"values": [["col1","col2",...]]}'
   ```
   Notes:
   - Use `\u0021` instead of `!` in `--params` JSON to avoid gws parser escape errors
   - Use `insertDataOption: INSERT_ROWS` to extend the table boundary (not just write below it)
   - Target the table header range (e.g. `A1:L1`) — Sheets will auto-detect the table and append at the end

### `/creator-payments update <creator>` — Update an existing row

1. Read CC Details to find the creator's row:
   ```bash
   gws sheets +read --spreadsheet "1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME" --range "'CC Details'" --format json
   ```
2. Parse JSON — find the row index where Creator Name matches (case-insensitive)
3. Row number in Sheets = array index + 1 (row 1 = header, row 2 = first data row)
4. Show current values vs proposed changes, **ask for confirmation**
5. Update:
   ```bash
   gws sheets spreadsheets values update \
     --params '{"spreadsheetId": "1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME", "range": "'\''CC Details'\''!A<ROW>:L<ROW>", "valueInputOption": "USER_ENTERED"}' \
     --json '{"values": [["col1","col2",...]]}'
   ```

### `/creator-payments sync` — Cross-reference dashboard vs sheet

1. Read CC Details (active creators on the sheet)
2. Read `creators-management/dashboard.md` → extract all Active creators
3. Compare (CC Details vs Dashboard only — do NOT read the Payments Follow up sheet):
   - **Dashboard Active but missing from CC Details** → flag for addition
   - **CC Details "Active" but not on dashboard** → flag for review (may be stale)
   - **Deal mismatches** between profile.md and CC Details (guarantee amount, currency, contract type) → flag
4. Present a summary report
5. Offer to fix mismatches (with confirmation before each write)

## Reading Spreadsheet Data

For programmatic parsing, always use `--format json`:
```bash
gws sheets +read --spreadsheet "1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME" --range "'CC Details'" --format json
```

For user-facing display, use `--format table`:
```bash
gws sheets +read --spreadsheet "1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME" --range "'CC Details'" --format table
```

To read a specific range (e.g., recent payments only):
```bash
gws sheets +read --spreadsheet "1j7_oxftBD-lRMhyLdREnfbXwFuWw5fTJPTnGtsRsEME" --range "'Payments Follow up'!A1:P5" --format table
```

## Name Mapping

Creator names may differ between the dashboard and the spreadsheet. Known mappings:

| Dashboard Name | Sheet Name |
|---------------|------------|
| Andrew Laird | Laird |
| MrFutlovers | Jakob - MrFutLover |
| SimplyAlex | SimplyAlex / Alex Lennox |
| ROYALIVI | Royalivi |

When matching creators, normalize names (case-insensitive, check both columns).

## Safety Rules

- **Always confirm with the user before writing** (append or update)
- **Never delete rows** — only append or update
- **Log all writes** — after any write operation, re-read the affected range and display it to confirm
- **SUM sheets are read-only** — never write to "Total Payable SUM" or "Revenues Attributes SUM"
