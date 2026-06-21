#!/usr/bin/env python3
"""
Platform news fetcher — RSS feeds filtered for IG/TikTok/FB news.
Uses stdlib only (urllib + xml.etree).
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

FEEDS = [
    {"name": "Hootsuite Blog",        "url": "https://blog.hootsuite.com/feed/"},
    {"name": "Buffer Blog",           "url": "https://buffer.com/resources/feed/"},
    {"name": "Sprout Social",         "url": "https://sproutsocial.com/insights/feed/"},
    {"name": "Social Media Examiner", "url": "https://www.socialmediaexaminer.com/feed/"},
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
