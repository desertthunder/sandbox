#!/usr/bin/env python3
"""
VS Code Theme to Base16 Color Mapper

Analyzes VS Code theme JSON files and maps colors to base16 palette entries,
showing which base16 colors correspond to which VS Code theme tokens.

Usage:
    # Use default files
    uv run scripts/vscode.py

    # Custom files
    uv run scripts/vscode.py --theme <path> --palette <path>
"""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from coloraide import Color
from rich.console import Console
from rich.panel import Panel

console = Console()


def normalize_color(color: str) -> str:
    """
    Normalize color string for comparison.
    Converts to lowercase and strips the # prefix.
    """
    if not color:
        return ""
    return color.lower().strip().lstrip("#")


def strip_alpha(color: str) -> str:
    """
    Strip alpha channel from color if present.
    Converts #RRGGBBAA to #RRGGBB
    """
    normalized = normalize_color(color)
    if len(normalized) == 8:
        return normalized[:6]
    return normalized


def color_for_display(color: str) -> str:
    """
    Prepare color for rich display by stripping alpha and adding # prefix.
    """
    if not color or color.lower() == "#0000":
        return "#000000"  # Transparent colors -> black for display

    stripped = strip_alpha(color)
    if not stripped:
        return "#000000"
    return f"#{stripped}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color string to RGB tuple.
    Handles both #RRGGBB and RRGGBB formats.
    """
    normalized = normalize_color(hex_color)
    if len(normalized) >= 6:
        r = int(normalized[0:2], 16)
        g = int(normalized[2:4], 16)
        b = int(normalized[4:6], 16)
        return (r, g, b)
    return (0, 0, 0)


def rgb_distance(color1: str, color2: str) -> float:
    """
    Calculate Euclidean distance between two colors in RGB space.
    Simple but not perceptually accurate.

    Returns distance in range [0, 441.67] where:
    - 0 = identical colors
    - ~441.67 = max distance (black to white)
    """
    r1, g1, b1 = hex_to_rgb(strip_alpha(color1))
    r2, g2, b2 = hex_to_rgb(strip_alpha(color2))
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


def delta_e_distance(color1: str, color2: str) -> Optional[float]:
    """
    Calculate Delta E 2000 distance between two colors using coloraide.
    Perceptually uniform - matches human color perception.

    Returns Delta E value where:
    - 0-1: Not perceptible
    - 1-2: Perceptible through close observation
    - 2-10: Similar colors
    - 10-50: Different colors
    - >50: Very different colors

    Returns None if coloraide is not available.
    """
    try:
        c1 = strip_alpha(color1)
        c2 = strip_alpha(color2)

        color_a = Color(f"#{c1}")
        color_b = Color(f"#{c2}")

        return color_a.delta_e(color_b, method="2000")
    except Exception:
        return None


def find_closest_base16_color(
    target_color: str, base16_palette: Dict[str, str]
) -> Tuple[str, float, Optional[float]]:
    """
    Find the closest base16 color to the target color.

    Returns tuple of (base16_key, rgb_distance, delta_e_distance)
    """
    if not base16_palette:
        return ("unknown", float("inf"), None)

    target_stripped = strip_alpha(target_color)

    closest_key = ""
    min_rgb_dist = float("inf")
    min_delta_e = None

    for base16_key, base16_color in base16_palette.items():
        rgb_dist = rgb_distance(target_stripped, base16_color)

        if rgb_dist < min_rgb_dist:
            min_rgb_dist = rgb_dist
            closest_key = base16_key

            min_delta_e = delta_e_distance(target_stripped, base16_color)

    return (closest_key, min_rgb_dist, min_delta_e)


def parse_vscode_theme(theme_path: Path) -> Dict[str, str]:
    """
    Parse VS Code theme JSON and extract all color definitions.

    Returns a dict mapping key paths to color values.
    E.g., {"colors.editor.background": "#232136", ...}
    """
    with open(theme_path, "r") as f:
        theme = json.load(f)

    color_map = {}

    if "colors" in theme:
        for key, value in theme["colors"].items():
            if value and isinstance(value, str) and value.startswith("#"):
                color_map[f"colors.{key}"] = value

    if "tokenColors" in theme:
        for idx, token in enumerate(theme["tokenColors"]):
            if "settings" in token:
                settings = token["settings"]
                scope = token.get("scope", [])
                if isinstance(scope, str):
                    scope = [scope]
                scope_str = ", ".join(scope) if scope else f"token[{idx}]"

                if "foreground" in settings:
                    key = f"tokenColors[{scope_str}].foreground"
                    color_map[key] = settings["foreground"]

                if "background" in settings:
                    key = f"tokenColors[{scope_str}].background"
                    color_map[key] = settings["background"]

    return color_map


def parse_base16_palette(yaml_path: Path) -> Dict[str, str]:
    """
    Parse base16 YAML and extract palette.

    Returns a dict mapping base16 keys to color values.
    E.g., {"base00": "#232136", ...}
    """
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    return data.get("palette", {})


def build_color_frequency_map(vscode_colors: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Build a map of colors to the keys that use them.
    Shows which colors are repeated and where.

    Returns dict: {color (normalized): [list of keys]}
    """
    frequency_map = defaultdict(list)

    for key, color in vscode_colors.items():
        normalized = normalize_color(color)
        if normalized:
            frequency_map[normalized].append(key)

    return dict(frequency_map)


