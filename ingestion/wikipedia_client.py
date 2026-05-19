import httpx
import asyncio

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary"
RATE_LIMIT_DELAY = 0.1  # 100ms delay between requests


async def fetch_description_from_wikipedia(title: str, author: str) -> str | None:
    # Try "Title (novel)" frst, then plain title, then "Title by Author"
    queries = [
        f"{title} (novel)",
        title,
        f"{title} by ({author.split(',')[0].strip()}) novel",
    ]

    headers = {
        "User-Agent": "ShelfSense/1.0 (book recommendation app; contact@example.com)"
    }

    async with httpx.AsyncClient(
        timeout=20, follow_redirects=True, headers=headers
    ) as client:
        for query in queries:
            url = f"{WIKI_API}/{query.replace(' ','_')}"
            resp = await client.get(url)
            await asyncio.sleep(RATE_LIMIT_DELAY)  # rate limit

            if resp.status_code == 429:
                await asyncio.sleep(2)
                resp = await client.get(url)

            if resp.status_code != 200:
                print(
                    f"Wikipedia: No page found for '{query}' (status {resp.status_code})"
                )
                continue

            data = resp.json()

            # skip disambiguation pages
            if data.get("type") == "disambiguation":
                print(f"Wikipedia: '{query}' is a disambiguation page, skipping")
                continue

            extract = data.get("extract", "").strip()

            if extract:
                return extract

    return None
