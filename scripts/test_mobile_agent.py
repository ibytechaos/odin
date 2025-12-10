#!/usr/bin/env python
"""Test Mobile Agent with HarmonyOS device using VLM."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def main():
    """Test mobile agent with real HarmonyOS device."""
    from openai import AsyncOpenAI

    from odin.agents.mobile.factory import (
        create_controller,
        create_mobile_agent,
        create_mobile_plugin,
    )
    from odin.config.settings import get_settings
    from odin.plugins.builtin.mobile.interaction import CLIInteractionHandler

    settings = get_settings()

    print("=" * 60)
    print("Testing Mobile Agent with HarmonyOS Device")
    print("=" * 60)
    print(f"Device ID: {settings.mobile_device_id}")
    print(f"Controller: {settings.mobile_controller}")
    print(f"VLM Model: {settings.vlm_model}")
    print(f"VLM Base URL: {settings.vlm_base_url}")
    print("=" * 60)

    # Create controller for HarmonyOS
    controller = create_controller(
        controller_type=settings.mobile_controller,
        device_id=settings.mobile_device_id,
        hdc_path=settings.mobile_hdc_path,
    )

    # Test connection
    connected = await controller.is_connected()
    print(f"\n[Connection] Device connected: {connected}")
    if not connected:
        print("ERROR: Device not connected!")
        return

    # Get screen size
    width, height = await controller.get_screen_size()
    print(f"[Screen] Size: {width}x{height}")

    # Create LLM client
    llm_client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    # Create VLM client
    vlm_client = AsyncOpenAI(
        api_key=settings.vlm_api_key,
        base_url=settings.vlm_base_url,
    )

    # Create plugin with CLI interaction handler
    plugin = create_mobile_plugin(
        controller=controller,
        interaction_handler=CLIInteractionHandler(),
        tool_delay_ms=settings.mobile_tool_delay_ms,
    )

    # Create mobile agent
    agent = create_mobile_agent(
        mode=settings.mobile_agent_mode,
        plugin=plugin,
        llm_client=llm_client,
        vlm_client=vlm_client,
        llm_model=settings.openai_model,
        vlm_model=settings.vlm_model,
        max_rounds=settings.mobile_max_rounds,
    )

    print(f"\n[Agent] Created {type(agent).__name__}")
    print(f"[Agent] Mode: {settings.mobile_agent_mode}")
    print(f"[Agent] Max rounds: {settings.mobile_max_rounds}")

    # Take initial screenshot and analyze
    print("\n[Test] Taking screenshot and analyzing with VLM...")
    screenshot = await controller.screenshot()
    print(f"[Screenshot] Size: {len(screenshot)} bytes")

    # Test VLM analysis
    import base64

    screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")

    print("\n[VLM] Analyzing screenshot...")
    response = await vlm_client.chat.completions.create(
        model=settings.vlm_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe what you see on this mobile screen. What app is open? What elements are visible?",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"},
                    },
                ],
            }
        ],
        max_tokens=500,
    )

    print("\n[VLM Response]")
    print("-" * 40)
    print(response.choices[0].message.content)
    print("-" * 40)

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
