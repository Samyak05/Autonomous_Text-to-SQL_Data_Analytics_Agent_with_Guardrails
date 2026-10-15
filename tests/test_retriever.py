
import pytest

from src.retriever import get_relevant_schema


def test_retrieves_customer_schema():
    result = get_relevant_schema(
        "Which customers live in Bengaluru?"
    )

    assert "Table: customers" in result
    assert "city" in result


def test_retrieves_product_schema():
    result = get_relevant_schema(
        "Find the most expensive products"
    )

    assert "Table: products" in result
    assert "price" in result


def test_retrieves_order_schema():
    result = get_relevant_schema(
        "Show completed orders by date"
    )

    assert "Table: orders" in result
    assert "order_date" in result
    assert "status" in result


def test_includes_relationships_when_tables_are_selected():
    result = get_relevant_schema(
        "Show customers and their orders",
        top_k=3,
    )

    assert "Table: customers" in result
    assert "Table: orders" in result
    assert "orders.customer_id = customers.customer_id" in result


def test_rejects_empty_question():
    with pytest.raises(ValueError):
        get_relevant_schema("")


def test_rejects_invalid_top_k():
    with pytest.raises(ValueError):
        get_relevant_schema("Show products", top_k=0)