def map_vscode_to_base16(
    vscode_colors: Dict[str, str], base16_palette: Dict[str, str]
) -> Dict[str, List[Tuple[str, str]]]:
    """
    Map VS Code colors to base16 palette entries.

    Returns dict: {base16_key: [list of vscode keys that use this color]}
    """
    base16_lookup = {}
    for base16_key, color in base16_palette.items():
        normalized = normalize_color(color)
        base16_lookup[normalized] = base16_key

    mapping = defaultdict(list)
    unmapped = []

    for vscode_key, color in vscode_colors.items():
        normalized = normalize_color(color)
        if normalized in base16_lookup:
            base16_key = base16_lookup[normalized]
            mapping[base16_key].append((vscode_key, color))
        else:
            stripped = strip_alpha(color)
            if stripped and stripped in base16_lookup:
                base16_key = base16_lookup[stripped]
                mapping[base16_key].append((vscode_key, color))
            else:
                unmapped.append((vscode_key, color))

    if unmapped:
        mapping["unmapped"] = unmapped
    return dict(mapping)


def display_color_analysis(
    base16_palette: Dict[str, str],
    vscode_to_base16: Dict[str, List[Tuple[str, str]]],
    frequency_map: Dict[str, List[str]],
):
    """
    Display the color mapping analysis with rich formatting.
    """
    console.print("\n")
    console.print(
        Panel.fit(
            "[bold cyan]VS Code Theme -> Base16 Color Mapping Analysis[/bold cyan]",
            border_style="cyan",
        )
    )

    base16_keys = [k for k in base16_palette.keys() if k in vscode_to_base16]
    base16_keys.sort()

    for base16_key in base16_keys:
        color = base16_palette[base16_key]
        vscode_keys = vscode_to_base16[base16_key]

        console.print(f"\n[bold]{base16_key}[/bold]", style=color_for_display(color))
        console.print(f"  Color: {color}", style=color_for_display(color))
        console.print(f"  Used in {len(vscode_keys)} locations:", style="dim")

        color_variations = defaultdict(list)
        for key, key_color in vscode_keys:
            color_variations[key_color].append(key)

        for variation_color, keys in color_variations.items():
            if variation_color != color:
                console.print("    Variation: ", style="dim", end="")
                console.print(
                    f"{variation_color}", style=color_for_display(variation_color)
                )

            for key in keys[:5]:
                console.print(f"      - {key}", style="dim")

            if len(keys) > 5:
                console.print(f"      ... and {len(keys) - 5} more", style="dim italic")

    if "unmapped" in vscode_to_base16:
        console.print("\n[bold yellow]Unmapped Colors[/bold yellow]")
        unmapped = vscode_to_base16["unmapped"]

        unmapped_by_color = defaultdict(list)
        for key, color in unmapped:
            unmapped_by_color[color].append(key)

        for color, keys in sorted(
            unmapped_by_color.items(), key=lambda x: len(x[1]), reverse=True
        ):
            console.print(f"\n  Color: {color}", style=color_for_display(color))
            console.print(f"  Used in {len(keys)} locations:", style="dim")

            closest_key, rgb_dist, delta_e = find_closest_base16_color(
                color, base16_palette
            )
            closest_color = base16_palette.get(closest_key, "")

            console.print("  Closest match: ", style="dim", end="")
            console.print(
                f"{closest_key} ", style=color_for_display(closest_color), end=""
            )
            console.print("-> ", style="dim", end="")
            console.print(f"{closest_color}", style=color_for_display(closest_color))

            if delta_e is not None:
                if delta_e < 10:
                    similarity_style = "green"
                    similarity_label = "very similar"
                elif delta_e < 50:
                    similarity_style = "yellow"
                    similarity_label = "different"
                else:
                    similarity_style = "red"
                    similarity_label = "very different"

                console.print(
                    f"    Delta E: [{similarity_style}]{delta_e:.2f}[/{similarity_style}] "
                    f"({similarity_label}), RGB distance: {rgb_dist:.2f}",
                    style="dim",
                )
            else:
                console.print(f"    RGB distance: {rgb_dist:.2f}", style="dim")

            for key in keys[:3]:
                console.print(f"    - {key}", style="dim")

            if len(keys) > 3:
                console.print(f"    ... and {len(keys) - 3} more", style="dim italic")

    # Summary statistics
    console.print("\n")
    console.print(
        Panel.fit(
            _build_summary_text(base16_palette, vscode_to_base16, frequency_map),
            title="[bold]Summary Statistics[/bold]",
            border_style="green",
        )
    )


