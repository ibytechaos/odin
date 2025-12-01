"""NotebookLLM Plugin for Odin.

Browser automation tools for interacting with Google NotebookLLM.
Provides capabilities to add notes, generate infographics and presentations,
and download generated content.

Uses browser_session for remote Chrome DevTools Protocol (CDP) connection.

Configuration via environment variables:
    CHROME_DEBUG_HOST: Remote Chrome host (e.g., chrome.example.com)
    CHROME_DEBUG_PORT: Remote Chrome port (default: 443 for TLS, 9222 otherwise)
    CHROME_DEBUG_TLS: Use TLS (true/false)

Requirements:
    - playwright
    - pdf2image (for PDF to images conversion)
    - poppler-utils (system dependency for pdf2image)

Tools:
- notebookllm_add_source: Add a web source (URL) to a notebook
- notebookllm_generate_mindmap: Generate a mind map from sources
- notebookllm_generate_infographic: Generate an infographic from sources
- notebookllm_generate_presentation: Generate a presentation from sources
- notebookllm_download_content: Download generated content
- pdf_to_images: Convert PDF to images
- images_to_editable_pptx: Convert slide images to editable PPTX
- notebookllm_close_browser: Close browser connection
"""

from __future__ import annotations

import asyncio
import base64
import time
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from odin.decorators import tool
from odin.plugins import DecoratorPlugin, PluginConfig
from odin.utils.browser_session import (
    BrowserConfig,
    BrowserSession,
    get_browser_session,
    cleanup_all_browser_sessions,
)


