#!/usr/bin/env python3
"""
Sandbox - Personal experimentation and data analysis workspace.

Lists available scripts and their descriptions.
"""

import argparse
import ast
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def get_module_docstring(file_path: Path, full: bool = False) -> str:
    """
    Extract the module-level docstring from a Python file.

    Args:
        file_path: Path to the Python file
        full: If True, return the full docstring; if False, return only first line

    Returns:
        The docstring (summary or full) or empty string if none found.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
            docstring = ast.get_docstring(tree)
            if docstring:
                if full:
                    # Return full docstring, cleaned up
                    return docstring.strip()
                else:
                    # Return first non-empty line as summary
                    lines = [line.strip() for line in docstring.split("\n") if line.strip()]
                    return lines[0] if lines else ""
    except Exception:
        pass
    return ""


def list_available_scripts(full: bool = False):
    """
    List all available scripts in the scripts/ directory.

    Args:
        full: If True, show full docstrings; if False, show only summaries
    """
    scripts_dir = Path(__file__).parent / "scripts"

    if not scripts_dir.exists():
        console.print("[yellow]No scripts directory found.[/yellow]")
        return

    # Find all Python files in scripts/
    scripts = []
    for script_path in sorted(scripts_dir.glob("*.py")):
        if script_path.name.startswith("_"):
            continue  # Skip private modules

        script_name = script_path.stem
        description = get_module_docstring(script_path, full=full)
        scripts.append((script_name, description, script_path))

    if not scripts:
        console.print("[yellow]No scripts found in scripts/ directory.[/yellow]")
        return

    # Display header
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Sandbox - Available Scripts[/bold cyan]",
        border_style="cyan"
    ))
    console.print("\n")

    if full:
        # Show full descriptions with panels
        for script_name, description, script_path in scripts:
            usage = f"uv run scripts/{script_name}.py"

            console.print(f"[bold cyan]{script_name}[/bold cyan]")
            console.print(f"[dim]Usage: {usage}[/dim]")
            console.print()

            if description:
                console.print(Panel(
                    description,
                    title="[bold]Description[/bold]",
                    border_style="blue",
                    padding=(1, 2)
                ))
            else:
                console.print("[dim]No description available[/dim]")

            console.print()
    else:
        # Show compact table view
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Script", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Usage", style="dim")

        for script_name, description, _ in scripts:
            usage = f"uv run scripts/{script_name}.py"
            table.add_row(script_name, description or "[dim]No description[/dim]", usage)

        console.print(table)
        console.print("\n")
        console.print("[dim]Tip: Use --full to see complete descriptions[/dim]\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="List available scripts in the sandbox",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Show full module docstrings instead of just summaries"
    )

    args = parser.parse_args()
    list_available_scripts(full=args.full)


if __name__ == "__main__":
    main()
