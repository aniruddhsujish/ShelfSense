from sentence_transformers import SentenceTransformer
import json
from pathlib import Path

MODEL_NAME = "all-MiniLM-L6-v2"

def load_model() -> SentenceTransformer:
    print(f"Loading embedding model '{MODEL_NAME}'")
    return SentenceTransformer(MODEL_NAME)

def load_books(path: str = "all_books.json") -> list[dict]:
    if not Path(path).exists():
        raise FileNotFoundError(f"No books file found at '{path}'. Run the ingestion pipeline first.")
    with open(path) as f:
        content = f.read().strip()
    if not content:
        return []
    if content.startswith("["):
        return json.loads(content)
    return [json.loads(line) for line in content.splitlines() if line.strip()]
    
def embed_books(books: list[dict], model: SentenceTransformer, batch_size: int = 64) -> list[dict]:
    print(f"Embedding {len(books)} books in batches of {batch_size}...")

    descriptions = [
        f"{book['title']} by {', '.join(book['authors'])}. "
        f"Categories: {', '.join(book['categories'])}. "
        f"{book['description']}"
        for book in books
    ]

    embeddings = model.encode(
        descriptions,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    for book, embedding in zip(books, embeddings):
        book["embedding"] = embedding.tolist()

    print("Embedding complete.")
    return books