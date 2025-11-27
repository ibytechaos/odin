"""AG-UI Client Demo.

Demonstrates how to interact with an AG-UI server programmatically.

Requirements:
1. Start the AG-UI server: PYTHONPATH=src uv run python examples/end_to_end_agent.py --protocol agui
2. Run this client: PYTHONPATH=src uv run python examples/agui_client_demo.py
"""

import asyncio
import json

import httpx

from odin.logging import get_logger

logger = get_logger(__name__)


async def test_health_check(client: httpx.AsyncClient, base_url: str):
    """Test health check endpoint."""
    logger.info("Testing health check endpoint")

    response = await client.get(f"{base_url}/health")

    if response.status_code == 200:
        data = response.json()
        logger.info(
            "Health check passed",
            status=data.get("status"),
            version=data.get("version"),
        )
        return True
    else:
        logger.error("Health check failed", status_code=response.status_code)
        return False


async def test_weather_query(client: httpx.AsyncClient, base_url: str):
    """Test weather query via AG-UI."""
    logger.info("Testing weather query")

    request_data = {
        "thread_id": "thread-001",
        "run_id": "run-001",
        "messages": [
            {
                "role": "user",
                "content": "What's the current weather in San Francisco?",
            }
        ],
    }

    logger.info("Sending AG-UI request", thread_id=request_data["thread_id"])

    try:
        async with client.stream(
            "POST",
            f"{base_url}/",
            json=request_data,
            headers={"Accept": "text/event-stream"},
            timeout=30.0,
        ) as response:
            if response.status_code != 200:
                logger.error(
                    "Request failed",
                    status_code=response.status_code,
                    body=await response.aread(),
                )
                return False

            logger.info("Receiving SSE events")

            event_count = 0
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    event_count += 1
                    data_str = line[5:].strip()  # Remove "data:" prefix

                    try:
                        event = json.loads(data_str)
                        event_type = event.get("event")

                        if event_type == "RUN_STARTED":
                            logger.info(
                                "Run started",
                                thread_id=event.get("thread_id"),
                                run_id=event.get("run_id"),
                            )

                        elif event_type == "TEXT_MESSAGE_CHUNK":
                            delta = event.get("delta", "")
                            logger.info(
                                "Text chunk received",
                                message_id=event.get("message_id"),
                                delta=delta[:50] + ("..." if len(delta) > 50 else ""),
                            )

                        elif event_type == "TOOL_CALL_CHUNK":
                            logger.info(
                                "Tool call",
                                tool=event.get("tool_call_name"),
                                tool_call_id=event.get("tool_call_id"),
                            )

                        elif event_type == "RUN_FINISHED":
                            logger.info(
                                "Run completed",
                                thread_id=event.get("thread_id"),
                                run_id=event.get("run_id"),
                            )

                        elif event_type == "RUN_ERROR":
                            logger.error(
                                "Run error",
                                message=event.get("message"),
                                error=event.get("error"),
                            )

                    except json.JSONDecodeError as e:
                        logger.warning("Invalid JSON in SSE event", error=str(e))

            logger.info("SSE stream completed", total_events=event_count)
            return event_count > 0

    except Exception as e:
        logger.error("Request failed with exception", error=str(e), exc_info=True)
        return False


async def test_calendar_event(client: httpx.AsyncClient, base_url: str):
    """Test calendar event creation via AG-UI."""
    logger.info("Testing calendar event creation")

    request_data = {
        "thread_id": "thread-002",
        "run_id": "run-002",
        "messages": [
            {
                "role": "user",
                "content": "Create a meeting for tomorrow at 2pm",
            }
        ],
    }

    logger.info("Sending calendar event request")

    try:
        async with client.stream(
            "POST",
            f"{base_url}/",
            json=request_data,
            headers={"Accept": "text/event-stream"},
            timeout=30.0,
        ) as response:
            if response.status_code != 200:
                logger.error("Request failed", status_code=response.status_code)
                return False

            event_count = 0
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    event_count += 1
                    data_str = line[5:].strip()

                    try:
                        event = json.loads(data_str)
                        event_type = event.get("event")
                        logger.info("Event received", type=event_type)

                    except json.JSONDecodeError:
                        pass

            logger.info("Calendar test completed", events=event_count)
            return event_count > 0

    except Exception as e:
        logger.error("Calendar test failed", error=str(e))
        return False


async def main():
    """Run AG-UI client tests."""
    base_url = "http://localhost:8000"

    logger.info("=" * 70)
    logger.info("AG-UI Client Demo")
    logger.info("=" * 70)
    logger.info("Target server", url=base_url)

    async with httpx.AsyncClient() as client:
        # Test 1: Health check
        logger.info("\n[Test 1/3] Health Check")
        health_ok = await test_health_check(client, base_url)

        if not health_ok:
            logger.error("Server is not healthy. Is it running?")
            return

        # Test 2: Weather query
        logger.info("\n[Test 2/3] Weather Query")
        weather_ok = await test_weather_query(client, base_url)

        if weather_ok:
            logger.info("Weather query test: PASSED")
        else:
            logger.error("Weather query test: FAILED")

        # Test 3: Calendar event
        logger.info("\n[Test 3/3] Calendar Event")
        calendar_ok = await test_calendar_event(client, base_url)

        if calendar_ok:
            logger.info("Calendar test: PASSED")
        else:
            logger.error("Calendar test: FAILED")

    logger.info("=" * 70)

    if health_ok and weather_ok and calendar_ok:
        logger.info("All tests PASSED")
    else:
        logger.warning("Some tests FAILED")

    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        raise
