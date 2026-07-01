import anthropic
import instructor
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = instructor.from_anthropic(
    anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
)


class BookExplanation(BaseModel):
    similar: list[str]
    different: list[str]
    recommended_because: str
    is_same_series: bool


def explain_similarity(book_a: dict, book_b: dict) -> dict:
    prompt = f"""You are a literary analyst. Compare these two books objectively.".

    Book A - {book_a['title']} by {', '.join(book_a['authors'])}:
    {book_a['description']}

    Book B - {book_b['title']} by {', '.join(book_b['authors'])}:
    {book_b['description']}

    Return:
    - similar: 2-3 factual bullet points on shared themes, tone or style
    - differnet: 2-3 factual bullet points on how they diverge
    - recommended_becasue: one sentence describing what kind of reader would enjoy Book B if they liked Book A. Be factual, not promotional.
    - is_same_series: true if both bools are part of the same series, or one is a direct sequel/ prequel of the other, otherwise false
    """

    explanation = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
        response_model=BookExplanation,
    )

    return explanation.model_dump()
