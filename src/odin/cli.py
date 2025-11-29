#!/usr/bin/env python
"""Odin CLI - Command line interface for the Odin framework.

Commands:
    odin create <project-name>  Create a new Odin project
    odin create --ui-only       Create UI only
    odin create --agent-only    Create agent only
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
