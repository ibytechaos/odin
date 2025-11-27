"""Weather plugin for Odin demo."""

from odin import DecoratorPlugin, tool


class WeatherPlugin(DecoratorPlugin):
    """Weather information plugin."""

    @property
    def name(self) -> str:
        return "weather"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Get weather information for any location"

    @tool(description="Get current weather for a location")
    async def get_weather(self, location: str, unit: str = "celsius") -> dict:
        """Get current weather for a location.

        Args:
            location: City name or location
            unit: Temperature unit (celsius or fahrenheit)
        """
        weather_data = {
            "tokyo": {"temp_c": 22, "condition": "Partly Cloudy", "humidity": 65},
            "new york": {"temp_c": 18, "condition": "Sunny", "humidity": 45},
            "london": {"temp_c": 15, "condition": "Rainy", "humidity": 80},
            "paris": {"temp_c": 20, "condition": "Cloudy", "humidity": 55},
            "san francisco": {"temp_c": 17, "condition": "Foggy", "humidity": 70},
            "beijing": {"temp_c": 12, "condition": "Hazy", "humidity": 40},
            "sydney": {"temp_c": 25, "condition": "Sunny", "humidity": 55},
        }

        data = weather_data.get(location.lower(), {
            "temp_c": 20, "condition": "Clear", "humidity": 50
        })

        temp = data["temp_c"]
        if unit.lower() == "fahrenheit":
            temp = round(temp * 9 / 5 + 32)
            unit_symbol = "°F"
        else:
            unit_symbol = "°C"

        return {
            "location": location,
            "temperature": f"{temp}{unit_symbol}",
            "condition": data["condition"],
            "humidity": f"{data['humidity']}%",
        }

    @tool(description="Get weather forecast for multiple days")
    async def get_forecast(self, location: str, days: int = 5) -> dict:
        """Get weather forecast for a location.

        Args:
            location: City name or location
            days: Number of days to forecast (1-7)
        """
        import random
        days = min(max(days, 1), 7)
        random.seed(hash(location))

        conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Clear"]
        forecast = []

        for i in range(days):
            forecast.append({
                "day": i + 1,
                "condition": random.choice(conditions),
                "high": random.randint(18, 28),
                "low": random.randint(10, 17),
            })

        return {
            "location": location,
            "days": days,
            "forecast": forecast,
        }
