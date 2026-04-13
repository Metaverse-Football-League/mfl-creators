#!/usr/bin/env python3
"""
Batch update creator profiles with YouTube/Twitch metrics.
Skips Active and Negotiation stage creators.
Uses yt-dlp to fetch live channel data.
"""

import os
import re
import json
import subprocess
import sys
import time
from datetime import datetime

CREATORS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'creators')
YT_DLP = '/opt/homebrew/bin/yt-dlp'
TODAY = datetime.now().strftime('%Y-%m-%d')

# Creators to skip (Active + Negotiation stages)
SKIP_SLUGS = {
    'nepenthez', 'workthespace', 'quinny', 'andrew-laird', 'mrfutlovers',
    'mookie-barbu', 'simply-alex', 'royalivi', 'le-poulain', 'monaco-sorare',
    'mcbrideace', 'arthur-ray', 'br10', 'trequinho', 'qtn', 'no-time',
    'warkik', 'vulrak', 'flyndle', 'lamella-bros', 'kempi', 'monsieur-quinton',
    '_template'
}

# Stats
stats = {
    'total': 0,
    'skipped_stage': 0,
    'yt_fetched': 0,
    'yt_failed': 0,
    'yt_already_has_metrics': 0,
    'no_yt_url': 0,
    'updated': 0,
    'errors': [],
}


def format_followers(count):
    """Format follower count like ~1.96M, ~223K, ~4.99K"""
    if count is None:
        return None
    if count >= 1_000_000:
        return f"~{count/1_000_000:.2f}M"
    elif count >= 1_000:
        return f"~{count/1_000:.1f}K"
    else:
        return f"~{count}"


def format_views(count):
    """Format view count like ~11K, ~1.2K"""
    if count is None or count == 0:
        return None
    if count >= 1_000_000:
        return f"~{count/1_000_000:.1f}M"
    elif count >= 1_000:
        return f"~{count/1_000:.1f}K"
    else:
        return f"~{count}"


