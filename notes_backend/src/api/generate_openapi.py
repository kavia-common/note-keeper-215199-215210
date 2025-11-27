#!/usr/bin/env python3
"""
Utility to generate and write the FastAPI OpenAPI schema to interfaces/openapi.json.

Usage:
    python -m src.api.generate_openapi
    or
    python src/api/generate_openapi.py

This imports the FastAPI `app` from src.api.main, generates its OpenAPI document,
and writes it to the repository's interfaces/openapi.json. The output reflects
the current definitions for all routes, including /notes CRUD endpoints.
"""

import json
import sys
from pathlib import Path

# Ensure package imports resolve when executed directly
# Allows running both as module and as a standalone script.
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]  # .../note-keeper-.../notes_backend
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    # Import the FastAPI application
    from src.api.main import app
except Exception as exc:
    print(f"Error importing app from src.api.main: {exc}", file=sys.stderr)
    sys.exit(1)


def _get_output_path() -> Path:
    """
    Determine the target path for the generated OpenAPI JSON file.
    Writes to 'interfaces/openapi.json' under the backend container root.
    """
    # interfaces directory is sibling to src in notes_backend
    interfaces_dir = PROJECT_ROOT / "interfaces"
    interfaces_dir.mkdir(parents=True, exist_ok=True)
    return interfaces_dir / "openapi.json"


# PUBLIC_INTERFACE
def generate_and_write_openapi(output_path: Path | None = None) -> Path:
    """Generate the OpenAPI schema from the FastAPI app and write it to disk.

    Args:
        output_path: Optional custom path to write the schema JSON. If None,
                     defaults to interfaces/openapi.json.

    Returns:
        The Path where the OpenAPI JSON was written.
    """
    path = output_path or _get_output_path()

    # Generate schema
    schema = app.openapi()

    # Write formatted JSON
    with path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write("\n")  # trailing newline for POSIX-friendly files

    return path


def main() -> None:
    """CLI entrypoint to generate OpenAPI JSON."""
    out_path = _get_output_path()
    written = generate_and_write_openapi(out_path)
    print(f"OpenAPI schema written to: {written}")


if __name__ == "__main__":
    main()
