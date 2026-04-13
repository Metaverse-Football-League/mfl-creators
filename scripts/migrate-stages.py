#!/usr/bin/env python3
"""
Pipeline Stages Migration Script

Batch-updates profile.md stages based on the new pipeline stage definitions:
- Prospect, To Contact, Outreach, Negotiation, Active, Paused, Archived
- Removes "Signed" (→ Active) and "Churned" (→ Archived)
- Clears Next Actions for Prospect, To Contact, and Archived profiles
"""

import os
import re
import glob
from pathlib import Path

CREATORS_DIR = Path(__file__).parent.parent / "creators"

# Mapping: creator folder slug → target status
# Built from the restructured dashboard.md
DASHBOARD_MAPPING = {
    # Active
    "nepenthez": "Active",
    "workthespace": "Active",
    "quinny": "Active",
    "andrew-laird": "Active",
    "mrfutlovers": "Active",
    "mookie-barbu": "Active",
    "simply-alex": "Active",
    "royalivi": "Active",
    "le-poulain": "Active",
    "monaco-sorare": "Active",
    "mcbrideace": "Active",

    # Paused
    "br10": "Paused",
    "guia-la-liga": "Paused",
    "jack-p-sorare": "Paused",

    # Negotiation
    "arthur-ray": "Negotiation",
    "trequinho": "Negotiation",
    "qtn": "Negotiation",
    "no-time": "Negotiation",
    "warkik": "Negotiation",
    "vulrak": "Negotiation",
    "flyndle": "Negotiation",
    "lamella-bros": "Negotiation",
    "kempi": "Negotiation",
    "monsieur-quinton": "Negotiation",
    "soraresrfc": "Negotiation",
    "sorare-eredivisie": "Negotiation",

    # Outreach (WorkTheSpace referrals with Outreach status)
    "busthenet": "Outreach",

    # Outreach — FM creators
    "chesnoidgaming": "Outreach",
    "fm-scout": "Outreach",
    "loki-doki": "Outreach",
    "tony-experiencefoot": "Outreach",
    "bassyboy": "Outreach",
    "vik-fm": "Outreach",
    "kiniitooo": "Outreach",

    # Outreach — Sorare creators
    "proownez-sorare": "Outreach",
    "harry-trades": "Outreach",
    "deglingo-mpg": "Outreach",
    "fab-sorare": "Outreach",
    "papin-le-bref": "Outreach",
    "ncf": "Outreach",
    "tommvm": "Outreach",
    "sullyyarb": "Outreach",
    "stefano-raimondi98": "Outreach",
    "wheatthins": "Outreach",
    "bassistentje": "Outreach",
    "together": "Outreach",
    "bushrod": "Outreach",
    "douud": "Outreach",

    # Outreach — WorkTheSpace referrals with Outreach status
    "tomfm": "Outreach",

    # To Contact (WorkTheSpace referrals)
    "lollujo": "To Contact",
    "clayts": "To Contact",

    # To Contact — FM Twitch creators
    "thefmjunkie": "To Contact",
    "thechroo": "To Contact",
    "gb32fm": "To Contact",
    "jayhuahua": "To Contact",
    "anklelee": "To Contact",
    "bracodu88": "To Contact",
    "bobmorane26": "To Contact",
    "kamposyt": "To Contact",
    "faucheurfifa": "To Contact",
    "theofficialfng": "To Contact",
    "ooclanoo": "To Contact",
    "theunitedcityfm": "To Contact",
    "elitegafferr": "To Contact",
    "liquidsnake888": "To Contact",
    "leemo57": "To Contact",
    "frodankbaggies": "To Contact",
    "scheme1": "To Contact",
}


