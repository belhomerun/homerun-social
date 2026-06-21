# Social Media Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the existing single-platform Instagram dashboard into an 8-tab social media analytics dashboard covering Instagram, TikTok, Facebook, trending intel, content ideas, platform news, and a content calendar placeholder — published to GitHub Pages.

**Architecture:** Multi-module Python app. Each platform/data source is an independent `fetch_*.py` module exposing a `fetch()` function that returns a dict. `dashboard.py` orchestrates all fetchers, merges the data, injects it into `template.html` (replacing the `__DATA__` placeholder), writes `dashboard.html`, and opens it. GitHub Pages publishing uses a separate `gh-pages` branch via `publish.sh`.

**Tech Stack:** Python 3 stdlib + urllib (no pip installs needed), Chart.js 4.4.0 (CDN), GitHub Pages

---

## File map

| File | Status | Responsibility |
|---|---|---|
| `social-dashboard/fetch_instagram.py` | MODIFY | Refactor: extract data fetch into `fetch()`, remove `build_html()`/`main()` |
| `social-dashboard/fetch_facebook.py` | CREATE | Facebook Page insights via Meta Graph API; mock fallback if no page ID |
| `social-dashboard/fetch_tiktok.py` | CREATE | Mock TikTok data (API wired in later) |
| `social-dashboard/fetch_trends.py` | CREATE | Mock niche + adjacent trending intel (Apify wired in later) |
| `social-dashboard/fetch_platform_news.py` | CREATE | Live RSS from Social Media Today, Later Blog, Hootsuite Blog |
| `social-dashboard/template.html` | CREATE | Full 8-tab HTML shell — all CSS, JS, tab structure; `__DATA__` placeholder |
| `social-dashboard/dashboard.py` | CREATE | Orchestrator: calls all fetchers, injects data, writes dashboard.html, opens browser |
| `social-dashboard/.gitignore` | MODIFY | Add `dashboard.html` so generated output stays off main branch |
| `publish.sh` | CREATE | One-command publish: copies dashboard.html to gh-pages branch and pushes |

---

## Task 1: Refactor fetch_instagram.py into a module

**Files:**
- Modify: `social-dashboard/fetch_instagram.py`

The existing script does two jobs: fetch data AND render HTML. After this task it exposes a single `fetch(token, ig_id=None)` function returning a data dict. All HTML/browser logic is removed.

- [ ] **Step 1: Replace the contents of fetch_instagram.py**

```python
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
    metrics = "reach,saved,plays" if media_type == "VIDEO" else "reach,saved,impressions"
    result = api_get(f"/{media_id}/insights", {"metric": metrics}, token)
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

    if not ig_id:
        print("[instagram] Finding account...")
        ig_id = find_ig_account_id(token)

    if not ig_id:
        print("[instagram] Could not find account. Set INSTAGRAM_ACCOUNT_ID in .env")
        return {"error": "account not found", "followers": 0, "post_count": 0, "avg_engagement": 0,
                "growth": {"dates": [], "counts": []}, "type_counts": [0, 0, 0], "posts": [],
                "eng_labels": [], "eng_values": [], "today": today}

    print("[instagram] Fetching profile...")
    profile = api_get(f"/{ig_id}", {"fields": "id,username,followers_count,media_count"}, token)
    if not profile:
        return {"error": "profile fetch failed", "followers": 0, "post_count": 0, "avg_engagement": 0,
                "growth": {"dates": [], "counts": []}, "type_counts": [0, 0, 0], "posts": [],
                "eng_labels": [], "eng_values": [], "today": today}

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
```

- [ ] **Step 2: Verify old entry points are gone**

```bash
grep -n "def main\|def build_html\|webbrowser\|if __name__" /Users/belindadodge/Desktop/Claude-Code/homerun-social/social-dashboard/fetch_instagram.py
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social add social-dashboard/fetch_instagram.py
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social commit -m "Refactor fetch_instagram.py into module with fetch() function"
```

---

## Task 2: Create fetch_facebook.py

**Files:**
- Create: `social-dashboard/fetch_facebook.py`

Same Meta token as Instagram. Reads `FACEBOOK_PAGE_ID` from env. Returns mock data if page ID not set.

- [ ] **Step 1: Create fetch_facebook.py**

```python
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
```

- [ ] **Step 2: Sanity check**

```bash
cd /Users/belindadodge/Desktop/Claude-Code/homerun-social/social-dashboard
python3 -c "import fetch_facebook; print('import ok')"
```

Expected: `import ok`

- [ ] **Step 3: Commit**

```bash
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social add social-dashboard/fetch_facebook.py
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social commit -m "Add fetch_facebook.py — Page insights with mock fallback"
```

---

## Task 3: Create fetch_tiktok.py (mock)

**Files:**
- Create: `social-dashboard/fetch_tiktok.py`

- [ ] **Step 1: Create fetch_tiktok.py**

```python
#!/usr/bin/env python3
"""
TikTok data fetcher — mock data. Wire up TikTok for Developers API later.
"""


def fetch():
    return {
        "mock": True,
        "username": "homerun.au",
        "followers": 0,
        "avg_views": 0,
        "total_videos": 0,
        "top_videos": [
            {"caption": "mock: great sharehouses use homerun", "date": "2026-06-18", "views": 1240, "likes": 87, "comments": 4, "shares": 12},
            {"caption": "mock: renting isn't temporary anymore", "date": "2026-06-15", "views": 890, "likes": 62, "comments": 1, "shares": 8},
            {"caption": "mock: house manager reporting for duty", "date": "2026-06-12", "views": 2100, "likes": 143, "comments": 9, "shares": 31},
        ],
        "type_counts": [0, 0, 0],
        "growth": {"dates": [], "counts": []},
    }
```

