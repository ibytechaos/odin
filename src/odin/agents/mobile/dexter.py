"""Dexter-style agent for mobile automation.

This agent exactly replicates the dexter_mobile project flow:
1. Plan stage: Generate XML plan (no screenshot first)
2. Flatten stage: Convert XML to flattened task list
3. Agent stage: ReAct loop with dexter_mobile prompts

The prompts and request format are identical to dexter_mobile,
but tools use odin's extensible plugin architecture.
"""

import asyncio
import base64
import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from xml.dom import minidom

logger = logging.getLogger(__name__)

from odin.agents.mobile.base import AgentResult, AgentStatus, MobileAgentBase
from odin.agents.mobile.prompts import (
    build_plan_system_prompt,
    build_plan_user_prompt,
)

# Tools available in dexter_mobile (only these 7 tools)
DEXTER_TOOL_NAMES = frozenset([
    "click",
    "input",
    "wait",
    "open_app",
    "human_interact",
    "variable_storage",
    "scroll",
])

# Static tool definitions exactly matching dexter_mobile/agent/tools.py
DEXTER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click at given page coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "point_2d": {
                        "type": "array",
                        "description": "Coordinate as [x, y]",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "num_clicks": {
                        "type": "number",
                        "description": "number of times to click the element, default 1",
                    },
                    "button": {
                        "type": "string",
                        "description": "Mouse button type, default left",
                        "enum": ["left", "right", "middle"],
                    },
                    "userSidePrompt": {
                        "type": "string",
                        "description": "The user-side prompt, showing what you are doing",
                    },
                },
                "required": ["point_2d", "userSidePrompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "input",
            "description": "Input text given page coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to input",
                    },
                    "point_2d": {
                        "type": "array",
                        "description": "Optional coordinate as [x, y] to focus before input",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "userSidePrompt": {
                        "type": "string",
                        "description": "The user-side prompt, showing what you are doing",
                    },
                },
                "required": ["text", "point_2d", "userSidePrompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": "Wait/pause execution for a specified duration. Use this tool when you need to wait for data loading, page rendering, or introduce delays between operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {
                        "type": "number",
                        "description": "Wait duration in milliseconds",
                        "default": 500,
                        "minimum": 200,
                        "maximum": 1000,
                    },
                    "userSidePrompt": {
                        "type": "string",
                        "description": "The user-side prompt, showing what you are doing",
                    },
                },
                "required": ["userSidePrompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an app by name (app name will be mapped to package/activity).",
            "parameters": {
                "type": "object",
                "properties": {
                    "appname": {
                        "type": "string",
                        "description": "Logical app name (mapped to package/activity by the agent).",
                    },
                    "userSidePrompt": {
                        "type": "string",
                        "description": "The user-side prompt, showing what you are doing",
                    },
                },
                "required": ["appname", "userSidePrompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "human_interact",
            "description": "Ask the human user for help or input via CLI; the text will be added as a user message and the loop continues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "userSidePrompt": {
                        "type": "string",
                        "description": "The user-side prompt, showing what you are doing",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Display prompts to users",
                    },
                },
                "required": ["userSidePrompt", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "variable_storage",
            "description": "Store/read/list shared variables across agents. Use when nodes contain input/output attributes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read_variable", "write_variable", "list_all_variable"],
                        "description": "read_variable: get value(s); write_variable: set value; list_all_variable: list keys.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Variable name(s). For read, supports comma-separated list.",
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to store when operation is write_variable. Record in detail whenever necessary.",
                    },
                    "userSidePrompt": {
                        "type": "string",
                        "description": "The user-side prompt, showing what you are doing",
                    },
                },
                "required": ["operation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll from start to end coordinates. Only scroll down(right) when the content at the bottom(rightmost) exceeds the visible area.",
            "parameters": {
                "type": "object",
                "properties": {
                    "point_2d_start": {
                        "type": "array",
                        "description": "Scroll start coordinate as [x, y]",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "point_2d_end": {
                        "type": "array",
                        "description": "Scroll end coordinate as [x, y]",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "userSidePrompt": {
                        "type": "string",
                        "description": "The user-side prompt, showing what you are doing",
                    },
                },
                "required": ["point_2d_start", "point_2d_end", "userSidePrompt"],
            },
        },
    },
]

# ============================================================================
# Dexter-style Prompts (exactly from dexter_mobile/agent/agent.py)
# ============================================================================

