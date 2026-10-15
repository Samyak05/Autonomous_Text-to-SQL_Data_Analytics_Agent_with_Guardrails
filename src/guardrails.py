
"""SQL validation and security guardrails."""

import sqlglot
import re
from sqlglot import exp


ALLOWED_TABLES = {
    "customers",
    "products",
    "orders",
    "order_items",
}

MAX_SQL_LENGTH = 10_000

# Functions that could access files, external sources, or
# dynamically execute SQL. These are blocked even if they
# appear inside an otherwise valid SELECT statement.
BLOCKED_FUNCTIONS = {
    "read_csv",
    "read_csv_auto",
    "read_parquet",
    "read_json",
    "read_json_auto",
    "read_text",
    "read_blob",
    "read_file",
    "parquet_scan",
    "csv_scan",
    "glob",
    "query",
    "query_table",
    "postgres_scan",
    "sqlite_scan",
    "duckdb_databases",
    "duckdb_tables",
    "duckdb_columns",
}


class SQLValidationError(ValueError):
    """Raised when a query violates the SQL security policy."""


def validate_sql(sql: str) -> str:
    """Validate one restricted, read-only SELECT query."""

    if not isinstance(sql, str) or not sql.strip():
        raise SQLValidationError("SQL query cannot be empty.")

    if len(sql) > MAX_SQL_LENGTH:
        raise SQLValidationError(
            f"SQL query exceeds {MAX_SQL_LENGTH} characters."
        )

    try:
        statements = [
            statement
            for statement in sqlglot.parse(sql, read="duckdb")
            if statement is not None
        ]
    except sqlglot.errors.ParseError as exc:
        raise SQLValidationError("Invalid SQL syntax.") from exc

    if len(statements) != 1:
        raise SQLValidationError(
            "Only one SQL statement is allowed."
        )

    tree = statements[0]

    # Only a plain SELECT is supported. This excludes UNION roots,
    # INSERT, UPDATE, DELETE, DDL, COPY, and other statement types.
    if not isinstance(tree, exp.Select):
        raise SQLValidationError(
            "Only SELECT queries are allowed."
        )

    # Explicitly reject SELECT INTO, which can create a table.
    if tree.args.get("into") is not None:
        raise SQLValidationError(
            "SELECT INTO is not allowed."
        )

    # This first version intentionally excludes nested queries and CTEs.
    if tree.find(exp.Subquery) or tree.find(exp.CTE):
        raise SQLValidationError(
            "Subqueries and CTEs are not allowed yet."
        )

    # Reject unsupported table sources, including table-valued functions.
    for table in tree.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier):
            raise SQLValidationError(
                "Table-valued functions and unsupported table "
                "sources are not allowed."
            )

        table_name = table.name.lower()

        if table_name not in ALLOWED_TABLES:
            raise SQLValidationError(
                f"Table '{table_name}' is not allowed."
            )

        # Do not allow database/catalog-qualified references.
        if table.db or table.catalog:
            raise SQLValidationError(
                "Qualified table references are not allowed."
            )

    
    # Block dangerous functions in the SQL text as a
    # defense-in-depth check. This catches functions used
    # inside SELECT expressions as well as table sources.
    blocked_pattern = (
        r"\b(?:"
        + "|".join(
            re.escape(name)
            for name in sorted(BLOCKED_FUNCTIONS, key=len, reverse=True)
        )
        + r")\s*\("
    )

    if re.search(blocked_pattern, sql, flags=re.IGNORECASE):
        raise SQLValidationError(
            "A restricted SQL function was detected."
        )

    # Also inspect parsed function nodes using SQLGlot's
    # canonical function name where available.
    for function in tree.find_all(exp.Func):
        function_names = {
            str(getattr(function, "name", "")).lower(),
            str(function.sql_name()).lower(),
        }

        if function_names & BLOCKED_FUNCTIONS:
            raise SQLValidationError(
                "A restricted SQL function was detected."
            )

    return tree.sql(dialect="duckdb")


if __name__ == "__main__":
    valid_queries = [
        "SELECT * FROM customers",
        """
        SELECT p.product_name, p.price
        FROM products p
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
        "SELECT * FROM read_parquet('secret.parquet')",
        "SELECT * FROM main.customers",
        "SELECT * INTO backup FROM customers",
        "WITH x AS (SELECT * FROM customers) SELECT * FROM x",
        "SELECT * FROM customers WHERE customer_id IN "
        "(SELECT customer_id FROM orders)",
        "SELECT * FROM customers " + " " * 10_000,
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
            print("UNEXPECTED ACCEPTANCE:", query[:100])
        except SQLValidationError as exc:
            print("BLOCKED:", exc)