- [ ] **Step 2: Sanity check**

```bash
cd /Users/belindadodge/Desktop/Claude-Code/homerun-social/social-dashboard
python3 -c "import fetch_tiktok; d = fetch_tiktok.fetch(); print('mock:', d['mock'], '| videos:', len(d['top_videos']))"
```

Expected: `mock: True | videos: 3`

- [ ] **Step 3: Commit**

```bash
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social add social-dashboard/fetch_tiktok.py
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social commit -m "Add fetch_tiktok.py — mock data, TikTok API to wire in later"
```

---

## Task 4: Create fetch_trends.py (mock)

**Files:**
- Create: `social-dashboard/fetch_trends.py`

- [ ] **Step 1: Create fetch_trends.py**

```python
#!/usr/bin/env python3
"""
Niche trending intel — mock data. Wire up Apify scrapers later.
"""


def fetch():
    return {
        "mock": True,
        "niche": [
            {"headline": "Rental vacancy rates hit 10-year low in Sydney and Melbourne", "source": "Domain", "date": "2026-06-20", "url": "#", "tags": ["rental crisis", "vacancy"]},
            {"headline": "New renters rights bill passes NSW parliament", "source": "SMH", "date": "2026-06-19", "url": "#", "tags": ["renters rights", "legislation"]},
            {"headline": "Energy bills for sharehouses up 18% year on year", "source": "The Guardian", "date": "2026-06-18", "url": "#", "tags": ["cost of living", "energy"]},
            {"headline": "One in three Australians aged 25–34 still renting", "source": "ABS", "date": "2026-06-17", "url": "#", "tags": ["renting", "demographics"]},
        ],
        "adjacent": [
            {"headline": "Gen Z's relationship with homeownership is fundamentally different", "source": "AFR", "date": "2026-06-20", "url": "#", "tags": ["gen z", "property"]},
            {"headline": "Cost of living pressures easing but rents remain sticky", "source": "RBA", "date": "2026-06-18", "url": "#", "tags": ["cost of living", "rent"]},
            {"headline": "Flatmates.com.au sees record listings in June", "source": "Flatmates.com.au", "date": "2026-06-17", "url": "#", "tags": ["sharehouse", "flatmates"]},
        ],
        "by_platform": {
            "instagram": [
                {"format": "Carousel", "topic": "Renters rights explainer", "why": "Educational carousels driving high saves"},
                {"format": "Reel", "topic": "Day in the life of a sharehouse", "why": "Relatable POV content performing well"},
                {"format": "Reel", "topic": "Energy bill reaction video", "why": "Cost of living anger = high share rate"},
            ],
            "tiktok": [
                {"format": "Talking head", "topic": "Loyalty tax explainer", "why": "Finance explainers trending in AU"},
                {"format": "Duet/stitch", "topic": "React to rental horror stories", "why": "High engagement in renting niche"},
                {"format": "Text overlay", "topic": "Sharehouse rules tier list", "why": "Tier lists still performing in this demo"},
            ],
            "facebook": [
                {"format": "Link post", "topic": "Renters rights news", "why": "News posts get organic reach on FB"},
                {"format": "Poll", "topic": "What's your biggest sharehouse pain point?", "why": "Polls drive engagement on FB pages"},
            ],
        },
    }
```

- [ ] **Step 2: Sanity check**

```bash
cd /Users/belindadodge/Desktop/Claude-Code/homerun-social/social-dashboard
python3 -c "import fetch_trends; d = fetch_trends.fetch(); print('niche:', len(d['niche']), '| adjacent:', len(d['adjacent']))"
```

Expected: `niche: 4 | adjacent: 3`

- [ ] **Step 3: Commit**

```bash
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social add social-dashboard/fetch_trends.py
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social commit -m "Add fetch_trends.py — mock niche + adjacent trending intel"
```

---

## Task 5: Create fetch_platform_news.py (live RSS)

**Files:**
- Create: `social-dashboard/fetch_platform_news.py`

Fetches real RSS from Social Media Today, Later Blog, Hootsuite Blog. Filters for Instagram/TikTok/Facebook mentions. Falls back to hardcoded mock if all feeds fail.

- [ ] **Step 1: Create fetch_platform_news.py**

