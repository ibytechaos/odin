"""UI Generation Tools - Tools that return UI component definitions.

These tools demonstrate the core pattern for Generative UI:
1. Tool performs some business logic
2. Tool returns a structured UI component definition
3. Frontend matches the tool name and renders the component

The key insight: Agent doesn't need special prompts to output UI format.
It simply calls tools, and tools return UI-friendly data structures.
The CopilotKit SDK handles the rest.
"""

from odin.plugins import AgentPlugin
from odin.decorators import tool


class UIToolsPlugin(AgentPlugin):
    """Plugin providing UI-generating tools."""

    name = "ui_tools"
    description = "Tools that generate interactive UI components"

    @tool
    def create_chart(
        self,
        data: list[dict],
        chart_type: str = "bar",
        title: str = "Chart",
        x_axis: str = "name",
        y_axis: str = "value",
    ) -> dict:
        """Create an interactive data visualization chart.

        The chart will be rendered in the chat UI as an interactive component.

        Args:
            data: List of data points, e.g. [{"name": "A", "value": 10}, {"name": "B", "value": 20}]
            chart_type: Type of chart - "bar", "line", or "pie"
            title: Chart title
            x_axis: Key for x-axis data
            y_axis: Key for y-axis data

        Returns:
            UI component definition that frontend will render as a chart
        """
        # Validate data
        if not data:
            return {"error": "No data provided"}

        # Return UI component definition
        # The frontend will match this to a useCopilotAction with name="create_chart"
        return {
            "component": "chart",
            "chartType": chart_type,
            "title": title,
            "data": data,
            "xAxis": x_axis,
            "yAxis": y_axis,
        }

    @tool
    def create_table(
        self,
        rows: list[dict],
        title: str = "Data Table",
    ) -> dict:
        """Create an interactive data table.

        The table will be rendered with sortable columns and row actions.

        Args:
            rows: List of row data, e.g. [{"id": 1, "name": "Alice", "email": "alice@example.com"}]
            title: Table title

        Returns:
            UI component definition for a data table
        """
        if not rows:
            return {"error": "No data provided"}

        # Extract column names from first row
        columns = list(rows[0].keys()) if rows else []

        return {
            "component": "table",
            "title": title,
            "columns": columns,
            "rows": rows,
        }

    @tool
    def create_card(
        self,
        title: str,
        content: str,
        image_url: str | None = None,
        actions: list[dict] | None = None,
    ) -> dict:
        """Create an interactive card component.

        Cards can display content with optional image and action buttons.

        Args:
            title: Card title
            content: Card content/description
            image_url: Optional image URL
            actions: Optional list of action buttons, e.g. [{"label": "Buy", "action": "buy"}]

        Returns:
            UI component definition for a card
        """
        return {
            "component": "card",
            "title": title,
            "content": content,
            "imageUrl": image_url,
            "actions": actions or [],
        }

    @tool
    def create_progress(
        self,
        current: int,
        total: int,
        label: str = "Progress",
        status: str = "in_progress",
    ) -> dict:
        """Create a progress indicator.

        Shows progress of a long-running operation.

        Args:
            current: Current progress value
            total: Total/target value
            label: Progress label
            status: Status - "in_progress", "completed", "error"

        Returns:
            UI component definition for a progress bar
        """
        percentage = min(100, int((current / total) * 100)) if total > 0 else 0

        return {
            "component": "progress",
            "label": label,
            "current": current,
            "total": total,
            "percentage": percentage,
            "status": status,
        }

    @tool
    def create_form(
        self,
        title: str,
        fields: list[dict],
        submit_label: str = "Submit",
    ) -> dict:
        """Create an interactive form.

        The form allows users to input data that can be processed by the agent.

        Args:
            title: Form title
            fields: List of field definitions, e.g. [
                {"name": "email", "type": "email", "label": "Email", "required": True},
                {"name": "message", "type": "textarea", "label": "Message"}
            ]
            submit_label: Submit button label

        Returns:
            UI component definition for a form
        """
        return {
            "component": "form",
            "title": title,
            "fields": fields,
            "submitLabel": submit_label,
        }

    @tool
    def create_alert(
        self,
        message: str,
        type: str = "info",
        title: str | None = None,
        dismissable: bool = True,
    ) -> dict:
        """Create an alert/notification component.

        Args:
            message: Alert message
            type: Alert type - "info", "success", "warning", "error"
            title: Optional alert title
            dismissable: Whether the alert can be dismissed

        Returns:
            UI component definition for an alert
        """
        return {
            "component": "alert",
            "type": type,
            "title": title,
            "message": message,
            "dismissable": dismissable,
        }
