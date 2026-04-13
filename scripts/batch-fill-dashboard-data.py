#!/usr/bin/env python3
"""
Fill profile channel metrics from dashboard.md data.
Parses dashboard tables and backfills follower/viewer data into profiles.
Also cleans up profiles: removes empty channel rows, ensures X handle is linked.
"""

import os
import re
from datetime import datetime

CREATORS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'creators')
DASHBOARD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dashboard.md')
TODAY = datetime.now().strftime('%Y-%m-%d')

SKIP_SLUGS = {
    'nepenthez', 'workthespace', 'quinny', 'andrew-laird', 'mrfutlovers',
    'mookie-barbu', 'simply-alex', 'royalivi', 'le-poulain', 'monaco-sorare',
    'mcbrideace', 'arthur-ray', 'br10', 'trequinho', 'qtn', 'no-time',
    'warkik', 'vulrak', 'flyndle', 'lamella-bros', 'kempi', 'monsieur-quinton',
    '_template'
}

stats = {'profiles_updated': 0, 'metrics_filled': 0, 'cleaned': 0}


def parse_dashboard():
    """Parse dashboard.md to extract follower data per creator."""
    with open(DASHBOARD_PATH) as f:
        content = f.read()

    # Map slug -> {followers: str, platform: str}
    creator_data = {}

    # Parse each table row looking for follower data
    for line in content.split('\n'):
        if not line.startswith('|') or '---' in line:
            continue

        cols = [c.strip() for c in line.split('|')]
        if len(cols) < 5:
            continue

        # Try to find creator name and followers
        name_col = cols[1] if len(cols) > 1 else ''
        followers_col = None
        platform_col = None

        # Different table formats
        for i, col in enumerate(cols):
            if re.search(r'~?\d+[KM]|~?\d+,\d+|\d+ avg', col, re.IGNORECASE):
                if 'followers' not in col.lower() and 'Followers' != col:
                    followers_col = col
            if col in ('YouTube', 'Twitter/X', 'Twitch', 'YouTube + Twitch',
                       'YouTube + Telegram', 'Twitch', 'Website/Discord',
                       'YouTube / Podcasts', 'Instagram', 'Streaming',
                       'Twitter/X + Instagram + Patreon'):
                platform_col = col

        if not followers_col or not name_col:
            continue

        # Try to derive slug from name
        # Extract link text or plain name
        link_match = re.search(r'\[([^\]]+)\]', name_col)
        name = link_match.group(1) if link_match else name_col.strip()
        if not name or name == 'Name':
            continue

        # Derive slug
        slug = name.lower().replace(' ', '-').replace('_', '-')
        # Common slug mappings
        slug_map = {
            'bustthenet': 'bustthenet',
            'tomfm': 'tomfm',
            'chesnoidgaming': 'chesnoidgaming',
            'fm-scout': 'fm-scout',
            'loki-doki': 'loki-doki',
            'tony-expériencefoot': 'tony-experiencefoot',
            'bassyboy': 'bassyboy',
            'vik-fm': 'vik-fm',
            'kiniitooo': 'kiniitooo',
            'thefmjunkie': 'thefmjunkie',
            'chroo': 'thechroo',
            'gb32fm': 'gb32fm',
            'jayhuahua': 'jayhuahua',
            'anklelee': 'anklelee',
            'bracodu88': 'bracodu88',
            'bobmorane26': 'bobmorane26',
            'kamposyt': 'kamposyt',
            'faucheurfifa': 'faucheurfifa',
            'theofficialfng': 'theofficialfng',
            'ooclanoo': 'ooclanoo',
            'theunitedcityfm': 'theunitedcityfm',
            'elitegafferr': 'elitegafferr',
            'liquidsnake888': 'liquidsnake888',
            'leemo57': 'leemo57',
            'frodankbaggies': 'frodankbaggies',
            'scheme1': 'scheme1',
            'guia-la-liga': 'guia-la-liga',
            'proownez-sorare': 'proownez-sorare',
            'harry-trades': 'harry-trades',
            'deglingo-mpg': 'deglingo-mpg',
            'jack-p-sorare': 'jack-p-sorare',
            'soraresrfc': 'soraresrfc',
            'fab-sorare': 'fab-sorare',
            'sorare-eredivisie': 'sorare-eredivisie',
            'papin-le-bref': 'papin-le-bref',
            'ncf': 'ncf',
            'tommvm': 'tommvm',
            'sullyyarb': 'sullyyarb',
            'stefano_raimondi98': 'stefano-raimondi98',
            'wheatthins': 'wheatthins',
            'bassistentje': 'bassistentje',
            'together': 'together',
            'bushrod': 'bushrod',
            'douud': 'douud',
            'lamella-bros': 'lamella-bros',
        }
        slug = slug_map.get(slug, slug)

        creator_data[slug] = {
            'followers': followers_col,
            'platform': platform_col,
        }

    return creator_data