DEXTER_SYSTEM_PROMPT = """You are a GUI action planner. Your job is to finish the mainTask.
- You need to follow the rules below:
- If the webpage content hasn't loaded, please use the `wait` tool to allow time for the content to load.
- Do not use the 'variable_storage' tool repeatly.
- Repeated use 'scroll' tool too many times may indicate that you've reached the bottom of the page.
- Step back and rethink your approach if you find yourself repeating the same actions to avoid getting stuck in an infinite loop.
- Any operation carries the risk of not matching expectations. You can flexibly plan your actions based on the actual execution situation and the goal.
- Before completing the task, please make sure to carefully check if the task has been completed fully and accurately.
- Always respond in Chinese.
"""

DEXTER_HUMAN_PROMPT = """
* HUMAN INTERACT
During the task execution process, you can use the `human_interact` tool to interact with humans, please call it in the following situations:
- When performing dangerous operations such as payment, authorization, deleting files, confirmation from humans is required.
- Whenever encountering obstacles while accessing websites, such as requiring user login, providing user information, captcha verification, QR code scanning, or human verification, you have to request manual assistance.
- The `human_interact` tool does not support parallel calls.
"""

DEXTER_TASK_PROMPT_TEMPLATE = """
Current datetime: {datetime}

# User input task instructions
<root>
 <!-- Main task, completed through the collaboration of multiple Agents -->
 <mainTask>main task</mainTask>
 <!-- The tasks that the current agent needs to complete, the current agent only needs to complete the currentTask -->
 <currentTask>specific task</currentTask>
 <!-- Complete the corresponding step nodes of the task, Only for reference -->
 <nodes>
 <!-- node supports input/output variables to pass dependencies -->
 <node input="variable name" output="variable name" status="todo / done">task step node</node>
 </nodes>
</root>

"""

DEXTER_SCREENSHOT_PROMPT = (
    "This is the environmental information after the operation, including the latest browser screenshot. "
    "Please perform the next operation based on the environmental information."
)


@dataclass
class FlattenedTask:
    """A flattened task from the XML plan."""

    index: int
    xml_content: str
    main_task: str
    current_task: str
    nodes: list[str] = field(default_factory=list)


@dataclass
class DexterPlan:
    """Plan generated from XML planner."""

    raw_xml: str
    tasks: list[FlattenedTask] = field(default_factory=list)
    current_index: int = 0

    @property
    def is_complete(self) -> bool:
        return self.current_index >= len(self.tasks)

    @property
    def current_task(self) -> FlattenedTask | None:
        if 0 <= self.current_index < len(self.tasks):
            return self.tasks[self.current_index]
        return None


