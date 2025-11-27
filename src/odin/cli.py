#!/usr/bin/env python
"""Odin CLI - Command line interface for the Odin framework.

Commands:
    odin create <project-name>  Create a new Odin project
    odin create --frontend      Create frontend only
    odin create --backend       Create backend only
"""

import shutil
from pathlib import Path

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


@click.group()
@click.version_option(version="0.1.0", prog_name="odin")
def cli() -> None:
    """Odin - Modern agent development framework."""
    pass


@cli.command()
@click.argument("name")
@click.option("--frontend", is_flag=True, help="Create frontend only")
@click.option("--backend", is_flag=True, help="Create backend only")
@click.option("--title", default=None, help="Project title (default: project name)")
def create(name: str, frontend: bool, backend: bool, title: str | None) -> None:
    """Create a new Odin project.

    NAME is the project directory name.

    Examples:

        odin create my-agent          # Full stack project

        odin create my-agent --backend   # Backend only

        odin create my-agent --frontend  # Frontend only
    """
    project_dir = Path.cwd() / name
    template_dir = get_template_dir()
    project_title = title or name.replace("-", " ").replace("_", " ").title()

    # Determine what to create
    create_frontend = frontend or (not frontend and not backend)
    create_backend = backend or (not frontend and not backend)

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

    # Create backend
    if create_backend:
        click.echo("Creating backend...")
        backend_src = template_dir / "backend"
        backend_dest = project_dir if not create_frontend else project_dir
        copy_template(backend_src, backend_dest, replacements)
        click.echo(click.style("  ✓ Backend created", fg="green"))

    # Create frontend
    if create_frontend:
        click.echo("Creating frontend...")
        frontend_src = template_dir / "frontend"
        frontend_dest = project_dir / "frontend" if create_backend else project_dir
        copy_template(frontend_src, frontend_dest, replacements)
        click.echo(click.style("  ✓ Frontend created", fg="green"))

    # Create start script and env file for full stack
    if create_frontend and create_backend:
        # Create .env.example
        env_content = f"""# {project_title} Configuration

# Server
HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=3000
PROTOCOL=copilotkit

# OpenAI (if using LLM features)
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o

# Observability
OTEL_ENABLED=false
LOG_LEVEL=INFO

# Frontend
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000/copilotkit
"""
        (project_dir / ".env.example").write_text(env_content)

        # Create start.sh
        start_script = '''#!/bin/bash
# Start script for {title}

set -e
cd "$(dirname "$0")"

# Load env
[ -f .env ] && export $(grep -v '^#' .env | xargs)

HOST=${{HOST:-0.0.0.0}}
BACKEND_PORT=${{BACKEND_PORT:-8000}}
FRONTEND_PORT=${{FRONTEND_PORT:-3000}}
PROTOCOL=${{PROTOCOL:-copilotkit}}

case "${{1:-all}}" in
    backend)
        python main.py --protocol "$PROTOCOL" --host "$HOST" --port "$BACKEND_PORT"
        ;;
    frontend)
        cd frontend && npm run dev
        ;;
    all)
        python main.py --protocol "$PROTOCOL" --host "$HOST" --port "$BACKEND_PORT" &
        sleep 2
        cd frontend && PORT=$FRONTEND_PORT npm run dev
        ;;
    *)
        echo "Usage: $0 [backend|frontend|all]"
        ;;
esac
'''.format(title=project_title)
        start_path = project_dir / "start.sh"
        start_path.write_text(start_script)
        start_path.chmod(0o755)

    click.echo()
    click.echo(click.style("Project created successfully!", fg="green"))
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  cd {name}")

    if create_backend:
        click.echo("  pip install odin-agent  # or: uv add odin-agent")

    if create_frontend:
        frontend_path = "frontend" if create_backend else "."
        click.echo(f"  cd {frontend_path} && npm install")

    click.echo()

    if create_frontend and create_backend:
        click.echo("To start the application:")
        click.echo("  ./start.sh              # Start both backend and frontend")
        click.echo("  ./start.sh backend      # Start backend only")
        click.echo("  ./start.sh frontend     # Start frontend only")
    elif create_backend:
        click.echo("To start the backend:")
        click.echo("  python main.py")
    elif create_frontend:
        click.echo("To start the frontend:")
        click.echo("  npm run dev")


@cli.command()
def version() -> None:
    """Show version information."""
    click.echo("Odin Framework v0.1.0")
    click.echo("Python agent development framework with MCP, A2A, and AG-UI support")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
