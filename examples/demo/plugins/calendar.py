"""Calendar plugin for Odin demo."""

from datetime import datetime, timedelta
from typing import ClassVar

from odin import DecoratorPlugin, tool


class CalendarPlugin(DecoratorPlugin):
    """Calendar management plugin."""

    _events: ClassVar[list[dict]] = []

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Manage calendar events"

    @tool(description="Create a new calendar event")
    async def create_event(
        self, title: str, date: str, time: str = "09:00", duration: int = 60
    ) -> dict:
        """Create a new calendar event.

        Args:
            title: Event title
            date: Event date (YYYY-MM-DD or 'tomorrow', 'next monday')
            time: Event time (HH:MM format)
            duration: Duration in minutes
        """
        today = datetime.now()
        if date.lower() == "tomorrow":
            event_date = today + timedelta(days=1)
            date_str = event_date.strftime("%Y-%m-%d")
        elif date.lower().startswith("next "):
            day_name = date.lower().replace("next ", "")
            days_map = {
                "monday": 0, "tuesday": 1, "wednesday": 2,
                "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
            }
            if day_name in days_map:
                target_day = days_map[day_name]
                current_day = today.weekday()
                days_ahead = target_day - current_day
                if days_ahead <= 0:
                    days_ahead += 7
                event_date = today + timedelta(days=days_ahead)
                date_str = event_date.strftime("%Y-%m-%d")
            else:
                date_str = date
        else:
            date_str = date

        event = {
            "id": len(self._events) + 1,
            "title": title,
            "date": date_str,
            "time": time,
            "duration": duration,
            "created_at": datetime.now().isoformat(),
        }
        self._events.append(event)

        return {
            "status": "created",
            "event": event,
            "message": f"Event '{title}' scheduled for {date_str} at {time}",
        }

    @tool(description="List upcoming calendar events")
    async def list_events(self, limit: int = 10) -> dict:
        """List upcoming calendar events.

        Args:
            limit: Maximum number of events to return
        """
        sorted_events = sorted(
            self._events,
            key=lambda e: (e["date"], e["time"])
        )[:limit]

        return {"count": len(sorted_events), "events": sorted_events}

    @tool(description="Delete a calendar event by ID")
    async def delete_event(self, event_id: int) -> dict:
        """Delete a calendar event.

        Args:
            event_id: ID of the event to delete
        """
        for i, event in enumerate(self._events):
            if event["id"] == event_id:
                deleted = self._events.pop(i)
                return {
                    "status": "deleted",
                    "event": deleted,
                    "message": f"Event '{deleted['title']}' has been deleted",
                }

        return {"status": "not_found", "message": f"Event with ID {event_id} not found"}
