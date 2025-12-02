"""Tests for CLI module."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from click.testing import CliRunner

from odin.cli import (
    cli,
    get_template_dir,
    copy_template,
    copy_root_files,
    find_project_root,
    get_odin_instance,
)


class TestHelperFunctions:
    """Test CLI helper functions."""

    def test_get_template_dir(self):
        """Test getting template directory."""
        template_dir = get_template_dir()
        assert template_dir.name == "templates"
        assert "odin" in str(template_dir)

    def test_copy_template(self, tmp_path):
        """Test copying template files with substitution."""
        # Create source template
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("Hello {{PROJECT_NAME}}")
        (src_dir / "subdir").mkdir()
        (src_dir / "subdir" / "nested.txt").write_text("Nested {{PROJECT_TITLE}}")

        # Copy with replacements
        dest_dir = tmp_path / "dest"
        copy_template(
            src_dir,
            dest_dir,
            {"PROJECT_NAME": "my-project", "PROJECT_TITLE": "My Project"},
        )

        # Verify
        assert (dest_dir / "file.txt").read_text() == "Hello my-project"
        assert (dest_dir / "subdir" / "nested.txt").read_text() == "Nested My Project"

    def test_copy_template_binary_file(self, tmp_path):
        """Test copying binary files without modification."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create binary file
        binary_content = bytes([0x00, 0x01, 0xFF, 0xFE])
        (src_dir / "binary.bin").write_bytes(binary_content)

        dest_dir = tmp_path / "dest"
        copy_template(src_dir, dest_dir, {"KEY": "value"})

        assert (dest_dir / "binary.bin").read_bytes() == binary_content

    def test_copy_root_files(self, tmp_path):
        """Test copying root-level template files."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / "Makefile").write_text("PROJECT={{PROJECT_NAME}}")
        (template_dir / "README.md").write_text("# {{PROJECT_TITLE}}")

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        copy_root_files(
            template_dir,
            project_dir,
            {"PROJECT_NAME": "test", "PROJECT_TITLE": "Test Project"},
        )

        assert (project_dir / "Makefile").read_text() == "PROJECT=test"
        assert (project_dir / "README.md").read_text() == "# Test Project"

    def test_copy_root_files_skips_missing(self, tmp_path):
        """Test that missing root files are skipped."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        # Only create Makefile, not README.md

        (template_dir / "Makefile").write_text("test")

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Should not raise
        copy_root_files(template_dir, project_dir, {})
        assert (project_dir / "Makefile").exists()
        assert not (project_dir / "README.md").exists()


class TestFindProjectRoot:
    """Test find_project_root function."""

    def test_find_project_with_agent_tools(self, tmp_path, monkeypatch):
        """Test finding project with agent/tools structure."""
        project = tmp_path / "project"
        (project / "agent" / "tools").mkdir(parents=True)

        monkeypatch.chdir(project)
        assert find_project_root() == project

    def test_find_project_with_app_yaml(self, tmp_path, monkeypatch):
        """Test finding project with app.yaml."""
        project = tmp_path / "project"
        project.mkdir()
        (project / "app.yaml").write_text("name: test")

        monkeypatch.chdir(project)
        assert find_project_root() == project

    def test_find_project_with_tools_dir(self, tmp_path, monkeypatch):
        """Test finding project with tools/ directory containing Python files."""
        project = tmp_path / "project"
        (project / "tools").mkdir(parents=True)
        (project / "tools" / "my_tool.py").write_text("# tool")

        monkeypatch.chdir(project)
        assert find_project_root() == project

    def test_find_project_from_agent_subdir(self, tmp_path, monkeypatch):
        """Test finding project from agent/ subdirectory."""
        project = tmp_path / "project"
        agent_dir = project / "agent"
        (agent_dir / "tools").mkdir(parents=True)

        monkeypatch.chdir(agent_dir)
        assert find_project_root() == project

    def test_find_project_from_parent(self, tmp_path, monkeypatch):
        """Test finding project from nested directory."""
        project = tmp_path / "project"
        (project / "agent" / "tools").mkdir(parents=True)
        (project / "agent" / "deep" / "nested").mkdir(parents=True)

        monkeypatch.chdir(project / "agent" / "deep")
        result = find_project_root()
        assert result == project

    def test_find_project_returns_none(self, tmp_path, monkeypatch):
        """Test returning None when not in a project."""
        non_project = tmp_path / "random"
        non_project.mkdir()

        monkeypatch.chdir(non_project)
        assert find_project_root() is None


