"""Tests for protocol dispatcher."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from odin.protocols.protocol_dispatcher import ProtocolDispatcher, ProtocolType


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, name: str = "test-agent"):
        self.name = name
        self.tools = []

    def get_metadata(self) -> dict:
        return {"name": self.name, "version": "1.0.0"}


class TestProtocolType:
    """Test ProtocolType enum."""

    def test_all_protocol_types(self):
        """Test all protocol type values."""
        assert ProtocolType.MCP.value == "mcp"
        assert ProtocolType.A2A.value == "a2a"
        assert ProtocolType.AGUI.value == "agui"
        assert ProtocolType.COPILOTKIT.value == "copilotkit"
        assert ProtocolType.HTTP.value == "http"


class TestProtocolDispatcherInit:
    """Test ProtocolDispatcher initialization."""

    def test_init(self):
        """Test dispatcher initialization."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        assert dispatcher.agent == agent
        assert dispatcher._adapters == {}

    def test_adapters_property(self):
        """Test adapters property returns empty dict initially."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        assert dispatcher.adapters == {}


class TestProtocolDispatcherDetection:
    """Test protocol detection."""

    @pytest.mark.asyncio
    async def test_detect_a2a_agent_card_path(self):
        """Test detection of A2A protocol from agent-card path."""
        request = MagicMock()
        request.url.path = "/.well-known/agent-card"
        request.headers = {}

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.A2A

    @pytest.mark.asyncio
    async def test_detect_a2a_message_send_path(self):
        """Test detection of A2A protocol from message/send path."""
        request = MagicMock()
        request.url.path = "/message/send"
        request.headers = {}

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.A2A

    @pytest.mark.asyncio
    async def test_detect_copilotkit_graphql(self):
        """Test detection of CopilotKit protocol from GraphQL query."""
        request = MagicMock()
        request.url.path = "/graphql"
        request.headers = {"content-type": "application/json"}
        request.json = AsyncMock(return_value={
            "query": "query { copilotActions { name } }"
        })

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.COPILOTKIT

    @pytest.mark.asyncio
    async def test_detect_copilotkit_agent_query(self):
        """Test detection of CopilotKit from agent keyword in query."""
        request = MagicMock()
        request.url.path = "/api"
        request.headers = {"content-type": "application/json"}
        request.json = AsyncMock(return_value={
            "query": "mutation { runAgent(input: {}) { result } }"
        })

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.COPILOTKIT

    @pytest.mark.asyncio
    async def test_detect_agui_sse_accept(self):
        """Test detection of AG-UI protocol from SSE accept header."""
        request = MagicMock()
        request.url.path = "/run"
        request.headers = {
            "content-type": "application/json",
            "accept": "text/event-stream",
        }
        request.json = AsyncMock(return_value={"messages": []})

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.AGUI

    @pytest.mark.asyncio
    async def test_detect_http_default(self):
        """Test default detection falls back to HTTP."""
        request = MagicMock()
        request.url.path = "/api/tools"
        request.headers = {
            "content-type": "application/json",
            "accept": "application/json",
        }
        request.json = AsyncMock(return_value={"tool": "search"})

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.HTTP

    @pytest.mark.asyncio
    async def test_detect_http_on_json_parse_error(self):
        """Test fallback to HTTP when JSON parsing fails."""
        request = MagicMock()
        request.url.path = "/api"
        request.headers = {"content-type": "application/json"}
        request.json = AsyncMock(side_effect=Exception("Invalid JSON"))

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.HTTP

    @pytest.mark.asyncio
    async def test_detect_http_non_json_content(self):
        """Test HTTP detection for non-JSON content."""
        request = MagicMock()
        request.url.path = "/api"
        request.headers = {"content-type": "text/plain"}

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.HTTP

    @pytest.mark.asyncio
    async def test_detect_json_without_query(self):
        """Test HTTP detection for JSON without query field."""
        request = MagicMock()
        request.url.path = "/api"
        request.headers = {"content-type": "application/json"}
        request.json = AsyncMock(return_value={"data": "test"})

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.HTTP


class TestProtocolDispatcherAdapterLoading:
    """Test adapter loading."""

    def test_get_adapter_mcp(self):
        """Test lazy loading MCP adapter."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        with patch("odin.protocols.mcp.adapter.MCPAdapter") as MockAdapter:
            mock_adapter = MagicMock()
            MockAdapter.return_value = mock_adapter

            adapter = dispatcher.get_adapter(ProtocolType.MCP)

            MockAdapter.assert_called_once_with(agent)
            assert adapter == mock_adapter
            assert ProtocolType.MCP in dispatcher._adapters

    def test_get_adapter_a2a(self):
        """Test lazy loading A2A adapter."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        with patch("odin.protocols.a2a.adapter.A2AAdapter") as MockAdapter:
            mock_adapter = MagicMock()
            MockAdapter.return_value = mock_adapter

            adapter = dispatcher.get_adapter(ProtocolType.A2A)

            MockAdapter.assert_called_once_with(agent)
            assert adapter == mock_adapter

    def test_get_adapter_agui(self):
        """Test lazy loading AG-UI adapter."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        with patch("odin.protocols.agui.adapter.AGUIAdapter") as MockAdapter:
            mock_adapter = MagicMock()
            MockAdapter.return_value = mock_adapter

            adapter = dispatcher.get_adapter(ProtocolType.AGUI)

            MockAdapter.assert_called_once_with(agent)
            assert adapter == mock_adapter

    def test_get_adapter_copilotkit(self):
        """Test lazy loading CopilotKit adapter."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        with patch("odin.protocols.copilotkit.adapter_v2.CopilotKitAdapter") as MockAdapter:
            mock_adapter = MagicMock()
            MockAdapter.return_value = mock_adapter

            adapter = dispatcher.get_adapter(ProtocolType.COPILOTKIT)

            MockAdapter.assert_called_once_with(agent)
            assert adapter == mock_adapter

    def test_get_adapter_http(self):
        """Test lazy loading HTTP adapter."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        with patch("odin.protocols.http.adapter.HTTPAdapter") as MockAdapter:
            mock_adapter = MagicMock()
            MockAdapter.return_value = mock_adapter

            adapter = dispatcher.get_adapter(ProtocolType.HTTP)

            MockAdapter.assert_called_once_with(agent)
            assert adapter == mock_adapter

    def test_get_adapter_caches_adapter(self):
        """Test that adapter is cached after first load."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        with patch("odin.protocols.http.adapter.HTTPAdapter") as MockAdapter:
            mock_adapter = MagicMock()
            MockAdapter.return_value = mock_adapter

            # First call
            adapter1 = dispatcher.get_adapter(ProtocolType.HTTP)
            # Second call
            adapter2 = dispatcher.get_adapter(ProtocolType.HTTP)

            # Should only create once
            MockAdapter.assert_called_once()
            assert adapter1 is adapter2


class TestProtocolDispatcherDispatch:
    """Test request dispatching."""

    @pytest.mark.asyncio
    async def test_dispatch_to_http(self):
        """Test dispatching to HTTP adapter."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        # Create mock request
        request = MagicMock()
        request.url.path = "/api/tools"
        request.method = "POST"
        request.headers = {
            "content-type": "application/json",
            "accept": "application/json",
        }
        request.json = AsyncMock(return_value={"tool": "test"})

        # Mock the HTTP adapter
        mock_adapter = MagicMock()
        mock_adapter.handle_request = AsyncMock(return_value={"status": "ok"})

        with patch("odin.protocols.http.adapter.HTTPAdapter", return_value=mock_adapter):
            result = await dispatcher.dispatch(request)

            mock_adapter.handle_request.assert_called_once_with(request)
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_dispatch_to_a2a(self):
        """Test dispatching to A2A adapter."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        request = MagicMock()
        request.url.path = "/.well-known/agent-card"
        request.method = "GET"
        request.headers = {}

        mock_adapter = MagicMock()
        mock_adapter.handle_request = AsyncMock(return_value={"name": "agent"})

        with patch("odin.protocols.a2a.adapter.A2AAdapter", return_value=mock_adapter):
            result = await dispatcher.dispatch(request)

            mock_adapter.handle_request.assert_called_once_with(request)
            assert result == {"name": "agent"}

    @pytest.mark.asyncio
    async def test_dispatch_to_agui(self):
        """Test dispatching to AG-UI adapter."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        request = MagicMock()
        request.url.path = "/run"
        request.method = "POST"
        request.headers = {
            "content-type": "application/json",
            "accept": "text/event-stream",
        }
        request.json = AsyncMock(return_value={})

        mock_adapter = MagicMock()
        mock_adapter.handle_request = AsyncMock(return_value="event: data")

        with patch("odin.protocols.agui.adapter.AGUIAdapter", return_value=mock_adapter):
            result = await dispatcher.dispatch(request)

            mock_adapter.handle_request.assert_called_once_with(request)


