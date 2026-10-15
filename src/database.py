"""Database connection, schema inspection, and safe query execution."""

from pathlib import Path

import duckdb
import pandas as pd

from src.guardrails import validate_sql


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "ecommerce.duckdb"

MAX_RESULT_ROWS = 1000
MAX_MEMORY = "256MB"
MAX_THREADS = 2


def get_connection():
    """Open a read-only connection with resource restrictions."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run 'python scripts/init_db.py' first."
        )

    return duckdb.connect(
        str(DB_PATH),
        read_only=True,
        config={
            "enable_external_access": "false",
            "memory_limit": MAX_MEMORY,
            "threads": str(MAX_THREADS),
        },
    )


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
    """Validate SQL, execute with restricted DuckDB settings,
    and cap the number of returned rows.
    """

    # Validate before opening a database connection.
    safe_sql = validate_sql(sql)

    connection = get_connection()

    try:
        # The original query has already passed validation.
        # The outer LIMIT caps rows materialized for the application.
        limited_sql = (
            f"SELECT * FROM ({safe_sql}) AS _agent_result "
            f"LIMIT {MAX_RESULT_ROWS + 1}"
        )

        result = connection.execute(limited_sql)
        df = result.fetchdf()

        if len(df) > MAX_RESULT_ROWS:
            df = df.iloc[:MAX_RESULT_ROWS].copy()
            df.attrs["truncated"] = True
            df.attrs["row_limit"] = MAX_RESULT_ROWS
        else:
            df.attrs["truncated"] = False

        return df

    finally:
        connection.close()