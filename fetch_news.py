"""
Runs on GitHub Actions every 2 days.
Fetches immigration news from multiple trusted government sources.
Saves to data/uscis_news.json for the Streamlit app to read.
"""

import feedparser
import requests
import json
import os
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ImmigrationCoPilot/1.0; "
        "+https://github.com/sainakakkar2006/immigration-copilot)"
    )
}

# Trusted government RSS feeds covering immigration
RSS_SOURCES = [
    {
        "url": "https://www.uscis.gov/rss/uscis-news.xml",
        "source": "USCIS"
    },
    {
        "url": "https://www.uscis.gov/rss/uscis-alerts.xml",
        "source": "USCIS"
    },
    {
        "url": "https://www.dhs.gov/rss.xml",
        "source": "DHS"
    },
    {
        "url": "https://www.whitehouse.gov/feed/",
        "source": "White House"
    },
    {
        "url": "https://travel.state.gov/content/travel/en/RSS.xml",
        "source": "State Department"
    },
]

# Federal Register API — immigration-related rules and notices
FEDERAL_REGISTER_URL = "https://www.federalregister.gov/api/v1/documents.json"
FEDERAL_REGISTER_PARAMS = {
    "per_page": 8,
    "order": "newest",
    "conditions[agencies][]": [
        "department-of-homeland-security",
        "executive-office-for-immigration-review",
        "department-of-state",
        "department-of-labor",
    ],
    "conditions[type][]": ["Rule", "Proposed Rule", "Notice", "Presidential Document"],
}

IMMIGRATION_KEYWORDS = [
    "visa", "immigration", "immigrant", "h-1b", "h1b", "green card",
    "citizenship", "naturalization", "asylum", "refugee", "border",
    "deportation", "removal", "uscis", "dhs", "passport", "travel ban",
    "executive order", "alien", "nonimmigrant", "adjustment of status",
    "parole", "daca", "tps", "i-130", "i-485", "f-1", "opt", "stem"
]

def is_immigration_related(title, summary=""):
    text = (title + " " + summary).lower()
    return any(kw in text for kw in IMMIGRATION_KEYWORDS)

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
                if not title:
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
            items.append({
                "title": doc.get("title", "").strip(),
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
