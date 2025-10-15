#!/usr/bin/env python3
"""VSCode Theme to Jinja2 Template Generator.

Analyzes a VSCode theme JSON and base16 palette, then generates a Jinja2 template
by replacing base16 colors with template variables.

Usage:
    # Use default files (data/rose-pine-moon.{json,yml})
    uv run scripts/template_generator.py

    # Custom theme and palette files
    uv run scripts/template_generator.py --theme theme.json --palette palette.yml
    uv run scripts/template_generator.py -t theme.json -p palette.yml

    # Custom output path
    uv run scripts/template_generator.py --output out/custom.json.j2
    uv run scripts/template_generator.py -o out/custom.json.j2

    # Replace similar colors within Delta E threshold
    uv run scripts/template_generator.py --threshold 5.0

How It Works:
    1. Reads a VSCode theme JSON and base16 palette YAML
    2. Identifies exact color matches between theme and palette
    3. Replaces matched colors with Jinja2 variables (e.g., "{{ base0A }}")
    4. Preserves alpha channel variations (e.g., "#ea9a97e6" → "{{ base0A }}e6")
    5. Optionally replaces similar colors within Delta E threshold
    6. Outputs a reusable .json.j2 template file

Template Generation:
    - Exact matches: #ea9a97 → "{{ base0A }}"
    - With alpha: #ea9a97e6 → "{{ base0A }}e6"
    - Metadata: name → "{{ theme_name }}", type → "{{ theme_type }}"
    - Unmapped colors remain as hex values

Delta E Threshold (optional):
    --threshold 5.0  = Replace colors within Delta E < 5.0
    --threshold 10.0 = More aggressive replacement
    No threshold     = Only exact matches (default)

Output:
    Default: out/generated-theme.json.j2

    Generated templates can be used with theme_builder.py:
      uv run scripts/theme_builder.py --template out/generated-theme.json.j2

Default Files:
    - Theme: data/rose-pine-moon.json
    - Palette: data/rose-pine-moon.yml
    - Output: out/generated-theme.json.j2
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent))
from vscode import (
    find_closest_base16_color,
    normalize_color,
    parse_base16_palette,
    strip_alpha,
)

console = Console()


def build_color_to_base16_map(
    base16_palette: Dict[str, str], threshold: Optional[float] = None
) -> Dict[str, Tuple[str, bool]]:
    """Build a mapping of color hex values to base16 keys.

    Returns dict: {normalized_color: (base16_key, is_exact_match)}

    If threshold is provided, also includes colors within the Delta E threshold.
    """
    color_map = {}

    for base16_key, color in base16_palette.items():
        normalized = normalize_color(color)
        color_map[normalized] = (base16_key, True)

    return color_map


def replace_color_with_variable(
    color: str,
    color_map: Dict[str, Tuple[str, bool]],
    base16_palette: Dict[str, str],
    threshold: Optional[float] = None,
) -> str:
    """Replace a color hex with a Jinja2 variable if it matches a base16 color.

    Handles:
    - Exact matches: #ea9a97 -> {{ base0A }}
    - Alpha variations: #ea9a97e6 -> {{ base0A }}e6
    - Similar colors (if threshold provided): #ea9b98 -> {{ base0A }}
    """
    if not color or not isinstance(color, str):
        return color

    if color.lower() in ["#0000", "#00000000"]:
        return color

    original_color = color
    normalized = normalize_color(color)
    stripped = strip_alpha(color)

    if stripped in color_map:
        base16_key, _ = color_map[stripped]

        if len(normalized) == 8:
            alpha = normalized[6:8]
            return f"{{{{ {base16_key} }}}}{alpha}"
        else:
            return f"{{{{ {base16_key} }}}}"

    if threshold is not None and threshold > 0:
        closest_key, rgb_dist, delta_e = find_closest_base16_color(color, base16_palette)

        if delta_e is not None and delta_e <= threshold:
            console.print(
                f"  [dim]Replacing similar color {color} with {closest_key} "
                f"(Delta E: {delta_e:.2f})[/dim]"
            )

            if len(normalized) == 8:
                alpha = normalized[6:8]
                return f"{{{{ {closest_key} }}}}{alpha}"
            else:
                return f"{{{{ {closest_key} }}}}"

    return original_color


def process_theme_value(
    value: Any,
    color_map: Dict[str, Tuple[str, bool]],
    base16_palette: Dict[str, str],
    threshold: Optional[float] = None,
) -> Any:
    """Recursively process theme values, replacing colors with variables."""
    if isinstance(value, str):
        # Check if this looks like a color (starts with #)
        if value.startswith("#"):
            return replace_color_with_variable(value, color_map, base16_palette, threshold)
        return value
    elif isinstance(value, dict):
        return {
            k: process_theme_value(v, color_map, base16_palette, threshold)
            for k, v in value.items()
        }
    elif isinstance(value, list):
        return [process_theme_value(item, color_map, base16_palette, threshold) for item in value]
    else:
        return value


def generate_template(
    theme_data: dict, base16_palette: Dict[str, str], threshold: Optional[float] = None
) -> dict:
    """Generate a Jinja2 template from a VSCode theme.

    Replaces:
    - theme.name -> {{ theme_name }}
    - theme.type -> {{ theme_type }}
    - Colors that match base16 -> {{ baseXX }}
    """
    color_map = build_color_to_base16_map(base16_palette, threshold)
    template_data = {}

    if "name" in theme_data:
        template_data["name"] = "{{ theme_name }}"

    if "type" in theme_data:
        template_data["type"] = "{{ theme_type }}"

    if "colors" in theme_data:
        console.print("[dim]Processing colors section...[/dim]")
        template_data["colors"] = process_theme_value(
            theme_data["colors"], color_map, base16_palette, threshold
        )

    if "tokenColors" in theme_data:
        console.print("[dim]Processing tokenColors section...[/dim]")
        template_data["tokenColors"] = process_theme_value(
            theme_data["tokenColors"], color_map, base16_palette, threshold
        )

    return template_data


def format_jinja2_template(data: dict) -> str:
    """Format the template data as properly formatted JSON with Jinja2 variables.

    Jinja2 variables remain quoted so they render correctly.
    """
    return json.dumps(data, indent=4, ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    default_data_dir = Path(__file__).parent.parent / "data"
    default_theme = default_data_dir / "rose-pine-moon.json"
    default_palette = default_data_dir / "rose-pine-moon.yml"
    default_output = Path(__file__).parent.parent / "out" / "generated-theme.json.j2"

    parser = argparse.ArgumentParser(
        description="Generate Jinja2 templates from VSCode themes and base16 palettes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-t",
        "--theme",
        type=Path,
        default=default_theme,
        help=f"Path to VS Code theme JSON file (default: {default_theme.relative_to(Path.cwd()) if default_theme.is_relative_to(Path.cwd()) else default_theme})",
    )

    parser.add_argument(
        "-p",
        "--palette",
        type=Path,
        default=default_palette,
        help=f"Path to base16 palette YAML file "
        f"(default: {default_palette.relative_to(Path.cwd()) if default_palette.is_relative_to(Path.cwd()) else default_palette})",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_output,
        help=f"Output template file path "
        f"(default: {default_output.relative_to(Path.cwd()) if default_output.is_relative_to(Path.cwd()) else default_output})",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Delta E threshold for replacing similar colors (default: None, only exact matches)",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    theme_path = args.theme
    palette_path = args.palette
    output_path = args.output

    if not theme_path.exists():
        console.print(f"[red]Error: Theme file not found: {theme_path}[/red]")
        return

    if not palette_path.exists():
        console.print(f"[red]Error: Palette file not found: {palette_path}[/red]")
        return

    console.print(f"[dim]Loading VS Code theme: {theme_path.name}[/dim]")
    with open(theme_path, "r") as f:
        theme_data = json.load(f)

    console.print(f"[dim]Loading base16 palette: {palette_path.name}[/dim]")
    base16_palette = parse_base16_palette(palette_path)

    console.print("[dim]Generating Jinja2 template...[/dim]")
    if args.threshold is not None:
        console.print(f"[dim]Using Delta E threshold: {args.threshold}[/dim]")

    template_data = generate_template(theme_data, base16_palette, args.threshold)

    console.print("[dim]Formatting template...[/dim]")
    template_str = format_jinja2_template(template_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[dim]Saving template to: {output_path}[/dim]")
    with open(output_path, "w") as f:
        f.write(template_str)

    console.print("\n[green]✓[/green] Template generated successfully!")
    console.print(f"[cyan]Output:[/cyan] {output_path}")
    console.print("\n[dim]You can now use this template with theme_builder.py:[/dim]")
    console.print(f"[dim]  uv run scripts/theme_builder.py --template {output_path}[/dim]")


if __name__ == "__main__":
    main()
