---
name: email
description: "General-purpose email skill: triage, read, search, send, reply, forward, and draft emails via gws CLI.
Use when the user asks to: (1) create Gmail drafts or send emails, (2) draft outreach/batch emails for creators or contacts, (3) check inbox or search emails, (4) reply to or forward emails, (5) any task involving gws gmail commands.
TRIGGER when: 'create draft', 'draft email', 'send email', 'email outreach', 'Gmail', 'check email', 'inbox', 'reply to email', 'forward email', 'batch emails', 'create drafts for', 'outreach emails'.
DO NOT hand-write gws gmail commands without loading this skill first — the correct syntax is documented here."
user_invocable: true
trigger: "/email"
arguments: "[subcommand] [flags]"
metadata:
  openclaw:
    category: "productivity"
    requires:
      bins: ["gws"]
---

# /email — Gmail Skill

Email management via the `gws` CLI. Routes to the appropriate gws Gmail command.

> **Prerequisites:** `gws` on `$PATH` + authenticated (`gws auth login`).

## Subcommands

| Invocation | Action | Confirmation |
|---|---|---|
| `/email` or `/email triage` | Show unread inbox summary | No |
| `/email read <message-id>` | Display full email content | No |
| `/email thread <thread-id>` | Display full thread | No |
| `/email search <query>` | Search emails by Gmail query | No |
| `/email send --to ... --subject ... --body ...` | Send an email | **Yes** |
| `/email draft --to ... --subject ... --body ...` | Create a draft | No |
| `/email draft-reply <message-id> --body ...` | Create a reply draft (threaded) | No |
| `/email drafts` | List existing drafts | No |
| `/email reply <message-id> --body ...` | Reply to a message | **Yes** |
| `/email reply-all <message-id> --body ...` | Reply-all to a message | **Yes** |
| `/email forward <message-id> --to ...` | Forward a message | **Yes** |

## Execution Flow

### Phase 0: Check Auth

```bash
gws gmail users getProfile
```

If this fails, tell the user to run `gws auth login`.

### Phase 1: Parse Arguments

Determine the subcommand from the skill arguments. Default to `triage` if no subcommand is given.

Supported flags (apply to send/draft/reply/reply-all/forward as relevant):
- `--to <emails>` — recipient(s), comma-separated
- `--cc <emails>` — CC recipient(s)
- `--bcc <emails>` — BCC recipient(s)
- `--subject <text>` — email subject
- `--body <text>` — email body (plain text)
- `--body-file <path>` — read body from a file (e.g., `/tmp/msg-outreach.md`)
- `--html` — treat body as HTML
- `--max <n>` — max results for triage/search (default: 20)
- `--query <gmail-query>` — Gmail search query for triage/search

If `--body-file` is provided, read the file contents and use as `--body`.

### Phase 2: Execute

#### `triage` (default)

```bash
gws gmail +triage [--max <n>] [--query '<query>']
```

Display the table output directly.

#### `read <message-id>`

```bash
gws gmail users messages get --params '{"id": "<message-id>", "format": "full"}'
```

Parse the response and display:
- **From**, **To**, **CC**, **Date**, **Subject** from headers
- Body text (decoded from base64 payload)

#### `thread <thread-id>`

```bash
gws gmail users threads get --params '{"id": "<thread-id>", "format": "full"}'
```

Display all messages in the thread chronologically.

#### `search <query>`

```bash
gws gmail +triage --query '<query>' [--max <n>]
```

Display results as a table.

#### `send`

**Requires confirmation.** Before executing:
1. Display the full message (To, CC, BCC, Subject, Body)
2. Ask: "Send this email? (yes/no)"
3. Only proceed on explicit confirmation

```bash
gws gmail +send --to <emails> --subject '<subject>' --body '<body>' [--cc <cc>] [--bcc <bcc>] [--html]
```

#### `draft` (single)

Create a draft without sending — safe, no confirmation needed.

**Always use Python** for draft creation (handles UTF-8, accents, batch). Never use shell `printf | base64` — it garbles non-ASCII characters.

