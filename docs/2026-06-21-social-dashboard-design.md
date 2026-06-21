# Social Media Analytics Dashboard — Design Spec
**Date:** 21 June 2026  
**Author:** Bel Dodge  
**Repo:** belhomerun/homerun-social  

---

## Goal

Expand the existing local Instagram analytics dashboard into a full-blown social media intelligence tool. Bel runs it locally, it generates a single HTML file, and that file is published to GitHub Pages so the team can view it at a URL without installing anything.

---

## What it does

- Shows performance analytics for all three Homerun social accounts (Instagram, TikTok, Facebook)
- Pulls trending news and content from the sharehouse/renting niche and adjacent niches
- Surfaces what content formats and topics are working, platform by platform
- Suggests specific content ideas based on what's trending
- Shows platform algorithm updates and feature news
- Displays a content calendar (placeholder for now, Notion connection later)

---

## Architecture

Multi-module Python app. Each platform or data source is its own file. One orchestrator script runs everything and writes a single `dashboard.html`.

```
homerun-social/
  social-dashboard/
    dashboard.py              ← orchestrator: runs all fetchers, renders HTML
    fetch_instagram.py        ← existing script (refactored into module)
    fetch_facebook.py         ← new: Page insights via existing Meta token
    fetch_tiktok.py           ← new: mock data now, TikTok API later
    fetch_trends.py           ← new: niche news + trending content (mock now, Apify later)
    fetch_platform_news.py    ← new: algorithm/feature updates via free RSS feeds
    template.html             ← HTML shell with tabs, no data baked in
    growth_history.json       ← existing: daily follower snapshots, keep as-is
    dashboard.html            ← generated output (gitignored on main; published via gh-pages branch)
    .gitignore                ← covers .env, __pycache__, dashboard.html
```

**Dependencies:** Python 3 stdlib + `requests` only. No Flask, no npm, no database.

**Credentials:** all in `homerun/.env` (never committed). Team members view the published URL — they never run the script.

---

## Tabs

### 1. Overview
Cross-platform snapshot at a glance.
- Follower counts for Instagram, TikTok, Facebook
- Engagement rate per platform (last 30 days)
- Top performing post from each platform (thumbnail + metric)
- Follower growth sparklines

### 2. Instagram
Current dashboard functionality, moved into this tab.
- Followers, avg engagement rate, total posts
- Follower growth chart
- Content type breakdown (photos/reels/carousels)
- Engagement rate bar chart
- Post performance table (reach, saves, engagement)

### 3. TikTok
Mock data on day one. Real TikTok API wired in later.
- Followers, avg views, total videos
- View trend chart
- Content type breakdown
- Top videos table

### 4. Facebook
Live on day one — same Meta Graph API token already in `.env`.
- Page likes/followers
- Post reach and engagement
- Top posts table

### 5. Trending Intel
What's happening in the sharehouse, renting, and adjacent niches.
- Niche news feed (sharehouse, renting, cost of living, utility bills, young Australians)
- Adjacent niche feed (personal finance, property, housing policy)
- Platform-specific breakdown: what formats/topics are getting traction on IG vs TikTok
- Mock data on day one; Apify scrapers wired in later

### 6. Content Ideas
Generated suggestions based on trending intel. Platform-specific.
- Ideas tagged by platform (IG, TikTok, Facebook) and content pillar (Better Times Together / Better Value Together / Better Standards Together)
- Each idea shows: hook, format, persona it maps to
- Static/hardcoded suggestions on day one; Claude API connected later for live generation

### 7. Platform News
Algorithm updates, new features, best practices. Live on day one via free RSS.
- Sources: Social Media Today, Later Blog, Hootsuite Blog, The Verge (social section)
- Filtered to Instagram, TikTok, Facebook news only
- Displays: headline, source, date, link

### 8. Content Calendar
Placeholder grid on day one. Notion pull added later once workflow is confirmed.
- Monthly calendar view (current month)
- Hardcoded placeholder entries showing the intended layout
- Each entry: date, platform, content type, status (draft / scheduled / live)

---

## Data sources — day one vs later

| Module | Day 1 | Later |
|---|---|---|
| Instagram | Live (Meta Graph API, existing token) | — |
| Facebook | Live (same Meta token) | — |
| TikTok | Mock data | TikTok for Developers API |
| Trending Intel | Mock data | Apify scrapers |
| Content Ideas | Static hardcoded suggestions | Claude API |
| Platform News | Live (free RSS feeds) | — |
| Content Calendar | Hardcoded placeholder | Notion API |

---

## Publishing (GitHub Pages)

- `dashboard.html` is committed to a `gh-pages` branch (not main)
- Main branch contains the Python source only — no generated output
- Bel's workflow: run `dashboard.py` → commit output to `gh-pages` → push → team URL updates
- URL: `https://belhomerun.github.io/homerun-social/`
- Repo is public so GitHub Pages works on the free plan

---

## Credentials needed (all in homerun/.env)

| Variable | Used for | Status |
|---|---|---|
| `INSTAGRAM_ACCESS_TOKEN` | Instagram + Facebook via Meta Graph API | Existing |
| `INSTAGRAM_ACCOUNT_ID` | Instagram account lookup | Existing |
| `FACEBOOK_PAGE_ID` | Facebook Page insights | To add |
| `TIKTOK_ACCESS_TOKEN` | TikTok API | Later |
| `APIFY_API_KEY` | Trending intel scraping | Later |

---

## Out of scope (not building now)

- Interactive filters or drill-downs (static HTML only)
- User login or authentication
- Scheduled auto-refresh (Bel runs manually)
- Notion calendar connection
- TikTok API connection
- Apify integration
- Claude API for content idea generation
