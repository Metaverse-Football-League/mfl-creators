# Platform Identification Guide

Quick reference for identifying messaging platforms from screenshots — used when logging touchpoints via `/creator-update`.

## X DMs (dark mode)
- Blue sent bubbles, dark gray received bubbles
- Verified badge (checkmark) next to display name
- "This conversation is end-to-end encrypted" banner
- Phone + video + `...` icons in top-right header
- No double-check read receipts — just a blue checkmark for "sent"
- Profile picture is circular, top-left corner

## WhatsApp
- Green sent bubbles, white/light gray received bubbles
- Double checkmarks (✓✓) for delivery/read receipts (blue = read, gray = delivered)
- Camera icon in compose bar
- Phone number or contact name in header (no @handle)
- "end-to-end encrypted" banner (similar to X — don't confuse)
- Green phone + video icons in header

## Discord
- Purple/blurple accent color
- Server/channel sidebar visible (unless in DM view)
- User avatars next to each message
- Timestamps inline with messages
- Reactions bar under messages
- Username#discriminator or display name format

## Telegram
- Single/double check marks (✓ = sent, ✓✓ = read)
- Cloud-based — no E2E banner by default (only in Secret Chats)
- Reply-swipe UI
- Blue sent bubbles in default theme (similar to X — check other indicators)
- "last seen" status under contact name

## When Unsure

Ask the user rather than assume. Incorrect platform = incorrect touchpoint type.
