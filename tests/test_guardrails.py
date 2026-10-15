import pytest

from src.guardrails import SQLValidationError, validate_sql


def test_allows_basic_select():
    sql = validate_sql("SELECT * FROM customers")
    assert "SELECT" in sql.upper()


def test_allows_approved_table_join():
    sql = """
        SELECT c.name, o.order_id
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
    """
    assert "JOIN" in validate_sql(sql).upper()


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM customers",
        "DROP TABLE products",
        "UPDATE products SET price = 0",
        "SELECT * FROM customers; SELECT * FROM orders",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM read_csv('secret.csv')",
    ],
)
def test_blocks_unsafe_queries(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql)


def test_rejects_empty_query():
    with pytest.raises(SQLValidationError):
        validate_sql("")


def test_rejects_invalid_syntax():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT FROM WHERE")


def test_blocks_table_valued_file_readers():
    queries = [
        "SELECT * FROM read_parquet('data.parquet')",
        "SELECT * FROM read_csv_auto('data.csv')",
    ]

    for sql in queries:
        with pytest.raises(SQLValidationError):
            validate_sql(sql)


def test_blocks_qualified_table_references():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM main.customers")


def test_blocks_select_into():
    with pytest.raises(SQLValidationError):
        validate_sql(
            "SELECT * INTO backup FROM customers"
        )


def test_blocks_ctes():
    with pytest.raises(SQLValidationError):
        validate_sql(
            "WITH x AS (SELECT * FROM customers) "
            "SELECT * FROM x"
        )


def test_blocks_subqueries():
    with pytest.raises(SQLValidationError):
        validate_sql(
            "SELECT * FROM customers "
            "WHERE customer_id IN "
            "(SELECT customer_id FROM orders)"
        )


def test_rejects_oversized_sql():
    with pytest.raises(SQLValidationError):
        validate_sql(
            "SELECT * FROM customers "
            + " " * 10_000
        )

