#!/usr/bin/env python3
"""
audit-creator.py — Audit content creator deliverables across X, YouTube, and Twitch.

Fetches MFL-related content from configured channels for a date range,
outputs structured JSON for the skill to process into markdown.

Usage:
    python3 scripts/audit-creator.py \
        --x-handle MookieBarbu \
        --start-date 2026-01-20 \
        --end-date 2026-02-02

    python3 scripts/audit-creator.py \
        --youtube-channel "https://www.youtube.com/@SimplyAlexGaming/videos" \
        --start-date 2026-01-20 \
        --end-date 2026-02-02 \
        --fetch-transcripts

Requires:
    - X_BEARER_TOKEN env var (or in .env file) for X/Twitter
    - yt-dlp for YouTube/Twitch
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


def load_dotenv():
    """Load variables from .env file in the repo root if it exists."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key not in os.environ:
                os.environ[key] = value


load_dotenv()

# Default MFL keywords — same across all creators
DEFAULT_X_KEYWORDS = "MFL OR playmfl OR playMFL"
DEFAULT_YT_KEYWORDS = ["mfl", "playmfl", "metaverse football league", "playmfl.com"]


def monday_of(d):
    """Return the Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())


def sunday_of(d):
    """Return the Sunday of the week containing date d."""
    return d + timedelta(days=6 - d.weekday())


def week_ranges(start_date, end_date):
    """Generate (week_label, mon, sun, is_complete) tuples for each week in range."""
    today = datetime.now().date()
    current_monday = monday_of(start_date)
    while current_monday <= end_date:
        sun = current_monday + timedelta(days=6)
        iso = current_monday.isocalendar()
        week_label = f"{iso[0]}-W{iso[1]:02d}"
        # A week is complete if its Sunday is in the past
        is_complete = sun < today
        yield week_label, current_monday, sun, is_complete
        current_monday += timedelta(days=7)


def fetch_x_tweets(handle, keywords, start_date, end_date):
    """Fetch tweets from X API v2 full-archive search for a date range."""
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        return {"error": "X_BEARER_TOKEN not set", "tweets": []}

    query = f"from:{handle} ({keywords})"
    api_base = "https://api.x.com/2"
    all_tweets = []
    pagination_token = None

    # Cap end_time at 10 seconds ago if the end date is today or in the future
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    today = datetime.utcnow().date()
    if end_dt >= today:
        # Use current UTC time minus 30 seconds to satisfy X API constraint
        now_utc = datetime.utcnow() - timedelta(seconds=30)
        end_time_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        end_time_str = f"{end_date}T23:59:59Z"

    while True:
        params = {
            "query": query,
            "max_results": "100",
            "tweet.fields": "created_at,public_metrics,entities,in_reply_to_user_id,referenced_tweets",
            "sort_order": "recency",
            "start_time": f"{start_date}T00:00:00Z",
            "end_time": end_time_str,
        }
        if pagination_token:
            params["next_token"] = pagination_token

        url = f"{api_base}/tweets/search/all?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 429:
                print("X API rate limited, waiting 60s...", file=sys.stderr)
                time.sleep(60)
                continue
            return {"error": f"X API error {e.code}: {body}", "tweets": []}

        tweets = data.get("data", [])
        all_tweets.extend(tweets)

        next_token = data.get("meta", {}).get("next_token")
        if not next_token:
            break
        pagination_token = next_token
        time.sleep(1)  # Rate limiting courtesy

    return {"tweets": all_tweets}


def classify_tweet(tweet):
    """Classify a tweet as Post, Reply, or RT."""
    refs = tweet.get("referenced_tweets", [])
    if refs:
        ref_types = {r["type"] for r in refs}
        if "retweeted" in ref_types:
            return "RT"
        if "replied_to" in ref_types:
            return "Reply"
    if tweet.get("in_reply_to_user_id"):
        return "Reply"
    if tweet.get("text", "").startswith("RT @"):
        return "RT"
    return "Post"


def find_yt_dlp():
    """Find the yt-dlp binary."""
    if os.path.exists("/opt/homebrew/bin/yt-dlp"):
        return "/opt/homebrew/bin/yt-dlp"
    return "yt-dlp"


def has_mfl_keywords(text):
    """Check if text contains any MFL keyword."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in DEFAULT_YT_KEYWORDS)


