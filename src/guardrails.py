
"""SQL validation and security guardrails."""

import sqlglot
from sqlglot import exp


# Tables that the agent is allowed to query.
ALLOWED_TABLES = {
    "customers",
    "products",
    "orders",
    "order_items",
}


class SQLValidationError(ValueError):
    """Raised when a SQL query violates the security policy."""


def validate_sql(sql: str) -> str:
    """Validate SQL and return its normalized representation.

    This initial policy accepts a single SELECT statement that
    references only approved tables and does not use subqueries,
    CTEs, or table functions. We can extend the policy later.
    """

    if not isinstance(sql, str) or not sql.strip():
        raise SQLValidationError("SQL query cannot be empty.")

    try:
        statements = [
            statement
            for statement in sqlglot.parse(sql, read="duckdb")
            if statement is not None
        ]
    except sqlglot.errors.ParseError as exc:
        raise SQLValidationError(
            "Invalid SQL syntax."
        ) from exc

    if len(statements) != 1:
        raise SQLValidationError(
            "Only one SQL statement is allowed."
        )

    tree = statements[0]

    # Accept SELECT statements only.
    if not isinstance(tree, exp.Select):
        raise SQLValidationError(
            "Only SELECT queries are allowed."
        )

    # Reject nested queries and CTEs in this initial version.
    if tree.find(exp.Subquery) or tree.find(exp.CTE):
        raise SQLValidationError(
            "Subqueries and CTEs are not allowed yet."
        )

    # Reject table-valued functions such as read_csv(), which
    # could access files outside the intended database tables.
    if tree.find(exp.TableFromRows) or any(
        isinstance(node, exp.Func)
        and isinstance(node.parent, exp.From)
        for node in tree.walk()
    ):
        raise SQLValidationError(
            "Table functions are not allowed."
        )

    # Reject queries that read from system catalogs.
    for table in tree.find_all(exp.Table):
        table_name = table.name.lower()

        if (
            table_name not in ALLOWED_TABLES
            or table.db
            or table.catalog
        ):
            raise SQLValidationError(
                f"Table '{table_name}' is not allowed."
            )

    # Normalize the validated SQL.
    return tree.sql(dialect="duckdb")


if __name__ == "__main__":
    valid_queries = [
        "SELECT * FROM customers",
        """
        SELECT p.product_name, p.price
        FROM products AS p
        WHERE p.price > 1000
        ORDER BY p.price DESC
        """,
        """
        SELECT category, COUNT(*) AS product_count
        FROM products
        GROUP BY category
        """,
    ]

    invalid_queries = [
        "DELETE FROM customers",
        "DROP TABLE products",
        "UPDATE products SET price = 0",
        "SELECT * FROM customers; SELECT * FROM orders",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM read_csv('secret.csv')",
    ]

    print("Testing valid queries:\n")

    for query in valid_queries:
        try:
            print("PASS:", validate_sql(query))
        except SQLValidationError as exc:
            print("UNEXPECTED FAILURE:", exc)

    print("\nTesting invalid queries:\n")

    for query in invalid_queries:
        try:
            validate_sql(query)
            print("UNEXPECTED ACCEPTANCE:", query)
        except SQLValidationError as exc:
            print("BLOCKED:", exc)
