#!/usr/bin/env python3
"""
Homerun Social Dashboard
Run: python3 dashboard.py
Starts a local server at http://localhost:8765 and opens it in your browser.
Click the Refresh button in the dashboard to pull fresh data anytime.
"""

import json
import os
import webbrowser
import datetime
import http.server
import threading
from pathlib import Path

import fetch_instagram
import fetch_facebook
import fetch_tiktok
import fetch_trends
import fetch_platform_news
import fetch_ig_hashtags

ENV_FILE      = Path(__file__).parent.parent.parent / "homerun" / ".env"
TEMPLATE      = Path(__file__).parent / "template.html"
OUTPUT_FILE   = Path(__file__).parent / "dashboard.html"
SNAPSHOT_FILE = Path(__file__).parent / "platform_news_snapshot.json"
PORT          = 8765


def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def generate():
    env = load_env()
    token = env.get("INSTAGRAM_ACCESS_TOKEN") or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        print("  [!] No INSTAGRAM_ACCESS_TOKEN — Instagram will show empty data")

    ig_id      = env.get("INSTAGRAM_ACCOUNT_ID")
    fb_page_id = env.get("FACEBOOK_PAGE_ID")
    apify_token = env.get("APIFY_TOKEN") or os.environ.get("APIFY_TOKEN")

    print("=== Refreshing Homerun Social Dashboard ===")
    ig_data      = fetch_instagram.fetch(token, ig_id) if token else {"followers": 0, "post_count": 0, "avg_engagement": 0, "posts": [], "growth": {"dates": [], "counts": []}, "type_counts": [0, 0, 0], "eng_labels": [], "eng_values": [], "today": datetime.date.today().isoformat()}
    fb_data      = fetch_facebook.fetch(token, fb_page_id)
    tt_data      = fetch_tiktok.fetch(apify_token)
    trends_data  = fetch_trends.fetch()
    pn_data      = fetch_platform_news.fetch()
    hashtag_data = fetch_ig_hashtags.fetch(apify_token)

    if SNAPSHOT_FILE.exists():
        try:
            snapshot = json.loads(SNAPSHOT_FILE.read_text())
            pn_data["snapshot"] = snapshot.get("snapshot", "")
            if snapshot.get("actions"):
                pn_data["actions"] = snapshot["actions"]
            print(f"  Loaded approved snapshot from {SNAPSHOT_FILE.name}")
        except Exception as e:
            print(f"  [snapshot] Could not load snapshot: {e}")

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
        "ig_hashtags":      hashtag_data,
        "ideas":            ideas,
        "calendar_entries": calendar_entries,
    }

    html = TEMPLATE.read_text().replace("__DATA__", json.dumps(dashboard_data))
    OUTPUT_FILE.write_text(html)
    print(f"Dashboard saved → {OUTPUT_FILE.name}\n")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/refresh":
            generate()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        elif self.path in ("/", "/dashboard.html"):
            content = OUTPUT_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def main():
    generate()
    url = f"http://localhost:{PORT}"
    print(f"Dashboard running at {url}")
    print("Press Ctrl+C to stop.\n")
    server = http.server.HTTPServer(("localhost", PORT), Handler)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
