"""Data plugin for Odin demo - generates tables and charts data."""

import random
from datetime import datetime, timedelta

from odin import DecoratorPlugin, tool


class DataPlugin(DecoratorPlugin):
    """Data generation plugin for UI demonstrations."""

    @property
    def name(self) -> str:
        return "data"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Generate sample data for tables and visualizations"

    @tool(description="Generate a sales report table")
    async def get_sales_report(self, period: str = "monthly", limit: int = 10) -> dict:
        """Generate a sales report with tabular data.

        Args:
            period: Report period (daily, weekly, monthly)
            limit: Number of rows to generate
        """
        random.seed(42)  # Consistent data

        products = ["Laptop", "Phone", "Tablet", "Monitor", "Keyboard", "Mouse", "Headphones"]
        regions = ["North", "South", "East", "West", "Central"]

        rows = []
        base_date = datetime.now()

        for i in range(limit):
            if period == "daily":
                date = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
            elif period == "weekly":
                date = f"Week {limit - i}"
            else:
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                date = months[i % 12]

            rows.append({
                "date": date,
                "product": random.choice(products),
                "region": random.choice(regions),
                "units": random.randint(10, 500),
                "revenue": round(random.uniform(1000, 50000), 2),
                "profit_margin": f"{random.randint(10, 40)}%",
            })

        return {
            "title": f"Sales Report ({period.capitalize()})",
            "columns": ["Date", "Product", "Region", "Units", "Revenue ($)", "Margin"],
            "rows": rows,
            "summary": {
                "total_units": sum(r["units"] for r in rows),
                "total_revenue": round(sum(r["revenue"] for r in rows), 2),
                "avg_margin": f"{sum(int(r['profit_margin'].strip('%')) for r in rows) // len(rows)}%",
            },
        }

    @tool(description="Generate user analytics data")
    async def get_user_analytics(self, days: int = 7) -> dict:
        """Generate user analytics data for visualization.

        Args:
            days: Number of days of data to generate
        """
        random.seed(123)
        base_date = datetime.now()

        data = []
        for i in range(days):
            date = (base_date - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            data.append({
                "date": date,
                "active_users": random.randint(1000, 5000),
                "new_signups": random.randint(50, 300),
                "page_views": random.randint(10000, 50000),
                "avg_session_duration": f"{random.randint(2, 15)}m {random.randint(0, 59)}s",
                "bounce_rate": f"{random.randint(20, 60)}%",
            })

        return {
            "title": f"User Analytics (Last {days} Days)",
            "columns": ["Date", "Active Users", "New Signups", "Page Views", "Avg Session", "Bounce Rate"],
            "data": data,
            "trends": {
                "users_growth": f"+{random.randint(5, 25)}%",
                "engagement_change": f"+{random.randint(1, 10)}%",
            },
        }

    @tool(description="Compare products or items in a table")
    async def compare_items(self, category: str = "phones") -> dict:
        """Generate a comparison table for products.

        Args:
            category: Product category to compare (phones, laptops, cars)
        """
        comparisons = {
            "phones": {
                "title": "Smartphone Comparison",
                "items": ["iPhone 15 Pro", "Samsung S24 Ultra", "Pixel 8 Pro", "OnePlus 12"],
                "attributes": [
                    {"name": "Price", "values": ["$999", "$1199", "$899", "$799"]},
                    {"name": "Display", "values": ["6.1\" OLED", "6.8\" AMOLED", "6.7\" OLED", "6.82\" AMOLED"]},
                    {"name": "Battery", "values": ["3274mAh", "5000mAh", "5050mAh", "5400mAh"]},
                    {"name": "Camera", "values": ["48MP", "200MP", "50MP", "50MP"]},
                    {"name": "Storage", "values": ["256GB", "256GB", "128GB", "256GB"]},
                    {"name": "Rating", "values": ["4.8/5", "4.7/5", "4.6/5", "4.5/5"]},
                ],
            },
            "laptops": {
                "title": "Laptop Comparison",
                "items": ["MacBook Pro 14", "Dell XPS 15", "ThinkPad X1", "Surface Laptop"],
                "attributes": [
                    {"name": "Price", "values": ["$1999", "$1499", "$1649", "$1299"]},
                    {"name": "CPU", "values": ["M3 Pro", "i7-13700H", "i7-1365U", "i7-1255U"]},
                    {"name": "RAM", "values": ["18GB", "16GB", "16GB", "16GB"]},
                    {"name": "Storage", "values": ["512GB SSD", "512GB SSD", "512GB SSD", "256GB SSD"]},
                    {"name": "Display", "values": ["14.2\" Retina", "15.6\" OLED", "14\" 2.8K", "13.5\" Touch"]},
                    {"name": "Battery Life", "values": ["17 hours", "13 hours", "15 hours", "18 hours"]},
                ],
            },
            "cars": {
                "title": "Electric Vehicle Comparison",
                "items": ["Tesla Model 3", "BMW i4", "Mercedes EQE", "Porsche Taycan"],
                "attributes": [
                    {"name": "Price", "values": ["$40,240", "$52,200", "$74,900", "$82,700"]},
                    {"name": "Range", "values": ["272 mi", "301 mi", "305 mi", "246 mi"]},
                    {"name": "0-60 mph", "values": ["5.8s", "5.5s", "4.5s", "5.1s"]},
                    {"name": "Top Speed", "values": ["140 mph", "118 mph", "137 mph", "143 mph"]},
                    {"name": "Charging", "values": ["250kW", "200kW", "170kW", "270kW"]},
                    {"name": "Rating", "values": ["4.9/5", "4.6/5", "4.5/5", "4.7/5"]},
                ],
            },
        }

        data = comparisons.get(category.lower(), comparisons["phones"])
        return {
            "type": "comparison_table",
            **data,
        }

    @tool(description="Generate a leaderboard or ranking table")
    async def get_leaderboard(self, type: str = "sales", limit: int = 10) -> dict:
        """Generate a leaderboard/ranking table.

        Args:
            type: Type of leaderboard (sales, performance, engagement)
            limit: Number of entries to show
        """
        random.seed(456)

        names = [
            "Alice Chen", "Bob Smith", "Carol Davis", "David Lee", "Emma Wilson",
            "Frank Brown", "Grace Kim", "Henry Zhang", "Iris Patel", "Jack Miller",
            "Karen White", "Leo Garcia", "Mia Johnson", "Noah Anderson", "Olivia Taylor"
        ]

        entries = []
        for i in range(min(limit, len(names))):
            if type == "sales":
                entries.append({
                    "rank": i + 1,
                    "name": names[i],
                    "deals_closed": random.randint(10, 50),
                    "revenue": f"${random.randint(50, 500)}K",
                    "target_achieved": f"{random.randint(80, 150)}%",
                })
            elif type == "performance":
                entries.append({
                    "rank": i + 1,
                    "name": names[i],
                    "tasks_completed": random.randint(20, 100),
                    "quality_score": round(random.uniform(4.0, 5.0), 1),
                    "efficiency": f"{random.randint(85, 100)}%",
                })
            else:  # engagement
                entries.append({
                    "rank": i + 1,
                    "name": names[i],
                    "posts": random.randint(10, 100),
                    "likes": random.randint(100, 5000),
                    "comments": random.randint(20, 500),
                })

        return {
            "title": f"Top {limit} - {type.capitalize()} Leaderboard",
            "type": type,
            "entries": entries,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
