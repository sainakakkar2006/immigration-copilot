"""
Runs on GitHub Actions every 2 days.
Fetches USCIS news RSS and saves to data/uscis_news.json.
GitHub's servers can reach USCIS.gov — Streamlit Cloud cannot.
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

RSS_FEEDS = [
    "https://www.uscis.gov/rss/uscis-news.xml",
    "https://www.uscis.gov/rss/uscis-alerts.xml",
]

def fetch_all():
    items = []
    seen = set()

    for url in RSS_FEEDS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            print(f"Fetched {len(feed.entries)} entries from {url}")

            for entry in feed.entries:
                link = entry.get("link", "")
                if link in seen:
                    continue
                seen.add(link)

                items.append({
                    "title": entry.get("title", "").strip(),
                    "link": link,
                    "summary": entry.get("summary", "").strip()[:600],
                    "published": entry.get("published", ""),
                })

        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    return items[:15]  # Keep the 15 most recent


def main():
    os.makedirs("data", exist_ok=True)

    items = fetch_all()

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }

    with open("data/uscis_news.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved {len(items)} items to data/uscis_news.json")


if __name__ == "__main__":
    main()