def normalize_channel_base_url(channel_url):
    """Extract base channel URL, stripping /videos, /streams, /shorts, etc."""
    url = channel_url.rstrip("/")
    for suffix in ["/videos", "/streams", "/featured", "/shorts", "/playlists", "/community"]:
        if url.endswith(suffix):
            url = url[: -len(suffix)]
            break
    return url


def _fetch_yt_tab(yt_dlp, tab_url, date_start, date_end):
    """Fetch videos from a single YouTube tab. Returns (entries, error)."""
    try:
        result = subprocess.run(
            [
                yt_dlp,
                "--dump-json",
                "--skip-download",
                "--dateafter",
                date_start,
                "--datebefore",
                date_end,
                "--no-warnings",
                tab_url,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError:
        return [], "yt-dlp not found"
    except subprocess.TimeoutExpired:
        return [], "yt-dlp timed out"

    if result.returncode != 0 and not result.stdout:
        return [], f"yt-dlp error: {result.stderr[:200]}"

    entries = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries, None


def fetch_transcript(video_id, language="en"):
    """Fetch auto-generated subtitles for a video. Returns plain text or None."""
    yt_dlp = find_yt_dlp()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, "%(id)s")
        try:
            subprocess.run(
                [
                    yt_dlp,
                    "--skip-download",
                    "--write-auto-subs",
                    "--sub-langs",
                    language,
                    "--sub-format",
                    "json3",
                    "-o",
                    output_template,
                    "--no-warnings",
                    f"https://www.youtube.com/watch?v={video_id}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        sub_file = os.path.join(tmpdir, f"{video_id}.{language}.json3")
        if not os.path.exists(sub_file):
            return None

        try:
            with open(sub_file) as f:
                data = json.load(f)
            texts = []
            for event in data.get("events", []):
                for seg in event.get("segs", []):
                    t = seg.get("utf8", "").strip()
                    if t and t != "\n":
                        texts.append(t)
            return " ".join(texts)
        except (json.JSONDecodeError, IOError):
            return None


def find_first_mfl_timestamp(video_id, language="en"):
    """Find the timestamp of the first MFL keyword mention in a video's subtitles.

    Downloads json3 subtitles and iterates over events, checking each segment
    for MFL keywords. Returns (found, timestamp_seconds):
    - (True, N) — MFL keyword found at N seconds
    - (False, None) — subtitles available but no MFL keywords
    - (None, None) — subtitles not available
    """
    yt_dlp = find_yt_dlp()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, "%(id)s")
        try:
            subprocess.run(
                [
                    yt_dlp,
                    "--skip-download",
                    "--write-auto-subs",
                    "--sub-langs",
                    language,
                    "--sub-format",
                    "json3",
                    "-o",
                    output_template,
                    "--no-warnings",
                    f"https://www.youtube.com/watch?v={video_id}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None, None

        sub_file = os.path.join(tmpdir, f"{video_id}.{language}.json3")
        if not os.path.exists(sub_file):
            return None, None

        try:
            with open(sub_file) as f:
                data = json.load(f)
            for event in data.get("events", []):
                for seg in event.get("segs", []):
                    t = seg.get("utf8", "").strip()
                    if t and t != "\n" and has_mfl_keywords(t):
                        # tStartMs is the event start time in milliseconds
                        ts_ms = event.get("tStartMs", 0)
                        return True, ts_ms // 1000
            return False, None
        except (json.JSONDecodeError, IOError):
            return None, None


def fetch_youtube_videos(channel_url, start_date, end_date, fetch_transcripts=False, transcript_language="en"):
    """Fetch YouTube videos from a channel using yt-dlp.

    Scans both /videos and /streams tabs, deduplicating by video ID.
    Classifies each video as:
    - "dedicated": MFL keyword found in the title
    - "integration": MFL keyword in description, confirmed by transcript
    - "description-only": MFL keyword in description but NOT in transcript
    - Videos with no MFL mention are excluded

    When fetch_transcripts is True:
    - Integration videos get transcript-verified (reclassified to description-only if no MFL in transcript)
    - Dedicated videos get transcript text attached for summarization
    """
    yt_dlp = find_yt_dlp()
    base_url = normalize_channel_base_url(channel_url)

    date_start = start_date.replace("-", "")
    date_end = end_date.replace("-", "")

    seen_ids = set()
    videos = []
    errors = []

    for tab, is_live_tab in [("/videos", False), ("/streams", True)]:
        tab_url = f"{base_url}{tab}"
        print(f"Fetching YouTube {tab}...", file=sys.stderr)
        entries, err = _fetch_yt_tab(yt_dlp, tab_url, date_start, date_end)
        if err:
            errors.append(f"{tab}: {err}")
            continue

        for entry in entries:
            vid_id = entry.get("id")
            if not vid_id or vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)

            title = entry.get("title") or ""
            description = entry.get("description") or ""
            video_url = (
                entry.get("url")
                or entry.get("webpage_url")
                or f"https://www.youtube.com/watch?v={vid_id}"
            )

            title_match = has_mfl_keywords(title)
            desc_match = has_mfl_keywords(description)

            if not title_match and not desc_match:
                continue

            # Detect livestream from yt-dlp metadata or tab source
            is_live = is_live_tab or entry.get("was_live", False)

            video_info = {
                "id": vid_id,
                "title": title,
                "upload_date": entry.get("upload_date"),  # YYYYMMDD
                "url": video_url,
                "view_count": entry.get("view_count"),
                "like_count": entry.get("like_count"),
                "duration": entry.get("duration"),
                "type": "dedicated" if title_match else "integration",
                "is_live": is_live,
            }

            videos.append(video_info)

    # Fetch transcripts if requested
    if fetch_transcripts:
        for video in videos:
            duration = video.get("duration") or 0
            if duration < 60:
                # Skip very short videos (likely Shorts)
                continue

            if video["type"] == "integration":
                print(f"Verifying transcript for '{video['title'][:50]}' ({video['id']})...", file=sys.stderr)
                found, timestamp = find_first_mfl_timestamp(video["id"], language=transcript_language)
                if found is None:
                    # Subtitles not available
                    video["transcript_available"] = False
                    video["transcript_verified"] = False
                elif found:
                    video["transcript_available"] = True
                    video["transcript_verified"] = True
                    video["integration_timestamp"] = timestamp
                    # Attach transcript so the LLM sub-agent can determine if truly dedicated
                    transcript = fetch_transcript(video["id"], language=transcript_language)
                    if transcript:
                        video["transcript"] = transcript[:5000]
                else:
                    # Subtitles available but no MFL keywords
                    video["transcript_available"] = True
                    video["type"] = "description-only"
                    video["transcript_verified"] = False

            elif video["type"] == "dedicated":
                print(f"Fetching transcript for '{video['title'][:50]}' ({video['id']})...", file=sys.stderr)
                transcript = fetch_transcript(video["id"], language=transcript_language)
                if transcript:
                    video["transcript_available"] = True
                    video["transcript"] = transcript[:5000]
                else:
                    video["transcript_available"] = False

    result = {"videos": videos}
    if errors:
        result["error"] = "; ".join(errors)
    return result


def fetch_video_metadata(yt_dlp, video_url):
    """Fetch full metadata for a single video."""
    try:
        result = subprocess.run(
            [yt_dlp, "--skip-download", "-j", "--no-warnings", video_url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            return {
                "view_count": data.get("view_count"),
                "like_count": data.get("like_count"),
                "duration": data.get("duration"),
                "upload_date": data.get("upload_date"),
                "description": data.get("description", "")[:200],
            }
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


def fetch_twitch_vods(channel_url, start_date, end_date):
    """Fetch Twitch VODs from a channel using yt-dlp."""
    yt_dlp = find_yt_dlp()

    # Twitch channel URL should point to /videos
    if not channel_url.endswith("/videos"):
        channel_url = channel_url.rstrip("/") + "/videos"

    try:
        result = subprocess.run(
            [yt_dlp, "--flat-playlist", "--dump-json", "--no-warnings", channel_url],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return {"error": "yt-dlp not found", "vods": []}
    except subprocess.TimeoutExpired:
        return {"error": "yt-dlp timed out", "vods": []}

    if result.returncode != 0 and not result.stdout:
        return {"error": f"yt-dlp error: {result.stderr[:200]}", "vods": []}

    vods = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Filter by date range
        upload_date = entry.get("upload_date", "")  # YYYYMMDD or empty
        if upload_date:
            if upload_date < start_date.replace("-", "") or upload_date > end_date.replace("-", ""):
                continue

        # Check title for MFL keywords
        title = entry.get("title") or ""
        if not has_mfl_keywords(title):
            continue

        vods.append({
            "id": entry.get("id"),
            "title": title,
            "upload_date": upload_date,
            "url": entry.get("url") or entry.get("webpage_url", ""),
            "view_count": entry.get("view_count"),
            "duration": entry.get("duration"),
        })

    return {"vods": vods}


def format_date(yyyymmdd):
    """Convert YYYYMMDD to YYYY-MM-DD."""
    if not yyyymmdd or len(yyyymmdd) != 8:
        return yyyymmdd or ""
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


def build_output(args, weeks):
    """Build the final JSON output with all data organized by week."""
    output = {
        "creator": {
            "x_handle": args.x_handle,
            "youtube_channel": args.youtube_channel,
            "twitch_channel": args.twitch_channel,
        },
        "date_range": {
            "start": args.start_date,
            "end": args.end_date,
        },
        "weeks": [],
    }

    # Fetch X tweets for the full range if configured
    x_data = None
    if args.x_handle:
        x_keywords = args.x_keywords or DEFAULT_X_KEYWORDS
        print(f"Fetching X tweets for @{args.x_handle}...", file=sys.stderr)
        x_data = fetch_x_tweets(args.x_handle, x_keywords, args.start_date, args.end_date)
        if x_data.get("error"):
            print(f"X API warning: {x_data['error']}", file=sys.stderr)

    # Fetch YouTube videos for the full range if configured
    # Scans both /videos and /streams tabs, checks titles + descriptions for MFL mentions
    yt_data = None
    if args.youtube_channel:
        yt_data = fetch_youtube_videos(
            args.youtube_channel,
            args.start_date,
            args.end_date,
            fetch_transcripts=args.fetch_transcripts,
            transcript_language=args.transcript_language,
        )
        if yt_data.get("error"):
            print(f"YouTube warning: {yt_data['error']}", file=sys.stderr)

    # Fetch Twitch VODs for the full range if configured
    tw_data = None
    if args.twitch_channel:
        print(f"Fetching Twitch VODs...", file=sys.stderr)
        tw_data = fetch_twitch_vods(args.twitch_channel, args.start_date, args.end_date)
        if tw_data.get("error"):
            print(f"Twitch warning: {tw_data['error']}", file=sys.stderr)

    # Organize data by week
    for week_label, mon, sun, is_complete in weeks:
        mon_str = mon.strftime("%Y-%m-%d")
        sun_str = sun.strftime("%Y-%m-%d")

        week_data = {
            "label": week_label,
            "start": mon_str,
            "end": sun_str,
            "is_complete": is_complete,
            "x_posts": [],
            "youtube_videos": [],
            "twitch_vods": [],
        }

        # Filter X tweets for this week
        if x_data and x_data.get("tweets"):
            for tweet in x_data["tweets"]:
                tweet_date = tweet["created_at"][:10]
                if mon_str <= tweet_date <= sun_str:
                    metrics = tweet.get("public_metrics", {})
                    week_data["x_posts"].append({
                        "date": tweet_date,
                        "type": classify_tweet(tweet),
                        "text": tweet["text"][:150],
                        "impressions": metrics.get("impression_count", 0),
                        "likes": metrics.get("like_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                        "replies": metrics.get("reply_count", 0),
                        "url": f"https://x.com/{args.x_handle}/status/{tweet['id']}",
                    })
            # Sort by date
            week_data["x_posts"].sort(key=lambda x: x["date"])

        # Filter YouTube videos for this week
        if yt_data and yt_data.get("videos"):
            for video in yt_data["videos"]:
                video_date = format_date(video.get("upload_date", ""))
                if video_date and mon_str <= video_date <= sun_str:
                    entry = {
                        "date": video_date,
                        "title": video.get("title", ""),
                        "type": video.get("type", "dedicated"),
                        "views": video.get("view_count"),
                        "likes": video.get("like_count"),
                        "duration": video.get("duration"),
                        "url": video.get("url", ""),
                        "is_live": video.get("is_live", False),
                    }
                    if "transcript" in video:
                        entry["transcript"] = video["transcript"]
                    if "transcript_available" in video:
                        entry["transcript_available"] = video["transcript_available"]
                    if "transcript_verified" in video:
                        entry["transcript_verified"] = video["transcript_verified"]
                    if "integration_timestamp" in video:
                        entry["integration_timestamp"] = video["integration_timestamp"]
                    week_data["youtube_videos"].append(entry)
            week_data["youtube_videos"].sort(key=lambda x: x["date"])

        # Filter Twitch VODs for this week
        if tw_data and tw_data.get("vods"):
            for vod in tw_data["vods"]:
                vod_date = format_date(vod.get("upload_date", ""))
                if vod_date and mon_str <= vod_date <= sun_str:
                    week_data["twitch_vods"].append({
                        "date": vod_date,
                        "title": vod.get("title", ""),
                        "views": vod.get("view_count"),
                        "duration": vod.get("duration"),
                        "url": vod.get("url", ""),
                    })
            week_data["twitch_vods"].sort(key=lambda x: x["date"])

        output["weeks"].append(week_data)

    # Include any errors/warnings
    errors = []
    if x_data and x_data.get("error"):
        errors.append(f"X: {x_data['error']}")
    if yt_data and yt_data.get("error"):
        errors.append(f"YouTube: {yt_data['error']}")
    if tw_data and tw_data.get("error"):
        errors.append(f"Twitch: {tw_data['error']}")
    if errors:
        output["warnings"] = errors

    return output


def main():
    parser = argparse.ArgumentParser(description="Audit creator content across X, YouTube, and Twitch")
    parser.add_argument("--x-handle", help="X/Twitter handle")
    parser.add_argument("--x-keywords", help=f"X search keywords (default: '{DEFAULT_X_KEYWORDS}')")
    parser.add_argument("--youtube-channel", help="YouTube channel videos URL")
    parser.add_argument("--twitch-channel", help="Twitch channel URL")
    parser.add_argument("--fetch-transcripts", action="store_true",
                        help="Fetch transcripts to verify integration videos and summarize dedicated videos")
    parser.add_argument("--transcript-language", default="en",
                        help="Language for auto-generated subtitles (default: en)")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD, should be a Monday)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD, should be a Sunday)")
    args = parser.parse_args()

    if not any([args.x_handle, args.youtube_channel, args.twitch_channel]):
        print("Error: At least one channel must be specified", file=sys.stderr)
        sys.exit(1)

    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    # Align to Monday–Sunday weeks
    start = monday_of(start)
    end = sunday_of(end)
    args.start_date = start.strftime("%Y-%m-%d")
    args.end_date = end.strftime("%Y-%m-%d")

    weeks = list(week_ranges(start, end))
    output = build_output(args, weeks)

    # Output JSON to stdout
    json.dump(output, sys.stdout, indent=2)
    print(file=sys.stdout)


if __name__ == "__main__":
    main()