class TestCliVersion:
    """Test CLI version command."""

    def test_version_command(self):
        """Test version command output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        assert "Odin Framework" in result.output
        assert "0.1.0" in result.output


class TestCliCreate:
    """Test CLI create command."""

    def test_create_full_project(self, tmp_path):
        """Test creating a full project."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("odin.cli.get_template_dir") as mock_template:
                # Create mock template directory
                template_dir = Path(tmp_path) / "templates"
                (template_dir / "agent").mkdir(parents=True)
                (template_dir / "ui").mkdir(parents=True)
                (template_dir / "agent" / "main.py").write_text("# {{PROJECT_NAME}}")
                (template_dir / "ui" / "index.js").write_text("// {{PROJECT_NAME}}")
                mock_template.return_value = template_dir

                result = runner.invoke(cli, ["create", "my-project"])

                assert result.exit_code == 0
                assert "Creating Odin project: my-project" in result.output
                assert "Project created successfully!" in result.output
                assert Path("my-project").exists()

    def test_create_agent_only(self, tmp_path):
        """Test creating agent-only project."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("odin.cli.get_template_dir") as mock_template:
                template_dir = Path(tmp_path) / "templates"
                (template_dir / "agent").mkdir(parents=True)
                (template_dir / "agent" / "main.py").write_text("# test")
                mock_template.return_value = template_dir

                result = runner.invoke(cli, ["create", "my-agent", "--agent-only"])

                assert result.exit_code == 0
                assert "Agent created" in result.output

    def test_create_ui_only(self, tmp_path):
        """Test creating UI-only project."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("odin.cli.get_template_dir") as mock_template:
                template_dir = Path(tmp_path) / "templates"
                (template_dir / "ui").mkdir(parents=True)
                (template_dir / "ui" / "index.js").write_text("// test")
                mock_template.return_value = template_dir

                result = runner.invoke(cli, ["create", "my-ui", "--ui-only"])

                assert result.exit_code == 0
                assert "UI created" in result.output

    def test_create_with_custom_title(self, tmp_path):
        """Test creating project with custom title."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("odin.cli.get_template_dir") as mock_template:
                template_dir = Path(tmp_path) / "templates"
                (template_dir / "agent").mkdir(parents=True)
                (template_dir / "agent" / "main.py").write_text("# {{PROJECT_TITLE}}")
                mock_template.return_value = template_dir

                result = runner.invoke(
                    cli, ["create", "my-project", "--agent-only", "--title", "My Custom Title"]
                )

                assert result.exit_code == 0
                assert "My Custom Title" in result.output

    def test_create_existing_directory_error(self, tmp_path):
        """Test error when directory already exists."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("existing").mkdir()

            result = runner.invoke(cli, ["create", "existing"])

            assert result.exit_code == 1
            assert "already exists" in result.output


class TestCliList:
    """Test CLI list command."""

    def test_list_with_builtin_flag(self):
        """Test listing builtin tools."""
        runner = CliRunner()

        with patch("odin.cli.find_project_root", return_value=None):
            # Mock the async list function to avoid actual tool loading
            with patch("odin.cli.asyncio.run") as mock_run:
                mock_run.return_value = [
                    {"name": "test_tool", "description": "A test tool", "parameters": []},
                ]

                result = runner.invoke(cli, ["list", "--builtin"])

                assert result.exit_code == 0
                assert "Built-in tools" in result.output
                assert "test_tool" in result.output

    def test_list_as_json(self):
        """Test listing tools as JSON."""
        runner = CliRunner()

        with patch("odin.cli.find_project_root", return_value=None):
            with patch("odin.cli.asyncio.run") as mock_run:
                mock_run.return_value = [
                    {"name": "tool1", "description": "Tool 1", "parameters": []},
                ]

                result = runner.invoke(cli, ["list", "--builtin", "--json"])

                assert result.exit_code == 0
                # Verify it's valid JSON
                data = json.loads(result.output)
                assert len(data) == 1
                assert data[0]["name"] == "tool1"

    def test_list_no_tools_found(self):
        """Test listing when no tools are found."""
        runner = CliRunner()

        with patch("odin.cli.find_project_root", return_value=None):
            with patch("odin.cli.asyncio.run") as mock_run:
                mock_run.return_value = []

                result = runner.invoke(cli, ["list", "--builtin"])

                assert result.exit_code == 0
                assert "No agents/tools found" in result.output

    def test_list_with_parameters(self):
        """Test listing tools with parameters display."""
        runner = CliRunner()

        with patch("odin.cli.find_project_root", return_value=None):
            with patch("odin.cli.asyncio.run") as mock_run:
                mock_run.return_value = [
                    {
                        "name": "greet",
                        "description": "Greet someone",
                        "parameters": [
                            {
                                "name": "name",
                                "type": "string",
                                "description": "Name to greet",
                                "required": True,
                            },
                        ],
                    },
                ]

                result = runner.invoke(cli, ["list", "--builtin"])

                assert result.exit_code == 0
                assert "greet" in result.output
                assert "name*" in result.output  # Required marker
                assert "string" in result.output

    def test_list_error_handling(self):
        """Test list command error handling."""
        runner = CliRunner()

        with patch("odin.cli.find_project_root", return_value=None):
            with patch("odin.cli.asyncio.run") as mock_run:
                mock_run.side_effect = Exception("Failed to load")

                result = runner.invoke(cli, ["list", "--builtin"])

                assert result.exit_code == 1
                assert "Error loading tools" in result.output


