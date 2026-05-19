from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from vectordb.client import COLLECTION_NAME


def get_book_by_title(title: str, client: QdrantClient) -> dict | None:
    results = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="title", match=MatchValue(value=title))]
        ),
        limit=1,
        with_vectors=True,
    )

    points = results[0]
    if not points:
        return None

    point = points[0]
    return {
        **point.payload,
        "vector": point.vector,
    }


def find_similar_books(
    query_vector: list[float],
    client: QdrantClient,
    exclude_title: str = None,
    limit: int = 5,
) -> list[dict]:
    results = client.query_points(
        collection_name=COLLECTION_NAME, query=query_vector, limit=limit + 10
    ).points

    books = []
    for result in results:
        payload = result.payload
        if exclude_title and exclude_title.lower() in payload["title"].lower():
            continue
        if result.score >= 0.4:
            books.append({**payload, "score": result.score})

    return books[:limit]


async def get_or_fetch_books(
    title: str, model: SentenceTransformer, client: QdrantClient, api_key: str
) -> dict | None:
    # 1. Exact title match
    book = get_book_by_title(title, client)
    if book:
        print(f"Found '{title}' in Qdrant")
        return book

    # 2. Semantic match - embed query and find closest title
    query_vector = model.encode(title).tolist()
    candidates = client.query_points(
        collection_name=COLLECTION_NAME, query=query_vector, limit=5
    ).points

    query_words = set(title.lower().split())
    for candidate in candidates:
        stored_title = candidate.payload.get("title", "").lower()
        word_overlap = sum(1 for w in query_words if w in stored_title)
        if word_overlap / len(query_words) >= 0.6 and candidate.score > 0.7:
            print(
                f"Found '{title}' in Qdrant (semantic -> '{candidate.payload['title']})"
            )
            return {**candidate.payload, "vector": candidate.vector}

    # 3. Fall back to Google Books
    print(f"'{title}' not in Qdrant, fetching from Google Books...")
    from ingestion.google_books_client import fetch_books

    books, _ = await fetch_books(query=f"intitle:{title}", api_key=api_key)
    if not books:
        return None

    # take the closest title match
    book_data = books[0].__dict__

    # Embed the fetched book
    text = (
        f"{book_data['title']} by {', '.join(book_data['authors'])}. "
        f"Categories: {', '.join(book_data['categories'])}. "
        f"{book_data['description']}"
    )

    embedding = model.encode(text).tolist()
    book_data["embedding"] = embedding

    # store it in Qdrant for next time
    from vectordb.client import upsert_books

    upsert_books(client, [book_data])
    print(f"Stored '{book_data['title']}' in Qdrant for future lookups")

    book_data["vector"] = embedding
    return book_data
