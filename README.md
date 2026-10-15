# Autonomous Text-to-SQL & Data Analytics Agent with Guardrails

A Data Analytics Agent that converts natural-language questions into SQL queries, validates the generated SQL, executes approved queries against a local DuckDB database, and presents the results through an interactive analytics interface.

## Overview

Working with databases often requires users to know SQL, understand table relationships, and write queries correctly. This project explores how a language model can make database analytics more accessible while applying validation and execution controls before running generated SQL.

Users can ask questions in plain English, inspect the generated SQL, and explore query results as tables and charts.

## Key Features

- **Natural-language to SQL:** Uses Azure OpenAI GPT-5 mini to generate SQL from user questions.
- **Relevant schema retrieval:** Retrieves relevant table definitions and relationships instead of passing the entire database schema for every question.
- **SQL validation:** Uses SQLGlot to parse and validate generated SQL before execution.
- **Query restrictions:** Allows only approved tables and a restricted class of read-only `SELECT` queries.
- **Database execution controls:** Uses a read-only DuckDB connection, disables external data access, and configures memory and thread limits.
- **Bounded results:** Limits returned results to 1,000 rows and exposes truncation metadata.
- **Interactive analytics:** Provides a Streamlit chat interface with SQL previews, result tables, and Plotly visualizations.
- **Automated tests:** Includes tests for SQL validation, database execution, schema retrieval, agent behavior, and the Streamlit interface.

## Architecture

```text
                 User question
                       |
                       v
              Streamlit interface
                       |
                       v
                 Agent module
                  /        \
                 v          v
       Schema retriever   Azure OpenAI
                 \          /
                  v        v
                 Generated SQL
                       |
                       v
              SQLGlot guardrails
                       |
                 Valid SQL only
                       |
                       v
              Read-only DuckDB
                       |
                       v
             Results and metadata
                       |
                       v
             Tables and Plotly charts
```

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| Language model | Azure OpenAI GPT-5 mini |
| Database | DuckDB |
| SQL parsing and validation | SQLGlot |
| Data processing | Pandas |
| Frontend | Streamlit |
| Visualization | Plotly |
| Testing | pytest and Streamlit AppTest |

## Project Structure

```text
proj/
├── data/
│   └── ecommerce.duckdb
├── scripts/
│   └── init_db.py
├── src/
│   ├── __init__.py
│   ├── agent.py
│   ├── app.py
│   ├── database.py
│   ├── guardrails.py
│   └── retriever.py
├── tests/
│   ├── test_agent.py
│   ├── test_app.py
│   ├── test_database.py
│   ├── test_guardrails.py
│   └── test_retriever.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Getting Started

### 1. Prerequisites

- Python 3.11 or newer, subject to dependency compatibility
- An Azure OpenAI deployment with access to GPT-5 mini
- Git

### 2. Clone the repository

```bash
git clone <THIS_GITHUB_REPOSITORY_URL>

move inside the project folder using cd 
```

### 3. Create and activate a virtual environment

On Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure environment variables

Copy the example configuration:

```bash
cp .env.example .env
```

Configure the following values in `.env` using your own Azure endpoint and API key:

```dotenv
AZURE_OPENAI_CHAT_ENDPOINT=https://YOUR-ENDPOINT/
AZURE_OPENAI_CHAT_API_KEY=YOUR_API_KEY
AZURE_OPENAI_CHAT_DEPLOYMENT=YOUR_MODEL_NAME
```

### 6. Initialize the demo database

```bash
python scripts/init_db.py
```

This creates the local DuckDB database and populates it with synthetic e-commerce data.

### 7. Start the application

```bash
python -m streamlit run src/app.py
```

Open the local URL printed by Streamlit in your browser.

## Example Questions

Try asking the application:

- Which customers are from Bengaluru?
- Show the top five products by revenue from completed orders.
- How many orders are there for each order status?
- What is the total revenue for each product category?

The exact results depend on the synthetic data in the local database.

## Security and Guardrails

The project applies several controls before generated SQL reaches the database:

1. Parses SQL using SQLGlot and rejects invalid or unsupported query structures.
2. Restricts table references to an explicit allowlist.
3. Rejects multiple statements and non-`SELECT` statements.
4. Rejects CTEs, subqueries, `UNION`, qualified table references, and identified external/file-reading functions.
5. Limits SQL length.
6. Opens DuckDB in read-only mode and disables external data access.
7. Applies database resource settings and a bounded result size.

These controls reduce the risk of unsafe generated queries, but they do not establish that arbitrary model-generated SQL is perfectly safe. The implementation deliberately supports a restricted SQL subset; more complex queries may be rejected.

The query timeout mechanism also requires testing under realistic workloads and should not be treated as a guarantee of a strict execution-time bound.

## Running Tests

Run the complete test suite from the project root:

```bash
python -m pytest -v
```

The current development version passes **47 tests**, covering the agent, database layer, SQL guardrails, schema retrieval, and Streamlit smoke tests.

## Current Limitations

- Uses a local DuckDB database populated with synthetic data.
- Requires a configured Azure OpenAI deployment for live natural-language SQL generation.
- Supports a restricted subset of SQL rather than arbitrary SQL.
- Schema retrieval is based on deterministic keyword matching, not semantic vector search.
- The current tests validate expected behavior but are not a substitute for a full security audit or adversarial penetration testing.
- Visualization selection is intended for a demo and may not produce an appropriate chart for every result set.

## Future Improvements

- Add bounded retries for correcting invalid model-generated SQL.
- Improve schema retrieval and support more complex database relationships.
- Add query-cost estimation and stronger execution isolation.
- Expand adversarial security tests and observability.
- Support additional database backends and more configurable visualizations.

## Learning Outcomes

This project provided hands-on experience with:

- Integrating a language model into a data application.
- Generating and validating SQL programmatically.
- Designing allowlists and defense-in-depth controls.
- Working with DuckDB, Pandas, and SQLGlot.
- Building an interactive Streamlit application.
- Writing automated unit and smoke tests.
- Managing application configuration and API credentials securely.