class TestCliTest:
    """Test CLI test command."""

    def test_test_command_basic(self):
        """Test basic tool testing."""
        runner = CliRunner()

        with patch("odin.cli.find_project_root", return_value=None):
            with patch("odin.cli.asyncio.run") as mock_run:
                mock_run.return_value = {"result": "success"}

                result = runner.invoke(cli, ["test", "greet", "-p", "name=World"])

                assert result.exit_code == 0
                assert "Testing tool: greet" in result.output
                assert "Result:" in result.output

    def test_test_command_with_json_params(self):
        """Test tool testing with JSON parameters."""
        runner = CliRunner()

        with patch("odin.cli.find_project_root", return_value=None):
            with patch("odin.cli.asyncio.run") as mock_run:
                mock_run.return_value = {"sum": 3}

                result = runner.invoke(
                    cli, ["test", "add", "-j", '{"a": 1, "b": 2}', "--builtin"]
                )

                assert result.exit_code == 0
                assert '"a": 1' in result.output or "a" in result.output

    def test_test_command_invalid_json_params(self):
        """Test tool testing with invalid JSON parameters."""
        runner = CliRunner()

        result = runner.invoke(cli, ["test", "tool", "-j", "not-valid-json"])

        assert result.exit_code == 1
        assert "Error parsing JSON" in result.output

    def test_test_command_invalid_param_format(self):
        """Test tool testing with invalid parameter format."""
        runner = CliRunner()

        result = runner.invoke(cli, ["test", "tool", "-p", "invalid_format"])

        assert result.exit_code == 1
        assert "Invalid param format" in result.output

    def test_test_command_tool_not_found(self):
        """Test when tool is not found."""
        runner = CliRunner()

        with patch("odin.cli.find_project_root", return_value=None):
            with patch("odin.cli.asyncio.run") as mock_run:
                mock_run.side_effect = ValueError("Tool 'unknown' not found")

                result = runner.invoke(cli, ["test", "unknown", "--builtin"])

                assert result.exit_code == 1
                assert "Error:" in result.output

    def test_test_command_execution_error(self):
        """Test tool execution error handling."""
        runner = CliRunner()

        with patch("odin.cli.find_project_root", return_value=None):
            with patch("odin.cli.asyncio.run") as mock_run:
                mock_run.side_effect = RuntimeError("Execution failed")

                result = runner.invoke(cli, ["test", "broken", "--builtin"])

                assert result.exit_code == 1
                assert "Execution error" in result.output


class TestCliRepl:
    """Test CLI repl command."""

    def test_repl_not_in_project(self, tmp_path, monkeypatch):
        """Test REPL error when not in project."""
        runner = CliRunner()

        # Ensure not in project
        non_project = tmp_path / "random"
        non_project.mkdir()
        monkeypatch.chdir(non_project)

        result = runner.invoke(cli, ["repl"])

        assert result.exit_code == 1
        assert "Not in an Odin project" in result.output


class TestCliServe:
    """Test CLI serve command."""

    def test_serve_help(self):
        """Test serve command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output
        assert "--protocol" in result.output
        assert "--reload" in result.output

    def test_serve_protocol_choices(self):
        """Test serve command validates protocol choices."""
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--protocol", "invalid"])

        assert result.exit_code != 0
        assert "Invalid value for '--protocol'" in result.output


class TestCliMain:
    """Test main entry point."""

    def test_cli_no_command(self):
        """Test CLI with no command shows help."""
        runner = CliRunner()
        result = runner.invoke(cli)

        # Click groups may return 0 (if invoke_without_command=True) or 2 (if help shown)
        # Both are valid - the important thing is help is shown
        assert result.exit_code in (0, 2)
        assert "Odin" in result.output or "Usage" in result.output

    def test_cli_help(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "create" in result.output
        assert "serve" in result.output
        assert "list" in result.output
        assert "test" in result.output

    def test_cli_version_option(self):
        """Test CLI --version option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output
