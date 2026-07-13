"""
Runs on GitHub Actions every 2 days.
Fetches immigration news from multiple trusted government sources.
Saves to data/uscis_news.json for the Streamlit app to read.
"""

import feedparser
import requests
import json
import os
import re
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

# Trusted government RSS feeds covering immigration.
# Verified working July 2026 — the old /rss/uscis-news.xml, dhs.gov/rss.xml,
# and whitehouse.gov/feed/ paths all return 404 now.
RSS_SOURCES = [
    {
        "url": "https://www.uscis.gov/rss.xml",
        "source": "USCIS"
    },
    {
        "url": "https://www.whitehouse.gov/news/feed/",
        "source": "White House"
    },
    {
        "url": "https://www.whitehouse.gov/presidential-actions/feed/",
        "source": "White House"
    },
    {
        "url": "https://www.state.gov/rss-feed/press-releases/feed/",
        "source": "State Department"
    },
]

# Federal Register API — immigration-related rules and notices
FEDERAL_REGISTER_URL = "https://www.federalregister.gov/api/v1/documents.json"
FEDERAL_REGISTER_PARAMS = {
    "per_page": 25,
    "order": "newest",
    "conditions[agencies][]": [
        "homeland-security-department",
        "u-s-citizenship-and-immigration-services",
        "executive-office-for-immigration-review",
        "state-department",
        "labor-department",
    ],
    "conditions[type][]": ["RULE", "PRORULE", "NOTICE", "PRESDOCU"],
}

IMMIGRATION_KEYWORDS = [
    "visa", "immigration", "immigrant", "h-1b", "h1b", "green card",
    "citizenship", "naturalization", "asylum", "refugee", "border",
    "deportation", "removal", "uscis", "passport", "travel ban",
    "executive order", "nonimmigrant", "adjustment of status",
    "parole", "daca", "tps", "i-130", "i-485", "f-1", "opt", "stem",
    "work permit", "ead", "petition", "priority date", "visa bulletin",
    "foreign national", "lawful permanent"
]

# Topics that are definitively NOT immigration news — skip regardless of summary
EXCLUDE_KEYWORDS = [
    "fifa", "world cup", "soccer", "football", "olympics", "fema",
    "hurricane", "tornado", "flood", "wildfire", "earthquake", "disaster",
    "cybersecurity", "cisa", "ransomware", "cyber attack", "data breach",
    "secret service", "tsa checkpoint", "airport security screening",
    "drug trafficking", "fentanyl", "human trafficking awareness"
]

def _matches_whole_word(keyword, text):
    # Word-boundary match so "stem" doesn't hit "Systems" or "visa" hit "visable"
    return re.search(r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])", text) is not None


def is_immigration_related(title, summary=""):
    title_lower = title.lower()
    # Hard exclude non-immigration topics based on title alone
    if any(_matches_whole_word(kw, title_lower) for kw in EXCLUDE_KEYWORDS):
        return False
    # Keyword must appear in the TITLE for non-USCIS sources (not just in body text)
    return any(_matches_whole_word(kw, title_lower) for kw in IMMIGRATION_KEYWORDS)

def is_recent(entry, max_age_days=120):
    """Some government feeds contain entries going back a decade."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return True  # no date — keep, better than dropping fresh items
    entry_date = datetime(*parsed[:6], tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - entry_date).days <= max_age_days


def fetch_rss_sources():
    items = []
    seen = set()

    for source in RSS_SOURCES:
        url = source["url"]
        name = source["source"]
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            count = 0
            for entry in feed.entries:
                link = entry.get("link", "")
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()

                if link in seen:
                    continue
                if not title or len(title.split()) < 2:
                    continue
                if not is_recent(entry):
                    continue
                # For non-USCIS sources, filter to immigration-related only
                if name != "USCIS" and not is_immigration_related(title, summary):
                    continue

                seen.add(link)
                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary[:600],
                    "published": entry.get("published", ""),
                    "source": name,
                })
                count += 1
                if count >= 6:
                    break

            print(f"{name}: fetched {count} relevant items from {url}")

        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    return items

def fetch_federal_register():
    items = []
    try:
        resp = requests.get(
            FEDERAL_REGISTER_URL,
            params=FEDERAL_REGISTER_PARAMS,
            headers=HEADERS,
            timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        for doc in data.get("results", []):
            title = doc.get("title", "").strip()
            # DHS includes the Coast Guard — drop "Safety Zone" style notices
            # by requiring an immigration keyword in the title
            if not is_immigration_related(title):
                continue
            items.append({
                "title": title,
                "link": doc.get("html_url", ""),
                "summary": (doc.get("abstract") or "")[:600],
                "published": doc.get("publication_date", ""),
                "source": "Federal Register",
                "doc_type": doc.get("type", ""),
            })
        print(f"Federal Register: fetched {len(items)} items")
    except Exception as e:
        print(f"Federal Register fetch failed: {e}")
    return items

def main():
    os.makedirs("data", exist_ok=True)

    rss_items = fetch_rss_sources()
    fr_items = fetch_federal_register()

    # Combine, deduplicate by title
    all_items = rss_items + fr_items
    seen_titles = set()
    unique_items = []
    for item in all_items:
        t = item["title"].lower()
        if t not in seen_titles:
            seen_titles.add(t)
            unique_items.append(item)

    # Keep 20 most recent
    final_items = unique_items[:20]

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(final_items),
        "sources": ["USCIS.gov", "DHS.gov", "WhiteHouse.gov", "State Department", "Federal Register"],
        "items": final_items,
    }

    with open("data/uscis_news.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone — saved {len(final_items)} items to data/uscis_news.json")

if __name__ == "__main__":
    main()