def update_twitch_metrics(content, followers_str):
    """Update Twitch row in channels table with follower data."""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '|' in line and 'twitch' in line.lower() and 'Platform' not in line and '---' not in line:
            cols = [c.strip() for c in line.split('|')]
            while len(cols) < 6:
                cols.append('')
            if not cols[3] or cols[3] in ('', 'TBD'):
                cols[3] = followers_str
                lines[i] = '| ' + ' | '.join(cols[1:5]) + ' |'
                return '\n'.join(lines), True
    return content, False


def update_x_metrics(content, followers_str):
    """Update Twitter/X row in channels table with follower data."""
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '|' in line and 'twitter' in line.lower() and 'Platform' not in line and '---' not in line:
            cols = [c.strip() for c in line.split('|')]
            while len(cols) < 6:
                cols.append('')
            if not cols[3] or cols[3] in ('', 'TBD'):
                cols[3] = followers_str
                lines[i] = '| ' + ' | '.join(cols[1:5]) + ' |'
                return '\n'.join(lines), True
    return content, False


def clean_empty_channels(content):
    """Remove empty channel rows (no link, no followers)."""
    lines = content.split('\n')
    result = []
    removed = 0
    platforms = ['youtube', 'twitter', 'twitch', 'tiktok', 'instagram']

    for line in lines:
        if '|' in line and any(p in line.lower() for p in platforms) and 'Platform' not in line and '---' not in line:
            cols = [c.strip() for c in line.split('|')]
            # Check if link and followers are both empty
            link = cols[2] if len(cols) > 2 else ''
            followers = cols[3] if len(cols) > 3 else ''
            if not link and not followers:
                removed += 1
                continue
        result.append(line)

    return '\n'.join(result), removed


def update_date(content):
    return re.sub(r'Updated:\s*\S+', f'Updated: {TODAY}', content, count=1)


def main():
    dashboard_data = parse_dashboard()
    print(f"Parsed {len(dashboard_data)} creators from dashboard")

    for slug in sorted(os.listdir(CREATORS_DIR)):
        if slug in SKIP_SLUGS:
            continue
        profile_path = os.path.join(CREATORS_DIR, slug, 'profile.md')
        if not os.path.isfile(profile_path):
            continue

        with open(profile_path, 'r') as f:
            content = f.read()
        original = content

        # Check if dashboard has data for this creator
        if slug in dashboard_data:
            data = dashboard_data[slug]
            followers = data['followers']
            platform = data.get('platform', '')

            if 'twitch' in platform.lower():
                content, updated = update_twitch_metrics(content, followers)
                if updated:
                    stats['metrics_filled'] += 1
            elif 'twitter' in platform.lower() or 'x' in platform.lower():
                content, updated = update_x_metrics(content, followers)
                if updated:
                    stats['metrics_filled'] += 1

        # Clean empty channel rows
        content, removed = clean_empty_channels(content)
        if removed > 0:
            stats['cleaned'] += 1

        if content != original:
            content = update_date(content)
            with open(profile_path, 'w') as f:
                f.write(content)
            stats['profiles_updated'] += 1

    print(f"\nProfiles updated: {stats['profiles_updated']}")
    print(f"Metrics filled from dashboard: {stats['metrics_filled']}")
    print(f"Profiles cleaned (empty rows removed): {stats['cleaned']}")


if __name__ == '__main__':
    main()