def read_profile(path):
    """Read a profile.md and return its content."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_current_stage(content):
    """Extract the current stage from the header line."""
    match = re.search(r'> \*\*([^*]+)\*\*', content)
    if match:
        return match.group(1).strip()
    return None


def set_stage(content, new_stage):
    """Replace the stage in the header line."""
    return re.sub(
        r'(> \*\*)[^*]+(\*\*)',
        rf'\g<1>{new_stage}\g<2>',
        content,
        count=1
    )


def clear_next_actions(content):
    """Clear the Next Actions section, setting it to '- None'."""
    # Match the ## Next Actions section until the next ## section or end of file
    pattern = r'(## Next Actions\n).*?(?=\n## |\Z)'
    replacement = r'\g<1>- None\n'
    return re.sub(pattern, replacement, content, flags=re.DOTALL)


def add_archived_note(content, reason):
    """Add an archived reason to the Notes section."""
    # Find the Notes section and append the reason
    if "## Notes" in content:
        content = content.rstrip()
        if content.endswith("## Notes"):
            content += f"\n{reason}\n"
        else:
            # Add before the last line if Notes has content
            notes_match = re.search(r'(## Notes\n)(.*)', content, re.DOTALL)
            if notes_match:
                notes_content = notes_match.group(2).strip()
                if notes_content:
                    content = content.rstrip() + f"\n{reason}\n"
                else:
                    content = re.sub(
                        r'(## Notes\n)',
                        rf'\g<1>{reason}\n',
                        content,
                        count=1
                    )
    return content


def main():
    profiles = sorted(glob.glob(str(CREATORS_DIR / "*/profile.md")))
    print(f"Found {len(profiles)} creator profiles\n")

    changes = {
        "Active": [],
        "Paused": [],
        "Negotiation": [],
        "Outreach": [],
        "To Contact": [],
        "Prospect": [],
        "Archived": [],
    }
    unchanged = []
    errors = []
    next_actions_cleared = []

    for profile_path in profiles:
        slug = Path(profile_path).parent.name
        content = read_profile(profile_path)
        current_stage = get_current_stage(content)

        if current_stage is None:
            errors.append(f"  {slug}: Could not parse stage")
            continue

        # Determine target status
        if slug in DASHBOARD_MAPPING:
            target_stage = DASHBOARD_MAPPING[slug]
        elif current_stage == "Signed":
            target_stage = "Active"
        elif current_stage == "Churned":
            target_stage = "Archived"
        elif current_stage in ("Active", "Paused", "Negotiation", "Outreach", "To Contact"):
            # Already a valid stage and on dashboard — keep it
            target_stage = current_stage
        else:
            # Default: anything not in the dashboard mapping becomes Prospect
            target_stage = "Prospect"

        modified = False

        # Update stage if different
        if current_stage != target_stage:
            content = set_stage(content, target_stage)
            modified = True
            print(f"  {slug}: {current_stage} -> {target_stage}")

        # Handle Churned -> Archived: add reason
        if current_stage == "Churned" and target_stage == "Archived":
            content = add_archived_note(content, "Archived: previously churned")
            modified = True

        # Clear Next Actions for Prospect, To Contact, Archived
        if target_stage in ("Prospect", "To Contact", "Archived"):
            original = content
            content = clear_next_actions(content)
            if content != original:
                next_actions_cleared.append(slug)
                modified = True

        # Write back if modified
        if modified:
            with open(profile_path, "w", encoding="utf-8") as f:
                f.write(content)
            changes[target_stage].append(slug)
        else:
            unchanged.append(slug)
            changes.setdefault(target_stage, [])
            if slug not in changes[target_stage]:
                changes[target_stage].append(slug)

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)

    total_changed = sum(len(v) for v in changes.values()) - len(unchanged)
    print(f"\nTotal profiles: {len(profiles)}")
    print(f"Changed: {len(profiles) - len(unchanged)}")
    print(f"Unchanged: {len(unchanged)}")

    print("\nCounts by stage:")
    for stage in ["Active", "Paused", "Negotiation", "Outreach", "To Contact", "Prospect", "Archived"]:
        count = len(changes.get(stage, []))
        print(f"  {stage}: {count}")

    if next_actions_cleared:
        print(f"\nNext Actions cleared: {len(next_actions_cleared)} profiles")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
