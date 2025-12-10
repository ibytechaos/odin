"""Tests for MobileAgentBase."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from odin.agents.mobile.base import (
    AgentResult,
    AgentStatus,
    MobileAgentBase,
    VisionAnalysis,
)


class ConcreteAgent(MobileAgentBase):
    """Concrete implementation for testing."""

    async def execute(self, task: str) -> AgentResult:
        self._status = AgentStatus.RUNNING
        self._current_round = 1
        self._status = AgentStatus.COMPLETED
        return AgentResult(success=True, message="Done", steps_executed=1)


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert AgentStatus.IDLE == "idle"
        assert AgentStatus.RUNNING == "running"
        assert AgentStatus.PAUSED == "paused"
        assert AgentStatus.COMPLETED == "completed"
        assert AgentStatus.FAILED == "failed"


class TestVisionAnalysis:
    """Tests for VisionAnalysis dataclass."""

    def test_default_values(self):
        """Test default values."""
        analysis = VisionAnalysis(description="Test")
        assert analysis.description == "Test"
        assert analysis.elements == []
        assert analysis.suggested_action is None
        assert analysis.confidence == 0.0
        assert analysis.raw_response == ""

    def test_full_values(self):
        """Test with all values."""
        analysis = VisionAnalysis(
            description="Home screen",
            elements=[{"type": "button", "text": "Login"}],
            suggested_action="Click login",
            confidence=0.95,
            raw_response="raw",
        )
        assert analysis.description == "Home screen"
        assert len(analysis.elements) == 1
        assert analysis.confidence == 0.95


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = AgentResult(success=True, message="Task completed")
        assert result.success is True
        assert result.message == "Task completed"
        assert result.steps_executed == 0
        assert result.error is None

    def test_failure_result(self):
        """Test failure result."""
        result = AgentResult(
            success=False,
            message="Task failed",
            error="Connection lost",
        )
        assert result.success is False
        assert result.error == "Connection lost"


class TestMobileAgentBase:
    """Tests for MobileAgentBase class."""

    @pytest.fixture
    def mock_plugin(self):
        """Create mock plugin."""
        plugin = MagicMock()
        plugin.screenshot = AsyncMock(return_value={
            "image_base64": base64.b64encode(b"PNG_DATA").decode(),
            "width": 1080,
            "height": 2340,
        })
        return plugin

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = MagicMock()
        client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"description": "Test screen", "confidence": 0.9}'))]
        ))
        return client

    @pytest.fixture
    def agent(self, mock_plugin, mock_llm_client):
        """Create test agent."""
        return ConcreteAgent(
            plugin=mock_plugin,
            llm_client=mock_llm_client,
            max_rounds=10,
        )

    def test_initial_state(self, agent):
        """Test initial agent state."""
        assert agent.status == AgentStatus.IDLE
        assert agent.current_round == 0
        assert agent.history == []

    def test_reset(self, agent):
        """Test reset clears state."""
        agent._status = AgentStatus.COMPLETED
        agent._current_round = 5
        agent._history.append({"action": "test"})

        agent.reset()

        assert agent.status == AgentStatus.IDLE
        assert agent.current_round == 0
        assert agent.history == []

    async def test_execute(self, agent):
        """Test execute method."""
        result = await agent.execute("Test task")

        assert result.success is True
        assert result.message == "Done"
        assert agent.status == AgentStatus.COMPLETED

    async def test_analyze_screen(self, agent, mock_llm_client):
        """Test screen analysis."""
        screenshot = b"PNG_DATA"
        analysis = await agent.analyze_screen(screenshot, context="test", task="login")

        assert analysis.description == "Test screen"
        assert analysis.confidence == 0.9
        mock_llm_client.chat.completions.create.assert_called_once()

    async def test_analyze_screen_invalid_json(self, agent, mock_llm_client):
        """Test screen analysis with invalid JSON response."""
        mock_llm_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Invalid response"))]
        )

        analysis = await agent.analyze_screen(b"PNG")

        assert analysis.description == "Invalid response"
        assert analysis.raw_response == "Invalid response"

    async def test_take_screenshot_and_analyze(self, agent):
        """Test combined screenshot and analysis."""
        screenshot, analysis = await agent.take_screenshot_and_analyze(task="test")

        assert screenshot == b"PNG_DATA"
        assert analysis.description == "Test screen"

    def test_add_to_history(self, agent):
        """Test adding entries to history."""
        agent._current_round = 1
        analysis = VisionAnalysis(description="Screen", suggested_action="Click")

        agent._add_to_history("click", {"success": True}, analysis)

        assert len(agent.history) == 1
        assert agent.history[0]["round"] == 1
        assert agent.history[0]["action"] == "click"
        assert agent.history[0]["analysis"]["suggested_action"] == "Click"

    async def test_stop(self, agent):
        """Test stopping agent."""
        agent._status = AgentStatus.RUNNING

        await agent.stop()

        assert agent.status == AgentStatus.PAUSED

    async def test_stop_not_running(self, agent):
        """Test stop when not running does nothing."""
        agent._status = AgentStatus.IDLE

        await agent.stop()

        assert agent.status == AgentStatus.IDLE

    async def test_resume_when_paused(self, agent):
        """Test resume when paused."""
        agent._status = AgentStatus.PAUSED

        result = await agent.resume()

        assert agent.status == AgentStatus.RUNNING
        assert result is None

    async def test_resume_when_not_paused(self, agent):
        """Test resume when not paused returns None."""
        agent._status = AgentStatus.IDLE

        result = await agent.resume()

        assert result is None
        assert agent.status == AgentStatus.IDLE
