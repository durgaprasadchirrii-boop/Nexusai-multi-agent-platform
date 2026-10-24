
import sqlite3
from pathlib import Path

from app.config import get_settings


DEMO_SALES = [
    ("North", "Laptop", "Q1", 12500.0, 10),
    ("South", "Laptop", "Q1", 10000.0, 8),
    ("East", "Monitor", "Q1", 6000.0, 20),
    ("West", "Laptop", "Q2", 15000.0, 12),
    ("North", "Monitor", "Q2", 7500.0, 25),
    ("South", "Monitor", "Q2", 4500.0, 15),
    ("East", "Laptop", "Q2", 17500.0, 14),
    ("West", "Monitor", "Q1", 3000.0, 10),
]


def get_connection() -> sqlite3.Connection:
    settings = get_settings()
    db_path = Path(settings.sales_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,
            product TEXT NOT NULL,
            quarter TEXT NOT NULL,
            revenue REAL NOT NULL,
            units INTEGER NOT NULL
        )
    """)

    count = connection.execute(
        "SELECT COUNT(*) FROM sales"
    ).fetchone()[0]

    if count == 0:
        connection.executemany(
            """
            INSERT INTO sales (region, product, quarter, revenue, units)
            VALUES (?, ?, ?, ?, ?)
            """,
            DEMO_SALES,
        )
        connection.commit()

    return connection


def run_sales_analytics(question: str) -> dict:
    """
    Execute one of a small set of approved SELECT queries.
    Unsupported requests return an explicit message.
    """
    q = question.lower()

    approved_queries = {
        "total_revenue": (
            ("total revenue", "overall revenue", "revenue overall"),
            """
            SELECT ROUND(SUM(revenue), 2) AS total_revenue
            FROM sales
            """,
        ),
        "revenue_by_region": (
            ("revenue by region", "region-wise revenue", "regional revenue"),
            """
            SELECT region, ROUND(SUM(revenue), 2) AS revenue
            FROM sales
            GROUP BY region
            ORDER BY revenue DESC
            """,
        ),
        "revenue_by_product": (
            ("revenue by product", "product-wise revenue", "best-selling product"),
            """
            SELECT product, ROUND(SUM(revenue), 2) AS revenue
            FROM sales
            GROUP BY product
            ORDER BY revenue DESC
            """,
        ),
        "units_by_product": (
            ("units by product", "units sold", "sales volume"),
            """
            SELECT product, SUM(units) AS units_sold
            FROM sales
            GROUP BY product
            ORDER BY units_sold DESC
            """,
        ),
        "revenue_by_quarter": (
            ("revenue by quarter", "quarterly revenue", "quarter-wise revenue"),
            """
            SELECT quarter, ROUND(SUM(revenue), 2) AS revenue
            FROM sales
            GROUP BY quarter
            ORDER BY quarter
            """,
        ),
    }

    selected = None
    for query_name, (phrases, sql) in approved_queries.items():
        if any(phrase in q for phrase in phrases):
            selected = (query_name, sql)
            break

    if selected is None:
        return {
            "status": "unsupported",
            "query_name": None,
            "data": [],
            "message": (
                "Supported requests include total revenue, revenue by region, "
                "revenue by product, units sold, and quarterly revenue."
            ),
        }

    query_name, sql = selected

    # SQLite is opened only inside this function. The tool runs only
    # fixed SELECT statements defined above.
    with get_connection() as connection:
        rows = connection.execute(sql).fetchall()

    return {
        "status": "success",
        "query_name": query_name,
        "data": [dict(row) for row in rows],
        "message": "Results came from the local demo sales database.",
    }
