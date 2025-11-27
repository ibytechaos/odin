"""Example plugin - customize this for your agent."""

from odin import DecoratorPlugin, tool


class ExamplePlugin(DecoratorPlugin):
    """Example plugin demonstrating Odin's @tool decorator.

    This plugin is automatically discovered and loaded by Odin.
    Add your own tools by creating methods with the @tool decorator.
    """

    @property
    def name(self) -> str:
        return "example"

    @property
    def version(self) -> str:
        return "1.0.0"

    @tool(description="Say hello to someone")
    async def greet(self, name: str = "World") -> dict:
        """Greet a user by name.

        Args:
            name: The name to greet (default: World)
        """
        return {"message": f"Hello, {name}!", "greeted": name}

    @tool(description="Add two numbers together")
    async def add(self, a: float, b: float) -> dict:
        """Add two numbers.

        Args:
            a: First number
            b: Second number
        """
        return {"result": a + b, "operation": f"{a} + {b}"}

    @tool(description="Get current timestamp")
    async def get_time(self) -> dict:
        """Get the current server time."""
        from datetime import datetime

        now = datetime.now()
        return {
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
        }
