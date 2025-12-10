"""Base controller interface for mobile device automation."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ControllerConfig(BaseModel):
    """Controller configuration."""

    device_id: str | None = Field(default=None, description="Device serial number")
    timeout_ms: int = Field(default=30000, description="Command timeout in milliseconds")
    retry_count: int = Field(default=3, description="Number of retries on failure")


class BaseController(ABC):
    """Abstract base class for mobile device controllers.

    Defines the standard interface for device automation operations.
    Platform-specific implementations (ADB, HDC, iOS) inherit from this.
    """

    def __init__(self, config: ControllerConfig) -> None:
        """Initialize controller.

        Args:
            config: Controller configuration
        """
        self.config = config
        self._screen_size: tuple[int, int] | None = None

    @abstractmethod
    async def tap(self, x: int, y: int) -> None:
        """Tap at specified coordinates.

        Args:
            x: X coordinate in pixels
            y: Y coordinate in pixels
        """

    @abstractmethod
    async def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """Long press at specified coordinates.

        Args:
            x: X coordinate in pixels
            y: Y coordinate in pixels
            duration_ms: Press duration in milliseconds
        """

    @abstractmethod
    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Swipe from one point to another.

        Args:
            x1: Start X coordinate
            y1: Start Y coordinate
            x2: End X coordinate
            y2: End Y coordinate
            duration_ms: Swipe duration in milliseconds
        """

    @abstractmethod
    async def input_text(self, text: str) -> None:
        """Input text on device.

        Args:
            text: Text to input
        """

    @abstractmethod
    async def press_key(self, key: str) -> None:
        """Press a key.

        Args:
            key: Key name (back, home, enter, volume_up, volume_down, etc.)
        """

    @abstractmethod
    async def screenshot(self) -> bytes:
        """Take a screenshot.

        Returns:
            PNG image bytes
        """

    @abstractmethod
    async def get_screen_size(self) -> tuple[int, int]:
        """Get screen dimensions.

        Returns:
            Tuple of (width, height) in pixels
        """

    @abstractmethod
    async def open_app(self, package: str, activity: str | None = None) -> None:
        """Open an application.

        Args:
            package: Package name or bundle ID
            activity: Activity name (Android only)
        """

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if device is connected.

        Returns:
            True if device is connected and responsive
        """

    async def get_cached_screen_size(self) -> tuple[int, int]:
        """Get screen size with caching.

        Returns:
            Tuple of (width, height) in pixels
        """
        if self._screen_size is None:
            self._screen_size = await self.get_screen_size()
        return self._screen_size