class TestProtocolDispatcherEdgeCases:
    """Test edge cases."""

    def test_adapters_returns_copy(self):
        """Test that adapters property returns current adapters."""
        agent = MockAgent()
        dispatcher = ProtocolDispatcher(agent)

        # Initially empty
        assert len(dispatcher.adapters) == 0

        # After loading one
        with patch("odin.protocols.http.adapter.HTTPAdapter") as MockAdapter:
            MockAdapter.return_value = MagicMock()
            dispatcher.get_adapter(ProtocolType.HTTP)

        assert len(dispatcher.adapters) == 1
        assert ProtocolType.HTTP in dispatcher.adapters

    @pytest.mark.asyncio
    async def test_detect_preserves_case_in_query(self):
        """Test that query parsing is case-insensitive."""
        request = MagicMock()
        request.url.path = "/graphql"
        request.headers = {"content-type": "application/json"}
        request.json = AsyncMock(return_value={
            "query": "query { COPILOT { actions } }"
        })

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.COPILOTKIT

    @pytest.mark.asyncio
    async def test_detect_handles_empty_headers(self):
        """Test detection with missing headers."""
        request = MagicMock()
        request.url.path = "/api"
        request.headers = {}

        protocol = await ProtocolDispatcher.detect_protocol(request)
        assert protocol == ProtocolType.HTTP
