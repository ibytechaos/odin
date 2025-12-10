#!/usr/bin/env python
"""Test HDC connection with HarmonyOS device."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from odin.plugins.builtin.mobile.controllers.hdc import HDCConfig, HDCController


async def main():
    """Test HDC controller functionality."""
    config = HDCConfig(device_id="33Z0224A12003916")
    controller = HDCController(config)

    print("=" * 60)
    print("Testing HDC Controller for HarmonyOS")
    print("=" * 60)

    # Test 1: Check connection
    print("\n[Test 1] Checking device connection...")
    connected = await controller.is_connected()
    print(f"  Connected: {connected}")
    if not connected:
        print("  ERROR: Device not connected!")
        return

    # Test 2: Get screen size
    print("\n[Test 2] Getting screen size...")
    try:
        width, height = await controller.get_screen_size()
        print(f"  Screen size: {width}x{height}")
    except Exception as e:
        print(f"  ERROR: {e}")
        width, height = 1260, 2844  # Use default for subsequent tests

    # Test 3: Take screenshot
    print("\n[Test 3] Taking screenshot...")
    try:
        screenshot = await controller.screenshot()
        screenshot_path = Path(__file__).parent / "test_screenshot.jpeg"
        screenshot_path.write_bytes(screenshot)
        print(f"  Screenshot saved to: {screenshot_path}")
        print(f"  Size: {len(screenshot)} bytes")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test 4: Test tap (center of screen)
    print("\n[Test 4] Testing tap at center of screen...")
    try:
        center_x, center_y = width // 2, height // 2
        await controller.tap(center_x, center_y)
        print(f"  Tapped at ({center_x}, {center_y})")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
