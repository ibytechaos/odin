"""A2A Client demonstration.

This example shows how to interact with an A2A server programmatically.

Make sure to run the A2A server first:
```bash
python examples/a2a_server_demo.py
```

Then run this client:
```bash
python examples/a2a_client_demo.py
```
"""

import asyncio
import httpx


async def main():
    """Demonstrate A2A client interactions."""
    print("=" * 70)
    print("Odin A2A Client Demo")
    print("=" * 70)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Get Agent Card
        print("\n[1/5] Fetching Agent Card...")
        print("-" * 70)

        response = await client.get(f"{base_url}/.well-known/agent-card")
        if response.status_code == 200:
            agent_card = response.json()
            print(f"  Agent Name: {agent_card['name']}")
            print(f"  Description: {agent_card['description']}")
            print(f"  Protocol Version: {agent_card['protocolVersion']}")
            print(f"  Capabilities:")
            print(f"    - Streaming: {agent_card['capabilities']['streaming']}")
            print(
                f"    - Push Notifications: {agent_card['capabilities']['pushNotifications']}"
            )
            print(f"  Skills: {len(agent_card.get('skills', []))}")
            for skill in agent_card.get("skills", []):
                print(f"    - {skill['name']}: {skill['description']}")
        else:
            print(f"  ✗ Failed to get agent card: {response.status_code}")
            return

        # 2. Send a message
        print("\n[2/5] Sending message to agent...")
        print("-" * 70)

        message_request = {
            "message": {
                "role": "USER",
                "parts": [
                    {"type": "text", "text": "Hello! Can you add 25 and 17 for me?"}
                ],
            },
            "contextId": "demo-context",
        }

        response = await client.post(
            f"{base_url}/message/send",
            json=message_request,
        )

        if response.status_code == 200:
            result = response.json()
            task = result.get("task")
            if task:
                task_id = task["id"]
                print(f"  Task created: {task_id}")
                print(f"  Status: {task['status']['state']}")
                print(f"  Message: {task['status'].get('message', 'N/A')}")

                # Wait a bit for processing
                await asyncio.sleep(2)

                # 3. Get task status
                print("\n[3/5] Checking task status...")
                print("-" * 70)

                response = await client.get(
                    f"{base_url}/tasks/{task_id}",
                    params={"include_history": True},
                )

                if response.status_code == 200:
                    task_data = response.json()["task"]
                    print(f"  Task ID: {task_data['id']}")
                    print(f"  Status: {task_data['status']['state']}")
                    print(f"  Message: {task_data['status'].get('message', 'N/A')}")

                    if task_data.get("artifacts"):
                        print(f"  Artifacts: {len(task_data['artifacts'])}")
                        for i, artifact in enumerate(task_data["artifacts"], 1):
                            print(f"\n  Artifact {i}:")
                            for part in artifact["parts"]:
                                if part["type"] == "text":
                                    print(f"    {part['text']}")
                else:
                    print(f"  ✗ Failed to get task: {response.status_code}")
            else:
                # Direct message response (no task)
                message = result.get("message")
                if message:
                    print("  Direct response:")
                    for part in message["parts"]:
                        if part["type"] == "text":
                            print(f"    {part['text']}")
        else:
            print(f"  ✗ Failed to send message: {response.status_code}")
            return

        # 4. List tasks
        print("\n[4/5] Listing tasks...")
        print("-" * 70)

        response = await client.get(
            f"{base_url}/tasks",
            params={
                "context_id": "demo-context",
                "limit": 10,
            },
        )

        if response.status_code == 200:
            data = response.json()
            print(f"  Total tasks: {data['total']}")
            print(f"  Showing: {len(data['tasks'])}")

            for task in data["tasks"]:
                print(f"\n  Task {task['id'][:8]}...")
                print(f"    Status: {task['status']['state']}")
                print(
                    f"    Created: {task['createdAt'][:19].replace('T', ' ')}"
                )
        else:
            print(f"  ✗ Failed to list tasks: {response.status_code}")

        # 5. Send streaming message
        print("\n[5/5] Sending streaming message...")
        print("-" * 70)

        streaming_request = {
            "message": {
                "role": "USER",
                "parts": [
                    {
                        "type": "text",
                        "text": "Can you reverse this text: 'Hello A2A Protocol'?",
                    }
                ],
            },
            "contextId": "demo-context",
        }

        print("  Connecting to streaming endpoint...")

        async with client.stream(
            "POST",
            f"{base_url}/message/send/streaming",
            json=streaming_request,
        ) as response:
            if response.status_code == 200:
                print("  Receiving events:")

                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        print(f"\n  Event: {event_type}")
                    elif line.startswith("data:"):
                        import json

                        data = line.split(":", 1)[1].strip()
                        try:
                            event_data = json.loads(data)
                            if event_type == "taskCreated":
                                print(f"    Task ID: {event_data.get('id', 'N/A')}")
                            elif event_type == "taskStatus":
                                status = event_data.get("status", {})
                                print(f"    State: {status.get('state')}")
                                print(f"    Message: {status.get('message', 'N/A')}")
                            elif event_type == "taskArtifact":
                                artifact = event_data.get("artifact", {})
                                print(f"    Artifact ID: {artifact.get('artifactId')}")
                                for part in artifact.get("parts", []):
                                    if part["type"] == "text":
                                        print(f"    Content: {part['text'][:100]}...")
                        except json.JSONDecodeError:
                            print(f"    Raw data: {data[:100]}")
            else:
                print(f"  ✗ Failed to connect: {response.status_code}")

    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nClient stopped by user")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
