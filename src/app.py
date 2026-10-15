
"""Streamlit interface for the Text-to-SQL Analytics Agent."""

import re

import plotly.express as px
import streamlit as st

from src.agent import ask_database


st.set_page_config(
    page_title="Text-to-SQL Analytics Agent",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Text-to-SQL Analytics Agent")
st.caption(
    "Ask questions about your e-commerce data using natural language. "
    "Powered by Azure AI Foundry and DuckDB."
)


def display_response(response: dict) -> None:
    """Display generated SQL, results, errors, and optional charts."""

    with st.expander("Generated SQL", expanded=True):
        st.code(response["sql"], language="sql")

    if response["error"]:
        st.error(response["error"])
        return

    df = response["results"]

    if df is None or df.empty:
        st.info("The query executed successfully but returned no rows.")
        return

    st.subheader("Query Results")

    metric_col1, metric_col2 = st.columns(2)

    metric_col1.metric("Rows returned", response["row_count"])
    metric_col2.metric("Columns returned", len(df.columns))

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    if df.attrs.get("truncated", False):
        limit = df.attrs.get("row_limit", 1000)
        st.warning(
            f"Results were limited to {limit:,} rows. "
            "The complete result may contain additional rows."
        )


    # Choose a meaningful numeric column for visualization.
    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    category_columns = [
        column
        for column in df.columns
        if column not in numeric_columns
    ]

    preferred_terms = (
        "revenue",
        "sales",
        "profit",
        "amount",
        "total",
        "count",
        "quantity",
        "price",
    )

    chart_numeric_columns = [
        column
        for column in numeric_columns
        if not re.search(r"(^|_)id$", column.lower())
    ]

    preferred_numeric = [
        column
        for column in chart_numeric_columns
        if any(
            term in column.lower()
            for term in preferred_terms
        )
    ]

    if preferred_numeric:
        chart_value = preferred_numeric[0]
    elif chart_numeric_columns:
        chart_value = chart_numeric_columns[0]
    else:
        chart_value = None

    if category_columns and chart_value and len(df) >= 2:
        chart_category = category_columns[0]

        st.subheader("Visualization")

        fig = px.bar(
            df,
            x=chart_category,
            y=chart_value,
            title=f"{chart_value} by {chart_category}",
            labels={
                chart_category: chart_category.replace("_", " ").title(),
                chart_value: chart_value.replace("_", " ").title(),
            },
            hover_data=list(df.columns),
        )

        fig.update_layout(
            xaxis_title=chart_category.replace("_", " ").title(),
            yaxis_title=chart_value.replace("_", " ").title(),
        )

        st.plotly_chart(fig, use_container_width=True)

    elif len(df) == 1:
        st.caption(
            "A chart is not necessary for a single-row result."
        )
    else:
        st.caption(
            "No suitable categorical and numeric columns "
            "were found for an automatic chart."
        )


# Keep the conversation available across Streamlit reruns.
if "messages" not in st.session_state:
    st.session_state.messages = []


with st.sidebar:
    st.header("About")
    st.write(
        "This application converts natural-language questions "
        "into SQL, validates the generated query, and executes "
        "it against a read-only DuckDB connection."
    )

    st.divider()

    st.subheader("Example questions")
    st.markdown(
        """
        - Which customers are from Bengaluru?
        - Show the top 5 products by revenue.
        - What are the most expensive products?
        - Show completed orders by date.
        - Which customers have placed orders?
        """
    )

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# Render previous messages.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        else:
            display_response(message["response"])


# Process a new question.
question = st.chat_input(
    "Ask a question about your e-commerce data..."
)

if question:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner(
            "Generating SQL and querying your database..."
        ):
            try:
                response = ask_database(question)

            except Exception:
                st.error(
                    "The agent could not process this question. "
                    "Check your Azure configuration and application logs."
                )

                response = {
                    "question": question,
                    "sql": "",
                    "results": None,
                    "row_count": 0,
                    "error": "The request could not be processed.",
                }

        display_response(response)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "response": response,
        }
    )
