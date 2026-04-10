"""Tests for Issue #1: Dashboard HTML extraction to separate file.

These tests verify that the monolithic HTML string has been extracted
from monitor_server.py into a standalone dashboard.html file.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent


def test_dashboard_html_file_exists():
    """A dashboard.html file should exist at the repo root."""
    html_path = REPO_ROOT / "dashboard.html"
    assert html_path.exists(), (
        "dashboard.html should be extracted from monitor_server.py "
        "into a standalone file"
    )


def test_dashboard_html_file_has_valid_content():
    """The dashboard.html file should contain valid HTML structure."""
    html_path = REPO_ROOT / "dashboard.html"
    content = html_path.read_text()
    assert "<!DOCTYPE html>" in content or "<html" in content.lower()
    assert "<head>" in content.lower()
    assert "<body>" in content.lower()
    assert "</html>" in content.lower()


def test_dashboard_html_not_hardcoded_in_python():
    """monitor_server.py should NOT contain a large inline HTML string.

    The HTML should be loaded from a file at startup, not hardcoded as
    a multi-line string literal in the Python source.
    """
    server_path = REPO_ROOT / "monitor_server.py"
    source = server_path.read_text()

    # Parse the AST to find string assignments
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DASHBOARD_HTML":
                    # If DASHBOARD_HTML is assigned as a string constant
                    # with more than 500 chars, it's still inline
                    if isinstance(node.value, ast.Constant) and isinstance(
                        node.value.value, str
                    ):
                        assert len(node.value.value) < 500, (
                            "DASHBOARD_HTML is still a large inline string; "
                            "it should be loaded from dashboard.html"
                        )


def test_dashboard_html_contains_key_elements():
    """dashboard.html should contain the dashboard UI elements."""
    html_path = REPO_ROOT / "dashboard.html"
    content = html_path.read_text()
    # Should contain the tab structure
    assert "dashboard" in content.lower()
    # Should contain essential UI elements
    assert "<script>" in content.lower() or "<script " in content.lower()
    assert "<style>" in content.lower() or "<style " in content.lower()
