# Dashboard Table Columns

The Negotiation and Active tables have **different column structures**. Getting this wrong creates broken rows.

## Negotiation Table

```
| Name | Profile | Main Platform | Followers | Ecosystem | Next Action | Due |
```

7 columns.

## Active Table

```
| Name | Profile | MFL Profile | Main Platform | Followers | Deal | Next Action | Due |
```

8 columns. Note the two extra columns vs Negotiation: **MFL Profile** and **Deal**.

## Column Values When Moving to Active

| Column | How to fill |
|--------|------------|
| **Name** | Creator display name (from profile.md) |
| **Profile** | `[@Handle](https://x.com/Handle)` |
| **MFL Profile** | `[Profile](https://app.playmfl.com/users/WALLET)` or `—` if unknown |
| **Main Platform** | From profile.md (e.g., Twitch, YouTube, X) |
| **Followers** | Rounded follower count from profile channels (e.g., 15K) |
| **Deal** | Brief summary, e.g. `Affiliate (€200/mo + tiered commission)` |
| **Next Action** | `Kickoff call with Bastien & Lucas` |
| **Due** | Per Due Date Policy in CLAUDE.md: our-side actions (schedule, set up, send) → next business day; their-side actions (await response) → today + 7 days |

## Status Summary

After moving a creator, update the Status Summary counts at the top of dashboard.md:
- Negotiation: -1
- Active: +1
