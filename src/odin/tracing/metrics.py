"""Metrics collection for Odin framework.

This module provides specialized metrics for AI/Agent systems:
- LLM request/response metrics (tokens, latency, cost)
- Tool execution metrics
- Agent performance metrics
- Error rates and types
"""

from functools import lru_cache

from opentelemetry import metrics

from odin.logging import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Centralized metrics collector for Odin framework.

    Provides high-level methods for recording common metrics in AI/Agent systems.
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._meter = metrics.get_meter("odin.metrics")

        # Tool execution metrics
        self._tool_executions = self._meter.create_counter(
            "odin.tool.executions",
            description="Total number of tool executions",
            unit="1",
        )
        self._tool_errors = self._meter.create_counter(
            "odin.tool.errors",
            description="Total number of tool execution errors",
            unit="1",
        )
        self._tool_latency = self._meter.create_histogram(
            "odin.tool.latency",
            description="Tool execution latency",
            unit="s",
        )

        # LLM metrics
        self._llm_requests = self._meter.create_counter(
            "odin.llm.requests",
            description="Total number of LLM API requests",
            unit="1",
        )
        self._llm_tokens = self._meter.create_counter(
            "odin.llm.tokens",
            description="Total number of tokens consumed",
            unit="1",
        )
        self._llm_cost = self._meter.create_counter(
            "odin.llm.cost",
            description="Estimated LLM API cost",
            unit="USD",
        )
        self._llm_latency = self._meter.create_histogram(
            "odin.llm.latency",
            description="LLM API request latency",
            unit="s",
        )

        # Agent metrics
        self._agent_tasks = self._meter.create_counter(
            "odin.agent.tasks",
            description="Total number of agent tasks executed",
            unit="1",
        )
        self._agent_success = self._meter.create_counter(
            "odin.agent.success",
            description="Number of successful agent tasks",
            unit="1",
        )
        self._agent_latency = self._meter.create_histogram(
            "odin.agent.latency",
            description="Agent task execution latency",
            unit="s",
        )

        # Plugin metrics
        self._plugin_loaded = self._meter.create_up_down_counter(
            "odin.plugin.loaded",
            description="Number of loaded plugins",
            unit="1",
        )

        # General metrics
        self._custom_counter = self._meter.create_counter(
            "odin.custom.counter",
            description="Custom counter metric",
            unit="1",
        )
        self._custom_histogram = self._meter.create_histogram(
            "odin.custom.histogram",
            description="Custom histogram metric",
            unit="1",
        )

    def record_tool_execution(
        self,
        tool_name: str,
        plugin_name: str,
        success: bool = True,
        latency: float | None = None,
        error_type: str | None = None,
    ) -> None:
        """Record a tool execution event.

        Args:
            tool_name: Name of the tool
            plugin_name: Name of the plugin
            success: Whether execution was successful
            latency: Execution latency in seconds
            error_type: Type of error if execution failed
        """
        labels = {
            "tool": tool_name,
            "plugin": plugin_name,
            "success": str(success).lower(),
        }

        self._tool_executions.add(1, labels)

        if not success and error_type:
            error_labels = {**labels, "error_type": error_type}
            self._tool_errors.add(1, error_labels)

        if latency is not None:
            self._tool_latency.record(latency, labels)

    def record_llm_request(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency: float,
        cost: float | None = None,
    ) -> None:
        """Record an LLM API request.

        Args:
            provider: LLM provider (openai, anthropic, etc.)
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            latency: Request latency in seconds
            cost: Estimated cost in USD
        """
        labels = {
            "provider": provider,
            "model": model,
        }

        self._llm_requests.add(1, labels)
        self._llm_tokens.add(
            prompt_tokens, {**labels, "token_type": "prompt"}
        )
        self._llm_tokens.add(
            completion_tokens, {**labels, "token_type": "completion"}
        )
        self._llm_latency.record(latency, labels)

        if cost is not None:
            self._llm_cost.add(cost, labels)

    def record_agent_task(
        self,
        agent_type: str,
        task_type: str,
        success: bool = True,
        latency: float | None = None,
    ) -> None:
        """Record an agent task execution.

        Args:
            agent_type: Type of agent (crewai, autogen, etc.)
            task_type: Type of task
            success: Whether task was successful
            latency: Task execution latency in seconds
        """
        labels = {
            "agent_type": agent_type,
            "task_type": task_type,
        }

        self._agent_tasks.add(1, labels)

        if success:
            self._agent_success.add(1, labels)

        if latency is not None:
            self._agent_latency.record(latency, labels)

    def record_plugin_loaded(self, plugin_name: str, loaded: bool = True) -> None:
        """Record a plugin load/unload event.

        Args:
            plugin_name: Name of the plugin
            loaded: True if loaded, False if unloaded
        """
        labels = {"plugin": plugin_name}
        delta = 1 if loaded else -1
        self._plugin_loaded.add(delta, labels)

    def record_latency(
        self,
        name: str,
        latency: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a custom latency metric.

        Args:
            name: Metric name
            latency: Latency value in seconds
            labels: Additional labels
        """
        metric_labels = {"name": name, **(labels or {})}
        self._custom_histogram.record(latency, metric_labels)

    def increment_counter(
        self,
        name: str,
        value: int = 1,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a custom counter.

        Args:
            name: Metric name
            value: Value to add
            labels: Additional labels
        """
        metric_labels = {"name": name, **(labels or {})}
        self._custom_counter.add(value, metric_labels)


@lru_cache
def get_metrics_collector() -> MetricsCollector:
    """Get singleton metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    return MetricsCollector()
