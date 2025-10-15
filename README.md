# Sandbox

A personal experimentation and data analysis workspace.

## Setup

```bash
# Install dependencies with uv
uv sync
```

## Projects

### VS Code Theme → Base16 Color Mapper

Analyzes VS Code theme JSON files and maps colors to base16 palette entries, helping you understand which base16 colors correspond to which VS Code theme tokens.

#### Usage

```bash
# Run with default files (data/rose-pine-moon.{json,yml})
uv run scripts/vscode.py

# Use custom theme and palette files
uv run scripts/vscode.py --theme path/to/theme.json --palette path/to/palette.yml

# Short flags
uv run scripts/vscode.py -t path/to/theme.json -p path/to/palette.yml

# Show help
uv run scripts/vscode.py --help
```

Default files:

- `data/rose-pine-moon.json` - VS Code theme file
- `data/rose-pine-moon.yml` - Base16 color palette

#### How Color Similarity Works

The tool uses two distance metrics:

1. **RGB Euclidean Distance** - Simple geometric distance in RGB space
   - Fast but not perceptually accurate
   - Range: 0 to ~441.67

2. **Delta E 2000** - Perceptually uniform color difference
   - Uses CIE Lab color space via the `coloraide` library
   - Matches human perception of color differences
   - Interpretation:
     - **< 10**: Very similar colors (green)
     - **10-50**: Different colors (yellow)
     - **> 50**: Very different colors (red)

#### Output

The analyzer provides:

- **Mapped Colors**: VS Code tokens that exactly match base16 colors
- **Color Variations**: Alpha channel variations of base16 colors
- **Unmapped Colors**: Colors not in the base16 palette
    - Shows closest base16 match
    - Displays Delta E 2000 similarity score
    - Visual side-by-side color comparison
- **Summary Stats**: Color usage patterns and similarity metrics

#### Dependencies

- `coloraide` - Perceptual color distance calculations
- `pyyaml` - YAML parsing for base16 palettes
- `rich` - Beautiful terminal output
