from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    TextIndexParams,
    TokenizerType,
    VectorParams,
    PointStruct,
)
import uuid

COLLECTION_NAME = "books"
VECTOR_SIZE = 384  # dimension output of sentence-transformers all-MiniLM-L6-v2 model


def get_client() -> QdrantClient:
    return QdrantClient(path="./qdrant_storage")


def create_collection(client: QdrantClient):
    existing = client.get_collections()
    names = [c.name for c in existing.collections]

    if COLLECTION_NAME in names:
        print(f"Collection '{COLLECTION_NAME}' already exists, skipping.")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"Collection '{COLLECTION_NAME}' created.")


def upsert_books(client: QdrantClient, books: list[dict]):
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=book["embedding"],
            payload={
                "book_id": book["id"],
                "title": book["title"],
                "authors": book["authors"],
                "description": book["description"],
                "categories": book["categories"],
                "published_date": book["published_date"],
                "average_rating": book["average_rating"],
                "ratings_count": book["ratings_count"],
                "page_count": book["page_count"],
                "thumbnail": book["thumbnail"],
            },
        )
        for book in books
    ]

    client.upsert(collection_name=COLLECTION_NAME, points=points)


def create_title_index(client: QdrantClient):
    client.delete_payload_index(collection_name=COLLECTION_NAME, field_name="title")
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="title",
        field_schema=TextIndexParams(
            type="text", tokenizer=TokenizerType.PREFIX, lowercase=True
        ),
    )
