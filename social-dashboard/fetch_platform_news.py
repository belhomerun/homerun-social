#!/usr/bin/env python3
"""
Platform news fetcher — RSS feeds filtered for IG/TikTok/FB news.
Returns a digest with themes + actionable steps. Uses stdlib only.
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import re

FEEDS = [
    {"name": "Hootsuite Blog",        "url": "https://blog.hootsuite.com/feed/"},
    {"name": "Buffer Blog",           "url": "https://buffer.com/resources/feed/"},
    {"name": "Sprout Social",         "url": "https://sproutsocial.com/insights/feed/"},
    {"name": "Social Media Examiner", "url": "https://www.socialmediaexaminer.com/feed/"},
]

PLATFORM_KEYWORDS = {
    "instagram": ["instagram", "reels", "ig "],
    "tiktok":    ["tiktok", "tik tok"],
    "facebook":  ["facebook", "meta ", "fb "],
}

THEMES = [
    ("algorithm changes",  ["algorithm", "ranking", "signal", "feed change"]),
    ("short-form video",   ["reels", "short-form", "shorts", "video feature"]),
    ("paid ads",           ["ads", "advertising", "promoted", "sponsored", "paid social"]),
    ("reach & engagement", ["reach", "engagement", "impressions", "organic"]),
    ("creator tools",      ["creator studio", "creator tool", "new feature", "rollout", "update"]),
    ("scheduling",         ["schedule", "best time", "posting time", "frequency"]),
    ("stories",            ["stories", "story feature"]),
    ("analytics",          ["analytics", "insights", "metrics"]),
]

ACTIONS = {
    "algorithm changes":  "Review your content mix and posting cadence — algorithm changes may affect reach.",
    "short-form video":   "Prioritise Reels this week — platforms are pushing short-form video.",
    "paid ads":           "Check any boosted posts — platform ad changes may affect performance.",
    "reach & engagement": "Test a new format or posting time — organic reach patterns are shifting.",
    "creator tools":      "Check Creator Studio for new tools or features worth using.",
    "scheduling":         "Review your posting schedule against updated best-time guidance.",
    "stories":            "Consider a Stories push this week — Stories updates are trending.",
    "analytics":          "Refresh your insights — analytics reporting may have changed.",
}


def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:160] + '…' if len(text) > 160 else text


def detect_platforms(text):
    text_lower = text.lower()
    return [p for p, kws in PLATFORM_KEYWORDS.items() if any(kw in text_lower for kw in kws)]


def detect_themes(items):
    combined = ' '.join(
        (i.get('title', '') + ' ' + i.get('excerpt', '')).lower()
        for i in items
    )
    found = []
    for theme, kws in THEMES:
        if any(kw in combined for kw in kws):
            found.append(theme)
    return found[:5]


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
            if not platforms:
                continue
            desc_raw = item.findtext("description") or ""
            items.append({
                "title":     title,
                "excerpt":   strip_html(desc_raw),
                "source":    feed["name"],
                "date":      (item.findtext("pubDate") or "")[:16],
                "url":       (item.findtext("link") or "").strip(),
                "platforms": platforms,
            })
        return items
    except Exception as e:
        print(f"  [platform_news] Failed to fetch {feed['name']}: {e}")
        return []


def fetch():
    print("[platform_news] Fetching RSS feeds...")
    all_items = []
    source_count = 0
    for feed in FEEDS:
        items = fetch_feed(feed)
        if items:
            source_count += 1
        print(f"  {feed['name']}: {len(items)} relevant items")
        all_items.extend(items)

    if not all_items:
        print("[platform_news] No items fetched — using mock fallback")
        return {
            "mock": True,
            "article_count": 3,
            "source_count": 1,
            "themes": ["algorithm changes", "short-form video"],
            "actions": [
                {"theme": "algorithm changes",  "action": ACTIONS["algorithm changes"]},
                {"theme": "short-form video",   "action": ACTIONS["short-form video"]},
            ],
            "by_platform": {
                "instagram": [{"title": "Instagram announces new Reels editing tools", "excerpt": "New tools make it easier to trim, add text, and schedule Reels directly in the app.", "source": "Social Media Today", "date": "2026-06-20", "url": "#"}],
                "tiktok":    [{"title": "TikTok's algorithm change: what creators need to know", "excerpt": "The For You page is now weighing watch-time over follows — short punchy hooks matter more.", "source": "Later Blog", "date": "2026-06-19", "url": "#"}],
                "facebook":  [{"title": "Facebook Pages reach declining — here's what still works", "excerpt": "Video and group-based content continues to outperform static posts for organic reach.", "source": "Hootsuite Blog", "date": "2026-06-18", "url": "#"}],
            },
            "items": [],
        }

    themes = detect_themes(all_items)
    actions = [{"theme": t, "action": ACTIONS[t]} for t in themes if t in ACTIONS]

    by_platform = {"instagram": [], "tiktok": [], "facebook": []}
    for item in all_items:
        for p in item["platforms"]:
            if p in by_platform:
                entry = {k: v for k, v in item.items() if k != "platforms"}
                by_platform[p].append(entry)

    return {
        "mock":          False,
        "article_count": len(all_items),
        "source_count":  source_count,
        "themes":        themes,
        "actions":       actions,
        "by_platform":   by_platform,
        "items":         all_items,
    }
