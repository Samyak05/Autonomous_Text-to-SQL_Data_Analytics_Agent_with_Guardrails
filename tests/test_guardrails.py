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


@pytest.mark.parametrize(
    "sql",
    [
        # External-data functions in scalar expressions
        "SELECT read_csv('secret.csv') FROM customers",
        "SELECT read_parquet('secret.parquet') FROM products",

        # Set operations outside the supported SELECT policy
        "SELECT name FROM customers UNION SELECT city FROM customers",

        # Attempts to access unapproved tables through joins
        "SELECT * FROM customers JOIN secrets ON TRUE",

        # Attempts to access qualified tables
        "SELECT * FROM customers JOIN main.orders ON TRUE",

        # Nested query attempts
        "SELECT * FROM customers WHERE customer_id IN "
        "(SELECT customer_id FROM orders)",
    ],
)
def test_blocks_adversarial_sql(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql)


def test_allows_valid_aggregate_query():
    sql = """
        SELECT category, COUNT(*) AS product_count
        FROM products
        GROUP BY category
        ORDER BY product_count DESC
    """

    validated_sql = validate_sql(sql)

    assert "SELECT" in validated_sql.upper()
    assert "GROUP BY" in validated_sql.upper()


def test_allows_valid_join_query():
    sql = """
        SELECT c.name, o.order_id
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
    """

    validated_sql = validate_sql(sql)

    assert "JOIN" in validated_sql.upper()

