# chatbot.py
import os
import re
from typing import Any

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableBranch, RunnableParallel

from prompts import (
    followup_prompt,
    general_prompt,
    keywords_prompt,
    math_prompt,
    programming_prompt,
    structuring_prompt,
    summary_prompt,
)

from schemas import ChatResponse


load_dotenv()


     
# LLM
     

def get_llm(
    provider: str | None = None,
    temperature: float = 0.3,
):
    provider = (
        provider or os.getenv("LLM_PROVIDER", "groq")
    ).lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is missing from the .env file."
            )

        return ChatGroq(
            model=os.getenv(
                "GROQ_MODEL",
                "llama-3.3-70b-versatile",
            ),
            temperature=temperature,
            api_key=api_key,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is missing from the .env file."
            )

        return ChatOpenAI(
            model=os.getenv(
                "OPENAI_MODEL",
                "gpt-4o-mini",
            ),
            temperature=temperature,
            api_key=api_key,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is missing from the .env file."
            )

        return ChatGoogleGenerativeAI(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-1.5-flash",
            ),
            temperature=temperature,
            google_api_key=api_key,
        )

    raise ValueError(
        f"Unsupported LLM provider: {provider}"
    )


     
# RunnableBranch
     

PROGRAMMING_KEYWORDS = [
    "code",
    "python",
    "java",
    "javascript",
    "typescript",
    "function",
    "bug",
    "error",
    "algorithm",
    "debug",
    "compile",
    "programming",
    "sql",
    "api",
    "class",
    "loop",
    "variable",
    "syntax",
    "framework",
    "library",
    "github",
    "regex",
    "array",
    "database",
    "react",
    "node",
    "langchain",
]


MATH_KEYWORDS = [
    "solve",
    "equation",
    "calculate",
    "calculation",
    "derivative",
    "integral",
    "algebra",
    "geometry",
    "math",
    "mathematics",
    "matrix",
    "probability",
    "theorem",
    "calculus",
    "arithmetic",
    "logarithm",
    "statistics",
    "factorial",
    "trigonometry",
]


def _matches_any(
    text: str,
    keywords: list[str],
) -> bool:
    """
    Check whether any keyword appears in the question.
    """

    return any(
        re.search(
            r"\b" + re.escape(keyword.strip()) + r"\b",
            text,
        )
        for keyword in keywords
    )


def classify_query(inputs: dict[str, Any]) -> str:
    """
    Classify the user's question.

    Returns:
        'programming'
        'mathematics'
        'general'
    """

    question = inputs["question"].lower()

    if _matches_any(
        question,
        PROGRAMMING_KEYWORDS,
    ):
        return "programming"

    if _matches_any(
        question,
        MATH_KEYWORDS,
    ):
        return "mathematics"

    return "general"


def build_branch_chain(llm):
    """
    Create the RunnableBranch.

    The question is routed to one of three specialized
    prompt pipelines.
    """

    programming_chain = (
        programming_prompt
        | llm
        | StrOutputParser()
    )

    mathematics_chain = (
        math_prompt
        | llm
        | StrOutputParser()
    )

    general_chain = (
        general_prompt
        | llm
        | StrOutputParser()
    )

    return RunnableBranch(
        (
            lambda x: classify_query(x) == "programming",
            programming_chain,
        ),
        (
            lambda x: classify_query(x) == "mathematics",
            mathematics_chain,
        ),
        general_chain,
    )


     
# RunnableParallel
     

def build_parallel_chain(
    branch_chain,
    llm,
):
    """
    Create the RunnableParallel stage.

    First, RunnableBranch generates the main answer.

    Then RunnableParallel uses that answer to generate:
        - Summary
        - Keywords
        - Follow-up question

    These independent tasks can run concurrently.
    """

    # Get the answer from the appropriate branch.
    answer_chain = branch_chain

    # Prepare the data required by the parallel stage.
    prepare_parallel_input = RunnableParallel(
        question=lambda x: x["question"],
        category=lambda x: classify_query(x),
        answer=answer_chain,
    )

    # Generate independent outputs in parallel.
    parallel_outputs = RunnableParallel(
        question=lambda x: x["question"],
        category=lambda x: x["category"],
        answer=lambda x: x["answer"],

        summary=(
            {
                "answer": lambda x: x["answer"]
            }
            | summary_prompt
            | llm
            | StrOutputParser()
        ),

        keywords=(
            {
                "answer": lambda x: x["answer"]
            }
            | keywords_prompt
            | llm
            | StrOutputParser()
        ),

        followup=(
            {
                "answer": lambda x: x["answer"]
            }
            | followup_prompt
            | llm
            | StrOutputParser()
        ),
    )

    return (
        prepare_parallel_input
        | parallel_outputs
    )


     
# Pydantic Structured Output
     

def build_structuring_chain(llm):
    """
    Convert the intermediate results into a validated
    ChatResponse Pydantic object.
    """

    structured_llm = llm.with_structured_output(
        ChatResponse
    )

    return (
        structuring_prompt
        | structured_llm
    )


     
# Main Chatbot
     

class LangChainChatbot:
    """
    Main chatbot class.

    Pipeline:

        RunnableBranch
            ->
        RunnableParallel
            ->
        Pydantic Structured Output
    """

    def __init__(
        self,
        provider: str | None = None,
    ):
        self.llm = get_llm(provider)

        self.branch_chain = build_branch_chain(
            self.llm
        )

        self.parallel_chain = build_parallel_chain(
            self.branch_chain,
            self.llm,
        )

        self.structuring_chain = build_structuring_chain(
            self.llm
        )

    def run(
        self,
        question: str,
    ) -> dict[str, Any]:
        """
        Run the complete chatbot pipeline.
        """

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        question = question.strip()

        # -------------------------------------------------------------
        # Step 1:
        # RunnableBranch -> RunnableParallel
        # -------------------------------------------------------------

        parallel_result = (
            self.parallel_chain.invoke(
                {
                    "question": question
                }
            )
        )

        # -------------------------------------------------------------
        # Step 2:
        # Pydantic Structured Output
        # -------------------------------------------------------------

        structured_response = (
            self.structuring_chain.invoke(
                {
                    "question": question,
                    "category": parallel_result["category"],
                    "answer": parallel_result["answer"],
                    "summary": parallel_result["summary"],
                    "keywords": parallel_result["keywords"],
                    "followup": parallel_result["followup"],
                }
            )
        )

        # -------------------------------------------------------------
        # Return structured and raw results
        # -------------------------------------------------------------

        return {
            "structured": structured_response,
            "raw": parallel_result,
        }
