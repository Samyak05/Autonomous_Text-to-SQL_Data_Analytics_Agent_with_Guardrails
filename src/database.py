
"""Database connection, schema inspection, and query execution."""

from pathlib import Path
from src.guardrails import validate_sql

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "ecommerce.duckdb"


def get_connection():
    """Open a read-only connection to the existing database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run 'python scripts/init_db.py' first."
        )

    return duckdb.connect(str(DB_PATH), read_only=True)


def get_schema():
    """Return all tables and their columns with data types."""
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT
                table_name,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position
        """).fetchall()

        schema = {}

        for table_name, column_name, data_type, is_nullable in rows:
            schema.setdefault(table_name, []).append({
                "column": column_name,
                "type": data_type,
                "nullable": is_nullable == "YES",
            })

        return schema

    finally:
        connection.close()


def execute_query(sql: str) -> pd.DataFrame:
    """Validate SQL before executing it against DuckDB."""

    # Step 1: Validate the query before opening a connection.
    safe_sql = validate_sql(sql)

    # Step 2: Execute only the validated SQL.
    connection = get_connection()

    try:
        result = connection.execute(safe_sql)
        return result.fetchdf()
    finally:
        connection.close()


if __name__ == "__main__":
    print("Database schema:\n")

    for table_name, columns in get_schema().items():
        print(f"{table_name}:")
        for column in columns:
            print(
                f"  - {column['column']}: {column['type']}"
            )

    print("\nSample query results:\n")

    df = execute_query("""
        SELECT
            p.product_name,
            SUM(oi.quantity * oi.unit_price) AS revenue
        FROM order_items oi
        JOIN products p
            ON oi.product_id = p.product_id
        JOIN orders o
            ON oi.order_id = o.order_id
        WHERE o.status = 'completed'
        GROUP BY p.product_name
        ORDER BY revenue DESC
        LIMIT 5
    """)

    print(df.to_string(index=False))
