
"""Natural-language-to-SQL agent using Azure AI Foundry."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.database import execute_query
from src.guardrails import SQLValidationError
from src.retriever import get_relevant_schema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def create_llm_client() -> OpenAI:
    """Create an OpenAI-compatible client for Azure AI Foundry."""

    endpoint = os.getenv("AZURE_OPENAI_CHAT_ENDPOINT", "").strip()
    api_key = os.getenv("AZURE_OPENAI_CHAT_API_KEY", "").strip()

    if not endpoint or not api_key:
        raise RuntimeError(
            "Azure configuration is incomplete. Check "
            "AZURE_OPENAI_CHAT_ENDPOINT and "
            "AZURE_OPENAI_CHAT_API_KEY in your .env file."
        )

    # Accept either the base endpoint or the endpoint copied
    # from the Foundry Responses API page.
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/responses"):
        endpoint = endpoint.removesuffix("/responses")

    if not endpoint.endswith("/openai/v1"):
        raise RuntimeError(
            "Expected an OpenAI-compatible endpoint ending in "
            "'/openai/v1'. Check your Azure AI Foundry deployment."
        )

    return OpenAI(
        base_url=endpoint + "/",
        api_key=api_key,
        timeout=30.0,
        max_retries=1,
    )


def generate_sql(question: str) -> str:
    """Generate SQL from a question and its relevant database schema."""

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    deployment = os.getenv(
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
        "gpt-5-mini",
    ).strip()

    if not deployment:
        raise RuntimeError("Azure model deployment name is missing.")

    schema = get_relevant_schema(question, top_k=3)
    client = create_llm_client()

    instructions = """
You are a Text-to-SQL assistant for a mock e-commerce database.

Generate exactly one DuckDB SELECT query answering the user's question.

Rules:
- Use only tables and columns provided in the schema.
- Use explicit JOIN conditions when multiple tables are needed.
- Do not generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER,
  or any other data-modifying statement.
- Do not use subqueries, CTEs, table-valued functions, or system catalogs.
- Never invent tables or columns.
- For revenue, calculate quantity * unit_price from order_items.
- For completed-order revenue, filter orders.status = 'completed'.
- Return SQL only, without Markdown fences or explanations.
"""

    response = client.responses.create(
        model=deployment,
        instructions=instructions,
        input=(
            f"Database schema:\n{schema}\n\n"
            f"User question:\n{question.strip()}"
        ),
        max_output_tokens=800,
    )

    sql = response.output_text.strip()

    # Remove optional Markdown fences if the model adds them.
    sql = re.sub(
        r"\A```(?:sql)?\s*|\s*```\Z",
        "",
        sql,
        flags=re.IGNORECASE,
    ).strip()

    if not sql:
        raise RuntimeError("The model returned an empty SQL query.")

    return sql


def ask_database(question: str) -> dict:
    """Generate SQL, validate it, and execute it."""

    sql = generate_sql(question)

    try:
        results = execute_query(sql)

        return {
            "question": question,
            "sql": sql,
            "results": results,
            "row_count": len(results),
            "error": None,
        }

    except SQLValidationError as exc:
        return {
            "question": question,
            "sql": sql,
            "results": None,
            "row_count": 0,
            "error": f"SQL rejected by guardrails: {exc}",
        }

    except Exception as exc:
        # Return a concise error without exposing credentials.
        return {
            "question": question,
            "sql": sql,
            "results": None,
            "row_count": 0,
            "error": f"Query execution failed: {exc}",
        }


if __name__ == "__main__":
    question = input("Ask a question about your e-commerce data: ")

    try:
        response = ask_database(question)

        print("\nGenerated SQL:\n")
        print(response["sql"])

        if response["error"]:
            print("\nError:", response["error"])
        else:
            print("\nQuery results:\n")
            print(response["results"].to_string(index=False))
            print(f"\nRows returned: {response['row_count']}")

    except Exception as exc:
        print(f"\nAgent error: {exc}")
