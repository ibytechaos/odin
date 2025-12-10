#!/usr/bin/env python
"""Odin CLI - Command line interface for the Odin framework.

Commands:
    odin serve                  Start Odin server (standalone or project mode)
    odin create <project-name>  Create a new Odin project
    odin list                   List available agents/tools
    odin test <agent-name>      Test an agent interactively
    odin run <agent-name>       Run a specific agent
"""

import asyncio
import json
import shutil
from pathlib import Path
from typing import Literal

import click


def get_template_dir() -> Path:
    """Get the templates directory path."""
    return Path(__file__).parent / "templates"


def copy_template(
    src_dir: Path,
    dest_dir: Path,
    replacements: dict[str, str],
) -> None:
    """Copy template files with variable substitution."""
    for src_file in src_dir.rglob("*"):
        if src_file.is_file():
            # Calculate relative path
            rel_path = src_file.relative_to(src_dir)
            dest_file = dest_dir / rel_path

            # Create parent directories
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Read and substitute
            try:
                content = src_file.read_text()
                for key, value in replacements.items():
                    content = content.replace(f"{{{{{key}}}}}", value)
                dest_file.write_text(content)
            except UnicodeDecodeError:
                # Binary file, copy directly
                shutil.copy2(src_file, dest_file)


def copy_root_files(template_dir: Path, project_dir: Path, replacements: dict[str, str]) -> None:
    """Copy root-level template files (Makefile, docker-compose, etc)."""
    root_files = [
        "Makefile",
        "docker-compose.yml",
        ".env.example",
        "README.md",
        ".gitignore",
    ]
    for filename in root_files:
        src_file = template_dir / filename
        if src_file.exists():
            try:
                content = src_file.read_text()
                for key, value in replacements.items():
                    content = content.replace(f"{{{{{key}}}}}", value)
                (project_dir / filename).write_text(content)
            except UnicodeDecodeError:
                shutil.copy2(src_file, project_dir / filename)


def find_project_root() -> Path | None:
    """Find the project root by looking for Odin project markers.

    An Odin project is identified by:
    - agent/tools/ directory (created by `odin create`)
    - app.yaml config file
    - tools/ directory with Python files
    """
    cwd = Path.cwd()

    def is_odin_project(path: Path) -> bool:
        """Check if a path is an Odin project root."""
        # Check for agent/tools/ structure (from `odin create`)
        agent_tools = path / "agent" / "tools"
        if agent_tools.is_dir():
            return True

        # Check for app.yaml
        if (path / "app.yaml").is_file():
            return True

        # Check for tools/ with Python files (simpler project)
        tools_dir = path / "tools"
        return tools_dir.is_dir() and any(tools_dir.glob("*.py"))

    # Check if we're in a project root
    if is_odin_project(cwd):
        return cwd

    # Check if we're in agent/ directory
    if cwd.name == "agent" and (cwd / "tools").is_dir():
        return cwd.parent

    # Check parent directories (limited depth to avoid false positives)
    for i, parent in enumerate(cwd.parents):
        if i > 3:  # Don't search more than 3 levels up
            break
        if is_odin_project(parent):
            return parent

    return None


def get_odin_instance(project_root: Path):
    """Get an Odin instance for the project."""
    import sys

    # Add agent directory to path if exists
    agent_dir = project_root / "agent"
    if agent_dir.is_dir():
        sys.path.insert(0, str(agent_dir))
        tools_dir = agent_dir / "tools"
    else:
        tools_dir = project_root / "tools"

    from odin import Odin
    from odin.config import Settings

    # Create settings with custom plugin directory
    settings = Settings(
        plugin_dirs=[tools_dir] if tools_dir.is_dir() else [],
        plugin_auto_discovery=True,
    )
    odin = Odin(settings=settings)
    return odin


@click.group()
@click.version_option(version="0.1.0", prog_name="odin")
def cli() -> None:
    """Odin - Modern agent development framework."""
    pass


