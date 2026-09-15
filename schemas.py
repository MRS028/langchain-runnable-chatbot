# schemas.py
from typing import List, Literal

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """
    Final validated response returned by the chatbot pipeline.

    This model represents the structured output displayed by
    the Streamlit application.
    """

    answer: str = Field(
        ...,
        description=(
            "The final, clear, complete, and polished answer "
            "to the user's question."
        ),
    )

    summary: str = Field(
        ...,
        description=(
            "A concise one-to-two sentence summary of the answer."
        ),
    )

    category: Literal[
        "programming",
        "mathematics",
        "general",
    ] = Field(
        ...,
        description=(
            "The detected category of the user's question. "
            "Must be programming, mathematics, or general."
        ),
    )

    keywords: List[str] = Field(
        default_factory=list,
        description=(
            "A list containing 3 to 6 important keywords or "
            "short key phrases related to the question and answer."
        ),
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "The model's confidence in the correctness and "
            "completeness of the answer, between 0 and 1."
        ),
    )

    follow_up_question: str = Field(
        ...,
        description=(
            "One natural and useful follow-up question that "
            "the user could ask next."
        ),
    )
