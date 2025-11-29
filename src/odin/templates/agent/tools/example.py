"""Example tools - customize this for your agent."""

from odin.plugins import DecoratorPlugin
from odin.decorators import tool


class ExampleTools(DecoratorPlugin):
    """Example tools demonstrating Odin's @tool decorator.

    This plugin is automatically discovered and loaded by Odin.
    Add your own tools by creating methods with the @tool() decorator.
    """

    @property
    def name(self) -> str:
        return "example"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Example tools demonstrating Odin framework"

    @tool()
    def greet(self, name: str = "World") -> dict:
        """Say hello to someone.

        Args:
            name: The name to greet (default: World)

        Returns:
            Greeting message
        """
        return {"message": f"Hello, {name}!", "greeted": name}

    @tool()
    def add(self, a: float, b: float) -> dict:
        """Add two numbers together.

        Args:
            a: First number
            b: Second number

        Returns:
            Sum of the two numbers
        """
        return {"result": a + b, "operation": f"{a} + {b}"}

    @tool()
    def get_time(self) -> dict:
        """Get current server timestamp.

        Returns:
            Current date and time information
        """
        from datetime import datetime

        now = datetime.now()
        return {
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
        }