class MobileDexterAgent(MobileAgentBase):
    """Dexter-style mobile automation agent.

    Exactly replicates dexter_mobile flow:
    1. Plan: Generate XML plan (no screenshot)
    2. Flatten: Convert to task list
    3. Execute: ReAct loop per task
    """

    def __init__(
        self,
        *args: Any,
        plan_temperature: float = 0.1,
        agent_temperature: float = 0.1,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._plan_temperature = plan_temperature
        self._agent_temperature = agent_temperature
        self._plan: DexterPlan | None = None

    @property
    def plan(self) -> DexterPlan | None:
        return self._plan

    async def execute(self, task: str) -> AgentResult:
        """Execute a task using dexter_mobile flow.

        Args:
            task: The task description to execute

        Returns:
            AgentResult with execution outcome
        """
        self.reset()
        self._status = AgentStatus.RUNNING
        self._plan = None
        self._log("info", f"Starting task: {task}")

        try:
            # ===== Stage 1: Plan (no screenshot, exactly like dexter_mobile) =====
            self._log("info", "=== Planner output ===")
            plan_xml = await self._generate_plan(task)
            self._log("info", plan_xml)

            # ===== Stage 2: Flatten plan to tasks =====
            self._log("info", "=== Flattened tasks in execution order ===")
            self._plan = self._flatten_plan(plan_xml, task)

            if not self._plan.tasks:
                self._status = AgentStatus.FAILED
                self._log("error", "Failed to generate plan")
                return AgentResult(
                    success=False,
                    message="Failed to generate plan",
                    error="empty_plan",
                )

            for i, flat_task in enumerate(self._plan.tasks):
                self._log("info", f"--- Task {i + 1}/{len(self._plan.tasks)} ---")
                self._log("info", flat_task.xml_content)

            # ===== Stage 3: Execute each flattened task =====
            self._log("info", "=== Agent run ===")
            while not self._plan.is_complete and self._current_round < self._max_rounds:
                if self._status == AgentStatus.PAUSED:
                    self._log("warning", "Execution paused")
                    return AgentResult(
                        success=False,
                        message="Execution paused",
                        steps_executed=self._current_round,
                    )

                current_task = self._plan.current_task
                if current_task is None:
                    break

                self._current_round += 1
                task_num = current_task.index + 1
                total = len(self._plan.tasks)
                self._log("info", f"[Agent {task_num}/{total}] executing currentTask...")

                # Execute task with ReAct loop
                task_result = await self._execute_task(current_task)

                if task_result.success:
                    self._plan.current_index += 1
                    self._log("info", f"Task {task_num} completed (steps: {task_result.steps_executed})")
                else:
                    self._status = AgentStatus.FAILED
                    self._log("error", f"Task {task_num} failed: {task_result.error}")
                    return task_result

            # Check completion
            if self._plan.is_complete:
                self._status = AgentStatus.COMPLETED
                self._log("info", "All tasks completed successfully")
                return AgentResult(
                    success=True,
                    message="All tasks completed successfully",
                    steps_executed=self._current_round,
                    variables=self._plugin._variables.copy(),
                )
            else:
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

    async def _generate_plan(self, task: str) -> str:
        """Generate XML plan (exactly like dexter_mobile planner).

        Args:
            task: Task description

        Returns:
            Raw XML plan string
        """
        system_prompt = build_plan_system_prompt(name="Planner")
        user_prompt = build_plan_user_prompt(
            task_prompt=task,
            platform="mobile",
            datetime_str=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # ============ DEBUG: Log full request ============
        logger.info("=" * 80)
        logger.info("[DEBUG] LLM REQUEST (dexter_mobile planner)")
        logger.info("=" * 80)
        debug_payload = {
            "model": self._llm_model,
            "temperature": self._plan_temperature,
            "messages": messages,
        }
        logger.info(json.dumps(debug_payload, indent=2, ensure_ascii=False))
        logger.info("=" * 80)

        response = await self._llm_client.chat.completions.create(
            model=self._llm_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self._plan_temperature,
        )

        content = response.choices[0].message.content or ""

        # ============ DEBUG: Log full response ============
        logger.info("=" * 80)
        logger.info("[DEBUG] LLM RESPONSE (dexter_mobile planner)")
        logger.info("=" * 80)
        debug_response = {
            "content": content,
        }
        logger.info(json.dumps(debug_response, indent=2, ensure_ascii=False))
        logger.info("=" * 80)

        return content

    def _flatten_plan(self, plan_xml: str, main_task: str) -> DexterPlan:
        """Flatten XML plan to task list (exactly like dexter_mobile).

        Args:
            plan_xml: Raw XML plan
            main_task: Original user task

        Returns:
            DexterPlan with flattened tasks
        """
        tasks: list[FlattenedTask] = []

        try:
            # Extract XML from response (may have extra text)
            xml_start = plan_xml.find("<root>")
            xml_end = plan_xml.rfind("</root>") + len("</root>")
            if xml_start >= 0 and xml_end > xml_start:
                plan_xml = plan_xml[xml_start:xml_end]

            root = ET.fromstring(plan_xml)
            agents_elem = root.find("agents")
            if agents_elem is None:
                return DexterPlan(raw_xml=plan_xml, tasks=tasks)

            agents = agents_elem.findall("agent")
            if not agents:
                return DexterPlan(raw_xml=plan_xml, tasks=tasks)

            # Build dependency graph and topological sort
            agent_by_id: dict[str, ET.Element] = {}
            deps: dict[str, list[str]] = {}
            for agent in agents:
                aid = agent.get("id")
                if aid is None:
                    continue
                agent_by_id[aid] = agent
                dep_str = (agent.get("dependsOn") or "").strip()
                dep_list = [d.strip() for d in dep_str.split(",") if d.strip()] if dep_str else []
                deps[aid] = dep_list

            # Topological sort
            ordered: list[str] = []
            remaining = set(agent_by_id.keys())
            while remaining:
                progressed = False
                for aid in sorted(list(remaining), key=lambda x: int(x) if x.isdigit() else x):
                    if all(d in ordered for d in deps.get(aid, [])):
                        ordered.append(aid)
                        remaining.remove(aid)
                        progressed = True
                        break
                if not progressed:
                    break  # Circular dependency, break

            # Flatten each agent to task
            for idx, aid in enumerate(ordered):
                agent_elem = agent_by_id[aid]
                xml_content, current_task, nodes = self._flatten_agent(agent_elem, main_task)
                tasks.append(FlattenedTask(
                    index=idx,
                    xml_content=xml_content,
                    main_task=main_task,
                    current_task=current_task,
                    nodes=nodes,
                ))

        except ET.ParseError:
            pass

        return DexterPlan(raw_xml=plan_xml, tasks=tasks)

    def _flatten_agent(
        self,
        agent_elem: ET.Element,
        main_task: str,
    ) -> tuple[str, str, list[str]]:
        """Flatten a single agent element to XML task format.

        Args:
            agent_elem: Agent XML element
            main_task: Original user task

        Returns:
            Tuple of (xml_content, current_task, nodes)
        """
        current_task = (agent_elem.findtext("task") or "").strip()
        nodes_elem = agent_elem.find("nodes")
        node_data: list[tuple[str, dict[str, str]]] = []
        if nodes_elem is not None:
            for node in nodes_elem.findall("node"):
                text = (node.text or "").strip()
                if text:
                    node_data.append((text, dict(node.attrib)))

        # Build XML output (exactly like dexter_mobile)
        new_root = ET.Element("root")
        ET.SubElement(new_root, "mainTask").text = main_task
        ET.SubElement(new_root, "currentTask").text = current_task
        nodes_out = ET.SubElement(new_root, "nodes")
        node_texts = []
        for idx, (text, attribs) in enumerate(node_data):
            attribs = attribs or {}
            attribs.setdefault("id", str(idx))
            ET.SubElement(nodes_out, "node", attribs).text = text
            node_texts.append(text)

        # Pretty print XML
        dom = minidom.parseString(ET.tostring(new_root, encoding="utf-8"))
        xml_with_decl = dom.toprettyxml(indent="  ")
        lines = xml_with_decl.splitlines()
        if lines and lines[0].strip().startswith("<?xml"):
            lines = lines[1:]
        xml_content = "\n".join(lines)

        return xml_content, current_task, node_texts

    async def _execute_task(self, task: FlattenedTask) -> AgentResult:
        """Execute a single flattened task using ReAct loop.

        Args:
            task: The flattened task to execute

        Returns:
            AgentResult from execution
        """
        # Build system prompt (exactly like dexter_mobile)
        dt_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        system_prompt = DEXTER_SYSTEM_PROMPT + DEXTER_HUMAN_PROMPT + DEXTER_TASK_PROMPT_TEMPLATE.format(datetime=dt_str)

        # Build initial messages (task XML as user message, no screenshot first)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text", "text": task.xml_content}]},
        ]

        # Use static tool definitions exactly matching dexter_mobile
        openai_tools = DEXTER_TOOLS

        steps = 0
        max_steps = 30  # Max steps per task

        while steps < max_steps:
            steps += 1

            # ============ DEBUG: Log full request ============
            logger.info("=" * 80)
            logger.info("[DEBUG] LLM REQUEST (dexter_mobile)")
            logger.info("=" * 80)
            debug_payload = {
                "model": self._llm_model,
                "temperature": self._agent_temperature,
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

            # Call LLM
            response = await self._llm_client.chat.completions.create(
                model=self._llm_model,
                messages=messages,  # type: ignore[arg-type]
                tools=openai_tools,  # type: ignore[arg-type]
                temperature=self._agent_temperature,
            )

            # ============ DEBUG: Log full response ============
            logger.info("=" * 80)
            logger.info("[DEBUG] LLM RESPONSE (dexter_mobile)")
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
                self._log("info", f"assistant message content:\n {msg.content[:200] if msg.content else '无'}")

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
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            messages.append(assistant_msg)

            # Check if done (no tool calls)
            if not msg.tool_calls or finish_reason != "tool_calls":
                return AgentResult(
                    success=True,
                    message=msg.content or "Task completed",
                    steps_executed=steps,
                    variables=self._plugin._variables.copy(),
                )

            # Execute tool calls
            for tool_call in msg.tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    self._log("warning", f"Failed to parse args: {tool_call.function.arguments}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": "Error: Failed to parse arguments",
                    })
                    continue

                tool_name = tool_call.function.name
                self._log("info", f"tool_call {tool_call.id} {tool_name}: {args}")

                # Log userSidePrompt if present
                if "userSidePrompt" in args:
                    self._log("info", f"userSidePrompt: {args['userSidePrompt']}")

                # Execute the tool
                try:
                    result = await self._plugin.execute_tool(tool_name, **args)
                    result_str = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
                    self._log("info", f"Executing {tool_name} {result_str[:100]}...")
                except Exception as e:
                    result_str = f"Error: {e!s}"
                    self._log("error", f"Tool error: {e!s}")

                # Add tool result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str,
                })

            # Take screenshot and add to messages
            screenshot = await self._plugin._controller.screenshot()  # type: ignore[union-attr]
            img_b64 = base64.b64encode(screenshot).decode("utf-8")

            # Remove old screenshot messages
            messages = [m for m in messages if not self._is_screenshot_message(m)]

            # Add new screenshot
            messages.append({
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": DEXTER_SCREENSHOT_PROMPT},
                ],
            })

            # Small delay
            await asyncio.sleep(0.3)

        # Max steps reached
        return AgentResult(
            success=False,
            message=f"Max steps ({max_steps}) reached for task",
            steps_executed=steps,
            error="max_steps_exceeded",
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
