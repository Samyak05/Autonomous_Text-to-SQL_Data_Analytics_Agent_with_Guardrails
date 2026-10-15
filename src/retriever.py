
"""Retrieve relevant database schema for natural-language questions."""

import re

from src.database import get_schema


# Foreign-key relationships used to explain how tables connect.
RELATIONSHIPS = [
    ("orders.customer_id", "customers.customer_id"),
    ("order_items.order_id", "orders.order_id"),
    ("order_items.product_id", "products.product_id"),
]

# Domain-specific terms help match natural-language questions
# to tables even when the wording differs from column names.
TABLE_KEYWORDS = {
    "customers": {
        "customer", "customers", "buyer", "buyers", "client", "clients",
        "person", "people", "city", "country",
    },
    "products": {
        "product", "products", "item", "items", "category", "categories",
        "price", "pricing", "catalog", "expensive", "cheap",
    },
    "orders": {
        "order", "orders", "purchase", "purchases", "status",
        "date", "month", "year", "completed", "pending", "cancelled",
    },
    "order_items": {
        "quantity", "quantities", "units", "unit", "line", "lines",
        "revenue", "sales", "sold", "total", "amount",
    },
}


def tokenize(text: str) -> set[str]:
    """Convert text into lowercase word tokens."""
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def get_relevant_schema(
    question: str,
    top_k: int = 3,
) -> str:
    """Return a compact schema relevant to a user's question."""

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    schema = get_schema()
    question_tokens = tokenize(question)

    scored_tables = []

    for table_name, columns in schema.items():
        table_tokens = tokenize(table_name)
        column_tokens = set()

        for column in columns:
            column_tokens.update(tokenize(column["column"]))

        # Direct matches receive the strongest signal.
        score = 4 * len(question_tokens & table_tokens)
        score += 2 * len(question_tokens & column_tokens)

        # Domain synonyms provide additional relevance signals.
        score += 3 * len(
            question_tokens & TABLE_KEYWORDS.get(table_name, set())
        )

        scored_tables.append((score, table_name))

    # Sort by relevance, with table name as a deterministic tie-breaker.
    scored_tables.sort(key=lambda item: (-item[0], item[1]))

    selected_tables = [
        table_name
        for _, table_name in scored_tables[:top_k]
    ]

    # Add directly related tables when needed to explain joins.
    # Keep the number of tables bounded to avoid oversized prompts.
    for left, right in RELATIONSHIPS:
        left_table = left.split(".")[0]
        right_table = right.split(".")[0]

        if (
            left_table in selected_tables
            and right_table not in selected_tables
            and len(selected_tables) < top_k + 1
        ):
            selected_tables.append(right_table)

        elif (
            right_table in selected_tables
            and left_table not in selected_tables
            and len(selected_tables) < top_k + 1
        ):
            selected_tables.append(left_table)

    lines = ["Relevant database schema:", ""]

    for table_name in selected_tables:
        lines.append(f"Table: {table_name}")

        for column in schema[table_name]:
            nullable = (
                "nullable" if column["nullable"] else "not nullable"
            )
            lines.append(
                f"  - {column['column']}: "
                f"{column['type']} ({nullable})"
            )

        lines.append("")

    lines.append("Relevant table relationships:")

    relevant_relationships = [
        (left, right)
        for left, right in RELATIONSHIPS
        if (
            left.split(".")[0] in selected_tables
            and right.split(".")[0] in selected_tables
        )
    ]

    if relevant_relationships:
        for left, right in relevant_relationships:
            lines.append(f"  - {left} = {right}")
    else:
        lines.append("  - No relationships between selected tables.")

    return "\n".join(lines)


if __name__ == "__main__":
    questions = [
        "Which customers are from Bengaluru?",
        "What are the most expensive products?",
        "Show monthly revenue from completed orders.",
    ]

    for question in questions:
        print(f"\nQuestion: {question}\n")
        print(get_relevant_schema(question))
        print("-" * 60)
