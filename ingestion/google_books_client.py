import httpx
import asyncio
from dataclasses import dataclass

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
MAX_RESULTS_PER_REQUEST = 40
MAX_503_RETRIES = 20


@dataclass
class Book:
    id: str
    title: str
    authors: list[str]
    description: str
    categories: list[str]
    published_date: str
    average_rating: float
    ratings_count: int
    page_count: int
    thumbnail: str


def parse_book(item: dict) -> Book | None:
    info = item.get("volumeInfo", {})

    # skip books without descriptions - useless for embeddings
    description = info.get("description", "").strip()
    if not description:
        return None

    return Book(
        id=item.get("id", ""),
        title=info.get("title", "Unknown"),
        authors=info.get("authors", []),
        description=description,
        categories=info.get("categories", []),
        published_date=info.get("publishedDate", ""),
        average_rating=info.get("averageRating", 0),
        ratings_count=info.get("ratingsCount", 0),
        page_count=info.get("pageCount", 0),
        thumbnail=info.get("imageLinks", {}).get("thumbnail", ""),
    )


class QuotaExceededException(Exception):
    pass


async def fetch_books(
    query: str,
    api_key: str,
    start_index: int = 0,
    retries: int = 5,
) -> tuple[list[Book], int]:
    params = {
        "q": query,
        "key": api_key,
        "maxResults": MAX_RESULTS_PER_REQUEST,
        "startIndex": start_index,
        "printType": "books",
        "langRestrict": "en",
    }

    for attempt in range(retries):
        consecutive_503s = 0
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(GOOGLE_BOOKS_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                raw_count = len(items)
                books = [parse_book(item) for item in items]
                return [b for b in books if b is not None], raw_count
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise QuotaExceededException("Daily API quota exceeded.")
            if e.response.status_code == 503:
                consecutive_503s += 1
                if consecutive_503s >= MAX_503_RETRIES:
                    print(
                        f"503 persisting after {MAX_503_RETRIES} retries, giving up on this page"
                    )
                    return []
                wait = min(2**consecutive_503s, 60)
                print(
                    f"503 error, retrying in {wait}s... ({consecutive_503s}/{MAX_503_RETRIES})"
                )
                await asyncio.sleep(wait)
                continue
            if attempt == retries - 1:
                raise
            wait = 2**attempt
            print(f"Request failed ({e.response.status_code}), retrying in {wait}s...")
            await asyncio.sleep(wait)

    return []


async def fetch_book_by_isbn(isbn: str, api_key: str) -> Book | None:
    params = {
        "q": f"isbn:{isbn}",
        "key": api_key,
        "maxResults": 1,
        "printType": "books",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(GOOGLE_BOOKS_URL, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch book for ISBN {isbn}: {response.status_code}")
            return None

        items = response.json().get("items", [])
        if not items:
            print(f"No book found for ISBN {isbn}")
            return None

        return parse_book(items[0])