@cli.command()
@click.argument("name")
@click.option("--ui-only", is_flag=True, help="Create UI only")
@click.option("--agent-only", is_flag=True, help="Create agent only")
@click.option("--title", default=None, help="Project title (default: project name)")
def create(name: str, ui_only: bool, agent_only: bool, title: str | None) -> None:
    """Create a new Odin project.

    NAME is the project directory name.

    Examples:

        odin create my-agent          # Full stack project

        odin create my-agent --agent-only   # Agent only

        odin create my-agent --ui-only      # UI only
    """
    project_dir = Path.cwd() / name
    template_dir = get_template_dir()
    project_title = title or name.replace("-", " ").replace("_", " ").title()

    # Determine what to create
    create_ui = ui_only or (not ui_only and not agent_only)
    create_agent = agent_only or (not ui_only and not agent_only)

    replacements = {
        "PROJECT_NAME": name,
        "PROJECT_TITLE": project_title,
    }

    click.echo(f"Creating Odin project: {name}")
    click.echo(f"  Title: {project_title}")
    click.echo(f"  Directory: {project_dir}")
    click.echo()

    if project_dir.exists():
        click.echo(click.style(f"Error: Directory '{name}' already exists", fg="red"))
        raise SystemExit(1)

    project_dir.mkdir(parents=True)

    # Create agent
    if create_agent:
        click.echo("Creating agent...")
        agent_src = template_dir / "agent"
        agent_dest = project_dir / "agent"
        copy_template(agent_src, agent_dest, replacements)
        click.echo(click.style("  ✓ Agent created", fg="green"))

    # Create UI
    if create_ui:
        click.echo("Creating UI...")
        ui_src = template_dir / "ui"
        ui_dest = project_dir / "ui"
        copy_template(ui_src, ui_dest, replacements)
        click.echo(click.style("  ✓ UI created", fg="green"))

    # Copy root files for full stack
    if create_ui and create_agent:
        click.echo("Creating project files...")
        copy_root_files(template_dir, project_dir, replacements)
        click.echo(click.style("  ✓ Project files created", fg="green"))

    click.echo()
    click.echo(click.style("Project created successfully!", fg="green"))
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  cd {name}")

    if create_ui and create_agent:
        click.echo("  cp .env.example .env      # Configure your API keys")
        click.echo("  make install              # Install dependencies")
        click.echo("  make dev                  # Start development servers")
        click.echo()
        click.echo("Or with Docker:")
        click.echo("  make docker-build         # Build containers")
        click.echo("  make docker-up            # Start services")
    elif create_agent:
        click.echo("  cd agent")
        click.echo("  pip install -e .")
        click.echo("  python main.py")
    elif create_ui:
        click.echo("  cd ui")
        click.echo("  npm install")
        click.echo("  npm run dev")


@cli.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--builtin", "include_builtin", is_flag=True, help="Include built-in tools")
@click.option("--all", "show_all", is_flag=True, help="Show all tools (builtin + project)")
def list_agents(as_json: bool, include_builtin: bool, show_all: bool) -> None:
    """List available agents and tools.

    Examples:

        odin list              # List project tools (or builtin if not in project)

        odin list --builtin    # List built-in tools only

        odin list --all        # List all tools (project + builtin)

        odin list --json       # Output as JSON
    """
    project_root = find_project_root()

    async def _list():
        from odin import Odin
        from odin.config import Settings
        from odin.plugins.builtin import BUILTIN_PLUGINS

        plugin_dirs: list[Path] = []
        builtin_plugins_to_load: list[str] = []

        # Add built-in plugins if requested or not in project
        if include_builtin or show_all or not project_root:
            # Load all available builtin plugins
            builtin_plugins_to_load = list(BUILTIN_PLUGINS.keys())

        # Add project tools if in project and not builtin-only mode
        if project_root and not include_builtin:
            import sys

            agent_dir = project_root / "agent"
            if agent_dir.is_dir():
                sys.path.insert(0, str(agent_dir))
                tools_dir = agent_dir / "tools"
            else:
                tools_dir = project_root / "tools"

            if tools_dir.is_dir():
                plugin_dirs.append(tools_dir)

        settings = Settings(
            plugin_dirs=plugin_dirs,
            plugin_auto_discovery=bool(plugin_dirs),
            builtin_plugins=builtin_plugins_to_load,
        )
        odin = Odin(settings=settings)
        await odin.initialize()
        return odin.list_tools()

    try:
        tools = asyncio.run(_list())
    except Exception as e:
        click.echo(click.style(f"Error loading tools: {e}", fg="red"))
        raise SystemExit(1) from e

    if as_json:
        click.echo(json.dumps(tools, indent=2))
        return

    if not tools:
        click.echo("No agents/tools found.")
        if not project_root:
            click.echo("Use --builtin to list built-in tools.")
        else:
            click.echo("Add tools in agent/tools/ directory.")
        return

    # Show mode
    if include_builtin:
        click.echo(click.style("Built-in tools:", fg="yellow"))
    elif show_all:
        click.echo(click.style("All tools (project + builtin):", fg="yellow"))
    elif project_root:
        click.echo(click.style(f"Project tools ({project_root.name}):", fg="green"))
    else:
        click.echo(click.style("Built-in tools (not in project):", fg="yellow"))

    click.echo(click.style(f"Found {len(tools)} tool(s)", fg="cyan"))
    click.echo()

    for tool in tools:
        name = tool.get("name", "unknown")
        desc = tool.get("description", "No description")
        click.echo(f"  {click.style(name, fg='cyan', bold=True)}")
        click.echo(f"    {desc}")

        # Show parameters if available
        params = tool.get("parameters", [])
        if params:
            click.echo("    Parameters:")
            # Handle both list format and dict format (JSON Schema)
            if isinstance(params, list):
                for param in params:
                    param_name = param.get("name", "unknown")
                    param_type = param.get("type", "any")
                    param_desc = param.get("description", "")
                    required = param.get("required", False)
                    req_mark = "*" if required else ""
                    click.echo(f"      - {param_name}{req_mark} ({param_type}): {param_desc}")
            elif isinstance(params, dict):
                # JSON Schema format
                properties = params.get("properties", {})
                required_list = params.get("required", [])
                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    required = param_name in required_list
                    req_mark = "*" if required else ""
                    click.echo(f"      - {param_name}{req_mark} ({param_type}): {param_desc}")
        click.echo()


