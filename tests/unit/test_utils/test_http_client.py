"""Tests for the HTTP client utilities."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import asyncio

from odin.utils.http_client import (
    AsyncHTTPClient,
    HTTPClientError,
    fetch_json,
    post_json,
)


class TestHTTPClientError:
    """Test HTTPClientError exception."""

    def test_error_with_message(self):
        """Test error with message only."""
        error = HTTPClientError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None

    def test_error_with_status_code(self):
        """Test error with status code."""
        error = HTTPClientError("Not found", status_code=404)
        assert str(error) == "Not found"
        assert error.status_code == 404


class TestAsyncHTTPClientInit:
    """Test AsyncHTTPClient initialization."""

    def test_default_init(self):
        """Test default initialization."""
        client = AsyncHTTPClient()
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert client.default_headers == {}
        assert client.session is None

    def test_custom_init(self):
        """Test custom initialization."""
        headers = {"Authorization": "Bearer token"}
        client = AsyncHTTPClient(
            timeout=60,
            max_retries=5,
            retry_delay=2.0,
            headers=headers,
        )
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
        assert client.default_headers == headers


class TestAsyncHTTPClientLifecycle:
    """Test AsyncHTTPClient lifecycle methods."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test session initialization."""
        client = AsyncHTTPClient()
        assert client.session is None

        await client.initialize()
        assert client.session is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_initialize_twice(self):
        """Test that initialize is idempotent."""
        client = AsyncHTTPClient()

        await client.initialize()
        session1 = client.session

        await client.initialize()
        session2 = client.session

        # Should be same session
        assert session1 is session2

        await client.close()

    @pytest.mark.asyncio
    async def test_close(self):
        """Test session close."""
        client = AsyncHTTPClient()
        await client.initialize()
        assert client.session is not None

        await client.close()
        assert client.session is None

    @pytest.mark.asyncio
    async def test_close_without_init(self):
        """Test close without initialization."""
        client = AsyncHTTPClient()
        # Should not raise
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with AsyncHTTPClient() as client:
            assert client.session is not None

        assert client.session is None


class TestAsyncHTTPClientRequest:
    """Test AsyncHTTPClient request methods."""

    @pytest.mark.asyncio
    async def test_get_request(self):
        """Test GET request."""
        client = AsyncHTTPClient()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.ok = True
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = AsyncMock(return_value='{"data": "test"}')
        mock_response.json = AsyncMock(return_value={"data": "test"})

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(
            aiohttp.ClientSession, "request", return_value=mock_context
        ) as mock_request:
            await client.initialize()
            result = await client.get("https://api.example.com/data")

            assert result["status"] == 200
            assert result["ok"] is True
            assert result["json"] == {"data": "test"}

        await client.close()

    @pytest.mark.asyncio
    async def test_post_request(self):
        """Test POST request."""
        client = AsyncHTTPClient()

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.ok = True
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = AsyncMock(return_value='{"id": 1}')
        mock_response.json = AsyncMock(return_value={"id": 1})

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(
            aiohttp.ClientSession, "request", return_value=mock_context
        ):
            await client.initialize()
            result = await client.post(
                "https://api.example.com/data",
                json={"name": "test"},
            )

            assert result["status"] == 201
            assert result["json"] == {"id": 1}

        await client.close()

    @pytest.mark.asyncio
    async def test_put_request(self):
        """Test PUT request."""
        client = AsyncHTTPClient()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.ok = True
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value='{"updated": true}')
        mock_response.json = AsyncMock(return_value={"updated": True})

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(
            aiohttp.ClientSession, "request", return_value=mock_context
        ):
            await client.initialize()
            result = await client.put(
                "https://api.example.com/data/1",
                json={"name": "updated"},
            )

            assert result["status"] == 200
            assert result["json"] == {"updated": True}

        await client.close()

    @pytest.mark.asyncio
    async def test_delete_request(self):
        """Test DELETE request."""
        client = AsyncHTTPClient()

        mock_response = AsyncMock()
        mock_response.status = 204
        mock_response.ok = True
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value="")
        mock_response.json = AsyncMock(side_effect=Exception("No JSON"))

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(
            aiohttp.ClientSession, "request", return_value=mock_context
        ):
            await client.initialize()
            result = await client.delete("https://api.example.com/data/1")

            assert result["status"] == 204
            assert result["json"] is None

        await client.close()

    @pytest.mark.asyncio
    async def test_request_auto_initialize(self):
        """Test that request auto-initializes session."""
        client = AsyncHTTPClient()
        assert client.session is None

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.ok = True
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.json = AsyncMock(side_effect=Exception())

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(
            aiohttp.ClientSession, "request", return_value=mock_context
        ):
            await client.get("https://example.com")
            assert client.session is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_request_with_headers(self):
        """Test request with custom headers."""
        client = AsyncHTTPClient(headers={"Default-Header": "value"})

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.ok = True
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.json = AsyncMock(side_effect=Exception())

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(
            aiohttp.ClientSession, "request", return_value=mock_context
        ) as mock_request:
            await client.initialize()
            await client.get(
                "https://example.com",
                headers={"Custom-Header": "custom"},
            )

            # Verify headers were merged
            call_kwargs = mock_request.call_args.kwargs
            assert "headers" in call_kwargs
            assert call_kwargs["headers"]["Default-Header"] == "value"
            assert call_kwargs["headers"]["Custom-Header"] == "custom"

        await client.close()


