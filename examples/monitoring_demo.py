"""Monitoring and observability demonstration.

This example shows how to:
1. Enable OpenTelemetry tracing
2. Collect Prometheus metrics
3. Monitor tool execution
4. Track plugin lifecycle
5. Record custom metrics

For production use:
- Set up OTLP collector (Jaeger/Tempo/etc.)
- Configure Prometheus scraping
- Set up Grafana dashboards
"""

import asyncio
import time

from odin import Odin, AgentPlugin, Tool, ToolParameter
from odin.plugins.base import ToolParameterType
from odin.tracing import get_metrics_collector, traced, timed


class MonitoredPlugin(AgentPlugin):
    """Example plugin with monitoring instrumentation."""

    @property
    def name(self) -> str:
        return "monitored"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="fast_operation",
                description="A fast operation (~10ms)",
                parameters=[],
            ),
            Tool(
                name="slow_operation",
                description="A slow operation (~1s)",
                parameters=[],
            ),
            Tool(
                name="failing_operation",
                description="An operation that fails",
                parameters=[],
            ),
            Tool(
                name="llm_simulation",
                description="Simulate an LLM request",
                parameters=[
                    ToolParameter(
                        name="prompt",
                        type=ToolParameterType.STRING,
                        description="Prompt text",
                        required=True,
                    ),
                ],
            ),
        ]

    @traced(name="monitored.execute_tool")
    @timed(metric_name="plugin.execution_time")
    async def execute_tool(self, tool_name: str, **kwargs):
        """Execute tool with automatic tracing and timing."""
        if tool_name == "fast_operation":
            return await self._fast_operation()
        elif tool_name == "slow_operation":
            return await self._slow_operation()
        elif tool_name == "failing_operation":
            return await self._failing_operation()
        elif tool_name == "llm_simulation":
            return await self._llm_simulation(kwargs["prompt"])
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _fast_operation(self):
        """Fast operation."""
        await asyncio.sleep(0.01)
        return {"status": "success", "latency_ms": 10}

    async def _slow_operation(self):
        """Slow operation."""
        await asyncio.sleep(1.0)
        return {"status": "success", "latency_ms": 1000}

    async def _failing_operation(self):
        """Operation that fails."""
        raise ValueError("Simulated error for monitoring demo")

    async def _llm_simulation(self, prompt: str):
        """Simulate an LLM API call."""
        metrics = get_metrics_collector()

        start_time = time.time()

        # Simulate LLM processing
        await asyncio.sleep(0.5)

        # Simulated token counts
        prompt_tokens = len(prompt.split()) * 1.3
        completion_tokens = 50

        latency = time.time() - start_time
        cost = (prompt_tokens * 0.00001 + completion_tokens * 0.00003)

        # Record LLM metrics
        metrics.record_llm_request(
            provider="simulated",
            model="gpt-4o-mini",
            prompt_tokens=int(prompt_tokens),
            completion_tokens=completion_tokens,
            latency=latency,
            cost=cost,
        )

        return {
            "response": "This is a simulated LLM response",
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": completion_tokens,
            "cost_usd": cost,
        }


async def main():
    """Run monitoring demonstration."""
    print("=" * 70)
    print("Odin Framework - Monitoring & Observability Demo")
    print("=" * 70)

    # Initialize framework with tracing enabled
    app = Odin()
    await app.initialize()

    # Register monitored plugin
    plugin = MonitoredPlugin()
    await app.register_plugin(plugin)

    print("\n[1/5] Plugin registered with automatic metrics")
    print("      Metric: odin.plugin.loaded = 1")

    # Execute various operations
    print("\n[2/5] Executing fast operation...")
    result = await app.execute_tool("fast_operation")
    print(f"      Result: {result}")
    print("      Metrics recorded:")
    print("        - odin.tool.executions (counter)")
    print("        - odin.tool.latency (histogram)")

    print("\n[3/5] Executing slow operation...")
    result = await app.execute_tool("slow_operation")
    print(f"      Result: {result}")

    # Execute LLM simulation
    print("\n[4/5] Executing LLM simulation...")
    result = await app.execute_tool(
        "llm_simulation",
        prompt="What is the meaning of life?",
    )
    print(f"      Result: {result}")
    print("      Metrics recorded:")
    print("        - odin.llm.requests (counter)")
    print("        - odin.llm.tokens (counter)")
    print("        - odin.llm.cost (counter)")
    print("        - odin.llm.latency (histogram)")

    # Execute failing operation
    print("\n[5/5] Executing failing operation...")
    try:
        await app.execute_tool("failing_operation")
    except Exception as e:
        print(f"      Expected error: {e.__class__.__name__}")
        print("      Metrics recorded:")
        print("        - odin.tool.errors (counter)")
        print("        - error_type label set")

    # Manual metrics recording
    print("\n[BONUS] Recording custom metrics...")
    metrics = get_metrics_collector()

    # Record agent task
    metrics.record_agent_task(
        agent_type="crewai",
        task_type="research",
        success=True,
        latency=2.5,
    )
    print("      - Recorded agent task metrics")

    # Custom counter
    metrics.increment_counter("demo.iterations", value=100)
    print("      - Incremented custom counter")

    # Custom latency
    metrics.record_latency("demo.processing", 0.123)
    print("      - Recorded custom latency")

    # Print summary
    print("\n" + "=" * 70)
    print("Monitoring Summary")
    print("=" * 70)
    print("\nMetrics Available:")
    print("  Tool Execution:")
    print("    - odin.tool.executions (counter)")
    print("    - odin.tool.errors (counter)")
    print("    - odin.tool.latency (histogram)")
    print("\n  LLM Operations:")
    print("    - odin.llm.requests (counter)")
    print("    - odin.llm.tokens (counter)")
    print("    - odin.llm.cost (counter)")
    print("    - odin.llm.latency (histogram)")
    print("\n  Agent Tasks:")
    print("    - odin.agent.tasks (counter)")
    print("    - odin.agent.success (counter)")
    print("    - odin.agent.latency (histogram)")
    print("\n  Plugin Lifecycle:")
    print("    - odin.plugin.loaded (up-down counter)")
    print("\n  Custom Metrics:")
    print("    - odin.custom.counter")
    print("    - odin.custom.histogram")

    print("\n" + "=" * 70)
    print("Integration Guide")
    print("=" * 70)
    print("\n1. OpenTelemetry (Traces + Metrics):")
    print("   Configure OTLP endpoint in .env:")
    print("   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317")
    print("\n2. Prometheus (Metrics only):")
    print("   From your code:")
    print("   from odin.tracing.prometheus import setup_prometheus_exporter")
    print("   setup_prometheus_exporter(settings, port=9090)")
    print("   Then configure Prometheus to scrape http://localhost:9090/metrics")
    print("\n3. Grafana Dashboards:")
    print("   Import pre-built dashboards (coming soon)")
    print("   Or create custom dashboards from metrics above")

    print("\n" + "=" * 70)
    print("Specialized LLM Monitoring Tools (Optional):")
    print("=" * 70)
    print("  - LangSmith: https://smith.langchain.com/")
    print("  - Helicone: https://helicone.ai/")
    print("  - Phoenix (Arize): https://phoenix.arize.com/")
    print("  - LangFuse: https://langfuse.com/")
    print("\n  These can be integrated via custom plugins")
    print("=" * 70)

    # Cleanup
    await app.shutdown()
    print("\n✓ Framework shut down (metrics flushed)")


if __name__ == "__main__":
    asyncio.run(main())
