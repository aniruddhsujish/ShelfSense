import httpx
import asyncio

BASE_URL = "https://openlibrary.org"
RATE_LIMIT_DELAY = 0.1  # 100ms delay between requests


def is_excerpt(description: str, title: str, authors: str) -> bool:
    desc_lower = description.lower()

    meta_keywords = [
        "novel",
        "book",
        "story",
        "author",
        "written",
        "published",
        "tells",
        "follows",
        "centers",
        "explores",
        "portrays",
        "depicts",
        "chronicles",
        "narrates",
        "set in",
        "takes place",
    ]

    # first two meaningful words of the title
    title_words = [w for w in title.lower().split() if len(w) > 3][:2]

    # last name of first author
    first_author = authors.split(",")[0].strip()
    author_last = first_author.split()[-1].lower() if first_author else ""

    has_meta = any(kw in desc_lower for kw in meta_keywords)
    has_title = any(w in desc_lower for w in title_words)
    has_author = author_last and author_last in desc_lower

    return not (has_meta or has_title or has_author)


async def fetch_description_from_ol(isbn: str, title: str, authors: str) -> str | None:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        # Step 1: resolve ISBN to a work ID
        edition_resp = await client.get(f"{BASE_URL}/isbn/{isbn}.json")
        if edition_resp.status_code != 200:
            print(
                f"Failed to fetch edition for ISBN {isbn}: {edition_resp.status_code}"
            )
            return None

        edition = edition_resp.json()
        works = edition.get("works", [])
        if not works:
            print(f"No works found for ISBN {isbn}")
            return None

        work_key = works[0]["key"]  # e.g. "/works/OL12345W"
        await asyncio.sleep(RATE_LIMIT_DELAY)  # rate limit

        # Step 2: fetch the work to get desctiption
        work_resp = await client.get(f"{BASE_URL}{work_key}.json")
        if work_resp.status_code != 200:
            print(
                f"Failed to fetch work {work_key} for ISBN {isbn}: {work_resp.status_code}"
            )
            return None

        work = work_resp.json()
        description = work.get("description")

        if not description:
            print(f"No description found for work {work_key} (ISBN {isbn})")
            return None

        if isinstance(description, dict):
            description = description.get("value", "").strip() or None
            if not description:
                return None

        if is_excerpt(description, title, authors):
            return None

        return description.strip() or None
