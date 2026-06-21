#!/usr/bin/env python3
"""
TikTok data fetcher — uses Apify to scrape public profile. No TikTok tokens needed.
Actor: clockworks~tiktok-scraper  (~$0.05–0.10 per run)
"""

import json
import time
import urllib.request

PROFILE = "homerun.app"
RESULTS_LIMIT = 20

MOCK_DATA = {
    "mock": True,
    "username": PROFILE,
    "followers": 0,
    "avg_views": 0,
    "total_videos": 0,
    "top_videos": [],
    "type_counts": [0, 0, 0],
    "growth": {"dates": [], "counts": []},
}


def run_apify(token):
    payload = json.dumps({
        "profiles": [f"https://www.tiktok.com/@{PROFILE}"],
        "resultsPerPage": RESULTS_LIMIT,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
    }).encode()

    req = urllib.request.Request(
        "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/runs",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        run = json.loads(r.read())

    run_id = run["data"]["id"]
    dataset_id = run["data"]["defaultDatasetId"]

    for _ in range(60):
        time.sleep(5)
        req2 = urllib.request.Request(
            f"https://api.apify.com/v2/actor-runs/{run_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req2, timeout=10) as r2:
            status = json.loads(r2.read())["data"]["status"]
        if status in ("SUCCEEDED", "FAILED", "ABORTED"):
            break

    req3 = urllib.request.Request(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items?limit=100",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req3, timeout=10) as r3:
        return json.loads(r3.read())


def parse(items):
    if not items:
        return MOCK_DATA

    # Profile-level stats come from authorMeta on first item
    author = items[0].get("authorMeta") or {}
    followers = author.get("fans") or author.get("followers") or 0
    total_videos = author.get("video") or len(items)

    videos = []
    for item in items:
        plays = item.get("playCount") or item.get("videoPlayCount") or 0
        date_raw = item.get("createTimeISO") or item.get("createTime") or ""
        date = date_raw[:10] if date_raw else ""
        videos.append({
            "caption": (item.get("text") or item.get("description") or "")[:120],
            "date": date,
            "views": plays,
            "likes": item.get("diggCount") or item.get("likeCount") or 0,
            "comments": item.get("commentCount") or 0,
            "shares": item.get("shareCount") or 0,
        })

    videos.sort(key=lambda v: v["date"], reverse=True)
    avg_views = round(sum(v["views"] for v in videos) / len(videos)) if videos else 0

    return {
        "mock": False,
        "username": PROFILE,
        "followers": followers,
        "avg_views": avg_views,
        "total_videos": total_videos,
        "top_videos": videos,
        "type_counts": [0, len(videos), 0],
        "growth": {"dates": [], "counts": []},
    }


def fetch(token=None):
    print("[tiktok] Fetching @" + PROFILE + " via Apify...")
    if not token:
        print("  [tiktok] No APIFY_TOKEN — using mock data")
        return MOCK_DATA
    try:
        items = run_apify(token)
        print(f"  {len(items)} videos fetched")
        result = parse(items)
        result["mock"] = False
        return result
    except Exception as e:
        print(f"  [tiktok] Failed: {e}")
        return {**MOCK_DATA, "error": str(e)}
