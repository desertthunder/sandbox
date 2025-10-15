# Sandbox

A personal experimentation and data analysis workspace.

## Setup

```bash
# Install uv if it's not on your system
curl -LsSf https://astral.sh/uv/install.sh | sh

# Then install dependencies with uv
uv sync
```

## Theming

### VS Code Theme Analyzer

Analyzes VS Code theme JSON files and maps colors to base16 palette entries.

```bash
uv run scripts/vscode.py --help
```

- Maps VSCode theme colors to base16 palette entries
- Shows color variations (alpha channels)
- Calculates Delta E 2000 for perceptual color similarity
- Rich terminal output with color previews

### Base16 Theme Builder

Generates VSCode theme JSON files from base16 palette YAML files using Jinja2 templates.

```bash
uv run scripts/theme_builder.py --help
```

- Template-based theme generation
- Supports any base16 color palette
- Outputs to `out/` directory

See [data/](./data/rose-pine-moon.yml) for an example base16 palette format and the tinted-theming
[gallery](https://tinted-theming.github.io/tinted-gallery/) for more palettes

### Template Generator

Automatically generates Jinja2 templates from existing VSCode themes.

```bash
uv run scripts/template_generator.py --help
```

- Analyzes existing themes to extract base16 color mappings
- Replaces colors with Jinja2 variables (`{{ baseXX }}`)
- Preserves alpha channel variations
- Optional similarity matching (Delta E threshold)

### Workflow

1. Analyze a theme to understand its color usage:

   ```bash
   uv run scripts/vscode.py -t theme.json -p palette.yml
   ```

2. Generate a reusable template (optional):

   ```bash
   uv run scripts/template_generator.py -t theme.json -p palette.yml
   ```

3. Build themes from any base16 palette:

   ```bash
   uv run scripts/theme_builder.py -p new-palette.yml
   ```
