#!/usr/bin/env python3
"""
Instagram hashtag research — scrapes broader Australian audience hashtags via Apify.
Returns top posts + hashtag frequency analysis. ~$0.16 per run.
"""

import urllib.request
import json
import time
from collections import Counter

HASHTAGS = [
    "costoflivingaustralia",
    "housingcrisisaustralia",
    "australiamillennials",
    "housemates",
    "australianlife",
    "sydneylife",
    "melbournelife",
]

RESULTS_PER_TAG = 10

SEED_TAGS = set(h.lower() for h in HASHTAGS)


def run_apify(token, hashtags, limit):
    payload = json.dumps({
        "directUrls": [f"https://www.instagram.com/explore/tags/{h}/" for h in hashtags],
        "resultsType": "posts",
        "resultsLimit": limit,
        "addParentData": False,
    }).encode()

    req = urllib.request.Request(
        "https://api.apify.com/v2/acts/apify~instagram-scraper/runs",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        run = json.loads(r.read())

    run_id = run["data"]["id"]
    dataset_id = run["data"]["defaultDatasetId"]

    for _ in range(40):
        time.sleep(4)
        req2 = urllib.request.Request(
            f"https://api.apify.com/v2/actor-runs/{run_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req2, timeout=10) as r2:
            status = json.loads(r2.read())["data"]["status"]
        if status in ("SUCCEEDED", "FAILED", "ABORTED"):
            break

    req3 = urllib.request.Request(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items?limit=200",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req3, timeout=10) as r3:
        return json.loads(r3.read())


def analyse(items):
    tag_counter = Counter()
    top_posts = []

    for item in items:
        tags = [t.lower().strip("#,. ") for t in (item.get("hashtags") or []) if t]
        relevant = [t for t in tags if t not in SEED_TAGS and t]
        for t in relevant:
            tag_counter[t] += 1

        top_posts.append({
            "type":     item.get("type", ""),
            "likes":    item.get("likesCount", 0) or 0,
            "views":    item.get("videoViewCount"),
            "caption":  (item.get("caption") or "")[:120],
            "url":      item.get("url", ""),
            "hashtags": relevant[:10],
            "owner":    item.get("ownerUsername", ""),
        })

    top_posts.sort(key=lambda x: x["likes"], reverse=True)

    return {
        "top_hashtags": [{"tag": t, "count": c} for t, c in tag_counter.most_common(25)],
        "top_posts":    top_posts[:10],
        "post_count":   len(items),
    }


MOCK_DATA = {
    "mock": True,
    "top_hashtags": [
        {"tag": "melbournelife", "count": 8}, {"tag": "sydneylife", "count": 7},
        {"tag": "australianfinance", "count": 6}, {"tag": "aussierenters", "count": 5},
        {"tag": "moneyhacks", "count": 5}, {"tag": "budgetingaustralia", "count": 4},
        {"tag": "rentingaustralia", "count": 4}, {"tag": "savemoney", "count": 3},
    ],
    "top_posts": [
        {"type": "Sidecar", "likes": 44, "views": None, "caption": "Melbourne is expensive 😤 but here's how to beat it", "url": "#", "hashtags": ["melbournelife", "moneyhacks", "australiadeals"], "owner": "example"},
    ],
    "post_count": 32,
}


def fetch(token=None):
    print("[ig_hashtags] Fetching Instagram hashtag research...")
    if not token:
        print("  [ig_hashtags] No APIFY_TOKEN — using mock data")
        return MOCK_DATA
    try:
        items = run_apify(token, HASHTAGS, RESULTS_PER_TAG)
        print(f"  {len(items)} posts fetched")
        result = analyse(items)
        result["mock"] = False
        result["hashtags_searched"] = HASHTAGS
        return result
    except Exception as e:
        print(f"  [ig_hashtags] Failed: {e}")
        return MOCK_DATA
