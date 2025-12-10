"""Tests for MobileHierarchicalAgent."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from odin.agents.mobile.base import AgentResult, AgentStatus
from odin.agents.mobile.hierarchical import (
    HierarchicalPlan,
    MobileHierarchicalAgent,
    SubTask,
)


class TestSubTask:
    """Tests for SubTask dataclass."""

    def test_default_values(self):
        """Test default values."""
        task = SubTask(index=1, app="Camera", objective="Take photo")
        assert task.status == "pending"
        assert task.result is None
        assert task.variables_in == {}
        assert task.variables_out == {}


class TestHierarchicalPlan:
    """Tests for HierarchicalPlan dataclass."""

    def test_is_complete_empty(self):
        """Test empty plan is complete."""
        plan = HierarchicalPlan(task="test", sub_tasks=[])
        assert plan.is_complete is True

    def test_is_complete_with_tasks(self):
        """Test completion with sub-tasks."""
        tasks = [SubTask(index=1, app="App", objective="obj")]
        plan = HierarchicalPlan(task="test", sub_tasks=tasks, current_index=0)
        assert plan.is_complete is False

        plan.current_index = 1
        assert plan.is_complete is True

    def test_current_sub_task(self):
        """Test current sub-task access."""
        tasks = [
            SubTask(index=1, app="App1", objective="obj1"),
            SubTask(index=2, app="App2", objective="obj2"),
        ]
        plan = HierarchicalPlan(task="test", sub_tasks=tasks, current_index=0)

        assert plan.current_sub_task.app == "App1"
        plan.current_index = 1
        assert plan.current_sub_task.app == "App2"
        plan.current_index = 2
        assert plan.current_sub_task is None


class TestMobileHierarchicalAgent:
    """Tests for MobileHierarchicalAgent."""

    @pytest.fixture
    def mock_plugin(self):
        """Create mock plugin."""
        plugin = MagicMock()
        plugin._variables = {}
        plugin.screenshot = AsyncMock(return_value={
            "image_base64": base64.b64encode(b"PNG").decode(),
        })
        plugin.click = AsyncMock(return_value={"success": True})
        plugin.open_app = AsyncMock(return_value={"success": True})
        plugin.wait = AsyncMock(return_value={"success": True})
        return plugin

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        # VLM analysis
        vlm_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"description": "Home screen"}'
        ))])
        # Hierarchical plan
        plan_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='[{"app": "Camera", "objective": "Take a photo"}]'
        ))])
        # ReAct complete action
        complete_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"type": "complete", "message": "Done"}'
        ))])
        client.chat.completions.create = AsyncMock(
            side_effect=[vlm_resp, plan_resp, vlm_resp, complete_resp, vlm_resp]
        )
        return client

    @pytest.fixture
    def agent(self, mock_plugin, mock_llm_client):
        """Create agent for testing."""
        return MobileHierarchicalAgent(
            plugin=mock_plugin,
            llm_client=mock_llm_client,
            max_rounds=10,
            sub_agent_max_rounds=5,
        )

    async def test_execute_success(self, agent):
        """Test successful hierarchical execution."""
        result = await agent.execute("Take photo and share")

        assert result.success is True
        assert agent.status == AgentStatus.COMPLETED
        assert agent.plan is not None
        assert agent.plan.is_complete

    async def test_execute_empty_plan(self, mock_plugin, mock_llm_client):
        """Test failure on empty plan."""
        vlm_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"description": "Screen"}'
        ))])
        empty_plan = MagicMock(choices=[MagicMock(message=MagicMock(
            content='[]'
        ))])
        mock_llm_client.chat.completions.create = AsyncMock(
            side_effect=[vlm_resp, empty_plan]
        )

        agent = MobileHierarchicalAgent(plugin=mock_plugin, llm_client=mock_llm_client)
        result = await agent.execute("Test")

        assert result.success is False
        assert result.error == "empty_plan"

    async def test_execute_sub_task_failure(self, mock_plugin, mock_llm_client):
        """Test sub-task failure propagates."""
        vlm_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"description": "Screen"}'
        ))])
        plan_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='[{"app": "Camera", "objective": "Take photo"}]'
        ))])
        fail_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"type": "fail", "message": "Cannot proceed", "error": "app_not_found"}'
        ))])
        mock_llm_client.chat.completions.create = AsyncMock(
            side_effect=[vlm_resp, plan_resp, vlm_resp, fail_resp]
        )

        agent = MobileHierarchicalAgent(plugin=mock_plugin, llm_client=mock_llm_client)
        result = await agent.execute("Test")

        assert result.success is False
        assert agent.status == AgentStatus.FAILED

    async def test_execute_multiple_sub_tasks(self, mock_plugin, mock_llm_client):
        """Test multiple sub-tasks execution."""
        vlm_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"description": "Screen"}'
        ))])
        plan_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='[{"app": "Camera", "objective": "Take photo"}, {"app": "WeChat", "objective": "Share photo"}]'
        ))])
        complete_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"type": "complete", "message": "Done"}'
        ))])
        mock_llm_client.chat.completions.create = AsyncMock(
            side_effect=[
                vlm_resp, plan_resp,  # Initial
                vlm_resp, complete_resp,  # Sub-task 1
                vlm_resp, complete_resp,  # Sub-task 2
                vlm_resp,  # Final screenshot
            ]
        )

        agent = MobileHierarchicalAgent(plugin=mock_plugin, llm_client=mock_llm_client)
        result = await agent.execute("Take and share photo")

        assert result.success is True
        assert len(agent.plan.sub_tasks) == 2
        assert all(t.status == "completed" for t in agent.plan.sub_tasks)

    async def test_variables_passed_between_sub_tasks(self, mock_plugin, mock_llm_client):
        """Test variables are passed between sub-tasks."""
        # Setup plugin to have variables
        mock_plugin._variables = {"photo_path": "/sdcard/photo.jpg"}

        vlm_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"description": "Screen"}'
        ))])
        plan_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='[{"app": "Camera", "objective": "Take photo"}]'
        ))])
        complete_resp = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"type": "complete", "message": "Done"}'
        ))])
        mock_llm_client.chat.completions.create = AsyncMock(
            side_effect=[vlm_resp, plan_resp, vlm_resp, complete_resp, vlm_resp]
        )

        agent = MobileHierarchicalAgent(plugin=mock_plugin, llm_client=mock_llm_client)
        result = await agent.execute("Test")

        # Variables should be captured
        assert agent.plan.sub_tasks[0].variables_in == {"photo_path": "/sdcard/photo.jpg"}

    async def test_plan_property(self, agent):
        """Test plan property."""
        assert agent.plan is None

        agent._plan = HierarchicalPlan(task="test", sub_tasks=[])
        assert agent.plan is not None

    async def test_execute_handles_exception(self, mock_plugin, mock_llm_client):
        """Test exception handling."""
        mock_llm_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        agent = MobileHierarchicalAgent(plugin=mock_plugin, llm_client=mock_llm_client)
        result = await agent.execute("Test")

        assert result.success is False
        assert "API error" in result.error
