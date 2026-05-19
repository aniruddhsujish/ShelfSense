from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from services.recommender import get_or_fetch_books, find_similar_books
from services.explainer import explain_similarity
from services.taste_profile import discover_books
from db.ratings import save_rating
from api.dependencies import client, model
from qdrant_client.models import FieldCondition, Filter, MatchText

from vectordb.client import COLLECTION_NAME

router = APIRouter()


class RecommendRequest(BaseModel):
    title: str
    limit: int = 5


class RateRequest(BaseModel):
    book_id: str
    title: str
    rating: int  # 1 or -1


@router.post(
    "/recommend",
    summary="Recommend similar books",
    description="Takes a book title, finds it in the database or fetches it live, and returns 5 similar books with explanations of similarities and differences.",
    response_description="The queried book and a list of recommendations with explanations",
)
async def recommend(request: RecommendRequest):
    book = await get_or_fetch_books(
        title=request.title,
        model=model,
        client=client,
        api_key=os.getenv("GOOGLE_BOOKS_API_KEY"),
    )

    if not book:
        raise HTTPException(status_code=404, detail=f"Book '{request.title}' not found")

    similar_books = find_similar_books(
        query_vector=book["vector"],
        client=client,
        exclude_title=request.title,
        limit=request.limit,
    )

    import asyncio

    def safe_explain(book_a, book_b):
        try:
            return explain_similarity(book_a, book_b)
        except Exception:
            return {
                "simialr": [],
                "different": [],
                "recommended_because": "Similar themes and writing style.",
            }

    explanations = await asyncio.gather(
        *[
            asyncio.to_thread(safe_explain, book, similar_book)
            for similar_book in similar_books
        ]
    )

    return {
        "query_book": {k: v for k, v in book.items() if k != "vector"},
        "recommendations": [
            {**similar_book, "explanation": explanation}
            for similar_book, explanation in zip(similar_books, explanations)
        ],
    }


@router.post(
    "/rate",
    summary="Rate a book",
    description="Save a thumbs up (1) or thumbs down (-1) for a book. Ratings are used to build your taste profile.",
    response_description="Confirmation message",
)
def rate(request: RateRequest):
    if request.rating not in [1, -1]:
        raise HTTPException(status_code=400, details="Rating must be 1 or -1")

    save_rating(request.book_id, request.title, request.rating)
    return {"message": f"Rating saved for '{request.title}'"}


@router.get(
    "/discover",
    summary="Discover books based on taste profile",
    description="Returns book recommendations based on your accumulated ratings. Rate more books for better results.",
    response_description="List of recommended books",
)
def discover(limit: int = 5):
    books = discover_books(client, limit=limit)

    if not books:
        return {"message": "No taste profile yet. Rate some books first.", "books": []}

    return {"books": books}


@router.post(
    "/explain",
    summary="Explain similarity between two books",
    description="Given two books, returns bullet points on what they share and how they differ.",
    response_description="Similarities, differences, and recommendation reason",
)
async def explain(book_a: dict, book_b: dict):
    explanation = explain_similarity(book_a, book_b)
    return explanation


@router.get("/suggest")
def suggest(q: str, limit: int = 6):
    if len(q.strip()) < 2:
        return {"suggestions": []}

    results = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="title", match=MatchText(text=q.lower()))]
        ),
        limit=limit,
        with_payload=["title", "authors"],
        with_vectors=False,
    )[0]

    return {
        "suggestions": [
            {"title": p.payload["title"], "authors": p.payload["authors"]}
            for p in results
        ]
    }
