"""Tests for veritasgraph CLI."""

import pytest
from veritasgraph.cli import create_parser, main


class TestCLI:
    """Tests for the command line interface."""

    def test_version(self, capsys):
        """Test --version flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_help(self, capsys):
        """Test help output."""
        result = main([])
        assert result == 0

    def test_info_command(self, capsys):
        """Test info command runs without error."""
        result = main(["info"])
        assert result == 0
        captured = capsys.readouterr()
        assert "VeritasGraph" in captured.out

    def test_parser_creation(self):
        """Test parser is created correctly."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "veritasgraph"

    def test_init_command_creates_structure(self, tmp_path):
        """Test init command creates project structure."""
        result = main(["init", str(tmp_path / "test_project")])
        assert result == 0
        
        project_path = tmp_path / "test_project"
        assert (project_path / "input").exists()
        assert (project_path / "output").exists()
        assert (project_path / "cache").exists()
        assert (project_path / "settings.yaml").exists()
