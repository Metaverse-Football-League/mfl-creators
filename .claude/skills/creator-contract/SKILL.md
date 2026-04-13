---
name: creator-contract
description: >
  Generate an MFL Affiliate Contract PDF for a content creator. Use when the user runs
  /creator-contract or asks to create/generate a contract for a creator. Takes creator info
  from their profile.md and touchpoints.md (deal terms), fills in the contract template,
  and outputs a downloadable PDF. Asks the user for any missing information (legal name,
  address, entity type).
---

# Creator Contract Skill

Generate a PDF Affiliate Contract for an MFL content creator using the standard template.

## Invocation

- `/creator-contract trequinho` — generate contract for a specific creator
- `/creator-contract` — user will specify creator or provide details inline
- "Create a contract for Trequinho" / "Generate affiliate contract for WorkTheSpace"

## Prerequisites

- `fpdf2` Python package must be installed (`pip3 install --break-system-packages fpdf2`)

## Workflow

### Phase 1: Gather Creator Information

1. Identify the creator slug from arguments or context
2. Read these files in parallel:
   - `creators-management/creators/<slug>/profile.md`
   - `creators-management/creators/<slug>/touchpoints.md`

3. Extract contract parameters from the creator's files:

   | Parameter | Where to find it |
   |-----------|-----------------|
   | **Operating alias** | Profile header (creator name) |
   | **Start date** | Deal section or latest touchpoint with deal proposal |
   | **Guarantee** | Deal section or latest touchpoint with deal terms |
   | **Deliverables** | Deal section or latest touchpoint with deal terms |
   | **Duration / Initial term** | Deal section (e.g., "3 months initial term") |
   | **Pack bonus** | Deal section (e.g., "1 monthly pack, rare if 5+ referrals") |

4. The following are NOT in creator files and must come from the user:

   | Parameter | Example |
   |-----------|---------|
   | **Legal name** | "Matty Hood" |
   | **Entity type** | "Sole Trader", "Ltd", etc. |
   | **Legal address** | "39 White Horse Close, Malton, North Yorkshire, YO17 6US, United Kingdom" |

### Phase 2: Confirm or Ask for Missing Info

5. Present what was found and what's missing. Ask the user for any missing required fields.
   - If the user says to use placeholders, use "XXXXX" for missing values
   - Start date, guarantee, and deliverables should always be filled (from profile/touchpoints or user)

### Phase 3: Generate PDF

6. Run the contract template generator:

   ```bash
   python3 .claude/skills/creator-contract/contract-template.py \
       --name "<legal name>" \
       --entity "<entity type>" \
       --address "<full address>" \
       --alias "<operating name>" \
       --start-date "<e.g., March 1st, 2026>" \
       --guarantee "<e.g., 200 EUR/month>" \
       --deliverables "<pipe-separated list>" \
       --output "creators-management/creators/<slug>/Affiliate Contract - <Alias> _ MFL (DRAFT).pdf"
   ```

   Optional flags:
   - `--no-conflict-clause` — removes the competition restriction paragraph from section 3 (Conflict of Interest). Use when the deal explicitly has no exclusivity.
   - `--initial-term "<e.g., three (3) months>"` — sets a fixed initial term with automatic monthly renewal after. If omitted, the contract is indefinite with 1-month notice to terminate (default).
   - `--pack-bonus "<text>"` — adds a pack bonus paragraph to the Minimum Guarantee Commission section. E.g.: `"one (1) monthly MFL pack: a Rare pack if more than five (5) successful referrals are generated in the calendar month, or a Standard pack otherwise"`

   Deliverables format: pipe-separated, e.g.:
   `"2 dedicated MFL video content (monthly)|1 MFL integration in a Football Manager video (weekly)|4 Twitter/X posts about MFL content (weekly)"`

7. Also copy the PDF to Downloads for easy access:
   ```bash
   cp "creators-management/creators/<slug>/Affiliate Contract - <Alias> _ MFL (DRAFT).pdf" \
      "/Users/mathurin/Downloads/"
   ```