```python
import base64, json, subprocess

def parse_gws_json(stdout):
    """Parse JSON from gws output, skipping the 'Using keyring backend' line."""
    text = stdout.strip()
    start = text.find('{')
    if start == -1: return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}': depth -= 1
        if depth == 0:
            return json.loads(text[start:i+1])
    return None

def create_draft(to, subject, body, cc=None):
    """Create a single Gmail draft. Returns draft ID or None."""
    if any(ord(c) > 127 for c in subject):
        encoded_subject = "=?UTF-8?B?" + base64.b64encode(subject.encode('utf-8')).decode('ascii') + "?="
    else:
        encoded_subject = subject

    headers = f"To: {to}\nSubject: {encoded_subject}\nContent-Type: text/plain; charset=utf-8"
    if cc:
        headers = f"To: {to}\nCc: {cc}\nSubject: {encoded_subject}\nContent-Type: text/plain; charset=utf-8"

    raw_msg = f"{headers}\n\n{body}"
    raw_b64 = base64.urlsafe_b64encode(raw_msg.encode('utf-8')).decode('utf-8').rstrip('=')

    result = subprocess.run(
        ['gws', 'gmail', 'users', 'drafts', 'create',
         '--params', '{"userId": "me"}',
         '--json', json.dumps({"message": {"raw": raw_b64}})],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        data = parse_gws_json(result.stdout)
        if data:
            return data.get("message", {}).get("id")
    return None
```

After creation, output:
- Draft created successfully
- **Draft ID:** `<id>`
- **Open in Gmail:** `https://mail.google.com/mail/u/0/#drafts?compose=<message.id>`

#### `draft-reply` (single reply draft)

Create a draft that replies to an existing thread. Safe, no confirmation needed.

**Critical:** Reply drafts require the original email's RFC `Message-Id` header in `In-Reply-To` / `References`. The Gmail internal message ID (e.g., `19d4d76f51ea8cc4`) is **NOT** the same thing. Using the wrong ID produces drafts that appear in Gmail but **cannot be sent**.

**Always use Python** for reply draft creation. The function below fetches the correct RFC `Message-Id` automatically.

```python
# Reuse parse_gws_json and imports from create_draft above

def create_reply_draft(to, subject, body, thread_id, original_msg_id, cc=None):
    """Create a Gmail draft as a reply to an existing thread.

    Args:
        to: recipient email
        subject: original subject (Re: prefix added automatically)
        body: reply body text
        thread_id: Gmail thread ID (e.g., '19d4856bb226f18c')
        original_msg_id: Gmail message ID to reply to (e.g., '19d4d76f51ea8cc4')
        cc: optional CC recipients
    Returns: draft message ID or None
    """
    # Step 1: Fetch the RFC Message-Id header from the original message
    r = subprocess.run(
        ['gws', 'gmail', 'users', 'messages', 'get',
         '--params', json.dumps({
             "userId": "me", "id": original_msg_id,
             "format": "metadata", "metadataHeaders": ["Message-Id"]
         }), '--format', 'json'],
        capture_output=True, text=True
    )
    rfc_message_id = ""
    if r.returncode == 0:
        data = parse_gws_json(r.stdout)
        if data:
            for h in data.get("payload", {}).get("headers", []):
                if h["name"] == "Message-Id":
                    rfc_message_id = h["value"]

    if not rfc_message_id:
        print(f"  WARNING: could not fetch Message-Id for {original_msg_id}")
        return None

    # Step 2: Build the reply with correct threading headers
    reply_subject = subject if subject.startswith("Re: ") else f"Re: {subject}"

    if any(ord(c) > 127 for c in reply_subject):
        encoded_subject = "=?UTF-8?B?" + base64.b64encode(
            reply_subject.encode('utf-8')).decode('ascii') + "?="
    else:
        encoded_subject = reply_subject

    header_lines = [
        f"To: {to}",
        f"Subject: {encoded_subject}",
        f"In-Reply-To: {rfc_message_id}",
        f"References: {rfc_message_id}",
        "Content-Type: text/plain; charset=utf-8",
    ]
    if cc:
        header_lines.insert(1, f"Cc: {cc}")

    raw_msg = "\n".join(header_lines) + f"\n\n{body}"
    raw_b64 = base64.urlsafe_b64encode(
        raw_msg.encode('utf-8')).decode('utf-8').rstrip('=')

    # Step 3: Create the draft with threadId in the payload
    result = subprocess.run(
        ['gws', 'gmail', 'users', 'drafts', 'create',
         '--params', '{"userId": "me"}',
         '--json', json.dumps({"message": {"raw": raw_b64, "threadId": thread_id}})],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        data = parse_gws_json(result.stdout)
        if data:
            return data.get("message", {}).get("id")
    return None
```

