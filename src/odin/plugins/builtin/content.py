"""Content plugin for Odin.

This plugin provides tools for content generation and storage,
including saving content to Obsidian vaults.

Tools:
- obsidian_save_file: Save markdown content to an Obsidian vault
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig


class ContentPlugin(DecoratorPlugin):
    """Content generation and storage plugin.

    This plugin provides tools for managing content,
    particularly saving markdown files to Obsidian vaults.
    """

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)
        self._default_vault_path: Path | None = None

    @property
    def name(self) -> str:
        return "content"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Content generation and storage (Obsidian integration)"

    async def initialize(self) -> None:
        """Initialize plugin."""
        await super().initialize()
        # Get default vault path from settings or environment
        vault_path = (
            self.config.settings.get("obsidian_vault_path")
            or os.environ.get("OBSIDIAN_VAULT_PATH")
        )
        if vault_path:
            self._default_vault_path = Path(vault_path)

    def _extract_title_from_markdown(self, content: str) -> str | None:
        """Extract title from markdown content.

        Tries multiple strategies:
        1. YAML frontmatter 'title' field
        2. First H1 heading (# Title)
        3. First non-empty line
        """
        # Try YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            title_match = re.search(r"^title:\s*(.+)$", frontmatter, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
                # Remove quotes if present
                title = title.strip('"\'')
                return title

        # Try H1 heading
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()

        # Try first non-empty line
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("---") and not line.startswith("#"):
                # Truncate if too long
                return line[:100] if len(line) > 100 else line

        return None

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a string for use as a filename.

        Removes or replaces invalid characters.
        """
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # Remove leading/trailing whitespace and dots
        filename = filename.strip(" .")

        # Limit length
        if len(filename) > 200:
            filename = filename[:200]

        return filename

    @tool(description="Save markdown content to an Obsidian vault")
    async def obsidian_save_file(
        self,
        content: Annotated[
            str,
            Field(description="Markdown content to save")
        ],
        vault_path: Annotated[
            str,
            Field(description="Path to the Obsidian vault")
        ],
        subfolder: Annotated[
            str,
            Field(description="Subfolder within the vault")
        ] = "odin/content",
        filename: Annotated[
            str | None,
            Field(description="Optional filename. If not provided, extracted from content.")
        ] = None,
    ) -> dict[str, Any]:
        """Save markdown content to an Obsidian vault.

        The content is saved as a .md file in the specified vault
        and subfolder. If no filename is provided, it's extracted
        from the content's title or frontmatter.

        Args:
            content: Markdown content to save
            vault_path: Path to the Obsidian vault directory
            subfolder: Subfolder within the vault (e.g., "notes/github")
            filename: Optional filename (without .md extension)

        Returns:
            File information including path, title, and size
        """
        try:
            # Validate vault path
            vault = Path(vault_path).expanduser().resolve()
            if not vault.exists():
                return {
                    "success": False,
                    "error": f"Vault path does not exist: {vault_path}",
                }

            if not vault.is_dir():
                return {
                    "success": False,
                    "error": f"Vault path is not a directory: {vault_path}",
                }

            # Create target directory
            target_dir = vault / subfolder
            target_dir.mkdir(parents=True, exist_ok=True)

            # Determine filename
            if not filename:
                title = self._extract_title_from_markdown(content)
                if title:
                    filename = self._sanitize_filename(title)
                else:
                    # Use timestamp as fallback
                    filename = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Ensure .md extension
            if not filename.endswith(".md"):
                filename = f"{filename}.md"

            # Full file path
            file_path = target_dir / filename

            # Handle duplicate filenames
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                file_path = target_dir / f"{stem}_{counter}.md"
                counter += 1

            # Write content
            file_path.write_text(content, encoding="utf-8")

            # Get file info
            file_size = file_path.stat().st_size
            title = self._extract_title_from_markdown(content)

            return {
                "success": True,
                "data": {
                    "file_path": str(file_path),
                    "filename": file_path.name,
                    "title": title,
                    "file_size_bytes": file_size,
                    "vault_path": str(vault),
                    "subfolder": subfolder,
                },
            }

        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied writing to: {vault_path}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
