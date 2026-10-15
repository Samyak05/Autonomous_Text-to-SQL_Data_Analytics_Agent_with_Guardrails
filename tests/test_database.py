
import pytest
import pandas as pd

from src.database import execute_query
from src.guardrails import SQLValidationError
from unittest.mock import patch
from src import database


def test_executes_valid_query():
    result = execute_query(
        "SELECT product_name FROM products ORDER BY product_id"
    )

    assert not result.empty
    assert "product_name" in result.columns
    assert result.iloc[0]["product_name"] == "Laptop"


def test_executes_aggregation_query():
    result = execute_query("""
        SELECT category, COUNT(*) AS product_count
        FROM products
        GROUP BY category
        ORDER BY category
    """)

    assert len(result) == 3
    assert {"category", "product_count"}.issubset(result.columns)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM customers",
        "DROP TABLE products",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM customers; SELECT * FROM orders",
    ],
)
def test_rejects_unsafe_query_before_execution(sql):
    with pytest.raises(SQLValidationError):
        execute_query(sql)

def test_caps_large_query_results():
    mock_df = pd.DataFrame({
        "value": range(database.MAX_RESULT_ROWS + 1)
    })

    class FakeConnection:
        def execute(self, sql):
            assert f"LIMIT {database.MAX_RESULT_ROWS + 1}" in sql
            return self

        def fetchdf(self):
            return mock_df

        def close(self):
            pass

    with patch(
        "src.database.get_connection",
        return_value=FakeConnection(),
    ):
        result = database.execute_query(
            "SELECT customer_id FROM customers"
        )

    assert len(result) == database.MAX_RESULT_ROWS
    assert result.attrs["truncated"] is True
    assert result.attrs["row_limit"] == database.MAX_RESULT_ROWS


def test_marks_small_results_as_not_truncated():
    mock_df = pd.DataFrame({"value": [1, 2, 3]})

    class FakeConnection:
        def execute(self, sql):
            return self

        def fetchdf(self):
            return mock_df

        def close(self):
            pass

    with patch(
        "src.database.get_connection",
        return_value=FakeConnection(),
    ):
        result = database.execute_query(
            "SELECT customer_id FROM customers"
        )

    assert len(result) == 3
    assert result.attrs["truncated"] is False


def test_read_only_connection_has_restrictions():
    with patch("src.database.duckdb.connect") as mock_connect:
        mock_connect.return_value = object()

        database.get_connection()

        _, kwargs = mock_connect.call_args

        assert kwargs["read_only"] is True
        assert kwargs["config"]["enable_external_access"] == "false"
        assert kwargs["config"]["memory_limit"] == database.MAX_MEMORY
        assert kwargs["config"]["threads"] == str(database.MAX_THREADS)

