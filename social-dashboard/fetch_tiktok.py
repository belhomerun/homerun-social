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