```python
#!/usr/bin/env python3
"""
Platform news fetcher — RSS feeds filtered for IG/TikTok/FB news.
Uses stdlib only (urllib + xml.etree).
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

FEEDS = [
    {"name": "Social Media Today", "url": "https://www.socialmediatoday.com/feeds/all.rss"},
    {"name": "Later Blog", "url": "https://later.com/blog/feed/"},
    {"name": "Hootsuite Blog", "url": "https://blog.hootsuite.com/feed/"},
]

PLATFORM_KEYWORDS = {
    "instagram": ["instagram", "reels", "ig "],
    "tiktok": ["tiktok", "tik tok"],
    "facebook": ["facebook", "meta ", "fb "],
}


def detect_platforms(text):
    text_lower = text.lower()
    return [p for p, keywords in PLATFORM_KEYWORDS.items() if any(kw in text_lower for kw in keywords)]


def fetch_feed(feed):
    try:
        req = urllib.request.Request(feed["url"], headers={"User-Agent": "Homerun Dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            root = ET.fromstring(resp.read())
        channel = root.find("channel")
        if channel is None:
            return []
        items = []
        for item in channel.findall("item")[:20]:
            title = (item.findtext("title") or "").strip()
            platforms = detect_platforms(title)
            if platforms:
                items.append({
                    "title": title,
                    "source": feed["name"],
                    "date": (item.findtext("pubDate") or "")[:16],
                    "url": (item.findtext("link") or "").strip(),
                    "platforms": platforms,
                })
        return items
    except Exception as e:
        print(f"  [platform_news] Failed to fetch {feed['name']}: {e}")
        return []


def fetch():
    print("[platform_news] Fetching RSS feeds...")
    all_items = []
    for feed in FEEDS:
        items = fetch_feed(feed)
        print(f"  {feed['name']}: {len(items)} relevant items")
        all_items.extend(items)

    if not all_items:
        print("[platform_news] No items fetched — using mock fallback")
        return {
            "mock": True,
            "items": [
                {"title": "Instagram announces new Reels editing tools", "source": "Social Media Today", "date": "2026-06-20", "url": "#", "platforms": ["instagram"]},
                {"title": "TikTok's algorithm change: what creators need to know", "source": "Later Blog", "date": "2026-06-19", "url": "#", "platforms": ["tiktok"]},
                {"title": "Facebook Pages reach declining — here's what still works", "source": "Hootsuite Blog", "date": "2026-06-18", "url": "#", "platforms": ["facebook"]},
            ],
        }

    return {"mock": False, "items": all_items}
```

- [ ] **Step 2: Test the RSS fetcher**

```bash
cd /Users/belindadodge/Desktop/Claude-Code/homerun-social/social-dashboard
python3 -c "
import fetch_platform_news
d = fetch_platform_news.fetch()
print('mock:', d['mock'], '| items:', len(d['items']))
for item in d['items'][:3]:
    print(' -', item['source'], '|', item['platforms'], '|', item['title'][:55])
"
```

Expected: items from at least one feed, or mock fallback. No crash.

- [ ] **Step 3: Commit**

```bash
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social add social-dashboard/fetch_platform_news.py
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social commit -m "Add fetch_platform_news.py — live RSS from Social Media Today, Later, Hootsuite"
```

---

## Task 6: Create template.html

**Files:**
- Create: `social-dashboard/template.html`

Full 8-tab HTML shell. Contains all CSS, tab structure, and JavaScript. The string `__DATA__` is the only placeholder — `dashboard.py` replaces it with the merged JSON object at build time. Chart.js loaded from CDN (requires internet).

- [ ] **Step 1: Create template.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Homerun — Social Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg: #fdfcfc; --surface: #ffffff; --surface2: #fcefe3; --border: #d7d6d5;
  --orange: #fc8f29; --orange-dark: #ea7e03; --orange-light: #fcefe3;
  --text: #24211e; --text2: #3f3b37; --muted: #5c5451; --warm1: #c25500;
  --radius: 11px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: Arial, sans-serif; font-size: 14px; line-height: 1.5; }
