"""Exception classes."""

from pathlib import Path


class TemplateNotFoundError(FileNotFoundError):
    """Jinja2 not found error."""

    def __init__(self, template_path: Path, *args: object):
        """Build message."""
        message = f"Template file not found: {template_path}"
        super().__init__(message, *args)
