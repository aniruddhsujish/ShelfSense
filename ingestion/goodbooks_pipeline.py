import asyncio
import csv
import json
import os
from pathlib import Path
from dotenv import load_dotenv

from ingestion.open_library_client import fetch_description_from_ol
from ingestion.wikipedia_client import fetch_description_from_wikipedia
from ingestion.google_books_client import fetch_book_by_isbn

load_dotenv()

GOODBOOKS_CSV = "goodbooks.csv"
OUTPUT_FILE = "all_books.json"
CHECKPOINT_FILE = "goodbooks_checkpoint.json"


def load_checkpoint() -> set:
    if Path(CHECKPOINT_FILE).exists():
        with open(CHECKPOINT_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_checkpoint(seen_isbns: set):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(seen_isbns), f)


def load_output() -> list[dict]:
    if not Path(OUTPUT_FILE).exists():
        return []
    books = []
    with open(OUTPUT_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                books.append(json.loads(line))
    return books


def append_book(book: dict):
    with open(OUTPUT_FILE, "a") as f:
        f.write(json.dumps(book) + "\n")


def parse_isbn(raw: str) -> str | None:
    try:
        return f"{int(float(raw)):010d}"
    except (ValueError, TypeError):
        return None


async def fetch_description(
    isbn: str, title: str, authors: str, api_key: str
) -> tuple[str, str, str | None]:
    # 1. Open Library
    desc = await fetch_description_from_ol(isbn, title, authors)
    if desc:
        return desc, "open_library", None

    # 2. Wikipedia
    desc = await fetch_description_from_wikipedia(title, authors)
    if desc:
        return desc, "wikipedia", None

    # 3. Google Books (last resort since often truncated and not great for embeddings)
    book = await fetch_book_by_isbn(isbn, api_key)
    if book and book.description:
        return book.description, "google_books", book.id

    return None, None, None


async def process_row(row, i, total, seen_isbns, in_flight, api_key, sem):
    async with sem:
        isbn = parse_isbn(row["isbn"])
        if not isbn or isbn in seen_isbns or isbn in in_flight:
            return

        in_flight.add(isbn)
        title = row["original_title"] or row["title"]
        authors = row["authors"]

        try:
            desc, source, gb_id = await fetch_description(isbn, title, authors, api_key)
        except Exception as e:
            print(f"[{i+1}/{total}] ERROR: {title} - {e}")
            in_flight.discard(isbn)
            return

        if not desc:
            print(f"[{i+1}/{total}] SKIP: {title}")
            in_flight.discard(isbn)
            return

        book = {
            "id": gb_id if source == "google_books" else f"ol:{isbn}",
            "isbn": isbn,
            "title": title,
            "authors": [a.strip() for a in authors.split(",")],
            "description": desc,
            "categories": [],
            "published_date": (
                str(int(float(row["original_publication_year"])))
                if row["original_publication_year"]
                else ""
            ),
            "average_rating": float(row["average_rating"] or 0),
            "ratings_count": int(float(row["ratings_count"] or 0)),
            "page_count": 0,
            "thumbnail": row["image_url"],
            "source": source,
        }

        append_book(book)
        seen_isbns.add(isbn)
        in_flight.discard(isbn)
        save_checkpoint(seen_isbns)
        print(f"[{i+1}/{total}] {source.upper()}: {title}")


async def run_pipeline(limit: int = None):
    # Convert JSON array to JSONL if needed (one-time migration)
    if Path(OUTPUT_FILE).exists():
        with open(OUTPUT_FILE) as f:
            content = f.read().strip()
        if content.startswith("["):
            books = json.loads(content)
            with open(OUTPUT_FILE, "w") as f:
                for book in books:
                    f.write(json.dumps(book) + "\n")
            print(f"Converted {len(books)} books from JSON array to JSONL")

    api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
    seen_isbns = load_checkpoint()

    with open(GOODBOOKS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} books from GoodBooks-10k dataset")
    print(f"Resuming from checkpoint: {len(seen_isbns)} already processed")

    sem = asyncio.Semaphore(10)
    in_flight = set()
    tasks = [
        process_row(row, i, len(rows), seen_isbns, in_flight, api_key, sem)
        for i, row in enumerate(rows[:limit] if limit else rows)
    ]
    await asyncio.gather(*tasks)
    print(f"Pipeline complete.")