class NotebookLLMPlugin(DecoratorPlugin):
    """NotebookLLM automation plugin for adding notes and generating content.

    This plugin provides browser automation tools for Google NotebookLLM,
    including adding sources, generating mind maps, infographics, and presentations.
    """

    def __init__(self, config: PluginConfig | None = None) -> None:
        super().__init__(config)
        self._session: BrowserSession | None = None

    @property
    def name(self) -> str:
        return "notebookllm"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "NotebookLLM automation tools for notes, infographics, and presentations"

    async def _get_session(self) -> BrowserSession:
        """Get browser session from pool (uses environment config)."""
        if self._session is None or self._session.page is None:
            self._session = await get_browser_session()
        return self._session

    async def _get_page(self):
        """Get browser page from session."""
        session = await self._get_session()
        return session.page

    async def _close_browser(self) -> None:
        """Disconnect from browser (does not close the browser)."""
        await cleanup_all_browser_sessions()
        self._session = None

    async def _wait_for_notebookllm_ready(self, page, timeout: int = 60) -> bool:
        """Wait for NotebookLLM page to be ready (logged in and loaded)."""
        try:
            await page.wait_for_selector(
                'section.source-panel, button.add-source-button, '
                'button[aria-label="添加来源"], button[aria-label="Add source"]',
                timeout=timeout * 1000,
            )
            return True
        except Exception:
            return False

    async def _create_new_notebook(self, notebook_name: str | None = None) -> str | None:
        """Create a new notebook and return its URL."""
        page = await self._get_page()

        await page.goto("https://notebooklm.google.com/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        if "accounts.google.com" in page.url:
            return None

        create_btn = await page.query_selector(
            'button[aria-label="新建笔记本"], button[aria-label="New notebook"], '
            'button.create-new-button'
        )

        if not create_btn:
            create_btn = await page.query_selector('.create-new-action-button')

        if create_btn:
            await create_btn.click()
            await asyncio.sleep(4)

        current_url = page.url

        if "notebooklm.google.com/notebook/" in current_url:
            return current_url

        return None

    @tool(description="Add a web source (URL) to a NotebookLLM notebook")
    async def notebookllm_add_source(
        self,
        source_url: Annotated[str, Field(description="URL of the webpage to add as a source")],
        notebook_url: Annotated[
            str | None,
            Field(description="Full URL of the NotebookLLM notebook (optional, creates new if not provided)")
        ] = None,
        notebook_name: Annotated[
            str | None,
            Field(description="Name for new notebook (only used when creating new notebook)")
        ] = None,
        wait_for_processing: Annotated[
            bool,
            Field(description="Whether to wait for source processing to complete")
        ] = True,
        timeout: Annotated[
            int,
            Field(description="Maximum time to wait in seconds", ge=30, le=600)
        ] = 120,
    ) -> dict[str, Any]:
        """Add a web source (URL) to a NotebookLLM notebook.

        If notebook_url is not provided, creates a new notebook first.

        Args:
            source_url: URL of the webpage to add as a source
            notebook_url: Full URL of the NotebookLLM notebook (optional)
            notebook_name: Name for new notebook (only used when creating new notebook)
            wait_for_processing: Whether to wait for source processing to complete
            timeout: Maximum time to wait in seconds

        Returns:
            Status of the operation including notebook_url
        """
        try:
            page = await self._get_page()

            created_new_notebook = False
            final_notebook_url = notebook_url

            if not notebook_url:
                final_notebook_url = await self._create_new_notebook(notebook_name)

                if not final_notebook_url:
                    if "accounts.google.com" in page.url:
                        return {
                            "success": False,
                            "error": "Not logged in to Google. Please login manually in the browser window.",
                            "action_required": "login",
                            "notebook_url": None,
                        }
                    return {
                        "success": False,
                        "error": "Failed to create new notebook",
                        "notebook_url": None,
                    }

                created_new_notebook = True
            else:
                await page.goto(notebook_url, wait_until="domcontentloaded")
                await asyncio.sleep(2)

            if "accounts.google.com" in page.url:
                return {
                    "success": False,
                    "error": "Not logged in to Google. Please login manually in the browser window.",
                    "action_required": "login",
                    "notebook_url": final_notebook_url,
                }

            if not await self._wait_for_notebookllm_ready(page, timeout=30):
                return {
                    "success": False,
                    "error": "NotebookLLM page did not load properly",
                    "notebook_url": final_notebook_url,
                }

            existing_dialog = await page.query_selector('.upload-dialog-panel')

            if not existing_dialog:
                add_button = await page.query_selector(
                    'button.add-source-button, button[aria-label="添加来源"], '
                    'button[aria-label="Add source"]'
                )

                if not add_button:
                    return {
                        "success": False,
                        "error": "Could not find 'Add source' button",
                        "notebook_url": final_notebook_url,
                    }

                await add_button.click()
                await asyncio.sleep(1.5)

                existing_dialog = await page.wait_for_selector(
                    '.upload-dialog-panel',
                    timeout=10000,
                )

            if not existing_dialog:
                return {
                    "success": False,
                    "error": "Upload dialog did not appear",
                    "notebook_url": final_notebook_url,
                }

            url_input = await page.query_selector(
                '.upload-dialog-panel textarea.text-area, '
                '.cdk-overlay-pane textarea.text-area, '
                '.multi-urls-input-form textarea'
            )

            if not url_input:
                website_chip = await page.query_selector(
                    '.mat-mdc-chip:has(.mdc-evolution-chip__text-label:has-text("网站")), '
                    '.mat-mdc-chip:has(mat-icon:has-text("web"))'
                )

                if not website_chip:
                    website_chip = await page.query_selector(
                        '.chip-group__chip:has-text("网站"), '
                        '.chip-group__chip:has-text("Website")'
                    )

                if not website_chip:
                    return {
                        "success": False,
                        "error": "Could not find 'Website' option in add source dialog",
                        "notebook_url": final_notebook_url,
                    }

                await website_chip.click()
                await asyncio.sleep(1)

                url_input = await page.query_selector(
                    '.upload-dialog-panel textarea.text-area, '
                    '.cdk-overlay-pane textarea.text-area, '
                    '.multi-urls-input-form textarea'
                )

            if not url_input:
                return {
                    "success": False,
                    "error": "Could not find URL input field",
                    "notebook_url": final_notebook_url,
                }

            await url_input.fill(source_url)
            await asyncio.sleep(0.5)

            submit_button = await page.query_selector(
                '.upload-dialog-panel button:has-text("插入"), '
                '.cdk-overlay-pane button:has-text("插入"), '
                '.upload-dialog-panel button:has-text("Insert")'
            )

            if not submit_button:
                return {
                    "success": False,
                    "error": "Could not find 'Insert' button",
                    "notebook_url": final_notebook_url,
                }

            await asyncio.sleep(0.5)
            await submit_button.click()

            if wait_for_processing:
                start_time = time.time()

                while time.time() - start_time < timeout:
                    dialog_visible = await page.query_selector('.upload-dialog-panel')
                    if not dialog_visible:
                        await asyncio.sleep(2)
                        break

                    error = await page.query_selector(
                        '.mat-mdc-snack-bar-container:has-text("error"), '
                        '[role="alert"]:has-text("失败"), '
                        '[role="alert"]:has-text("failed")'
                    )
                    if error:
                        error_text = await error.inner_text()
                        return {
                            "success": False,
                            "error": f"NotebookLLM error: {error_text}",
                            "notebook_url": final_notebook_url,
                        }

                    await asyncio.sleep(1)

            final_notebook_url = page.url

            return {
                "success": True,
                "data": {
                    "message": f"Successfully added source: {source_url}",
                    "notebook_url": final_notebook_url,
                    "created_new_notebook": created_new_notebook,
                },
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "hint": "Start Chrome with: google-chrome --remote-debugging-port=9222",
                "notebook_url": notebook_url,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "notebook_url": notebook_url,
            }

    @tool(description="Generate a mind map from NotebookLLM sources")
    async def notebookllm_generate_mindmap(
        self,
        notebook_url: Annotated[str, Field(description="Full URL of the NotebookLLM notebook")],
        timeout: Annotated[
            int,
            Field(description="Maximum time to wait for generation in seconds", ge=60, le=600)
        ] = 180,
    ) -> dict[str, Any]:
        """Generate a mind map from NotebookLLM sources.

        Args:
            notebook_url: Full URL of the NotebookLLM notebook
            timeout: Maximum time to wait for generation in seconds

        Returns:
            Status of the operation with mind map info
        """
        try:
            page = await self._get_page()

            await page.goto(notebook_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            if not await self._wait_for_notebookllm_ready(page, timeout=30):
                return {
                    "success": False,
                    "error": "NotebookLLM page did not load properly",
                    "notebook_url": notebook_url,
                }

            mindmap_btn = await page.query_selector('button.mind-map-button')

            if not mindmap_btn:
                mindmap_btn = await page.query_selector(
                    'button:has-text("思维导图"), button:has-text("Mind map")'
                )

            if not mindmap_btn:
                mindmap_btn = await page.query_selector(
                    '.studio-panel button:has(mat-icon:has-text("flowchart"))'
                )

            if not mindmap_btn:
                return {
                    "success": False,
                    "error": "Could not find mind map generation button",
                    "notebook_url": notebook_url,
                }

            existing_artifacts = await page.query_selector_all(
                '.studio-panel mat-icon.artifact-icon:has-text("flowchart")'
            )
            initial_count = len(existing_artifacts)

            await mindmap_btn.click()
            await asyncio.sleep(2)

            start_time = time.time()

            while time.time() - start_time < timeout:
                studio_panel = await page.query_selector('.studio-panel')
                if studio_panel:
                    studio_text = await studio_panel.inner_text()

                    if "正在生成" in studio_text or "Generating" in studio_text:
                        await asyncio.sleep(3)
                        continue

                    current_artifacts = await page.query_selector_all(
                        '.studio-panel mat-icon.artifact-icon:has-text("flowchart")'
                    )
                    if len(current_artifacts) > initial_count:
                        return {
                            "success": True,
                            "data": {
                                "message": "Mind map generated successfully",
                                "notebook_url": notebook_url,
                            },
                        }

                error = await page.query_selector(
                    '.mat-mdc-snack-bar-container:has-text("error"), '
                    '[role="alert"]:has-text("失败"), '
                    '[role="alert"]:has-text("failed")'
                )
                if error:
                    error_text = await error.inner_text()
                    return {
                        "success": False,
                        "error": f"Generation failed: {error_text}",
                        "notebook_url": notebook_url,
                    }

                await asyncio.sleep(3)

            return {
                "success": False,
                "error": "Timeout waiting for mind map generation",
                "notebook_url": notebook_url,
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "hint": "Start Chrome with: google-chrome --remote-debugging-port=9222",
                "notebook_url": notebook_url,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "notebook_url": notebook_url,
            }

    @tool(description="Generate an infographic from NotebookLLM sources")
    async def notebookllm_generate_infographic(
        self,
        notebook_url: Annotated[str, Field(description="Full URL of the NotebookLLM notebook")],
        timeout: Annotated[
            int,
            Field(description="Maximum time to wait for generation in seconds", ge=60, le=600)
        ] = 180,
    ) -> dict[str, Any]:
        """Generate an infographic from NotebookLLM sources.

        Args:
            notebook_url: Full URL of the NotebookLLM notebook
            timeout: Maximum time to wait for generation in seconds

        Returns:
            Status of the operation with infographic info
        """
        try:
            page = await self._get_page()

            await page.goto(notebook_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            if not await self._wait_for_notebookllm_ready(page, timeout=30):
                return {
                    "success": False,
                    "error": "NotebookLLM page did not load properly",
                    "notebook_url": notebook_url,
                }

            infographic_btn = await page.query_selector(
                '.create-artifact-button-container:has-text("信息图")'
            )

            if not infographic_btn:
                infographic_btn = await page.query_selector(
                    '.create-artifact-button-container:has(mat-icon:has-text("stacked_bar_chart"))'
                )

            if not infographic_btn:
                infographic_btn = await page.query_selector(
                    '.create-artifact-button-container:has-text("Infographic")'
                )

            if not infographic_btn:
                return {
                    "success": False,
                    "error": "Could not find infographic generation button",
                    "notebook_url": notebook_url,
                }

            existing_artifacts = await page.query_selector_all(
                '.studio-panel mat-icon.artifact-icon:has-text("stacked_bar_chart")'
            )
            initial_count = len(existing_artifacts)

            await infographic_btn.click()
            await asyncio.sleep(2)

            start_time = time.time()

            while time.time() - start_time < timeout:
                studio_panel = await page.query_selector('.studio-panel')
                if studio_panel:
                    studio_text = await studio_panel.inner_text()

                    if "正在生成" in studio_text or "Generating" in studio_text:
                        await asyncio.sleep(3)
                        continue

                    current_artifacts = await page.query_selector_all(
                        '.studio-panel mat-icon.artifact-icon:has-text("stacked_bar_chart")'
                    )
                    if len(current_artifacts) > initial_count:
                        return {
                            "success": True,
                            "data": {
                                "message": "Infographic generated successfully",
                                "notebook_url": notebook_url,
                            },
                        }

                error = await page.query_selector(
                    '.mat-mdc-snack-bar-container:has-text("error"), '
                    '[role="alert"]:has-text("失败")'
                )
                if error:
                    error_text = await error.inner_text()
                    return {
                        "success": False,
                        "error": f"Generation failed: {error_text}",
                        "notebook_url": notebook_url,
                    }

                await asyncio.sleep(3)

            return {
                "success": False,
                "error": "Timeout waiting for infographic generation",
                "notebook_url": notebook_url,
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "hint": "Start Chrome with: google-chrome --remote-debugging-port=9222",
                "notebook_url": notebook_url,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "notebook_url": notebook_url,
            }

    @tool(description="Generate a presentation (slides) from NotebookLLM sources")
    async def notebookllm_generate_presentation(
        self,
        notebook_url: Annotated[str, Field(description="Full URL of the NotebookLLM notebook")],
        timeout: Annotated[
            int,
            Field(description="Maximum time to wait for generation in seconds", ge=60, le=7200)
        ] = 3600,
    ) -> dict[str, Any]:
        """Generate a presentation (slides) from NotebookLLM sources.

        Note: Presentation generation can take a long time (up to 1 hour).

        Args:
            notebook_url: Full URL of the NotebookLLM notebook
            timeout: Maximum time to wait for generation in seconds (default: 1 hour)

        Returns:
            Status of the operation with presentation info
        """
        try:
            page = await self._get_page()

            await page.goto(notebook_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            if not await self._wait_for_notebookllm_ready(page, timeout=30):
                return {
                    "success": False,
                    "error": "NotebookLLM page did not load properly",
                    "notebook_url": notebook_url,
                }

            presentation_btn = await page.query_selector(
                '.create-artifact-button-container:has-text("演示文稿")'
            )

            if not presentation_btn:
                presentation_btn = await page.query_selector(
                    '.create-artifact-button-container:has(mat-icon:has-text("tablet"))'
                )

            if not presentation_btn:
                presentation_btn = await page.query_selector(
                    '.create-artifact-button-container:has-text("Presentation")'
                )

            if not presentation_btn:
                return {
                    "success": False,
                    "error": "Could not find presentation generation button",
                    "notebook_url": notebook_url,
                }

            existing_artifacts = await page.query_selector_all(
                '.studio-panel mat-icon.artifact-icon:has-text("tablet")'
            )
            initial_count = len(existing_artifacts)

            await presentation_btn.click()
            await asyncio.sleep(2)

            start_time = time.time()

            while time.time() - start_time < timeout:
                studio_panel = await page.query_selector('.studio-panel')
                if studio_panel:
                    studio_text = await studio_panel.inner_text()

                    if "正在生成" in studio_text or "Generating" in studio_text:
                        await asyncio.sleep(3)
                        continue

                    current_artifacts = await page.query_selector_all(
                        '.studio-panel mat-icon.artifact-icon:has-text("tablet")'
                    )
                    if len(current_artifacts) > initial_count:
                        return {
                            "success": True,
                            "data": {
                                "message": "Presentation generated successfully",
                                "notebook_url": notebook_url,
                            },
                        }

                error = await page.query_selector(
                    '.mat-mdc-snack-bar-container:has-text("error"), '
                    '[role="alert"]:has-text("失败")'
                )
                if error:
                    error_text = await error.inner_text()
                    return {
                        "success": False,
                        "error": f"Generation failed: {error_text}",
                        "notebook_url": notebook_url,
                    }

                await asyncio.sleep(3)

            return {
                "success": False,
                "error": "Timeout waiting for presentation generation",
                "notebook_url": notebook_url,
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "hint": "Start Chrome with: google-chrome --remote-debugging-port=9222",
                "notebook_url": notebook_url,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "notebook_url": notebook_url,
            }

    async def _wait_for_content_rendered(
        self,
        page,
        content_type: str,
        timeout: int = 60,
    ) -> bool:
        """Wait for artifact content to be fully rendered before downloading."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            loading_indicators = await page.query_selector_all(
                '.mat-progress-spinner, '
                '.mat-progress-bar, '
                '.loading-indicator, '
                '.spinner, '
                '[class*="loading"], '
                '[class*="spinner"]'
            )

            visible_loading = False
            for indicator in loading_indicators:
                is_visible = await indicator.is_visible()
                if is_visible:
                    visible_loading = True
                    break

            if visible_loading:
                await asyncio.sleep(1)
                continue

            if content_type == "presentation":
                slides = await page.query_selector_all(
                    '.slide-container, '
                    '.presentation-slide, '
                    '[class*="slide"], '
                    '.pdf-page, '
                    'canvas'
                )

                if slides:
                    for slide in slides:
                        box = await slide.bounding_box()
                        if box and box['width'] > 0 and box['height'] > 0:
                            await asyncio.sleep(3)
                            return True

            elif content_type == "infographic":
                content_elements = await page.query_selector_all(
                    'img[src], svg, canvas'
                )
                for elem in content_elements:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        box = await elem.bounding_box()
                        if box and box['width'] > 100 and box['height'] > 100:
                            await asyncio.sleep(2)
                            return True

            await asyncio.sleep(2)

            loading_still = await page.query_selector(
                '.mat-progress-spinner:visible, '
                '.mat-progress-bar:visible'
            )
            if not loading_still:
                await asyncio.sleep(3)
                return True

        return False

    async def _download_artifact(
        self,
        page,
        artifact_icon: str,
        content_type: str,
        output_path: Path,
        timeout: int,
    ) -> dict[str, Any] | None:
        """Download a specific artifact by clicking it and then the download button."""
        artifact_btn = await page.query_selector(
            f'button:has(mat-icon.artifact-icon:has-text("{artifact_icon}"))'
        )

        if not artifact_btn:
            return None

        await artifact_btn.click()
        await asyncio.sleep(2)

        render_timeout = min(timeout, 120)
        await self._wait_for_content_rendered(page, content_type, timeout=render_timeout)

        download_btn = await page.query_selector(
            'button[aria-label="下载"], '
            'button[aria-label="Download"], '
            'button:has(mat-icon:has-text("save_alt"))'
        )

        if not download_btn:
            close_btn = await page.query_selector('button:has(mat-icon:has-text("close"))')
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(1)
            return None

        try:
            async with page.expect_download(timeout=timeout * 1000) as download_info:
                await download_btn.click()

            download = await download_info.value
            suggested_name = download.suggested_filename
            ext = Path(suggested_name).suffix if suggested_name else ".png"
            file_path = output_path / f"{content_type}_{int(time.time())}{ext}"
            await download.save_as(str(file_path))

            close_btn = await page.query_selector('button:has(mat-icon:has-text("close"))')
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(1)

            return {
                "type": content_type,
                "path": str(file_path),
                "original_name": suggested_name,
            }
        except Exception:
            close_btn = await page.query_selector('button:has(mat-icon:has-text("close"))')
            if close_btn:
                await close_btn.click()
                await asyncio.sleep(1)
            return None

    @tool(description="Download generated content from NotebookLLM")
    async def notebookllm_download_content(
        self,
        notebook_url: Annotated[str, Field(description="Full URL of the NotebookLLM notebook")],
        content_type: Annotated[
            str,
            Field(description="Type of content to download: infographic, presentation, or all")
        ] = "all",
        output_dir: Annotated[
            str | None,
            Field(description="Directory to save downloaded files (default: current directory)")
        ] = None,
        timeout: Annotated[
            int,
            Field(description="Maximum time to wait for downloads in seconds", ge=30, le=600)
        ] = 120,
    ) -> dict[str, Any]:
        """Download generated content (infographic and/or presentation) from NotebookLLM.

        Args:
            notebook_url: Full URL of the NotebookLLM notebook
            content_type: Type of content to download ("infographic", "presentation", or "all")
            output_dir: Directory to save downloaded files (default: current directory)
            timeout: Maximum time to wait for downloads in seconds

        Returns:
            Paths to downloaded files and status
        """
        try:
            page = await self._get_page()

            output_path = Path(output_dir) if output_dir else Path.cwd()
            output_path.mkdir(parents=True, exist_ok=True)

            await page.goto(notebook_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            if not await self._wait_for_notebookllm_ready(page, timeout=30):
                return {
                    "success": False,
                    "error": "NotebookLLM page did not load properly",
                }

            downloaded_files = []

            if content_type in ("infographic", "all"):
                result = await self._download_artifact(
                    page, "stacked_bar_chart", "infographic", output_path, timeout
                )
                if result:
                    downloaded_files.append(result)

            if content_type in ("presentation", "all"):
                result = await self._download_artifact(
                    page, "tablet", "presentation", output_path, timeout
                )
                if result:
                    downloaded_files.append(result)

            if not downloaded_files:
                return {
                    "success": False,
                    "error": "No downloadable content found. Make sure infographic/presentation has been generated.",
                }

            return {
                "success": True,
                "data": {
                    "message": f"Downloaded {len(downloaded_files)} file(s)",
                    "files": downloaded_files,
                    "output_dir": str(output_path),
                },
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "hint": "Start Chrome with: google-chrome --remote-debugging-port=9222",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @tool(description="Convert PDF file to a list of images (one per page)")
    async def pdf_to_images(
        self,
        pdf_path: Annotated[str, Field(description="Path to the PDF file")],
        output_dir: Annotated[
            str | None,
            Field(description="Directory to save images (default: same directory as PDF)")
        ] = None,
        dpi: Annotated[int, Field(description="Image resolution in DPI", ge=72, le=600)] = 200,
        format: Annotated[str, Field(description="Output image format (png, jpg, jpeg)")] = "png",
        return_base64: Annotated[
            bool,
            Field(description="Whether to include base64 encoded images in response")
        ] = False,
    ) -> dict[str, Any]:
        """Convert PDF file to a list of images (one per page).

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save images (default: same directory as PDF)
            dpi: Image resolution in DPI
            format: Output image format (png, jpg, jpeg)
            return_base64: Whether to include base64 encoded images in response

        Returns:
            List of generated image paths and optionally base64 data
        """
        try:
            from pdf2image import convert_from_path
        except ImportError:
            return {
                "success": False,
                "error": "pdf2image library not installed. Install with: pip install pdf2image",
                "hint": "Also requires poppler-utils: brew install poppler (macOS) or apt-get install poppler-utils (Linux)",
            }

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            return {
                "success": False,
                "error": f"PDF file not found: {pdf_path}",
            }

        output_path = Path(output_dir) if output_dir else pdf_file.parent
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            images = convert_from_path(str(pdf_file), dpi=dpi)

            image_files = []
            base64_images = []

            for i, image in enumerate(images):
                filename = f"{pdf_file.stem}_page_{i + 1}.{format}"
                image_path = output_path / filename
                image.save(str(image_path), format.upper())

                image_info = {
                    "page": i + 1,
                    "path": str(image_path),
                    "width": image.width,
                    "height": image.height,
                }
                image_files.append(image_info)

                if return_base64:
                    import io

                    buffer = io.BytesIO()
                    image.save(buffer, format=format.upper())
                    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    base64_images.append({
                        "page": i + 1,
                        "base64": b64,
                        "mime_type": f"image/{format}",
                    })

            result = {
                "success": True,
                "data": {
                    "message": f"Converted {len(images)} pages to images",
                    "total_pages": len(images),
                    "images": image_files,
                    "output_dir": str(output_path),
                    "format": format,
                    "dpi": dpi,
                },
            }

            if return_base64:
                result["data"]["base64_images"] = base64_images

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"PDF conversion failed: {str(e)}",
            }

    def _detect_text_regions(
        self,
        image_path: str,
        lang: str = "ch",
    ) -> list[dict[str, Any]]:
        """Detect text regions in an image using PaddleOCR."""
        try:
            from odin.compat import patch_langchain_for_paddlex
            patch_langchain_for_paddlex()
            from paddleocr import PaddleOCR
        except ImportError:
            raise ImportError(
                "PaddleOCR not installed. Install with: pip install paddlepaddle paddleocr"
            ) from None

        ocr = PaddleOCR(lang=lang)
        result = ocr.ocr(image_path)

        text_regions = []
        if result and result[0]:
            for line in result[0]:
                box = line[0]
                text, confidence = line[1]

                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)

                box_height = y_max - y_min
                estimated_font_size = int(box_height * 0.75)

                text_regions.append({
                    "text": text,
                    "confidence": confidence,
                    "box": {
                        "x": int(x_min),
                        "y": int(y_min),
                        "width": int(x_max - x_min),
                        "height": int(y_max - y_min),
                    },
                    "polygon": [[int(p[0]), int(p[1])] for p in box],
                    "estimated_font_size": estimated_font_size,
                })

        return text_regions

    def _create_text_mask(
        self,
        image_size: tuple[int, int],
        text_regions: list[dict[str, Any]],
        dilate_pixels: int = 5,
    ):
        """Create a binary mask for text regions."""
        import cv2
        import numpy as np

        width, height = image_size
        mask = np.zeros((height, width), dtype=np.uint8)

        for region in text_regions:
            polygon = np.array(region["polygon"], dtype=np.int32)
            cv2.fillPoly(mask, [polygon], 255)

        if dilate_pixels > 0:
            kernel = np.ones((dilate_pixels, dilate_pixels), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)

        return mask

    def _inpaint_background(
        self,
        image_path: str,
        mask,
        method: str = "telea",
        inpaint_radius: int = 5,
    ):
        """Remove text from image using inpainting to reconstruct background."""
        import cv2

        image = cv2.imread(image_path)

        if method == "lama":
            try:
                from lama_cleaner.model_manager import ModelManager
                from lama_cleaner.schema import Config

                model = ModelManager(name="lama", device="cpu")
                config = Config(
                    ldm_steps=25,
                    hd_strategy="Original",
                    hd_strategy_crop_margin=128,
                    hd_strategy_crop_trigger_size=800,
                    hd_strategy_resize_limit=800,
                )
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                result = model(image_rgb, mask, config)
                return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
            except ImportError:
                method = "telea"

        if method == "telea":
            return cv2.inpaint(image, mask, inpaint_radius, cv2.INPAINT_TELEA)
        else:
            return cv2.inpaint(image, mask, inpaint_radius, cv2.INPAINT_NS)

    def _estimate_font_color(
        self,
        image_path: str,
        region: dict[str, Any],
    ) -> tuple[int, int, int]:
        """Estimate the font color from a text region."""
        import cv2
        import numpy as np

        image = cv2.imread(image_path)
        box = region["box"]

        x, y, w, h = box["x"], box["y"], box["width"], box["height"]
        roi = image[y:y+h, x:x+w]

        if roi.size == 0:
            return (0, 0, 0)

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        mean_val = np.mean(gray)
        if mean_val > 127:
            text_mask = binary == 0
        else:
            text_mask = binary == 255

        if np.any(text_mask):
            text_pixels = roi[text_mask]
            avg_color = np.mean(text_pixels, axis=0)
            return (int(avg_color[2]), int(avg_color[1]), int(avg_color[0]))

        return (0, 0, 0)

    @tool(description="Convert slide images to an editable PowerPoint presentation")
    async def images_to_editable_pptx(
        self,
        image_paths: Annotated[list[str], Field(description="List of paths to slide images (in order)")],
        output_path: Annotated[str, Field(description="Path for the output .pptx file")],
        lang: Annotated[
            str,
            Field(description="OCR language ('ch' for Chinese+English, 'en' for English only)")
        ] = "ch",
        inpaint_method: Annotated[
            str,
            Field(description="Background reconstruction method ('telea', 'ns', or 'lama')")
        ] = "telea",
        slide_width_inches: Annotated[
            float,
            Field(description="Slide width in inches (default: 16:9 widescreen)", ge=1.0, le=30.0)
        ] = 13.333,
        slide_height_inches: Annotated[
            float,
            Field(description="Slide height in inches", ge=1.0, le=30.0)
        ] = 7.5,
        min_font_size: Annotated[
            int,
            Field(description="Minimum font size in points", ge=6, le=72)
        ] = 10,
        max_font_size: Annotated[
            int,
            Field(description="Maximum font size in points", ge=12, le=144)
        ] = 44,
    ) -> dict[str, Any]:
        """Convert slide images to an editable PowerPoint presentation.

        This tool:
        1. Uses OCR to detect text and its positions in each image
        2. Removes text from images using inpainting to create clean backgrounds
        3. Generates a PPTX with background images and editable text boxes

        Args:
            image_paths: List of paths to slide images (in order)
            output_path: Path for the output .pptx file
            lang: OCR language ('ch' for Chinese+English, 'en' for English only)
            inpaint_method: Background reconstruction method ('telea', 'ns', or 'lama')
            slide_width_inches: Slide width in inches (default: 16:9 widescreen)
            slide_height_inches: Slide height in inches
            min_font_size: Minimum font size in points
            max_font_size: Maximum font size in points

        Returns:
            Status with output path and processing details
        """
        try:
            import cv2
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
            from pptx.enum.text import PP_ALIGN
        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else str(e)
            return {
                "success": False,
                "error": f"Missing dependency: {missing}",
                "hint": "Install with: pip install python-pptx opencv-python paddlepaddle paddleocr",
            }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        prs = Presentation()
        prs.slide_width = Inches(slide_width_inches)
        prs.slide_height = Inches(slide_height_inches)

        blank_layout = prs.slide_layouts[6]

        processed_slides = []
        temp_files = []

        try:
            for idx, image_path in enumerate(image_paths):
                slide_info = {
                    "page": idx + 1,
                    "image": image_path,
                    "text_regions": 0,
                    "status": "processing",
                }

                if not Path(image_path).exists():
                    slide_info["status"] = "error"
                    slide_info["error"] = "Image file not found"
                    processed_slides.append(slide_info)
                    continue

                try:
                    text_regions = self._detect_text_regions(image_path, lang)
                    slide_info["text_regions"] = len(text_regions)
                except Exception as e:
                    slide_info["status"] = "error"
                    slide_info["error"] = f"OCR failed: {str(e)}"
                    processed_slides.append(slide_info)
                    continue

                image = cv2.imread(image_path)
                img_height, img_width = image.shape[:2]

                if text_regions:
                    mask = self._create_text_mask(
                        (img_width, img_height),
                        text_regions,
                        dilate_pixels=8,
                    )
                    background = self._inpaint_background(
                        image_path, mask, method=inpaint_method
                    )
                else:
                    background = image

                temp_bg_path = output_file.parent / f"_temp_bg_{idx}.png"
                cv2.imwrite(str(temp_bg_path), background)
                temp_files.append(temp_bg_path)

                slide = prs.slides.add_slide(blank_layout)

                slide.shapes.add_picture(
                    str(temp_bg_path),
                    Inches(0),
                    Inches(0),
                    width=prs.slide_width,
                    height=prs.slide_height,
                )

                scale_x = slide_width_inches / img_width
                scale_y = slide_height_inches / img_height

                for region in text_regions:
                    box = region["box"]

                    left = Inches(box["x"] * scale_x)
                    top = Inches(box["y"] * scale_y)
                    width = Inches(box["width"] * scale_x)
                    height = Inches(box["height"] * scale_y)

                    textbox = slide.shapes.add_textbox(left, top, width, height)
                    tf = textbox.text_frame
                    tf.word_wrap = False

                    p = tf.paragraphs[0]
                    p.text = region["text"]

                    font_size = int(region["estimated_font_size"] * scale_y * 72)
                    font_size = max(min_font_size, min(font_size, max_font_size))
                    p.font.size = Pt(font_size)

                    try:
                        r, g, b = self._estimate_font_color(image_path, region)
                        p.font.color.rgb = RGBColor(r, g, b)
                    except Exception:
                        p.font.color.rgb = RGBColor(0, 0, 0)

                    p.alignment = PP_ALIGN.LEFT

                slide_info["status"] = "success"
                processed_slides.append(slide_info)

            prs.save(str(output_file))

            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                except Exception:
                    pass

            success_count = sum(1 for s in processed_slides if s["status"] == "success")
            total_text_regions = sum(s.get("text_regions", 0) for s in processed_slides)

            return {
                "success": True,
                "data": {
                    "message": f"Created editable PPTX with {success_count}/{len(image_paths)} slides",
                    "output_path": str(output_file),
                    "total_slides": len(image_paths),
                    "successful_slides": success_count,
                    "total_text_regions": total_text_regions,
                    "slides": processed_slides,
                },
            }

        except Exception as e:
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                except Exception:
                    pass

            return {
                "success": False,
                "error": f"PPTX generation failed: {str(e)}",
            }

    @tool(description="Close the browser connection")
    async def notebookllm_close_browser(self) -> dict[str, Any]:
        """Close the browser connection (does not close the actual browser).

        Returns:
            Status of the operation
        """
        try:
            await self._close_browser()
            return {
                "success": True,
                "data": {"message": "Browser connection closed successfully"},
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