### Phase 4: E-Signature Info

8. Generate an e-signature helper file at `/tmp/msg-esign-<slug>.md` with the signer info and email message. The language (FR or EN) is determined from the creator's profile (`> ... | Language` line in the header).

   Format:
   ```markdown
   # E-Signature — {Alias}

   ## Signataire

   | Prénom | Nom | Adresse e-mail |
   |--------|-----|----------------|
   | {First Name} | {Last Name} | {Email} |

   ## Envoyer par e-mail aux signataires

   MFL x {Alias} - Affiliate Contract

   Hi {First Name},

   Following our discussion, please find attached your MFL Affiliate Contract for review and signature.

   If you have any questions, feel free to reach out.

   Best,
   Mathurin
   ```

   French version (use when creator language is French):
   ```
   Hello {First Name},

   Suite à nos échanges, voici le contrat d'affiliation à signer.

   N'hésite pas si tu as la moindre question,

   Bonne journée,
   Mathurin
   ```

   - Use the **FR message** if the creator's language is French, **EN message** otherwise. Only include the relevant language version.
   - The "Envoyer par e-mail aux signataires" section uses plain text (no bold/markdown formatting for titre and message) — the title line comes first, then a blank line, then the message body.
   - Split the legal name into First Name / Last Name (e.g., "BORNAND Michaël" → Prénom: Michaël, Nom: BORNAND)
   - Print the file contents in the terminal so the user can copy-paste directly

### Phase 5: Report

9. Tell the user:
   - Where the PDF was saved (CRM folder + Downloads copy)
   - Where the e-signature file was saved (`/tmp/msg-esign-<slug>.md`)
   - Summary table of all values used (name, entity, address, alias, **email**, start date, guarantee, deliverables). Always include the creator's email (from `profile.md`) in the table so the user can copy it directly when sending the contract.
   - Which values are placeholders (XXXXX) if any — remind user to fill these before sending

## Contract Structure

The template generates an 11-page PDF matching the standard MFL Affiliate Contract format:

- **Page 1**: Cover page (title, prepared for, created by)
- **Pages 2-4**: Main contract body
  - Description of Services (with deliverables)
  - Commission (tiered 5-20% Net Revenue table)
  - Minimum Guarantee Commission (+ optional pack bonus)
  - Duration (indefinite by default, or fixed initial term with monthly auto-renewal)
  - Payment Terms (monthly, net 30)
  - Signature block
- **Pages 5-11**: Attachment A — Terms and Conditions
  - 1. Intellectual Property Rights
  - 2. Confidentiality
  - 3. Conflict of Interest
  - 4. Termination
  - 5. Warranties
  - 6. Limitation of Liability
  - 7. Inspection and Acceptance
  - 8. Insurance
  - 10. Miscellaneous (Assignment, Governing Law, Severability, Independent Contractor, Force Majeure, Entire Contract)
  - Final signature block

## Fixed Contract Terms (not parameterized)

These are identical across all creator contracts:
- **Customer**: Meta Football League, SIRET 92220026600018, 9 rue des Colonnes, 75002 Paris
- **CEO**: Mathurin Blouin
- **Commission tiers**: 0 users = 5%, 1-2 = 10%, 3-5 = 12%, 6-20 = 15%, 21+ = 20%
- **Net Revenue definition**: Primary Market purchases, excluding chargebacks, secondary sales, credits, processing fees, sales tax. Capped at 1 year per user.
- **Duration (default)**: Indefinite, 1 month written notice to terminate. Override with `--initial-term` for a fixed initial period + monthly auto-renewal.
- **Payment**: Monthly, within 30 days of invoice
- **Governing law**: France
- **All Attachment A terms**: IP, Confidentiality, Termination, Warranties, etc.

## Error Handling

- If creator folder doesn't exist → ask user for the creator's info directly
- If no deal terms found in profile/touchpoints → ask user for guarantee, deliverables, start date
- If fpdf2 not installed → install it with `pip3 install --break-system-packages fpdf2`
