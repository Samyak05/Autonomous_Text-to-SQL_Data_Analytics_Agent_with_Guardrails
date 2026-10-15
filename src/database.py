"""Database connection, schema inspection, and safe query execution."""

import duckdb
import pandas as pd
import threading

from pathlib import Path
from src.guardrails import validate_sql


QUERY_TIMEOUT_SECONDS = 5
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
    """Validate SQL and execute it with resource and time limits."""

    safe_sql = validate_sql(sql)
    connection = get_connection()

    timed_out = threading.Event()

    def interrupt_query():
        timed_out.set()
        try:
            connection.interrupt()
        except Exception:
            pass

    timer = threading.Timer(
        QUERY_TIMEOUT_SECONDS,
        interrupt_query,
    )
    timer.daemon = True

    try:
        limited_sql = (
            f"SELECT * FROM ({safe_sql}) AS _agent_result "
            f"LIMIT {MAX_RESULT_ROWS + 1}"
        )

        timer.start()

        result = connection.execute(limited_sql)
        df = result.fetchdf()

        if timed_out.is_set():
            raise TimeoutError(
                f"Query exceeded {QUERY_TIMEOUT_SECONDS} seconds."
            )

        if len(df) > MAX_RESULT_ROWS:
            df = df.iloc[:MAX_RESULT_ROWS].copy()
            df.attrs["truncated"] = True
            df.attrs["row_limit"] = MAX_RESULT_ROWS
        else:
            df.attrs["truncated"] = False

        return df

    except Exception as exc:
        if timed_out.is_set():
            raise TimeoutError(
                f"Query exceeded {QUERY_TIMEOUT_SECONDS} seconds."
            ) from exc
        raise

    finally:
        timer.cancel()
        connection.close()
