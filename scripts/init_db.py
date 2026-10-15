
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "ecommerce.duckdb"


def initialize_database():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(DB_PATH))

    connection.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL,
            city VARCHAR,
            country VARCHAR
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            product_name VARCHAR NOT NULL,
            category VARCHAR,
            price DECIMAL(10, 2) NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date DATE NOT NULL,
            status VARCHAR NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL
        )
    """)

    connection.execute("""
        INSERT INTO customers VALUES
            (1, 'Aarav', 'Mangaluru', 'India'),
            (2, 'Diya', 'Bengaluru', 'India'),
            (3, 'Rahul', 'Mumbai', 'India'),
            (4, 'Ananya', 'Chennai', 'India'),
            (5, 'Ishaan', 'Hyderabad', 'India')
        ON CONFLICT DO NOTHING
    """)

    connection.execute("""
        INSERT INTO products VALUES
            (1, 'Laptop', 'Electronics', 65000.00),
            (2, 'Smartphone', 'Electronics', 25000.00),
            (3, 'Headphones', 'Accessories', 2500.00),
            (4, 'Office Chair', 'Furniture', 8000.00),
            (5, 'Keyboard', 'Accessories', 1500.00)
        ON CONFLICT DO NOTHING
    """)

    connection.execute("""
        INSERT INTO orders VALUES
            (1, 1, '2026-01-10', 'completed'),
            (2, 2, '2026-01-15', 'completed'),
            (3, 3, '2026-02-05', 'completed'),
            (4, 1, '2026-02-20', 'pending'),
            (5, 4, '2026-03-12', 'completed'),
            (6, 5, '2026-03-18', 'cancelled')
        ON CONFLICT DO NOTHING
    """)

    connection.execute("""
        INSERT INTO order_items VALUES
            (1, 1, 1, 1, 65000.00),
            (2, 1, 3, 2, 2500.00),
            (3, 2, 2, 1, 25000.00),
            (4, 2, 5, 2, 1500.00),
            (5, 3, 4, 1, 8000.00),
            (6, 3, 3, 1, 2500.00),
            (7, 4, 2, 1, 25000.00),
            (8, 5, 1, 1, 65000.00),
            (9, 5, 5, 1, 1500.00),
            (10, 6, 3, 1, 2500.00)
        ON CONFLICT DO NOTHING
    """)

    print("Database initialized successfully!")
    print(f"Database location: {DB_PATH}")

    print("\nAvailable tables:")
    tables = connection.execute("SHOW TABLES").fetchall()

    for table in tables:
        print(f"- {table[0]}")

    connection.close()


if __name__ == "__main__":
    initialize_database()
