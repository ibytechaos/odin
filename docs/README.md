# Odin Documentation

Odin is a modern, protocol-agnostic agent development framework with first-class support for MCP, A2A, and AG-UI protocols.

## Protocols

Odin supports multiple protocols for different use cases:

| Protocol | Use Case | Transport |
|----------|----------|-----------|
| [AG-UI](./AGUI_PROTOCOL.md) | Frontend integration | HTTP + SSE |
| [A2A](./A2A_PROTOCOL.md) | Agent-to-agent | HTTP + SSE |
| MCP | Claude Desktop | stdio |

### [AG-UI Protocol](./AGUI_PROTOCOL.md)

For frontend integration with generative UI systems like CopilotKit.

- Real-time streaming (SSE)
- Tool execution with streaming results
- Generative UI support
- Human-in-the-loop workflows

### [A2A Protocol](./A2A_PROTOCOL.md)

For agent-to-agent communication following Google's A2A standard.

- Task-based interaction model
- Agent discovery via Agent Cards
- Multi-agent orchestration
- Structured message passing

### MCP Protocol

For integration with Claude Desktop and other MCP clients.

- Tool exposure via stdio transport
- Claude Desktop configuration
- Stateless tool execution
- Resource and prompt support

## Development

### [Monitoring & Observability](./development/MONITORING.md)

Production-ready monitoring with OpenTelemetry and Prometheus.

- Distributed tracing
- AI/Agent specific metrics
- Grafana dashboards
- Alert configuration

## Quick Links

- [Getting Started](../README.md) - Main project README
- [Demo Application](../examples/demo/) - Complete working example with frontend
