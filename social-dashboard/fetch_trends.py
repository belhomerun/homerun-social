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
