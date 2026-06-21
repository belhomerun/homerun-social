#!/usr/bin/env python3
"""
Facebook Page data fetcher for Homerun dashboard.
Call fetch(token, page_id) — returns a dict. Falls back to mock if page_id is None.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

API_BASE = "https://graph.facebook.com/v20.0"


def api_get(path, params, token):
    params["access_token"] = token
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  [facebook] API error {e.code} on {path}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  [facebook] Request failed: {e}")
        return None


def fetch(token, page_id=None):
    """Fetch Facebook Page data. Returns dict for dashboard injection."""
    if not page_id:
        print("[facebook] No FACEBOOK_PAGE_ID in .env — using mock data")
        return {"mock": True, "page_name": "Homerun", "fans": 0, "posts": [], "top_post": None}

    print("[facebook] Fetching page info...")
    page = api_get(f"/{page_id}", {"fields": "name,fan_count,followers_count"}, token)
    if not page:
        print("[facebook] Page fetch failed — using mock data")
        return {"mock": True, "page_name": "Homerun", "fans": 0, "posts": [], "top_post": None}

    page_name = page.get("name", "Homerun")
    fans = page.get("fan_count") or page.get("followers_count", 0)
    print(f"[facebook] {page_name} — {fans:,} fans")

    print("[facebook] Fetching posts...")
    posts_resp = api_get(f"/{page_id}/posts", {
        "fields": "message,created_time,reactions.summary(true),comments.summary(true)",
        "limit": "20"
    }, token)

    posts_data = []
    if posts_resp:
        for p in posts_resp.get("data", []):
            reactions = p.get("reactions", {}).get("summary", {}).get("total_count", 0)
            comments = p.get("comments", {}).get("summary", {}).get("total_count", 0)
            posts_data.append({
                "caption": (p.get("message") or "")[:80],
                "date": p["created_time"][:10],
                "likes": reactions,
                "comments": comments,
            })

    return {
        "mock": False,
        "page_name": page_name,
        "fans": fans,
        "posts": posts_data,
        "top_post": posts_data[0] if posts_data else None,
    }