class TestAsyncHTTPClientErrorHandling:
    """Test error handling in AsyncHTTPClient."""

    @pytest.mark.asyncio
    async def test_client_error_raises(self):
        """Test that client errors (4xx) raise immediately."""
        client = AsyncHTTPClient()

        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.ok = False
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_response.json = AsyncMock(side_effect=Exception())

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(
            aiohttp.ClientSession, "request", return_value=mock_context
        ):
            await client.initialize()
            with pytest.raises(HTTPClientError) as exc_info:
                await client.get("https://example.com/notfound")

            assert exc_info.value.status_code == 404

        await client.close()

    @pytest.mark.asyncio
    async def test_connection_error_with_retry(self):
        """Test that connection errors are retried."""
        client = AsyncHTTPClient(max_retries=2, retry_delay=0.01)

        await client.initialize()

        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # Create a context manager that raises on enter
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(
                side_effect=aiohttp.ClientError("Connection failed")
            )
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        with patch.object(
            client.session, "request", side_effect=mock_request
        ):
            with pytest.raises(HTTPClientError) as exc_info:
                await client.get("https://example.com", retry=True)

            assert "Request failed" in str(exc_info.value)
            assert call_count == 2  # Retried once

        await client.close()

    @pytest.mark.asyncio
    async def test_no_retry_when_disabled(self):
        """Test that retry can be disabled."""
        client = AsyncHTTPClient(max_retries=3, retry_delay=0.01)

        await client.initialize()

        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(
                side_effect=aiohttp.ClientError("Connection failed")
            )
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        with patch.object(
            client.session, "request", side_effect=mock_request
        ):
            with pytest.raises(HTTPClientError):
                await client.get("https://example.com", retry=False)

            assert call_count == 1  # No retry

        await client.close()

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test timeout error handling."""
        client = AsyncHTTPClient(max_retries=1, retry_delay=0.01)

        await client.initialize()

        def mock_request(*args, **kwargs):
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        with patch.object(
            client.session, "request", side_effect=mock_request
        ):
            with pytest.raises(HTTPClientError) as exc_info:
                await client.get("https://example.com", retry=False)

            assert "timed out" in str(exc_info.value)

        await client.close()


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_fetch_json(self):
        """Test fetch_json function."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.ok = True
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value='{"data": "test"}')
        mock_response.json = AsyncMock(return_value={"data": "test"})

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(
            aiohttp.ClientSession, "request", return_value=mock_context
        ):
            result = await fetch_json("https://api.example.com/data")
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_post_json(self):
        """Test post_json function."""
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.ok = True
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value='{"id": 1}')
        mock_response.json = AsyncMock(return_value={"id": 1})

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(
            aiohttp.ClientSession, "request", return_value=mock_context
        ):
            result = await post_json(
                "https://api.example.com/data",
                data={"name": "test"},
            )
            assert result == {"id": 1}
