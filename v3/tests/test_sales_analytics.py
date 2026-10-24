
from app.tools.sales_analytics import run_sales_analytics


def test_total_revenue_uses_demo_database():
    result = run_sales_analytics("What is the total revenue?")

    assert result["status"] == "success"
    assert result["query_name"] == "total_revenue"
    assert result["data"][0]["total_revenue"] > 0


def test_revenue_by_region_returns_rows():
    result = run_sales_analytics("Show revenue by region")

    assert result["status"] == "success"
    assert len(result["data"]) > 0
    assert "region" in result["data"][0]
    assert "revenue" in result["data"][0]


def test_unsupported_analytics_request_is_rejected():
    result = run_sales_analytics("Predict next year's stock price")

    assert result["status"] == "unsupported"
    assert result["data"] == []
