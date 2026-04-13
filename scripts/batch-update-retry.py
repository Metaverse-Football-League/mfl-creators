#!/usr/bin/env python3
"""
Retry failed YouTube fetches with longer timeout + fix missing URLs.
"""

import os
import re
import json
import subprocess
import time
from datetime import datetime

CREATORS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'creators')
YT_DLP = '/opt/homebrew/bin/yt-dlp'
TODAY = datetime.now().strftime('%Y-%m-%d')
TIMEOUT = 60  # Longer timeout

# Profiles that timed out in the first run
RETRY_SLUGS = [
    'chris-wood', 'darkhorsefm', 'dmac', 'elitegafferr', 'fut-fatish',
    'geografifa', 'hmfootball-station', 'hood-gaming', 'jake-cooper', 'jeje',
    'jirotf16', 'jowick', 'kamposyt', 'kimpembro', 'leemo57',
    'liquidsnake888', 'lucks-games-fc', 'lucullus-games', 'magosunited',
    'mamun-prefer-gaming-top-eleven', 'mattfuttrading', 'meidallinho',
    'mike-wagner', 'money-ball-en-fm24', 'ncf', 'ooclanoo', 'ozilla',
    'passion-for-fm', 'pepitesorare', 'play2earn', 'poirito',
    'regen-hunter', 'regenhunters', 'scheme1', 'second-yellowcard',
    'sfethiyespor', 'the-king-pekka-yt', 'theofficialfng', 'top-eleven-elites',
    'whycallum'
]

# Missing YouTube URLs — try to discover
DISCOVER_YT = {
    'clayts': ['@claytsfm', '@ClaytsGaming', '@Clayts'],
    'lollujo': ['@lollujo', '@LollujoFM'],
    'tomfm': ['@TomFM_YT', '@TomFM', '@TomFMYT'],
}

stats = {'updated': 0, 'failed': 0, 'discovered': 0}


def format_followers(count):
    if count is None: return None
    if count >= 1_000_000: return f"~{count/1_000_000:.2f}M"
    elif count >= 1_000: return f"~{count/1_000:.1f}K"
    else: return f"~{count}"


def format_views(count):
    if count is None or count == 0: return None
    if count >= 1_000_000: return f"~{count/1_000_000:.1f}M"
    elif count >= 1_000: return f"~{count/1_000:.1f}K"
    else: return f"~{count}"