header { display: flex; align-items: baseline; gap: 16px; padding: 24px 36px 20px; border-bottom: 1px solid var(--border); }
.wordmark { font-size: 20px; font-weight: 700; letter-spacing: -.3px; }
.wordmark span { color: var(--orange); }
.header-right { margin-left: auto; text-align: right; }
.updated { color: var(--muted); font-size: 12px; }
nav { display: flex; gap: 2px; padding: 0 36px; border-bottom: 1px solid var(--border); background: var(--surface); position: sticky; top: 0; z-index: 10; overflow-x: auto; }
.tab-btn { padding: 12px 16px; font-size: 13px; font-weight: 600; color: var(--muted); background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; white-space: nowrap; transition: color .15s; }
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--orange-dark); border-bottom-color: var(--orange); }
main { padding: 28px 36px; }
section { display: none; }
section.active { display: block; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }
.stat { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px 24px; }
.stat-label { font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px; }
.stat-value { font-size: 32px; font-weight: 700; letter-spacing: -.5px; }
.stat-value.accent { color: var(--orange); }
.row2 { display: grid; grid-template-columns: 3fr 2fr; gap: 12px; margin-bottom: 20px; }
.row3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px 24px; margin-bottom: 20px; }
.card h2, .table-wrap h2 { font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 16px; }
.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; margin-bottom: 20px; }
.table-wrap h2 { padding: 20px 24px 14px; margin-bottom: 0; }
table { width: 100%; border-collapse: collapse; }
th { padding: 9px 14px; text-align: left; font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid var(--border); background: var(--surface2); }
td { padding: 11px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; color: var(--text2); }
tr:last-child td { border-bottom: none; }
tbody tr:hover td { background: #fdf8f4; }
.pill { display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: .04em; }
.pill-photo { background: #f5e6d3; color: var(--text2); }
.pill-reel { background: var(--orange-light); color: var(--orange-dark); }
.pill-carousel { background: #fcd5aa; color: var(--warm1); }
.pill-ig { background: #fce4d6; color: #c0392b; }
.pill-tiktok { background: #e8f4f8; color: #1a6985; }
.pill-fb { background: #e8eaf6; color: #3949ab; }
.cap { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--muted); }
.na { color: var(--border); }
.footer-note { color: var(--muted); font-size: 12px; padding-top: 8px; }
.mock-banner { background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; padding: 8px 14px; font-size: 12px; color: #856404; margin-bottom: 16px; }
.news-list { list-style: none; }
.news-item { padding: 14px 0; border-bottom: 1px solid var(--border); display: flex; gap: 12px; align-items: flex-start; }
.news-item:last-child { border-bottom: none; }
.news-item-body { flex: 1; }
.news-title { font-weight: 600; font-size: 14px; color: var(--text); text-decoration: none; }
.news-title:hover { color: var(--orange-dark); }
.news-meta { font-size: 12px; color: var(--muted); margin-top: 3px; }
.news-platforms { display: flex; gap: 4px; flex-shrink: 0; padding-top: 2px; }
.ideas-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin-bottom: 20px; }
.idea-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 20px; }
.idea-platform { display: flex; gap: 6px; margin-bottom: 10px; }
.idea-pillar { font-size: 11px; color: var(--muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: .04em; }
.idea-hook { font-weight: 600; font-size: 14px; margin-bottom: 6px; }
.idea-format { font-size: 12px; color: var(--muted); }
.calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cal-header { font-size: 11px; font-weight: 700; color: var(--muted); text-align: center; padding: 8px 4px; text-transform: uppercase; letter-spacing: .05em; }
.cal-day { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; min-height: 80px; padding: 8px; }
.cal-day.empty { background: none; border: none; }
.cal-day.today { border-color: var(--orange); }
.cal-num { font-weight: 700; font-size: 13px; margin-bottom: 4px; }
.cal-entry { background: var(--orange-light); border-radius: 3px; padding: 2px 5px; font-size: 10px; margin-bottom: 2px; color: var(--orange-dark); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.top-posts-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }
.top-post-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 18px; }
.top-post-platform { font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 8px; }
.top-post-caption { font-size: 13px; color: var(--text2); margin-bottom: 10px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
.top-post-metrics { display: flex; gap: 16px; }
.top-post-metric { font-size: 12px; color: var(--muted); }
.top-post-metric strong { color: var(--text); display: block; font-size: 16px; }
.section-title { font-size: 16px; font-weight: 700; margin-bottom: 16px; }
</style>
</head>
<body>
<script>const DATA = __DATA__;</script>

<header>
  <div class="wordmark">home<span>run</span></div>
  <div class="header-right"><div class="updated" id="updated"></div></div>
</header>

<nav>
  <button class="tab-btn active" data-tab="overview">Overview</button>
  <button class="tab-btn" data-tab="instagram">Instagram</button>
  <button class="tab-btn" data-tab="tiktok">TikTok</button>
  <button class="tab-btn" data-tab="facebook">Facebook</button>
  <button class="tab-btn" data-tab="trends">Trending Intel</button>
  <button class="tab-btn" data-tab="ideas">Content Ideas</button>
  <button class="tab-btn" data-tab="platform-news">Platform News</button>
  <button class="tab-btn" data-tab="calendar">Calendar</button>
</nav>

<main>

<section id="tab-overview" class="active">
  <div class="stats" id="overview-stats"></div>
  <div class="section-title">Top post per platform</div>
  <div class="top-posts-grid" id="overview-top-posts"></div>
</section>

<section id="tab-instagram">
  <div id="ig-mock-banner"></div>
  <div class="stats">
    <div class="stat"><div class="stat-label">Followers</div><div class="stat-value accent" id="ig-followers"></div></div>
    <div class="stat"><div class="stat-label">Avg engagement (last 30)</div><div class="stat-value" id="ig-eng"></div></div>
    <div class="stat"><div class="stat-label">Total posts</div><div class="stat-value" id="ig-posts"></div></div>
  </div>
  <div class="row2">
    <div class="card"><h2>Follower growth</h2><canvas id="ig-growthChart"></canvas></div>
    <div class="card"><h2>Content breakdown (last 50)</h2><canvas id="ig-typeChart"></canvas></div>
  </div>
  <div class="card"><h2>Engagement rate — last 30 posts</h2><canvas id="ig-engChart" height="70"></canvas></div>
  <div class="table-wrap">
    <h2>Post performance</h2>
    <table><thead><tr><th>Caption</th><th>Type</th><th>Date</th><th>Likes</th><th>Comments</th><th>Engagement</th><th>Reach</th><th>Saves</th></tr></thead>
    <tbody id="ig-tbody"></tbody></table>
  </div>
  <p class="footer-note">Engagement = (likes + comments) / followers × 100</p>
</section>

<section id="tab-tiktok">
  <div class="mock-banner">TikTok: mock data — real API connection coming soon</div>
  <div class="stats">
    <div class="stat"><div class="stat-label">Followers</div><div class="stat-value accent" id="tt-followers"></div></div>
    <div class="stat"><div class="stat-label">Avg views</div><div class="stat-value" id="tt-views"></div></div>
    <div class="stat"><div class="stat-label">Total videos</div><div class="stat-value" id="tt-videos"></div></div>
  </div>
  <div class="table-wrap">
    <h2>Top videos</h2>
    <table><thead><tr><th>Caption</th><th>Date</th><th>Views</th><th>Likes</th><th>Comments</th><th>Shares</th></tr></thead>
    <tbody id="tt-tbody"></tbody></table>
  </div>
</section>

<section id="tab-facebook">
  <div id="fb-mock-banner"></div>
  <div class="stats">
    <div class="stat"><div class="stat-label">Page fans</div><div class="stat-value accent" id="fb-fans"></div></div>
    <div class="stat"><div class="stat-label">Recent posts</div><div class="stat-value" id="fb-post-count"></div></div>
  </div>
  <div class="table-wrap">
    <h2>Recent posts</h2>
    <table><thead><tr><th>Caption</th><th>Date</th><th>Reactions</th><th>Comments</th></tr></thead>
    <tbody id="fb-tbody"></tbody></table>
  </div>
</section>

<section id="tab-trends">
  <div id="trends-mock-banner"></div>
  <div class="row2">
    <div class="card" style="margin-bottom:0"><h2>Sharehouse &amp; renting niche</h2><ul class="news-list" id="trends-niche"></ul></div>
    <div class="card" style="margin-bottom:0"><h2>Adjacent niches</h2><ul class="news-list" id="trends-adjacent"></ul></div>
  </div>
  <div class="card" style="margin-top:12px">
    <h2>What's working by platform</h2>
    <div class="row3" id="trends-by-platform" style="margin-bottom:0"></div>
  </div>
</section>

<section id="tab-ideas">
  <p style="color:var(--muted);font-size:13px;margin-bottom:20px">Generated from trending intel. Claude API connection coming soon — ideas below are curated starting points.</p>
  <div class="ideas-grid" id="ideas-grid"></div>
</section>

<section id="tab-platform-news">
  <div id="pn-mock-banner"></div>
  <div class="card"><h2>Latest platform updates</h2><ul class="news-list" id="pn-list"></ul></div>
</section>

<section id="tab-calendar">
  <div class="mock-banner">Calendar: placeholder — Notion connection coming soon</div>
  <div style="display:flex;align-items:center;margin-bottom:16px">
    <div class="section-title" style="margin-bottom:0" id="cal-month-label"></div>
  </div>
  <div class="card"><div class="calendar-grid" id="cal-grid"></div></div>
</section>

</main>

<script>
const D = DATA;
const C = { orange: '#fc8f29', orangeDark: '#ea7e03', warm1: '#c25500', muted: '#5c5451', border: '#d7d6d5', orangeLight: '#fcefe3' };
const axisStyle = (opts = {}) => ({ ticks: { color: C.muted, font: { size: 11 }, maxTicksLimit: 7, ...opts.ticks }, grid: { color: C.border } });
const pillMap = { instagram: 'pill-ig', tiktok: 'pill-tiktok', facebook: 'pill-fb' };

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('main section').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

document.getElementById('updated').textContent = 'Updated ' + (D.today || '');

// OVERVIEW
const overviewStats = [
  { label: 'Instagram followers', value: (D.instagram.followers || 0).toLocaleString(), accent: true },
  { label: 'TikTok followers', value: (D.tiktok.followers || 0).toLocaleString(), accent: false },
  { label: 'Facebook fans', value: (D.facebook.fans || 0).toLocaleString(), accent: false },
  { label: 'IG avg engagement', value: (D.instagram.avg_engagement || 0) + '%', accent: false },
];
document.getElementById('overview-stats').innerHTML = overviewStats.map(s =>
  `<div class="stat"><div class="stat-label">${s.label}</div><div class="stat-value${s.accent ? ' accent' : ''}">${s.value}</div></div>`
).join('');

const makeTopPost = (platform, post, m1l, m1, m2l, m2) => {
  if (!post) return `<div class="top-post-card"><div class="top-post-platform">${platform}</div><div class="top-post-caption" style="color:var(--muted)">No data yet</div></div>`;
  return `<div class="top-post-card"><div class="top-post-platform">${platform}</div><div class="top-post-caption">${post.caption || '—'}</div><div class="top-post-metrics"><div class="top-post-metric"><strong>${Number(m1).toLocaleString()}</strong>${m1l}</div><div class="top-post-metric"><strong>${Number(m2).toLocaleString()}</strong>${m2l}</div></div></div>`;
};
const igTop = (D.instagram.posts || [])[0];
const ttTop = (D.tiktok.top_videos || [])[0];
const fbTop = D.facebook.top_post;
document.getElementById('overview-top-posts').innerHTML =
  makeTopPost('Instagram', igTop, 'likes', igTop ? igTop.likes : 0, 'engagement', igTop ? igTop.engagement : 0) +
  makeTopPost('TikTok', ttTop, 'views', ttTop ? ttTop.views : 0, 'likes', ttTop ? ttTop.likes : 0) +
  makeTopPost('Facebook', fbTop, 'reactions', fbTop ? fbTop.likes : 0, 'comments', fbTop ? fbTop.comments : 0);

// INSTAGRAM
const ig = D.instagram;
if (ig.error) document.getElementById('ig-mock-banner').innerHTML = `<div class="mock-banner">Instagram: ${ig.error}</div>`;
document.getElementById('ig-followers').textContent = (ig.followers || 0).toLocaleString();
document.getElementById('ig-eng').textContent = (ig.avg_engagement || 0) + '%';
document.getElementById('ig-posts').textContent = (ig.post_count || 0).toLocaleString();
if (ig.growth && ig.growth.dates.length) {
  new Chart(document.getElementById('ig-growthChart'), {
    type: 'line',
    data: { labels: ig.growth.dates, datasets: [{ data: ig.growth.counts, borderColor: C.orange, backgroundColor: 'rgba(252,143,41,0.07)', fill: true, tension: 0.35, pointRadius: ig.growth.dates.length > 10 ? 2 : 4, pointBackgroundColor: C.orange, borderWidth: 2 }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: axisStyle(), y: { ...axisStyle(), beginAtZero: false } } }
  });
}
new Chart(document.getElementById('ig-typeChart'), {
  type: 'doughnut',
  data: { labels: ['Photos', 'Reels', 'Carousels'], datasets: [{ data: ig.type_counts || [0,0,0], backgroundColor: ['#f5e6d3', C.orangeLight, C.orange], borderWidth: 0, hoverOffset: 6 }] },
  options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { color: C.muted, padding: 16, font: { size: 12 }, boxWidth: 12, boxHeight: 12 } } } }
});
if (ig.eng_values && ig.eng_values.length) {
  new Chart(document.getElementById('ig-engChart'), {
    type: 'bar',
    data: { labels: ig.eng_labels, datasets: [{ data: ig.eng_values, backgroundColor: 'rgba(252,143,41,0.4)', borderColor: C.orange, borderWidth: 1, borderRadius: 3 }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: axisStyle({ ticks: { maxTicksLimit: 10 } }), y: { ...axisStyle(), ticks: { color: C.muted, font: { size: 11 }, callback: v => v + '%' } } } }
  });
}
const typeLabel = { IMAGE: 'Photo', VIDEO: 'Reel', CAROUSEL_ALBUM: 'Carousel' };
const typePill  = { IMAGE: 'pill-photo', VIDEO: 'pill-reel', CAROUSEL_ALBUM: 'pill-carousel' };
const igTbody = document.getElementById('ig-tbody');
(ig.posts || []).forEach(p => {
  const tr = document.createElement('tr');
  const reach = p.reach != null ? p.reach.toLocaleString() : '<span class="na">—</span>';
  const saves = p.saves != null ? p.saves.toLocaleString() : '<span class="na">—</span>';
  tr.innerHTML = `<td class="cap" title="${p.caption}">${p.caption || '<span class="na">no caption</span>'}</td><td><span class="pill ${typePill[p.type] || ''}">${typeLabel[p.type] || p.type}</span></td><td>${p.date}</td><td>${p.likes.toLocaleString()}</td><td>${p.comments.toLocaleString()}</td><td>${p.engagement}%</td><td>${reach}</td><td>${saves}</td>`;
  igTbody.appendChild(tr);
});

// TIKTOK
const tt = D.tiktok;
document.getElementById('tt-followers').textContent = (tt.followers || 0).toLocaleString();
document.getElementById('tt-views').textContent = (tt.avg_views || 0).toLocaleString();
document.getElementById('tt-videos').textContent = (tt.total_videos || 0).toLocaleString();
(tt.top_videos || []).forEach(v => {
  const tr = document.createElement('tr');
  tr.innerHTML = `<td class="cap">${v.caption}</td><td>${v.date}</td><td>${v.views.toLocaleString()}</td><td>${v.likes.toLocaleString()}</td><td>${v.comments.toLocaleString()}</td><td>${v.shares.toLocaleString()}</td>`;
  document.getElementById('tt-tbody').appendChild(tr);
});

// FACEBOOK
const fb = D.facebook;
if (fb.mock) document.getElementById('fb-mock-banner').innerHTML = '<div class="mock-banner">Facebook: add FACEBOOK_PAGE_ID to homerun/.env to connect live data</div>';
document.getElementById('fb-fans').textContent = (fb.fans || 0).toLocaleString();
document.getElementById('fb-post-count').textContent = (fb.posts || []).length.toLocaleString();
(fb.posts || []).forEach(p => {
  const tr = document.createElement('tr');
  tr.innerHTML = `<td class="cap">${p.caption || '<span class="na">no caption</span>'}</td><td>${p.date}</td><td>${p.likes.toLocaleString()}</td><td>${p.comments.toLocaleString()}</td>`;
  document.getElementById('fb-tbody').appendChild(tr);
});

// TRENDING INTEL
const tr_data = D.trends;
if (tr_data.mock) document.getElementById('trends-mock-banner').innerHTML = '<div class="mock-banner">Trending intel: mock data — Apify connection coming soon</div>';
const renderNewsList = (items, id, headlineKey) => {
  document.getElementById(id).innerHTML = items.map(item =>
    `<li class="news-item"><div class="news-item-body"><a class="news-title" href="${item.url || '#'}" target="_blank">${item[headlineKey]}</a><div class="news-meta">${item.source} · ${item.date}</div></div></li>`
  ).join('');
};
renderNewsList(tr_data.niche || [], 'trends-niche', 'headline');
renderNewsList(tr_data.adjacent || [], 'trends-adjacent', 'headline');
const platformNames = { instagram: 'Instagram', tiktok: 'TikTok', facebook: 'Facebook' };
document.getElementById('trends-by-platform').innerHTML = Object.entries(tr_data.by_platform || {}).map(([platform, items]) =>
  `<div><div style="font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px">${platformNames[platform] || platform}</div>` +
  items.map(item => `<div style="margin-bottom:12px"><div style="font-weight:600;font-size:13px">${item.format}: ${item.topic}</div><div style="font-size:12px;color:var(--muted);margin-top:2px">${item.why}</div></div>`).join('') +
  '</div>'
).join('');

// CONTENT IDEAS
const pillarColour = { 'Better Times Together': '#fce4d6', 'Better Value Together': '#e8f4f8', 'Better Standards Together': '#e8f0e8' };
document.getElementById('ideas-grid').innerHTML = (D.ideas || []).map(idea =>
  `<div class="idea-card"><div class="idea-platform">${(idea.platforms || []).map(p => `<span class="pill ${pillMap[p] || ''}">${p}</span>`).join('')}</div><div class="idea-pillar" style="background:${pillarColour[idea.pillar] || '#f5f5f5'};padding:2px 6px;border-radius:3px;display:inline-block;margin-bottom:8px">${idea.pillar}</div><div class="idea-hook">${idea.hook}</div><div class="idea-format">${idea.format}</div></div>`
).join('');

// PLATFORM NEWS
const pn = D.platform_news;
if (pn.mock) document.getElementById('pn-mock-banner').innerHTML = '<div class="mock-banner">Platform news: RSS feeds unreachable — showing fallback items</div>';
document.getElementById('pn-list').innerHTML = (pn.items || []).map(item =>
  `<li class="news-item"><div class="news-platforms">${(item.platforms || []).map(p => `<span class="pill ${pillMap[p] || ''}">${p}</span>`).join('')}</div><div class="news-item-body"><a class="news-title" href="${item.url || '#'}" target="_blank">${item.title}</a><div class="news-meta">${item.source} · ${item.date}</div></div></li>`
).join('');

// CALENDAR
const calEntries = D.calendar_entries || [];
const now = new Date();
const year = now.getFullYear(), month = now.getMonth();
const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
document.getElementById('cal-month-label').textContent = monthNames[month] + ' ' + year;
const daysInMonth = new Date(year, month + 1, 0).getDate();
const firstDay = new Date(year, month, 1).getDay();
const dayNames = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
let calHtml = dayNames.map(d => `<div class="cal-header">${d}</div>`).join('');
for (let i = 0; i < firstDay; i++) calHtml += '<div class="cal-day empty"></div>';
for (let d = 1; d <= daysInMonth; d++) {
  const isToday = d === now.getDate();
  const entries = calEntries.filter(e => parseInt(e.day) === d);
  calHtml += `<div class="cal-day${isToday ? ' today' : ''}"><div class="cal-num">${d}</div>${entries.map(e => `<div class="cal-entry">${e.platform ? e.platform + ': ' : ''}${e.label}</div>`).join('')}</div>`;
}
document.getElementById('cal-grid').innerHTML = calHtml;
</script>
</body>
</html>
```

- [ ] **Step 2: Open template.html in browser to verify structure**

```bash
open /Users/belindadodge/Desktop/Claude-Code/homerun-social/social-dashboard/template.html
```

Expected: page opens, 8 tabs visible in nav, tabs switch on click. JavaScript error in console is expected (`DATA is not defined`) because `__DATA__` is not yet replaced — that's correct at this stage.

- [ ] **Step 3: Commit**

```bash
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social add social-dashboard/template.html
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social commit -m "Add template.html — 8-tab dashboard shell with CSS and JS"
```

---

## Task 7: Create dashboard.py (orchestrator)

**Files:**
- Create: `social-dashboard/dashboard.py`
- Modify: `social-dashboard/.gitignore`

- [ ] **Step 1: Create dashboard.py**

```python
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

ENV_FILE = Path(__file__).parent.parent.parent / "homerun" / ".env"
TEMPLATE_FILE = Path(__file__).parent / "template.html"
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

    ig_id = env.get("INSTAGRAM_ACCOUNT_ID")
    fb_page_id = env.get("FACEBOOK_PAGE_ID")

    print("=== Homerun Social Dashboard ===")
    ig_data = fetch_instagram.fetch(token, ig_id)
    fb_data = fetch_facebook.fetch(token, fb_page_id)
    tt_data = fetch_tiktok.fetch()
    trends_data = fetch_trends.fetch()
    pn_data = fetch_platform_news.fetch()

    ideas = [
        {"platforms": ["instagram"], "pillar": "Better Times Together", "hook": "The hierarchy of sharehouse jobs — who actually does anything?", "format": "Carousel — tier list format"},
        {"platforms": ["instagram", "tiktok"], "pillar": "Better Value Together", "hook": "Loyalty tax is real and your energy company is counting on you not knowing", "format": "Reel — talking head with text overlay"},
        {"platforms": ["tiktok"], "pillar": "Better Times Together", "hook": "POV: you're the only one who ever buys toilet paper", "format": "Reel — POV talking head"},
        {"platforms": ["instagram"], "pillar": "Better Standards Together", "hook": "What the new NSW renters rights bill actually means for you", "format": "Carousel — explainer, 5 slides"},
        {"platforms": ["instagram", "tiktok"], "pillar": "Better Value Together", "hook": "We checked 3 electricity plans for a typical 4-person sharehouse — here's what we found", "format": "Reel — screen recording + voiceover"},
        {"platforms": ["facebook"], "pillar": "Better Standards Together", "hook": "New renters rights legislation — what changed and what didn't", "format": "Link post to news article"},
        {"platforms": ["instagram"], "pillar": "Better Times Together", "hook": "Signs your sharehouse is thriving (vs surviving)", "format": "Carousel — 6 slides, relatable format"},
        {"platforms": ["tiktok"], "pillar": "Better Value Together", "hook": "We found savings hiding in our sharehouse bills — here's how", "format": "Reel — screen recording"},
    ]

    calendar_entries = [
        {"day": "23", "platform": "IG", "label": "Reel — loyalty tax hook"},
        {"day": "24", "platform": "TT", "label": "POV: toilet paper"},
        {"day": "26", "platform": "IG", "label": "Carousel — renters rights"},
        {"day": "28", "platform": "IG", "label": "Post — sharehouse thriving"},
        {"day": "30", "platform": "TT", "label": "Reel — bills breakdown"},
    ]

    dashboard_data = {
        "today": datetime.date.today().isoformat(),
        "instagram": ig_data,
        "facebook": fb_data,
        "tiktok": tt_data,
        "trends": trends_data,
        "platform_news": pn_data,
        "ideas": ideas,
        "calendar_entries": calendar_entries,
    }

    template = TEMPLATE_FILE.read_text()
    html = template.replace("__DATA__", json.dumps(dashboard_data))
    OUTPUT_FILE.write_text(html)
    print(f"\nDashboard saved → {OUTPUT_FILE.name}")
    webbrowser.open(f"file://{OUTPUT_FILE.absolute()}")
    print("Opened in browser.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Update .gitignore**

Open `social-dashboard/.gitignore` and ensure it contains:
```
dashboard.html
__pycache__/
*.pyc
```

- [ ] **Step 3: Run the dashboard end-to-end**

```bash
cd /Users/belindadodge/Desktop/Claude-Code/homerun-social/social-dashboard
python3 dashboard.py
```

Expected console output:
```
=== Homerun Social Dashboard ===
[instagram] Using hardcoded account ID: ...
[instagram] Fetching profile...
[instagram] @homerun.au — 169 followers
...
[facebook] No FACEBOOK_PAGE_ID in .env — using mock data
[platform_news] Fetching RSS feeds...
  Social Media Today: N relevant items
Dashboard saved → dashboard.html
Opened in browser.
```

Browser opens showing the 8-tab dashboard. Instagram tab shows real data (followers, charts, post table). All other tabs visible with mock banners where applicable.

- [ ] **Step 4: Commit**

```bash
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social add social-dashboard/dashboard.py social-dashboard/.gitignore
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social commit -m "Add dashboard.py — orchestrator generating 8-tab dashboard.html"
```

---

## Task 8: Set up GitHub Pages publishing

**Files:**
- Create: `publish.sh` (repo root)

- [ ] **Step 1: Create the gh-pages branch (one-time)**

```bash
cd /Users/belindadodge/Desktop/Claude-Code/homerun-social
git checkout --orphan gh-pages
git rm -rf .
printf '<html><body><script>window.location="dashboard.html"</script></body></html>' > index.html
git add index.html
git commit -m "Init gh-pages branch"
git push origin gh-pages
git checkout main
```

- [ ] **Step 2: Enable GitHub Pages in repo settings**

Open: https://github.com/belhomerun/homerun-social/settings/pages

Set:
- Source: **Deploy from a branch**
- Branch: **gh-pages** / **/ (root)**
- Click Save

GitHub will show: *"Your site is published at https://belhomerun.github.io/homerun-social/"*

- [ ] **Step 3: Create publish.sh**

```bash
#!/bin/bash
# Usage: bash publish.sh
# Run python3 social-dashboard/dashboard.py first, then this script.
set -e
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
DASHBOARD="$REPO_ROOT/social-dashboard/dashboard.html"

if [ ! -f "$DASHBOARD" ]; then
  echo "Error: dashboard.html not found. Run: python3 social-dashboard/dashboard.py"
  exit 1
fi

echo "Stashing any uncommitted changes..."
git -C "$REPO_ROOT" stash

echo "Switching to gh-pages..."
git -C "$REPO_ROOT" checkout gh-pages

echo "Copying dashboard.html..."
cp "$DASHBOARD" "$REPO_ROOT/dashboard.html"
git -C "$REPO_ROOT" add dashboard.html
git -C "$REPO_ROOT" commit -m "Update dashboard $(date +%Y-%m-%d)"
git -C "$REPO_ROOT" push origin gh-pages

echo "Switching back to main..."
git -C "$REPO_ROOT" checkout main
git -C "$REPO_ROOT" stash pop 2>/dev/null || true
echo ""
echo "Published! https://belhomerun.github.io/homerun-social/dashboard.html"
```

- [ ] **Step 4: Make executable and commit**

```bash
chmod +x /Users/belindadodge/Desktop/Claude-Code/homerun-social/publish.sh
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social add publish.sh
git -C /Users/belindadodge/Desktop/Claude-Code/homerun-social commit -m "Add publish.sh — pushes dashboard.html to GitHub Pages"
```

- [ ] **Step 5: Test publish end-to-end**

```bash
cd /Users/belindadodge/Desktop/Claude-Code/homerun-social/social-dashboard && python3 dashboard.py
cd .. && bash publish.sh
```

Expected: script copies, commits, pushes to gh-pages, returns to main. After ~60 seconds open https://belhomerun.github.io/homerun-social/dashboard.html — dashboard visible in browser.

---

## Bel's workflow going forward

1. `cd /Users/belindadodge/Desktop/Claude-Code/homerun-social/social-dashboard && python3 dashboard.py` — refresh data, opens locally
2. Check it looks right
3. `cd .. && bash publish.sh` — push to GitHub Pages

Team URL: **https://belhomerun.github.io/homerun-social/dashboard.html**