#### `draft` and `draft-reply` (bulk / batch)

For multiple drafts (e.g., creator outreach), use a **single Python script with a loop**. Never use parallel Bash calls — one failure cancels all siblings.

**New drafts** (no existing thread):

```python
drafts = [
    ("email1@example.com", "Subject 1", "Body 1"),
    ("email2@example.com", "Subject 2", "Body 2"),
]

success, failed = 0, []
for to, subject, body in drafts:
    draft_id = create_draft(to, subject, body)
    if draft_id:
        success += 1
        print(f"  OK: {to}")
    else:
        failed.append(to)
        print(f"  FAIL: {to}")

print(f"\nCreated {success}/{len(drafts)} drafts")
if failed:
    print(f"Failed: {', '.join(failed)}")
```

**Reply drafts** (follow-ups to existing threads):

```python
# Each tuple: (to, original_subject, body, thread_id, original_msg_id)
replies = [
    ("email1@example.com", "MFL x Creator1: Collab opportunity", body_en, "thread_id_1", "msg_id_1"),
    ("email2@example.com", "MFL x Creator2: Opportunité de collab", body_fr, "thread_id_2", "msg_id_2"),
]

success, failed = 0, []
for to, subject, body, thread_id, msg_id in replies:
    draft_id = create_reply_draft(to, subject, body, thread_id, msg_id)
    if draft_id:
        success += 1
        print(f"  OK: {to}")
    else:
        failed.append(to)
        print(f"  FAIL: {to}")

print(f"\nCreated {success}/{len(replies)} reply drafts")
if failed:
    print(f"Failed: {', '.join(failed)}")
```

#### `drafts`

```bash
gws gmail users drafts list --params '{"maxResults": 10}' --format table
```

#### `reply <message-id>`

**Requires confirmation.** Show the original message context + reply body, then ask for confirmation.

```bash
gws gmail +reply --message-id <id> --body '<body>' [--cc <cc>] [--html]
```

#### `reply-all <message-id>`

**Requires confirmation.** Same as reply but uses `+reply-all`.

```bash
gws gmail +reply-all --message-id <id> --body '<body>' [--cc <cc>] [--html]
```

#### `forward <message-id>`

**Requires confirmation.** Show who the message will be forwarded to, then ask.

```bash
gws gmail +forward --message-id <id> --to <emails> [--body '<note>'] [--cc <cc>] [--html]
```

### Phase 3: Output

- For read-only operations: display results directly
- For write operations: confirm success and show any relevant IDs
- For drafts: include the Gmail compose URL

## Compose Assistance

When composing emails without a provided body, read `creators-management/messaging-style.md` for tone and formatting, draft following those guidelines, and present for review before creating.

## Body File Integration

`--body-file` integrates with skills that save messages to `/tmp/msg-*.md`:
- `/creator-outreach` → `/tmp/msg-outreach-<slug>.md`
- `/creator-digest` → `/tmp/msg-followup-<slug>.md`

## Common Pitfalls

- **Wrong**: `gws gmail draft` — this subcommand does not exist
- **Right**: `gws gmail users drafts create --params '{"userId":"me"}' --json '...'`
- **Wrong**: parallel Bash calls for bulk drafts — one failure cascades and cancels all
- **Right**: single Python script with a loop (see bulk draft section above)
- **Wrong**: shell `printf | base64` for non-ASCII — garbles accents
- **Right**: Python `base64.urlsafe_b64encode` with RFC 2047 subject encoding
- **Wrong**: using Gmail message ID (e.g., `19d4d76f51ea8cc4`) in `In-Reply-To` header — drafts appear in Gmail but **cannot be sent**
- **Right**: fetch the RFC `Message-Id` header (e.g., `<CAxxxxxxx@mail.gmail.com>`) from the original message and use that in `In-Reply-To` / `References`. The `create_reply_draft` function does this automatically

## Error Handling

- Auth failure → prompt `gws auth login`
- Missing required flags → show usage for that subcommand
- API errors → display the error message from gws output
