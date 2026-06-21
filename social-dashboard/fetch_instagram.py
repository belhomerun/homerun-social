#!/usr/bin/env python3
"""
Instagram data fetcher for Homerun dashboard.
Call fetch(token, ig_id) — returns a dict of dashboard data.
"""

import json
import datetime
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

API_BASE = "https://graph.facebook.com/v20.0"
HISTORY_FILE = Path(__file__).parent / "growth_history.json"


def api_get(path, params, token):
    params["access_token"] = token
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  [instagram] API error {e.code} on {path}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  [instagram] Request failed: {e}")
        return None


def find_ig_account_id(token):
    pages = api_get("/me/accounts", {"fields": "id,name,instagram_business_account"}, token)
    if pages:
        for page in pages.get("data", []):
            ig = page.get("instagram_business_account")
            if ig:
                return ig["id"]

    businesses = api_get("/me/businesses", {"fields": "id,name"}, token)
    if businesses:
        for biz in businesses.get("data", []):
            biz_id = biz["id"]
            owned = api_get(f"/{biz_id}/owned_pages", {"fields": "id,name,instagram_business_account"}, token)
            if owned:
                for page in owned.get("data", []):
                    ig = page.get("instagram_business_account")
                    if ig:
                        return ig["id"]
            ig_accounts = api_get(f"/{biz_id}/instagram_accounts", {"fields": "id,username"}, token)
            if ig_accounts:
                for acct in ig_accounts.get("data", []):
                    return acct["id"]

    client_pages = api_get("/me/client_pages", {"fields": "id,name,instagram_business_account"}, token)
    if client_pages:
        for page in client_pages.get("data", []):
            ig = page.get("instagram_business_account")
            if ig:
                return ig["id"]

    return None


def fetch_post_insights(media_id, media_type, token):
    # impressions removed in v22+; plays not a valid insights metric — use reach,saved,total_interactions
    result = api_get(f"/{media_id}/insights", {"metric": "reach,saved,total_interactions"}, token)
    if not result:
        return {}
    out = {}
    for item in result.get("data", []):
        val = item.get("value")
        if val is None and item.get("values"):
            val = item["values"][0].get("value", 0)
        out[item["name"]] = val or 0
    return out


def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return []


def fetch(token, ig_id=None):
    """Fetch Instagram data. Returns dict for dashboard injection."""
    today = datetime.date.today().isoformat()
    _empty = {"followers": 0, "post_count": 0, "avg_engagement": 0, "today": today,
              "growth": {"dates": [], "counts": []}, "type_counts": [0, 0, 0],
              "posts": [], "eng_labels": [], "eng_values": []}

    if not ig_id:
        print("[instagram] Finding account...")
        ig_id = find_ig_account_id(token)

    if not ig_id:
        print("[instagram] Could not find account. Set INSTAGRAM_ACCOUNT_ID in .env")
        return {**_empty, "error": "account not found"}

    print("[instagram] Fetching profile...")
    profile = api_get(f"/{ig_id}", {"fields": "id,username,followers_count,media_count"}, token)
    if not profile:
        return {**_empty, "error": "profile fetch failed"}

    username = profile.get("username", "unknown")
    followers = profile.get("followers_count", 0)
    print(f"[instagram] @{username} — {followers:,} followers")

    print("[instagram] Fetching posts...")
    media_resp = api_get(f"/{ig_id}/media", {
        "fields": "id,caption,media_type,timestamp,like_count,comments_count",
        "limit": "50"
    }, token)
    posts = media_resp.get("data", []) if media_resp else []

    print(f"[instagram] Fetching insights for {len(posts)} posts...")
    for i, post in enumerate(posts):
        insights = fetch_post_insights(post["id"], post.get("media_type", "IMAGE"), token)
        post.update(insights)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(posts)}")

    history = load_history()
    if not any(h["date"] == today for h in history):
        history.append({"date": today, "followers": followers})
        HISTORY_FILE.write_text(json.dumps(history, indent=2))

    recent = sorted(posts, key=lambda x: x["timestamp"], reverse=True)[:30]

    posts_data = []
    for p in recent:
        likes = p.get("like_count", 0)
        comments = p.get("comments_count", 0)
        eng = round((likes + comments) / followers * 100, 2) if followers else 0
        posts_data.append({
            "caption": (p.get("caption") or "")[:80],
            "type": p.get("media_type", "IMAGE"),
            "date": p["timestamp"][:10],
            "likes": likes,
            "comments": comments,
            "engagement": eng,
            "reach": p.get("reach"),
            "saves": p.get("saved"),
        })

    eng_vals = [p["engagement"] for p in posts_data]
    avg_eng = round(sum(eng_vals) / len(eng_vals), 2) if eng_vals else 0

    type_counts = {"IMAGE": 0, "VIDEO": 0, "CAROUSEL_ALBUM": 0}
    for p in posts:
        t = p.get("media_type", "IMAGE")
        type_counts[t] = type_counts.get(t, 0) + 1

    history_data = load_history()
    return {
        "username": username,
        "followers": followers,
        "post_count": profile.get("media_count", len(posts)),
        "today": today,
        "avg_engagement": avg_eng,
        "growth": {
            "dates": [h["date"] for h in history_data[-60:]],
            "counts": [h["followers"] for h in history_data[-60:]],
        },
        "type_counts": [type_counts["IMAGE"], type_counts["VIDEO"], type_counts["CAROUSEL_ALBUM"]],
        "posts": posts_data,
        "eng_labels": [p["date"] for p in reversed(posts_data)],
        "eng_values": [p["engagement"] for p in reversed(posts_data)],
    }
