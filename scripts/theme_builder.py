#!/usr/bin/env python3
"""Base16 to VS Code Theme Builder.

Generates VS Code theme JSON files from base16 palette YAML files using
a Jinja2 template.

Usage:
    # Use default palette (data/rose-pine-moon.yml)
    uv run scripts/theme_builder.py

    # Custom palette file
    uv run scripts/theme_builder.py --palette path/to/palette.yml
    uv run scripts/theme_builder.py -p palette.yml

    # Custom output directory
    uv run scripts/theme_builder.py --output themes/
    uv run scripts/theme_builder.py -o themes/

    # Custom template
    uv run scripts/theme_builder.py --template custom.json.j2
    uv run scripts/theme_builder.py -t custom.json.j2

    # Custom output filename
    uv run scripts/theme_builder.py --output-name my-theme.json

Template Variables:
    {{ theme_name }}  - Theme name from palette YAML
    {{ theme_type }}  - Theme type (dark/light) from palette YAML
    {{ base00 }}      - Background color
    {{ base01 }}      - Lighter background
    {{ base02 }}      - Selection background
    {{ base03 }}      - Comments, invisibles
    {{ base04 }}      - Dark foreground
    {{ base05 }}      - Default foreground
    {{ base06 }}      - Light foreground
    {{ base07 }}      - Light background
    {{ base08 }}      - Variables, XML tags
    {{ base09 }}      - Integers, booleans
    {{ base0A }}      - Classes, search text
    {{ base0B }}      - Strings, inherited classes
    {{ base0C }}      - Support, regex
    {{ base0D }}      - Functions, methods
    {{ base0E }}      - Keywords, storage
    {{ base0F }}      - Deprecated, embedded

Required Palette Format (YAML):
    system: "base16"
    name: "Theme Name"
    slug: "theme-slug"
    variant: "dark"  # or "light"
    palette:
      base00: "#hexcolor"
      base01: "#hexcolor"
      # ... base02-base0F

Default Files:
    - Palette: data/rose-pine-moon.yml
    - Template: templates/vscode-theme.json.j2
    - Output: out/
"""

import argparse
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from rich.console import Console

from libs.exceptions import TemplateNotFoundError

console = Console()


def parse_base16_palette(yaml_path: Path) -> dict:
    """Parse base16 YAML and extract palette and metadata.

    Returns a dict with:
    - theme_name: str
    - theme_type: str ("dark" or "light")
    - baseXX: str (colors)
    """
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    result = {
        "theme_name": data.get("name", "Unknown Theme"),
        "theme_type": data.get("variant", "dark"),
    }

    palette = data.get("palette", {})
    result.update(palette)

    return result


def load_template(template_path: Path) -> Template:
    """Load Jinja2 template from file."""
    if not template_path.exists():
        raise TemplateNotFoundError(template_path)

    template_dir = template_path.parent
    template_name = template_path.name

    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    return env.get_template(template_name)


def render_theme(template: Template, palette_data: dict) -> str:
    """Render the VSCode theme JSON using the template and palette data."""
    return template.render(**palette_data)


def save_theme(output_path: Path, theme_json: str):
    """Save the rendered theme JSON to a file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(theme_json)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    default_data_dir = Path(__file__).parent.parent / "data"
    default_palette = default_data_dir / "rose-pine-moon.yml"
    default_template = Path(__file__).parent.parent / "templates" / "vscode-theme.json.j2"
    default_output = Path(__file__).parent.parent / "out"

    parser = argparse.ArgumentParser(
        description="Generate VS Code themes from base16 palettes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--palette",
        type=Path,
        default=default_palette,
        help=f"Path to base16 palette YAML file (default: {default_palette.relative_to(Path.cwd()) if default_palette.is_relative_to(Path.cwd()) else default_palette})",
    )

    parser.add_argument(
        "-t",
        "--template",
        type=Path,
        default=default_template,
        help=f"Path to Jinja2 template file (default: {default_template.relative_to(Path.cwd()) if default_template.is_relative_to(Path.cwd()) else default_template})",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_output,
        help=f"Output directory (default: {default_output.relative_to(Path.cwd()) if default_output.is_relative_to(Path.cwd()) else default_output})",
    )

    parser.add_argument(
        "--output-name",
        type=str,
        help="Output filename (default: <palette-slug>.json or <palette-name>.json)",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    palette_path = args.palette
    template_path = args.template
    output_dir = args.output

    if not palette_path.exists():
        console.print(f"[red]Error: Palette file not found: {palette_path}[/red]")
        return

    if not template_path.exists():
        console.print(f"[red]Error: Template file not found: {template_path}[/red]")
        return

    console.print(f"[dim]Loading base16 palette: {palette_path.name}[/dim]")
    palette_data = parse_base16_palette(palette_path)

    console.print(f"[dim]Loading template: {template_path.name}[/dim]")
    template = load_template(template_path)

    console.print(f"[dim]Rendering theme: {palette_data['theme_name']}[/dim]")
    theme_json = render_theme(template, palette_data)

    if args.output_name:
        output_name = args.output_name
        if not output_name.endswith(".json"):
            output_name += ".json"
    else:
        with open(palette_path, "r") as f:
            data = yaml.safe_load(f)
        slug = data.get("slug")
        if slug:
            output_name = f"{slug}.json"
        else:
            name = palette_data["theme_name"]
            output_name = name.lower().replace(" ", "-").replace("'", "") + ".json"

    output_path = output_dir / output_name

    console.print(f"[dim]Saving theme to: {output_path}[/dim]")
    save_theme(output_path, theme_json)

    console.print("\n[green]✓[/green] Theme generated successfully!")
    console.print(f"[cyan]Theme:[/cyan] {palette_data['theme_name']}")
    console.print(f"[cyan]Type:[/cyan] {palette_data['theme_type']}")
    console.print(f"[cyan]Output:[/cyan] {output_path}")


if __name__ == "__main__":
    main()
