
from unittest.mock import patch

import pytest

from src.agent import ask_database, generate_sql


def test_generate_sql_rejects_empty_question():
    with pytest.raises(ValueError):
        generate_sql("")


@patch("src.agent.execute_query")
@patch("src.agent.generate_sql")
def test_ask_database_executes_generated_sql(
    mock_generate_sql,
    mock_execute_query,
):
    import pandas as pd

    mock_generate_sql.return_value = (
        "SELECT * FROM customers"
    )
    mock_execute_query.return_value = pd.DataFrame({
        "name": ["Diya"],
    })

    response = ask_database("Show customers")

    assert response["error"] is None
    assert response["row_count"] == 1
    assert response["results"].iloc[0]["name"] == "Diya"

    mock_generate_sql.assert_called_once_with("Show customers")
    mock_execute_query.assert_called_once_with(
        "SELECT * FROM customers"
    )


@patch("src.agent.execute_query")
@patch("src.agent.generate_sql")
def test_ask_database_handles_rejected_sql(
    mock_generate_sql,
    mock_execute_query,
):
    mock_generate_sql.return_value = (
        "DELETE FROM customers"
    )

    from src.guardrails import SQLValidationError

    mock_execute_query.side_effect = SQLValidationError(
        "Only SELECT queries are allowed."
    )

    response = ask_database("Delete customers")

    assert response["results"] is None
    assert response["error"].startswith(
        "SQL rejected by guardrails:"
    )


@patch("src.agent.execute_query")
@patch("src.agent.generate_sql")
def test_ask_database_handles_execution_errors(
    mock_generate_sql,
    mock_execute_query,
):
    mock_generate_sql.return_value = (
        "SELECT * FROM customers"
    )
    mock_execute_query.side_effect = RuntimeError(
        "Database execution failed"
    )

    response = ask_database("Show customers")

    assert response["results"] is None
    assert response["error"].startswith(
        "Query execution failed:"
    )