@cli.command()
@click.argument("tool_name")
@click.option("--params", "-p", multiple=True, help="Parameters as key=value pairs")
@click.option("--json-params", "-j", default=None, help="Parameters as JSON string")
@click.option("--builtin", is_flag=True, help="Test builtin tools (not project tools)")
def test(tool_name: str, params: tuple, json_params: str | None, builtin: bool) -> None:
    """Test a specific tool/agent.

    Examples:

        odin test greet -p name=World      # Test project tool

        odin test --builtin pdf_to_images -p pdf_path=/path/to.pdf  # Test builtin tool

        odin test add -j '{"a": 1, "b": 2}'  # JSON params
    """
    project_root = find_project_root()

    # If not in a project and not using --builtin, default to builtin
    if not project_root and not builtin:
        builtin = True

    # Parse parameters
    kwargs = {}
    if json_params:
        try:
            kwargs = json.loads(json_params)
        except json.JSONDecodeError as e:
            click.echo(click.style(f"Error parsing JSON params: {e}", fg="red"))
            raise SystemExit(1) from e

    for param in params:
        if "=" not in param:
            click.echo(click.style(f"Invalid param format: {param} (use key=value)", fg="red"))
            raise SystemExit(1)
        key, value = param.split("=", 1)
        # Try to parse as JSON for complex types
        try:
            kwargs[key] = json.loads(value)
        except json.JSONDecodeError:
            kwargs[key] = value

    async def _test():
        from odin import Odin
        from odin.config import Settings
        from odin.plugins.builtin import BUILTIN_PLUGINS

        plugin_dirs: list[Path] = []
        builtin_plugins_to_load: list[str] = []

        # Add builtin plugins if requested or not in project
        if builtin or not project_root:
            builtin_plugins_to_load = list(BUILTIN_PLUGINS.keys())

        # Add project tools if in project and not builtin-only mode
        if project_root and not builtin:
            import sys

            agent_dir = project_root / "agent"
            if agent_dir.is_dir():
                sys.path.insert(0, str(agent_dir))
                tools_dir = agent_dir / "tools"
            else:
                tools_dir = project_root / "tools"

            if tools_dir.is_dir():
                plugin_dirs.append(tools_dir)

        settings = Settings(
            plugin_dirs=plugin_dirs,
            plugin_auto_discovery=bool(plugin_dirs),
            builtin_plugins=builtin_plugins_to_load,
        )
        odin = Odin(settings=settings)
        await odin.initialize()
        return await odin.execute_tool(tool_name, **kwargs)

    click.echo(f"Testing tool: {click.style(tool_name, fg='cyan', bold=True)}")
    if kwargs:
        click.echo(f"Parameters: {json.dumps(kwargs)}")
    click.echo()

    try:
        result = asyncio.run(_test())
        click.echo(click.style("Result:", fg="green"))
        click.echo(json.dumps(result, indent=2, default=str))
    except ValueError as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise SystemExit(1) from e
    except Exception as e:
        click.echo(click.style(f"Execution error: {e}", fg="red"))
        raise SystemExit(1) from e