def _build_summary_text(
    base16_palette: Dict[str, str],
    vscode_to_base16: Dict[str, List[Tuple[str, str]]],
    frequency_map: Dict[str, List[str]],
) -> str:
    """Build summary statistics text."""
    total_vscode_keys = sum(len(v) for v in vscode_to_base16.values())
    mapped_keys = sum(len(v) for k, v in vscode_to_base16.items() if k != "unmapped")
    unmapped_keys = len(vscode_to_base16.get("unmapped", []))

    base16_used = len(
        [k for k in base16_palette.keys() if k in vscode_to_base16 and k != "unmapped"]
    )
    base16_total = len(base16_palette)

    repeated = [(color, keys) for color, keys in frequency_map.items() if len(keys) > 1]
    repeated.sort(key=lambda x: len(x[1]), reverse=True)

    unmapped_colors = []
    if "unmapped" in vscode_to_base16:
        for key, color in vscode_to_base16["unmapped"]:
            if color not in [c for c, _ in unmapped_colors]:
                unmapped_colors.append((color, key))

    similar_count = 0
    different_count = 0

    if unmapped_colors:
        for color, _ in unmapped_colors:
            _, _, delta_e = find_closest_base16_color(color, base16_palette)
            if delta_e is not None:
                if delta_e < 10:
                    similar_count += 1
                else:
                    different_count += 1

    lines = [
        f"Total VS Code theme keys: {total_vscode_keys}",
        f"Mapped to base16: {mapped_keys}",
        f"Unmapped colors: {unmapped_keys}",
        "",
        f"Base16 palette colors used: {base16_used}/{base16_total}",
    ]

    if unmapped_colors:
        unique_unmapped = len(unmapped_colors)
        lines.extend(
            [
                "",
                "Unmapped color similarity:",
                f"  - Similar (Delta E < 10): {similar_count}/{unique_unmapped}",
                f"  - Different (Delta E >= 10): {different_count}/{unique_unmapped}",
            ]
        )

    lines.extend(
        [
            "",
            "Most repeated colors:",
        ]
    )

    for color, keys in repeated[:3]:
        lines.append(f"  - #{color}: used {len(keys)} times")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    default_data_dir = Path(__file__).parent.parent / "data"
    default_theme = default_data_dir / "rose-pine-moon.json"
    default_palette = default_data_dir / "rose-pine-moon.yml"

    parser = argparse.ArgumentParser(
        description="Analyze VS Code theme colors and map them to base16 palette entries.",
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
        help=f"Path to base16 palette YAML file (default: {default_palette.relative_to(Path.cwd()) if default_palette.is_relative_to(Path.cwd()) else default_palette})",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    theme_path = args.theme
    yaml_path = args.palette

    if not theme_path.exists():
        console.print(f"[red]Error: Theme file not found: {theme_path}[/red]")
        return

    if not yaml_path.exists():
        console.print(f"[red]Error: Palette file not found: {yaml_path}[/red]")
        return

    console.print(f"[dim]Loading VS Code theme: {theme_path.name}[/dim]")
    vscode_colors = parse_vscode_theme(theme_path)

    console.print(f"[dim]Loading base16 palette: {yaml_path.name}[/dim]")
    base16_palette = parse_base16_palette(yaml_path)

    console.print("[dim]Analyzing color usage...[/dim]")
    frequency_map = build_color_frequency_map(vscode_colors)
    vscode_to_base16 = map_vscode_to_base16(vscode_colors, base16_palette)

    display_color_analysis(base16_palette, vscode_to_base16, frequency_map)


if __name__ == "__main__":
    main()
