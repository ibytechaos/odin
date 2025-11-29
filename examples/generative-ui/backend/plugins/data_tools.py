"""Data Tools - Business logic tools that also generate UI.

These tools demonstrate real-world scenarios where:
1. Tool performs actual business logic (fetch data, calculate, etc.)
2. Tool returns results in UI-friendly format
3. Frontend renders rich visualization

This is the key pattern: your business logic tools naturally return
data that the frontend knows how to render beautifully.
"""

import random
from datetime import datetime, timedelta

from odin.plugins import DecoratorPlugin
from odin.decorators import tool


class DataToolsPlugin(DecoratorPlugin):
    """Plugin providing data analysis tools with UI output."""

    @property
    def name(self) -> str:
        return "data_tools"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Data analysis tools that generate visualizations"

    @tool()
    def get_sales_data(
        self,
        period: str = "week",
        product_category: str | None = None,
    ) -> dict:
        """Get sales data and return as a chart.

        Fetches sales data from the database and returns it formatted
        for visualization.

        Args:
            period: Time period - "day", "week", "month", "year"
            product_category: Optional filter by product category

        Returns:
            Chart component with sales data
        """
        # Simulate fetching data from database
        if period == "day":
            labels = [f"{i}:00" for i in range(0, 24, 2)]
            data = [random.randint(50, 200) for _ in labels]
        elif period == "week":
            labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            data = [random.randint(500, 2000) for _ in labels]
        elif period == "month":
            labels = [f"Week {i}" for i in range(1, 5)]
            data = [random.randint(5000, 20000) for _ in labels]
        else:  # year
            labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            data = [random.randint(50000, 150000) for _ in labels]

        chart_data = [{"name": l, "value": v} for l, v in zip(labels, data)]
        total = sum(data)

        return {
            "component": "chart",
            "chartType": "bar",
            "title": f"Sales Data ({period})" + (f" - {product_category}" if product_category else ""),
            "data": chart_data,
            "xAxis": "name",
            "yAxis": "value",
            "summary": {
                "total": total,
                "average": total // len(data),
                "period": period,
            }
        }

    @tool()
    def get_customer_list(
        self,
        status: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Get customer list and return as a table.

        Args:
            status: Filter by status - "active", "inactive", "pending"
            limit: Maximum number of customers to return

        Returns:
            Table component with customer data
        """
        # Simulate customer data
        statuses = [status] if status else ["active", "inactive", "pending"]
        customers = []

        first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
        domains = ["gmail.com", "outlook.com", "company.com", "example.com"]

        for i in range(min(limit, 20)):
            first = random.choice(first_names)
            last = random.choice(last_names)
            customers.append({
                "id": i + 1,
                "name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}@{random.choice(domains)}",
                "status": random.choice(statuses),
                "orders": random.randint(0, 50),
                "total_spent": f"${random.randint(100, 10000):,}",
            })

        return {
            "component": "table",
            "title": f"Customer List" + (f" ({status})" if status else ""),
            "columns": ["id", "name", "email", "status", "orders", "total_spent"],
            "rows": customers,
        }

    @tool()
    def get_product_details(
        self,
        product_id: int | None = None,
        product_name: str | None = None,
    ) -> dict:
        """Get product details and return as a card.

        Args:
            product_id: Product ID to look up
            product_name: Product name to search for

        Returns:
            Card component with product details
        """
        # Simulate product data
        products = [
            {
                "id": 1,
                "name": "iPhone 15 Pro",
                "price": 999,
                "description": "The most advanced iPhone yet with A17 Pro chip, titanium design, and pro-level camera system.",
                "image": "https://placehold.co/400x300/png?text=iPhone+15+Pro",
                "in_stock": True,
            },
            {
                "id": 2,
                "name": "MacBook Pro 14\"",
                "price": 1999,
                "description": "Supercharged by M3 Pro or M3 Max chip with up to 22 hours of battery life.",
                "image": "https://placehold.co/400x300/png?text=MacBook+Pro",
                "in_stock": True,
            },
            {
                "id": 3,
                "name": "AirPods Pro 2",
                "price": 249,
                "description": "Active Noise Cancellation, Adaptive Transparency, and Personalized Spatial Audio.",
                "image": "https://placehold.co/400x300/png?text=AirPods+Pro",
                "in_stock": False,
            },
        ]

        # Find product
        product = None
        if product_id:
            product = next((p for p in products if p["id"] == product_id), None)
        elif product_name:
            product = next((p for p in products if product_name.lower() in p["name"].lower()), None)

        if not product:
            # Return first product as default
            product = products[0]

        return {
            "component": "card",
            "title": product["name"],
            "content": product["description"],
            "imageUrl": product["image"],
            "price": f"${product['price']}",
            "inStock": product["in_stock"],
            "actions": [
                {"label": "Add to Cart", "action": "add_to_cart", "primary": True},
                {"label": "Save for Later", "action": "save"},
            ],
        }

    @tool()
    def analyze_metrics(
        self,
        metric_type: str = "revenue",
    ) -> dict:
        """Analyze business metrics and return visualization.

        Args:
            metric_type: Type of metric - "revenue", "users", "orders", "conversion"

        Returns:
            Multiple UI components showing the analysis
        """
        # Generate metric data
        if metric_type == "revenue":
            current = random.randint(80000, 120000)
            previous = random.randint(70000, 110000)
            trend_data = [
                {"name": "Week 1", "value": random.randint(15000, 30000)},
                {"name": "Week 2", "value": random.randint(15000, 30000)},
                {"name": "Week 3", "value": random.randint(15000, 30000)},
                {"name": "Week 4", "value": current // 4},
            ]
        elif metric_type == "users":
            current = random.randint(5000, 15000)
            previous = random.randint(4000, 12000)
            trend_data = [
                {"name": "Week 1", "value": random.randint(1000, 4000)},
                {"name": "Week 2", "value": random.randint(1000, 4000)},
                {"name": "Week 3", "value": random.randint(1000, 4000)},
                {"name": "Week 4", "value": current // 4},
            ]
        else:
            current = random.randint(1000, 5000)
            previous = random.randint(800, 4500)
            trend_data = [
                {"name": "Week 1", "value": random.randint(200, 1500)},
                {"name": "Week 2", "value": random.randint(200, 1500)},
                {"name": "Week 3", "value": random.randint(200, 1500)},
                {"name": "Week 4", "value": current // 4},
            ]

        change = ((current - previous) / previous) * 100 if previous > 0 else 0
        trend = "up" if change > 0 else "down" if change < 0 else "neutral"

        return {
            "component": "dashboard",
            "metric": metric_type,
            "current": current,
            "previous": previous,
            "change": round(change, 1),
            "trend": trend,
            "chart": {
                "type": "line",
                "data": trend_data,
            },
            "insights": [
                f"{'Increased' if change > 0 else 'Decreased'} by {abs(round(change, 1))}% from last period",
                f"Current {metric_type}: {current:,}",
                f"Trend is {trend}",
            ],
        }

    @tool()
    def search_products(
        self,
        query: str,
        category: str | None = None,
        max_price: float | None = None,
    ) -> dict:
        """Search products and return results as cards.

        Args:
            query: Search query
            category: Optional category filter
            max_price: Optional maximum price filter

        Returns:
            List of product cards matching the search
        """
        # Simulate search results
        all_products = [
            {"name": "iPhone 15", "price": 799, "category": "phones", "rating": 4.8},
            {"name": "iPhone 15 Pro", "price": 999, "category": "phones", "rating": 4.9},
            {"name": "Samsung Galaxy S24", "price": 899, "category": "phones", "rating": 4.7},
            {"name": "MacBook Air M3", "price": 1099, "category": "laptops", "rating": 4.9},
            {"name": "MacBook Pro 14", "price": 1999, "category": "laptops", "rating": 4.8},
            {"name": "Dell XPS 15", "price": 1499, "category": "laptops", "rating": 4.6},
            {"name": "AirPods Pro 2", "price": 249, "category": "audio", "rating": 4.8},
            {"name": "Sony WH-1000XM5", "price": 399, "category": "audio", "rating": 4.9},
        ]

        # Filter
        results = []
        for p in all_products:
            if query.lower() not in p["name"].lower():
                continue
            if category and p["category"] != category:
                continue
            if max_price and p["price"] > max_price:
                continue
            results.append(p)

        # Format as product cards
        cards = []
        for p in results[:5]:
            cards.append({
                "component": "card",
                "title": p["name"],
                "content": f"Rating: {'⭐' * int(p['rating'])} ({p['rating']})",
                "price": f"${p['price']}",
                "category": p["category"],
                "imageUrl": f"https://placehold.co/300x200/png?text={p['name'].replace(' ', '+')}",
                "actions": [
                    {"label": "View Details", "action": "view"},
                    {"label": "Add to Cart", "action": "add_to_cart", "primary": True},
                ],
            })

        return {
            "component": "search_results",
            "query": query,
            "total": len(results),
            "results": cards,
        }
