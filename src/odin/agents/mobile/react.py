"""ReAct agent for mobile automation.

This agent uses the ReAct pattern (Reasoning + Acting) with OpenAI function calling.
It follows the same approach as the dexter_mobile project, using validated prompts.
"""

import asyncio
import base64
import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

from odin.agents.mobile.base import AgentResult, AgentStatus, MobileAgentBase
from odin.agents.mobile.prompts import (
    SCREENSHOT_PROMPT,
    build_system_prompt,
    build_task_prompt,
)

# Debug mode: set ODIN_MOBILE_DEBUG=1 to enable detailed request logging
MOBILE_DEBUG = os.environ.get("ODIN_MOBILE_DEBUG", "0") == "1"


class MobileReActAgent(MobileAgentBase):
    """ReAct-style mobile automation agent.

    Uses OpenAI function calling with tools from MobilePlugin,
    following the same approach as the dexter_mobile project.
    """

    def _debug_log_tools(self, openai_tools: list[dict[str, Any]]) -> None:
        """Log tool definitions for debugging."""
        if not MOBILE_DEBUG:
            return
        self._log("debug", "=" * 60)
        self._log("debug", "TOOL DEFINITIONS (OpenAI format):")
        self._log("debug", "=" * 60)
        for tool in openai_tools:
            self._log("debug", json.dumps(tool, indent=2, ensure_ascii=False))
        self._log("debug", "=" * 60)

    def _debug_log_request(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> None:
        """Log the full LLM request for debugging."""
        if not MOBILE_DEBUG:
            return
        self._log("debug", "=" * 60)
        self._log("debug", "LLM REQUEST:")
        self._log("debug", "=" * 60)
        self._log("debug", f"Model: {self._llm_model}")
        self._log("debug", f"Tools count: {len(tools)}")
        self._log("debug", "Messages:")
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # Truncate image data for logging
            if isinstance(content, list):
                content_summary = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        content_summary.append({"type": "image_url", "url": "[BASE64_IMAGE_DATA]"})
                    else:
                        content_summary.append(item)
                content = content_summary
            self._log("debug", f"  [{i}] {role}: {json.dumps(content, ensure_ascii=False)[:500]}...")
        self._log("debug", "=" * 60)

    def _debug_log_response(self, response: Any) -> None:
        """Log the LLM response for debugging."""
        if not MOBILE_DEBUG:
            return
        self._log("debug", "=" * 60)
        self._log("debug", "LLM RESPONSE:")
        self._log("debug", "=" * 60)
        msg = response.choices[0].message
        self._log("debug", f"Finish reason: {response.choices[0].finish_reason}")
        self._log("debug", f"Content: {msg.content[:500] if msg.content else 'None'}...")
        if msg.tool_calls:
            self._log("debug", f"Tool calls: {len(msg.tool_calls)}")
            for tc in msg.tool_calls:
                self._log("debug", f"  - {tc.function.name}: {tc.function.arguments}")
        self._log("debug", "=" * 60)

    async def execute(self, task: str) -> AgentResult:
        """Execute a task using ReAct loop with function calling.

        Args:
            task: The task description to execute

        Returns:
            AgentResult with execution outcome
        """
        self.reset()
        self._status = AgentStatus.RUNNING
        self._log("info", f"Starting task: {task}")

        # Build initial messages with validated prompts
        datetime_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        system_prompt = build_system_prompt()
        task_prompt = build_task_prompt(main_task=task, datetime_str=datetime_str)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text", "text": task_prompt}]},
        ]

        # Get tools from plugin and convert to OpenAI format
        tools = await self._plugin.get_tools()
        openai_tools = [tool.to_openai_format() for tool in tools]
        self._log("debug", f"Loaded {len(openai_tools)} tools")

        # Debug: log tool definitions
        self._debug_log_tools(openai_tools)

        try:
            while self._current_round < self._max_rounds:
                if self._status == AgentStatus.PAUSED:
                    self._log("warning", "Execution paused")
                    return AgentResult(
                        success=False,
                        message="Execution paused",
                        steps_executed=self._current_round,
                    )

                self._current_round += 1
                self._log("info", f"Round {self._current_round}/{self._max_rounds}")

                # Take screenshot and add to messages
                self._log("debug", "Taking screenshot...")
                screenshot = await self._plugin._controller.screenshot()  # type: ignore[union-attr]
                img_b64 = base64.b64encode(screenshot).decode("utf-8")

                # Remove old screenshot messages to save context
                messages = [m for m in messages if not self._is_screenshot_message(m)]

                # Add new screenshot
                if self._current_round > 1:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                            {"type": "text", "text": SCREENSHOT_PROMPT},
                        ],
                    })
                else:
                    # First round - add initial screenshot
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                            {"type": "text", "text": "This is the current screen state."},
                        ],
                    })

                # ============ DEBUG: Log full request ============
                logger.info("=" * 80)
                logger.info("[DEBUG] LLM REQUEST (odin react)")
                logger.info("=" * 80)
                # 直接打印完整的 request payload（截断图片数据）
                debug_payload = {
                    "model": self._llm_model,
                    "tools": openai_tools,
                    "messages": [],
                }
                for m in messages:
                    msg_copy = {"role": m.get("role", "unknown")}
                    content = m.get("content", "")
                    if isinstance(content, list):
                        content_display = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "image_url":
                                content_display.append({"type": "image_url", "image_url": {"url": "[BASE64_TRUNCATED]"}})
                            else:
                                content_display.append(item)
                        msg_copy["content"] = content_display
                    else:
                        msg_copy["content"] = content
                    if "tool_calls" in m:
                        msg_copy["tool_calls"] = m["tool_calls"]
                    if "tool_call_id" in m:
                        msg_copy["tool_call_id"] = m["tool_call_id"]
                    debug_payload["messages"].append(msg_copy)
                logger.info(json.dumps(debug_payload, indent=2, ensure_ascii=False))
                logger.info("=" * 80)

                # Call LLM with tools
                self._log("debug", "Calling LLM...")
                response = await self._llm_client.chat.completions.create(
                    model=self._llm_model,
                    messages=messages,  # type: ignore[arg-type]
                    tools=openai_tools,  # type: ignore[arg-type]
                )

                # ============ DEBUG: Log full response ============
                logger.info("=" * 80)
                logger.info("[DEBUG] LLM RESPONSE (odin react)")
                logger.info("=" * 80)
                debug_response = {
                    "finish_reason": response.choices[0].finish_reason,
                    "content": response.choices[0].message.content,
                    "tool_calls": [
                        {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in (response.choices[0].message.tool_calls or [])
                    ] if response.choices[0].message.tool_calls else None,
                }
                logger.info(json.dumps(debug_response, indent=2, ensure_ascii=False))
                logger.info("=" * 80)

                msg = response.choices[0].message
                finish_reason = response.choices[0].finish_reason

                # Log assistant response
                if msg.content:
                    self._log("info", f"Assistant: {msg.content[:100]}...")

                # Add assistant message to history
                assistant_msg: dict[str, Any] = {"role": "assistant"}
                if msg.content:
                    assistant_msg["content"] = msg.content
                if msg.tool_calls:
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,  # type: ignore[union-attr]
                                "arguments": tc.function.arguments,  # type: ignore[union-attr]
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                messages.append(assistant_msg)

                # Check if we're done (no tool calls)
                if not msg.tool_calls or finish_reason != "tool_calls":
                    self._status = AgentStatus.COMPLETED
                    self._log("info", "Task completed - no more tool calls")
                    return AgentResult(
                        success=True,
                        message=msg.content or "Task completed",
                        steps_executed=self._current_round,
                        final_screenshot=screenshot,
                        variables=self._plugin._variables.copy(),
                    )

                # Execute tool calls
                for tool_call in msg.tool_calls:
                    try:
                        args = json.loads(tool_call.function.arguments)  # type: ignore[union-attr]
                    except json.JSONDecodeError:
                        self._log("warning", f"Failed to parse args: {tool_call.function.arguments}")  # type: ignore[union-attr]
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": "Error: Failed to parse arguments",
                        })
                        continue

                    tool_name = tool_call.function.name  # type: ignore[union-attr]
                    self._log("info", f"Tool: {tool_name}")
                    self._log("debug", f"Args: {json.dumps(args, ensure_ascii=False)}")

                    # Execute the tool using plugin
                    try:
                        result = await self._plugin.execute_tool(tool_name, **args)
                        result_str = json.dumps(result, ensure_ascii=False)
                        self._log("debug", f"Result: {result_str[:100]}...")
                    except Exception as e:
                        result_str = f"Error: {e!s}"
                        self._log("error", f"Tool error: {e!s}")

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    })

                    self._add_to_history(
                        action=f"{tool_name}: {json.dumps(args, ensure_ascii=False)}",
                        result={"content": result_str},
                    )

                # Small delay between rounds
                await asyncio.sleep(0.3)

            # Max rounds reached
            self._status = AgentStatus.FAILED
            self._log("error", f"Max rounds ({self._max_rounds}) reached")
            return AgentResult(
                success=False,
                message=f"Max rounds ({self._max_rounds}) reached",
                steps_executed=self._current_round,
                error="max_rounds_exceeded",
            )

        except Exception as e:
            self._status = AgentStatus.FAILED
            self._log("error", f"Execution error: {e!s}")
            return AgentResult(
                success=False,
                message=f"Execution error: {e!s}",
                steps_executed=self._current_round,
                error=str(e),
            )

    def _is_screenshot_message(self, msg: dict[str, Any]) -> bool:
        """Check if a message contains a screenshot."""
        if msg.get("role") != "user":
            return False
        content = msg.get("content")
        if not isinstance(content, list):
            return False
        return any(
            isinstance(part, dict) and part.get("type") == "image_url"
            for part in content
        )
