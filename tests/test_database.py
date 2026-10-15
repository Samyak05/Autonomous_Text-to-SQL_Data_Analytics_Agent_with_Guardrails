
import pytest

from src.database import execute_query
from src.guardrails import SQLValidationError


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
