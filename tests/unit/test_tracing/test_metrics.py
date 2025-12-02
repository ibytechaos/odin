"""Tests for metrics collection."""

import pytest
from unittest.mock import patch, MagicMock

from odin.tracing.metrics import MetricsCollector, get_metrics_collector


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_init(self):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector()

        # Should have all expected metric instruments
        assert collector._tool_executions is not None
        assert collector._tool_errors is not None
        assert collector._tool_latency is not None
        assert collector._llm_requests is not None
        assert collector._llm_tokens is not None
        assert collector._llm_cost is not None
        assert collector._llm_latency is not None
        assert collector._agent_tasks is not None
        assert collector._agent_success is not None
        assert collector._agent_latency is not None
        assert collector._plugin_loaded is not None

    def test_record_tool_execution_success(self):
        """Test recording successful tool execution."""
        collector = MetricsCollector()

        # Should not raise
        collector.record_tool_execution(
            tool_name="test_tool",
            plugin_name="test_plugin",
            success=True,
            latency=0.5,
        )

    def test_record_tool_execution_failure(self):
        """Test recording failed tool execution."""
        collector = MetricsCollector()

        collector.record_tool_execution(
            tool_name="test_tool",
            plugin_name="test_plugin",
            success=False,
            latency=1.0,
            error_type="ValueError",
        )

    def test_record_tool_execution_without_latency(self):
        """Test recording tool execution without latency."""
        collector = MetricsCollector()

        collector.record_tool_execution(
            tool_name="test_tool",
            plugin_name="test_plugin",
            success=True,
        )

    def test_record_llm_request(self):
        """Test recording LLM request."""
        collector = MetricsCollector()

        collector.record_llm_request(
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            latency=1.5,
            cost=0.05,
        )

    def test_record_llm_request_without_cost(self):
        """Test recording LLM request without cost."""
        collector = MetricsCollector()

        collector.record_llm_request(
            provider="anthropic",
            model="claude-3",
            prompt_tokens=200,
            completion_tokens=100,
            latency=2.0,
        )

    def test_record_agent_task_success(self):
        """Test recording successful agent task."""
        collector = MetricsCollector()

        collector.record_agent_task(
            agent_type="crewai",
            task_type="research",
            success=True,
            latency=10.0,
        )

    def test_record_agent_task_failure(self):
        """Test recording failed agent task."""
        collector = MetricsCollector()

        collector.record_agent_task(
            agent_type="autogen",
            task_type="coding",
            success=False,
            latency=5.0,
        )

    def test_record_agent_task_without_latency(self):
        """Test recording agent task without latency."""
        collector = MetricsCollector()

        collector.record_agent_task(
            agent_type="crewai",
            task_type="analysis",
            success=True,
        )

    def test_record_plugin_loaded(self):
        """Test recording plugin load event."""
        collector = MetricsCollector()

        collector.record_plugin_loaded("http_plugin", loaded=True)

    def test_record_plugin_unloaded(self):
        """Test recording plugin unload event."""
        collector = MetricsCollector()

        collector.record_plugin_loaded("http_plugin", loaded=False)

    def test_record_latency(self):
        """Test recording custom latency metric."""
        collector = MetricsCollector()

        collector.record_latency(
            name="api_request",
            latency=0.25,
            labels={"endpoint": "/users"},
        )

    def test_record_latency_without_labels(self):
        """Test recording latency without labels."""
        collector = MetricsCollector()

        collector.record_latency(
            name="operation",
            latency=0.1,
        )

    def test_increment_counter(self):
        """Test incrementing custom counter."""
        collector = MetricsCollector()

        collector.increment_counter(
            name="requests",
            value=1,
            labels={"type": "api"},
        )

    def test_increment_counter_default_value(self):
        """Test incrementing counter with default value."""
        collector = MetricsCollector()

        collector.increment_counter(name="events")

    def test_increment_counter_without_labels(self):
        """Test incrementing counter without labels."""
        collector = MetricsCollector()

        collector.increment_counter(name="count", value=5)


class TestGetMetricsCollector:
    """Test get_metrics_collector function."""

    def test_returns_metrics_collector(self):
        """Test that function returns MetricsCollector."""
        # Clear cache to get fresh instance
        get_metrics_collector.cache_clear()

        collector = get_metrics_collector()
        assert isinstance(collector, MetricsCollector)

    def test_returns_singleton(self):
        """Test that function returns same instance (singleton)."""
        get_metrics_collector.cache_clear()

        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2


class TestMetricsLabels:
    """Test metrics with various label combinations."""

    def test_tool_execution_labels(self):
        """Test tool execution with all label combinations."""
        collector = MetricsCollector()

        # Various combinations
        collector.record_tool_execution("tool1", "plugin1", True, 0.5)
        collector.record_tool_execution("tool2", "plugin2", False, 1.0, "TypeError")
        collector.record_tool_execution("tool3", "plugin1", True)

    def test_llm_request_labels(self):
        """Test LLM request with different providers and models."""
        collector = MetricsCollector()

        collector.record_llm_request("openai", "gpt-4", 100, 50, 1.0, 0.05)
        collector.record_llm_request("anthropic", "claude-3-opus", 200, 100, 2.0)
        collector.record_llm_request("openai", "gpt-3.5-turbo", 50, 25, 0.5, 0.01)

    def test_agent_task_labels(self):
        """Test agent task with different types."""
        collector = MetricsCollector()

        collector.record_agent_task("crewai", "research", True, 10.0)
        collector.record_agent_task("autogen", "coding", False)
        collector.record_agent_task("langchain", "qa", True, 5.0)


class TestMetricsIntegration:
    """Integration tests for metrics system."""

    def test_complete_workflow_metrics(self):
        """Test recording metrics for a complete workflow."""
        get_metrics_collector.cache_clear()
        collector = get_metrics_collector()

        # Simulate a workflow
        collector.record_plugin_loaded("workflow_plugin")
        collector.record_agent_task("crewai", "workflow", True, 30.0)
        collector.record_tool_execution("search", "workflow_plugin", True, 2.0)
        collector.record_tool_execution("process", "workflow_plugin", True, 3.0)
        collector.record_llm_request("openai", "gpt-4", 500, 300, 5.0, 0.10)
        collector.increment_counter("workflow_completed", labels={"type": "test"})
        collector.record_latency("total_workflow", 40.0, {"status": "success"})

    def test_error_workflow_metrics(self):
        """Test recording metrics for a workflow with errors."""
        collector = MetricsCollector()

        # Simulate workflow with error
        collector.record_agent_task("crewai", "workflow", False, 5.0)
        collector.record_tool_execution(
            "failing_tool",
            "plugin",
            success=False,
            latency=1.0,
            error_type="RuntimeError",
        )
        collector.increment_counter("workflow_failed", labels={"reason": "tool_error"})