def fetch_youtube_metrics(url):
    """Fetch YouTube channel metrics using yt-dlp."""
    # Normalize URL to channel videos page
    # Handle various URL formats
    clean_url = url.strip().rstrip('/')
    if '/videos' not in clean_url:
        clean_url += '/videos'

    try:
        result = subprocess.run(
            [YT_DLP, '--dump-json', '--playlist-items', '1-5', clean_url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None, None, result.stderr[:200]

        views = []
        subs = None
        channel_name = None
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                channel_name = d.get('channel', channel_name)
                s = d.get('channel_follower_count')
                if s and s > 0:
                    subs = s
                v = d.get('view_count', 0)
                if v:
                    views.append(v)
            except json.JSONDecodeError:
                continue

        avg_views = sum(views) // len(views) if views else None
        return subs, avg_views, None
    except subprocess.TimeoutExpired:
        return None, None, 'timeout'
    except Exception as e:
        return None, None, str(e)


def extract_youtube_url(content):
    """Extract YouTube channel URL from profile content."""
    # Look in channels table first
    for line in content.split('\n'):
        if '|' in line and 'youtube' in line.lower():
            cols = [c.strip() for c in line.split('|')]
            for col in cols:
                m = re.search(r'(https?://(?:www\.)?youtube\.com/[@\w/\-\.]+)', col)
                if m:
                    return m.group(1)
    # Look anywhere in the file
    m = re.search(r'(https?://(?:www\.)?youtube\.com/[@\w/\-\.]+)', content)
    if m:
        return m.group(1)
    return None


def extract_twitch_url(content):
    """Extract Twitch channel URL from profile content."""
    m = re.search(r'(https?://(?:www\.)?twitch\.tv/[\w\-]+)', content)
    if m:
        return m.group(1)
    return None


def has_yt_metrics(content):
    """Check if YouTube row in channels table already has metrics."""
    for line in content.split('\n'):
        if '|' in line and 'youtube' in line.lower():
            cols = [c.strip() for c in line.split('|')]
            # cols: ['', 'YouTube', 'link', 'followers', 'avg views', '']
            if len(cols) >= 5:
                followers_col = cols[3] if len(cols) > 3 else ''
                if followers_col and followers_col not in ('', 'Followers'):
                    # Check it's not just a bare number or TBD
                    if followers_col != 'TBD':
                        return True
    return False


def update_youtube_in_profile(content, yt_url, subs_str, views_str):
    """Update the YouTube row in channels table with metrics."""
    lines = content.split('\n')
    updated = False
    for i, line in enumerate(lines):
        if '|' in line and 'youtube' in line.lower() and 'Platform' not in line and '---' not in line:
            cols = [c.strip() for c in line.split('|')]
            # Ensure we have enough columns: | Platform | Link | Followers | Avg Views |
            while len(cols) < 6:
                cols.append('')

            # Update link if missing
            if not cols[2] or cols[2] == '':
                cols[2] = yt_url

            # Update followers
            if subs_str:
                cols[3] = subs_str

            # Update avg views
            if views_str:
                cols[4] = f"{views_str} avg views"

            lines[i] = '| ' + ' | '.join(cols[1:5]) + ' |'
            updated = True
            break

    if not updated:
        # YouTube row doesn't exist, try to add it after the header row
        for i, line in enumerate(lines):
            if '|' in line and 'Platform' in line and 'Link' in line:
                # Found header, skip separator
                insert_at = i + 2
                new_row = f"| YouTube | {yt_url} | {subs_str or ''} | {views_str + ' avg views' if views_str else ''} |"
                lines.insert(insert_at, new_row)
                updated = True
                break

    if updated:
        return '\n'.join(lines)
    return content


def update_date_in_profile(content):
    """Update the Updated: date in the profile header."""
    return re.sub(
        r'Updated:\s*\S+',
        f'Updated: {TODAY}',
        content,
        count=1
    )


def process_creator(slug):
    """Process a single creator profile."""
    profile_path = os.path.join(CREATORS_DIR, slug, 'profile.md')
    if not os.path.isfile(profile_path):
        return False

    with open(profile_path, 'r') as f:
        content = f.read()
    original = content

    # Extract YouTube URL
    yt_url = extract_youtube_url(content)

    if not yt_url:
        stats['no_yt_url'] += 1
        return False

    # Check if metrics already exist
    if has_yt_metrics(content):
        stats['yt_already_has_metrics'] += 1
        return False

    # Fetch metrics
    subs, avg_views, error = fetch_youtube_metrics(yt_url)

    if error:
        stats['yt_failed'] += 1
        stats['errors'].append(f"{slug}: {error[:100]}")
        return False

    if subs is None and avg_views is None:
        stats['yt_failed'] += 1
        stats['errors'].append(f"{slug}: no data returned")
        return False

    stats['yt_fetched'] += 1

    # Format
    subs_str = format_followers(subs)
    views_str = format_views(avg_views)

    # Update profile
    content = update_youtube_in_profile(content, yt_url, subs_str, views_str)
    content = update_date_in_profile(content)

    if content != original:
        with open(profile_path, 'w') as f:
            f.write(content)
        stats['updated'] += 1
        print(f"  [UPDATED] {slug}: {subs_str} subs, {views_str} avg views")
        return True
    return False


def main():
    start_time = time.time()
    slugs = sorted(os.listdir(CREATORS_DIR))

    print(f"Batch Profile Updater — {TODAY}")
    print(f"Found {len(slugs)} creator folders")
    print(f"Skipping {len(SKIP_SLUGS)} Active/Negotiation creators")
    print("=" * 60)

    for slug in slugs:
        if slug in SKIP_SLUGS:
            stats['skipped_stage'] += 1
            continue
        if not os.path.isdir(os.path.join(CREATORS_DIR, slug)):
            continue

        stats['total'] += 1
        process_creator(slug)

        # Small delay to avoid rate limiting
        if stats['yt_fetched'] % 10 == 0 and stats['yt_fetched'] > 0:
            time.sleep(1)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"DONE in {elapsed:.1f}s")
    print(f"Total processed: {stats['total']}")
    print(f"YouTube fetched: {stats['yt_fetched']}")
    print(f"YouTube already had metrics: {stats['yt_already_has_metrics']}")
    print(f"YouTube fetch failed: {stats['yt_failed']}")
    print(f"No YouTube URL: {stats['no_yt_url']}")
    print(f"Profiles updated: {stats['updated']}")

    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for e in stats['errors'][:20]:
            print(f"  - {e}")
        if len(stats['errors']) > 20:
            print(f"  ... and {len(stats['errors']) - 20} more")


if __name__ == '__main__':
    main()