def fetch_youtube_metrics(url, timeout=TIMEOUT):
    clean_url = url.strip().rstrip('/')
    if '/videos' not in clean_url:
        clean_url += '/videos'
    try:
        result = subprocess.run(
            [YT_DLP, '--dump-json', '--playlist-items', '1-5', clean_url],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return None, None, result.stderr[:200]
        views = []
        subs = None
        for line in result.stdout.strip().split('\n'):
            if not line.strip(): continue
            try:
                d = json.loads(line)
                s = d.get('channel_follower_count')
                if s and s > 0: subs = s
                v = d.get('view_count', 0)
                if v: views.append(v)
            except json.JSONDecodeError:
                continue
        avg_views = sum(views) // len(views) if views else None
        return subs, avg_views, None
    except subprocess.TimeoutExpired:
        return None, None, 'timeout'
    except Exception as e:
        return None, None, str(e)


def extract_youtube_url(content):
    for line in content.split('\n'):
        if '|' in line and 'youtube' in line.lower():
            cols = [c.strip() for c in line.split('|')]
            for col in cols:
                m = re.search(r'(https?://(?:www\.)?youtube\.com/[@\w/\-\.]+)', col)
                if m: return m.group(1)
    m = re.search(r'(https?://(?:www\.)?youtube\.com/[@\w/\-\.]+)', content)
    if m: return m.group(1)
    return None


def update_youtube_in_profile(content, yt_url, subs_str, views_str):
    lines = content.split('\n')
    updated = False
    for i, line in enumerate(lines):
        if '|' in line and 'youtube' in line.lower() and 'Platform' not in line and '---' not in line:
            cols = [c.strip() for c in line.split('|')]
            while len(cols) < 6: cols.append('')
            if not cols[2] or cols[2] == '': cols[2] = yt_url
            if subs_str: cols[3] = subs_str
            if views_str: cols[4] = f"{views_str} avg views"
            lines[i] = '| ' + ' | '.join(cols[1:5]) + ' |'
            updated = True
            break
    if not updated:
        for i, line in enumerate(lines):
            if '|' in line and 'Platform' in line and 'Link' in line:
                insert_at = i + 2
                new_row = f"| YouTube | {yt_url} | {subs_str or ''} | {views_str + ' avg views' if views_str else ''} |"
                lines.insert(insert_at, new_row)
                updated = True
                break
    if updated: return '\n'.join(lines)
    return content


def update_date_in_profile(content):
    return re.sub(r'Updated:\s*\S+', f'Updated: {TODAY}', content, count=1)


def process_retry(slug):
    profile_path = os.path.join(CREATORS_DIR, slug, 'profile.md')
    if not os.path.isfile(profile_path):
        print(f"  [{slug}] profile not found")
        return

    with open(profile_path, 'r') as f:
        content = f.read()
    original = content

    yt_url = extract_youtube_url(content)
    if not yt_url:
        print(f"  [{slug}] no YouTube URL")
        stats['failed'] += 1
        return

    subs, avg_views, error = fetch_youtube_metrics(yt_url)
    if error:
        print(f"  [{slug}] FAILED: {error[:80]}")
        stats['failed'] += 1
        return

    if subs is None and avg_views is None:
        print(f"  [{slug}] no data returned")
        stats['failed'] += 1
        return

    subs_str = format_followers(subs)
    views_str = format_views(avg_views)
    content = update_youtube_in_profile(content, yt_url, subs_str, views_str)
    content = update_date_in_profile(content)

    if content != original:
        with open(profile_path, 'w') as f:
            f.write(content)
        stats['updated'] += 1
        print(f"  [UPDATED] {slug}: {subs_str} subs, {views_str} avg views")


def discover_youtube(slug, handles):
    """Try multiple YouTube handles to find the channel."""
    profile_path = os.path.join(CREATORS_DIR, slug, 'profile.md')
    if not os.path.isfile(profile_path):
        return

    for handle in handles:
        url = f"https://www.youtube.com/{handle}"
        subs, avg_views, error = fetch_youtube_metrics(url)
        if subs and subs > 50:  # Found a real channel
            with open(profile_path, 'r') as f:
                content = f.read()
            subs_str = format_followers(subs)
            views_str = format_views(avg_views)
            content = update_youtube_in_profile(content, url, subs_str, views_str)
            content = update_date_in_profile(content)
            with open(profile_path, 'w') as f:
                f.write(content)
            stats['discovered'] += 1
            print(f"  [DISCOVERED] {slug}: {handle} -> {subs_str} subs, {views_str} avg views")
            return
        time.sleep(0.5)
    print(f"  [{slug}] no valid YouTube channel found")
    stats['failed'] += 1


def main():
    start = time.time()
    print(f"Retry + Discover — {TODAY}")
    print(f"Retrying {len(RETRY_SLUGS)} timeouts (60s timeout)")
    print(f"Discovering YouTube for {len(DISCOVER_YT)} creators")
    print("=" * 60)

    print("\n--- Retrying timeouts ---")
    for slug in RETRY_SLUGS:
        process_retry(slug)
        time.sleep(0.3)

    print("\n--- Discovering YouTube channels ---")
    for slug, handles in DISCOVER_YT.items():
        discover_youtube(slug, handles)
        time.sleep(0.3)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"DONE in {elapsed:.1f}s")
    print(f"Updated: {stats['updated']}")
    print(f"Discovered: {stats['discovered']}")
    print(f"Failed: {stats['failed']}")


if __name__ == '__main__':
    main()