@cli.command()
@click.option("--interactive", "-i", is_flag=True, help="Interactive REPL mode")
def repl(interactive: bool) -> None:  # noqa: ARG001
    """Start an interactive REPL to test tools.

    Examples:

        odin repl              # Start REPL
    """
    project_root = find_project_root()

    if not project_root:
        click.echo(click.style("Error: Not in an Odin project directory", fg="red"))
        raise SystemExit(1)

    async def _repl():
        odin = get_odin_instance(project_root)
        await odin.initialize()

        tools = odin.list_tools()
        tool_names = [t["name"] for t in tools]

        click.echo(click.style("Odin REPL - Interactive Tool Testing", fg="cyan", bold=True))
        click.echo(f"Available tools: {', '.join(tool_names)}")
        click.echo("Type 'help' for commands, 'exit' to quit")
        click.echo()

        while True:
            try:
                line = click.prompt(click.style("odin", fg="green"), prompt_suffix="> ")
            except (EOFError, KeyboardInterrupt):
                click.echo("\nGoodbye!")
                break

            line = line.strip()
            if not line:
                continue

            if line in ("exit", "quit", "q"):
                click.echo("Goodbye!")
                break

            if line == "help":
                click.echo("Commands:")
                click.echo("  list                  - List all tools")
                click.echo("  <tool> [params]       - Execute tool (e.g., greet name=World)")
                click.echo("  exit                  - Exit REPL")
                continue

            if line == "list":
                for t in tools:
                    click.echo(f"  {t['name']}: {t.get('description', '')}")
                continue

            # Parse tool call
            parts = line.split()
            tool_name = parts[0]
            kwargs = {}

            for part in parts[1:]:
                if "=" in part:
                    key, value = part.split("=", 1)
                    try:
                        kwargs[key] = json.loads(value)
                    except json.JSONDecodeError:
                        kwargs[key] = value

            try:
                result = await odin.execute_tool(tool_name, **kwargs)
                click.echo(click.style("→ ", fg="green") + json.dumps(result, default=str))
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"))

    asyncio.run(_repl())


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
@click.option("--port", "-p", type=int, default=8000, help="Port to bind to (default: 8000)")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to app.yaml config file")
@click.option(
    "--protocol",
    type=click.Choice(["copilotkit", "http", "agui", "a2a"]),
    default="copilotkit",
    help="Protocol to expose (default: copilotkit). Ignored if --unified is set.",
)
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--standalone", is_flag=True, help="Force standalone mode (ignore project context)")
@click.option(
    "--unified",
    is_flag=True,
    help="Run unified server with all protocols on single port",
)
def serve(
    host: str,
    port: int,
    config: str | None,  # noqa: ARG001
    protocol: Literal["copilotkit", "http", "agui", "a2a"],
    reload: bool,
    standalone: bool,
    unified: bool,
) -> None:
    """Start the Odin server.

    Can run in three modes:

    1. Unified mode (recommended): All protocols on single port
       odin serve --unified           # All protocols at /a2a, /mcp, /agui, /copilotkit, /api

    2. Standalone mode: Run Odin with built-in tools only
       odin serve                     # Start with built-in tools

    3. Project mode: Run from within a project directory
       cd my-project && odin serve    # Load project tools + built-in tools

    Examples:

        odin serve --unified                # All protocols on port 8000

        odin serve --unified --port 9000    # All protocols on port 9000

        odin serve --protocol http          # HTTP/REST mode only

        odin serve --config app.yaml        # Use config file

        odin serve --standalone             # Force standalone mode
    """
    click.echo(click.style("Odin Server", fg="cyan", bold=True))
    click.echo()

    async def _serve_unified():
        """Run unified server with all protocols."""
        from odin import Odin
        from odin.config import Settings
        from odin.plugins.builtin import BUILTIN_PLUGINS
        from odin.server import UnifiedServer

        # Determine mode
        project_root = None if standalone else find_project_root()
        is_project_mode = project_root is not None

        # Collect plugin directories and builtin plugins
        plugin_dirs: list[Path] = []
        builtin_plugins_to_load = list(BUILTIN_PLUGINS.keys())

        # Add project tools if in project mode
        if is_project_mode:
            import sys

            agent_dir = project_root / "agent"
            if agent_dir.is_dir():
                sys.path.insert(0, str(agent_dir))
                tools_dir = agent_dir / "tools"
            else:
                tools_dir = project_root / "tools"

            if tools_dir.is_dir():
                plugin_dirs.append(tools_dir)

            click.echo(f"Mode: {click.style('Unified + Project', fg='green')}")
            click.echo(f"Project: {project_root}")
        else:
            click.echo(f"Mode: {click.style('Unified + Standalone', fg='cyan')}")

        click.echo(f"Builtin plugins: {builtin_plugins_to_load}")
        if plugin_dirs:
            click.echo(f"Plugin directories: {[str(d) for d in plugin_dirs]}")
        click.echo()

        # Create settings
        settings = Settings(
            plugin_dirs=plugin_dirs,
            plugin_auto_discovery=bool(plugin_dirs),
            builtin_plugins=builtin_plugins_to_load,
        )

        # Initialize Odin
        odin_instance = Odin(settings=settings)
        await odin_instance.initialize()

        tools = odin_instance.list_tools()
        click.echo(f"Loaded {click.style(str(len(tools)), fg='cyan')} tool(s)")
        for tool in tools[:10]:  # Show first 10
            click.echo(f"  - {tool['name']}")
        if len(tools) > 10:
            click.echo(f"  ... and {len(tools) - 10} more")
        click.echo()

        # Create and run unified server
        server = UnifiedServer(odin_instance, name="Odin Unified Server")
        server.create_app()

        click.echo("Protocols:")
        click.echo("  - A2A:        /a2a")
        click.echo("  - MCP:        /mcp")
        click.echo("  - AG-UI:      /agui")
        click.echo("  - CopilotKit: /copilotkit")
        click.echo("  - REST API:   /api")
        click.echo()
        click.echo(f"Server: http://{host}:{port}")
        click.echo(f"API Docs: http://{host}:{port}/docs")
        click.echo()
        click.echo(click.style("Press Ctrl+C to stop", fg="yellow"))

        await server.run(host=host, port=port)

    async def _serve_single():
        """Run server with single protocol."""
        from contextlib import asynccontextmanager

        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel

        from odin import Odin
        from odin.config import Settings
        from odin.plugins.builtin import BUILTIN_PLUGINS

        # Determine mode
        project_root = None if standalone else find_project_root()
        is_project_mode = project_root is not None

        # Collect plugin directories and builtin plugins
        plugin_dirs: list[Path] = []
        builtin_plugins_to_load = list(BUILTIN_PLUGINS.keys())

        # Add project tools if in project mode
        if is_project_mode:
            import sys

            agent_dir = project_root / "agent"
            if agent_dir.is_dir():
                sys.path.insert(0, str(agent_dir))
                tools_dir = agent_dir / "tools"
            else:
                tools_dir = project_root / "tools"

            if tools_dir.is_dir():
                plugin_dirs.append(tools_dir)

            click.echo(f"Mode: {click.style('Project', fg='green')}")
            click.echo(f"Project: {project_root}")
        else:
            click.echo(f"Mode: {click.style('Standalone', fg='yellow')}")

        click.echo(f"Builtin plugins: {builtin_plugins_to_load}")
        if plugin_dirs:
            click.echo(f"Plugin directories: {[str(d) for d in plugin_dirs]}")
        click.echo()

        # Create settings
        settings = Settings(
            plugin_dirs=plugin_dirs,
            plugin_auto_discovery=bool(plugin_dirs),
            builtin_plugins=builtin_plugins_to_load,
        )

        # Initialize Odin
        odin_instance = Odin(settings=settings)
        await odin_instance.initialize()

        tools = odin_instance.list_tools()
        click.echo(f"Loaded {click.style(str(len(tools)), fg='cyan')} tool(s)")
        for tool in tools[:10]:  # Show first 10
            click.echo(f"  - {tool['name']}")
        if len(tools) > 10:
            click.echo(f"  ... and {len(tools) - 10} more")
        click.echo()

        # Create FastAPI app
        @asynccontextmanager
        async def lifespan(app: FastAPI):  # noqa: ARG001
            yield
            await odin_instance.shutdown()

        app = FastAPI(
            title="Odin Server",
            description="AI Agent Server powered by Odin Framework",
            version="0.1.0",
            lifespan=lifespan,
        )

        # CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Pydantic models for API documentation
        class ToolCallRequest(BaseModel):
            params: dict = {}

        class ToolCallResponse(BaseModel):
            result: dict | list | str | None
            error: str | None = None

        class ToolInfo(BaseModel):
            name: str
            description: str
            parameters: dict

        class HealthResponse(BaseModel):
            status: str
            mode: str
            tools_count: int
            protocol: str

        # Health endpoint
        @app.get("/health", response_model=HealthResponse, tags=["System"])
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "mode": "project" if is_project_mode else "standalone",
                "tools_count": len(tools),
                "protocol": protocol,
            }

        # Tools endpoints
        @app.get("/tools", response_model=list[ToolInfo], tags=["Tools"])
        async def list_tools_endpoint():
            """List all available tools."""
            return odin_instance.list_tools()

        @app.get("/tools/{tool_name}", response_model=ToolInfo, tags=["Tools"])
        async def get_tool(tool_name: str):
            """Get information about a specific tool."""
            tools_list = odin_instance.list_tools()
            for t in tools_list:
                if t["name"] == tool_name:
                    return t
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        @app.post("/tools/{tool_name}", response_model=ToolCallResponse, tags=["Tools"])
        async def execute_tool(tool_name: str, request: ToolCallRequest):
            """Execute a tool by name."""
            try:
                result = await odin_instance.execute_tool(tool_name, **request.params)
                return {"result": result, "error": None}
            except Exception as e:
                return {"result": None, "error": str(e)}

        # Setup protocol endpoint
        if protocol == "copilotkit":
            from odin.protocols.copilotkit import CopilotKitAdapter

            adapter = CopilotKitAdapter(odin_instance)
            adapter.mount(app, "/copilotkit")
            click.echo("Protocol: CopilotKit at /copilotkit")
        elif protocol == "http":
            click.echo("Protocol: HTTP/REST at /tools")
        elif protocol == "agui":
            try:
                from odin.protocols.agui import AGUIServer

                agui = AGUIServer(odin_instance, path="/agui")
                app.mount("/agui", agui.app)
                click.echo("Protocol: AG-UI at /agui")
            except ImportError:
                click.echo(click.style("AG-UI protocol not available", fg="yellow"))
        elif protocol == "a2a":
            try:
                from odin.protocols.a2a import A2AServer

                a2a = A2AServer(odin_instance, name="Odin Server")
                app.mount("/a2a", a2a.app)
                click.echo("Protocol: A2A at /a2a")
            except ImportError:
                click.echo(click.style("A2A protocol not available", fg="yellow"))

        click.echo()
        click.echo(f"Server: http://{host}:{port}")
        click.echo(f"API Docs: http://{host}:{port}/docs")
        click.echo()
        click.echo(click.style("Press Ctrl+C to stop", fg="yellow"))

        # Run server
        import uvicorn

        uvi_config = uvicorn.Config(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
        server = uvicorn.Server(uvi_config)
        await server.serve()

    try:
        if unified:
            asyncio.run(_serve_unified())
        else:
            asyncio.run(_serve_single())
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")


@cli.command()
def version() -> None:
    """Show version information."""
    click.echo("Odin Framework v0.1.0")
    click.echo("Python agent development framework with MCP, A2A, and AG-UI support")


@cli.command()
@click.argument("task")
@click.option("--mode", "-m", type=click.Choice(["react", "plan_execute", "hierarchical"]), default=None, help="Agent mode (default: from settings)")
@click.option("--max-rounds", "-r", type=int, default=None, help="Maximum execution rounds (default: from settings)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed execution logs")
def mobile(task: str, mode: str | None, max_rounds: int | None, verbose: bool) -> None:
    """Run Mobile Agent to automate phone tasks.

    TASK is the natural language description of what you want the agent to do.

    Examples:

        odin mobile "打开微信"

        odin mobile "打开设置，找到WiFi设置"

        odin mobile "打开相机拍一张照片" --mode plan_execute

        odin mobile "滑动屏幕浏览内容" -v
    """
    async def _run_mobile():
        from odin.config.settings import get_settings
        from odin.plugins.builtin.mobile.interaction import CLIInteractionHandler

        settings = get_settings()

        # Override settings if provided
        actual_mode = mode or settings.mobile_agent_mode
        actual_max_rounds = max_rounds or settings.mobile_max_rounds

        click.echo(click.style("Mobile Agent", fg="cyan", bold=True))
        click.echo()
        click.echo(f"Task: {click.style(task, fg='yellow')}")
        click.echo(f"Mode: {actual_mode}")
        click.echo(f"Device: {settings.mobile_device_id or 'auto'}")
        click.echo(f"Controller: {settings.mobile_controller}")
        click.echo(f"Max rounds: {actual_max_rounds}")
        click.echo()

        # Create agent with CLI interaction handler
        try:
            from openai import AsyncOpenAI

            from odin.agents.mobile.factory import (
                create_controller,
                create_mobile_agent,
                create_mobile_plugin,
            )

            # Create LLM client
            llm_client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )

            # Create VLM client
            vlm_client = None
            if settings.vlm_api_key:
                vlm_client = AsyncOpenAI(
                    api_key=settings.vlm_api_key,
                    base_url=settings.vlm_base_url,
                )

            # Create controller
            controller = create_controller(
                controller_type=settings.mobile_controller,
                device_id=settings.mobile_device_id,
                adb_path=settings.mobile_adb_path,
                hdc_path=settings.mobile_hdc_path,
            )

            # Check connection
            connected = await controller.is_connected()
            if not connected:
                click.echo(click.style("Error: Device not connected!", fg="red"))
                raise SystemExit(1)

            width, height = await controller.get_screen_size()
            click.echo(f"Screen: {width}x{height}")
            click.echo()

            # Create plugin with CLI interaction handler
            plugin = create_mobile_plugin(
                controller=controller,
                interaction_handler=CLIInteractionHandler(),
                tool_delay_ms=settings.mobile_tool_delay_ms,
            )

            # Create log callback for real-time output
            def log_callback(level: str, message: str) -> None:
                """Display log messages in real-time."""
                if level == "error":
                    click.echo(click.style(f"[ERROR] {message}", fg="red"))
                elif level == "warning":
                    click.echo(click.style(f"[WARN] {message}", fg="yellow"))
                elif level == "info":
                    click.echo(click.style(f"[INFO] {message}", fg="cyan"))
                elif verbose and level == "debug":
                    click.echo(click.style(f"[DEBUG] {message}", fg="white", dim=True))

            # Create agent
            agent = create_mobile_agent(
                mode=actual_mode,
                plugin=plugin,
                llm_client=llm_client,
                vlm_client=vlm_client,
                llm_model=settings.openai_model,
                vlm_model=settings.vlm_model,
                max_rounds=actual_max_rounds,
                log_callback=log_callback,
            )

            click.echo(click.style("Starting execution...", fg="green"))
            click.echo("-" * 40)

            # Execute agent
            result = await agent.execute(task)

            click.echo("-" * 40)
            click.echo()

            # Show result
            if result.success:
                click.echo(click.style("✓ Task completed!", fg="green", bold=True))
            else:
                click.echo(click.style("✗ Task failed!", fg="red", bold=True))

            click.echo()
            click.echo(f"Steps: {result.steps_executed}")

            if result.message:
                click.echo(f"Message: {result.message}")

            if result.error:
                click.echo(f"Error: {result.error}")

            if verbose and agent.history:
                click.echo()
                click.echo(click.style("Execution history:", fg="cyan"))
                for i, step in enumerate(agent.history, 1):
                    click.echo(f"  {i}. {step}")

        except Exception as e:
            click.echo(click.style(f"Error: {e}", fg="red"))
            if verbose:
                import traceback
                traceback.print_exc()
            raise SystemExit(1) from None

    asyncio.run(_run_mobile())


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
