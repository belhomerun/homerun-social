#!/usr/bin/env python3
"""
Homerun Social Dashboard
Run: python3 dashboard.py
Generates dashboard.html and opens it in your browser.
"""

import json
import os
import webbrowser
import datetime
from pathlib import Path

import fetch_instagram
import fetch_facebook
import fetch_tiktok
import fetch_trends
import fetch_platform_news

ENV_FILE    = Path(__file__).parent.parent.parent / "homerun" / ".env"
TEMPLATE    = Path(__file__).parent / "template.html"
OUTPUT_FILE = Path(__file__).parent / "dashboard.html"


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def main():
    env = load_env()
    token = env.get("INSTAGRAM_ACCESS_TOKEN") or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        print("No INSTAGRAM_ACCESS_TOKEN found. Add it to homerun/.env")
        raise SystemExit(1)

    ig_id      = env.get("INSTAGRAM_ACCOUNT_ID")
    fb_page_id = env.get("FACEBOOK_PAGE_ID")

    print("=== Homerun Social Dashboard ===")
    ig_data     = fetch_instagram.fetch(token, ig_id)
    fb_data     = fetch_facebook.fetch(token, fb_page_id)
    tt_data     = fetch_tiktok.fetch()
    trends_data = fetch_trends.fetch()
    pn_data     = fetch_platform_news.fetch()

    ideas = [
        {"platforms": ["instagram"],            "pillar": "Better Times Together",    "hook": "The hierarchy of sharehouse jobs — who actually does anything?",                              "format": "Carousel — tier list format"},
        {"platforms": ["instagram", "tiktok"],  "pillar": "Better Value Together",    "hook": "Loyalty tax is real and your energy company is counting on you not knowing",                 "format": "Reel — talking head with text overlay"},
        {"platforms": ["tiktok"],               "pillar": "Better Times Together",    "hook": "POV: you're the only one who ever buys toilet paper",                                        "format": "Reel — POV talking head"},
        {"platforms": ["instagram"],            "pillar": "Better Standards Together","hook": "What the new NSW renters rights bill actually means for you",                                 "format": "Carousel — explainer, 5 slides"},
        {"platforms": ["instagram", "tiktok"],  "pillar": "Better Value Together",    "hook": "We checked electricity plans for a 4-person sharehouse — here's what we found",             "format": "Reel — screen recording + voiceover"},
        {"platforms": ["facebook"],             "pillar": "Better Standards Together","hook": "New renters rights legislation — what changed and what didn't",                               "format": "Link post to news article"},
        {"platforms": ["instagram"],            "pillar": "Better Times Together",    "hook": "Signs your sharehouse is thriving (vs just surviving)",                                      "format": "Carousel — 6 slides, relatable format"},
        {"platforms": ["tiktok"],               "pillar": "Better Value Together",    "hook": "We found savings hiding in our sharehouse bills — here's how",                               "format": "Reel — screen recording"},
    ]

    calendar_entries = [
        {"day": "23", "platform": "IG",  "label": "Reel — loyalty tax hook"},
        {"day": "24", "platform": "TT",  "label": "POV: toilet paper"},
        {"day": "26", "platform": "IG",  "label": "Carousel — renters rights"},
        {"day": "28", "platform": "IG",  "label": "Post — sharehouse thriving"},
        {"day": "30", "platform": "TT",  "label": "Reel — bills breakdown"},
    ]

    dashboard_data = {
        "today":            datetime.date.today().isoformat(),
        "instagram":        ig_data,
        "facebook":         fb_data,
        "tiktok":           tt_data,
        "trends":           trends_data,
        "platform_news":    pn_data,
        "ideas":            ideas,
        "calendar_entries": calendar_entries,
    }

    html = TEMPLATE.read_text().replace("__DATA__", json.dumps(dashboard_data))
    OUTPUT_FILE.write_text(html)
    print(f"\nDashboard saved → {OUTPUT_FILE.name}")
    webbrowser.open(f"file://{OUTPUT_FILE.absolute()}")
    print("Opened in browser.")


if __name__ == "__main__":
    main()
