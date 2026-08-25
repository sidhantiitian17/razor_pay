"""Validate contracts/report.schema.json is valid JSON Schema draft 2020-12."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema.validators import Draft202012Validator


def main() -> None:
    """Validate the report schema file."""
    schema_path = Path(__file__).resolve().parents[2] / "contracts" / "report.schema.json"
    if not schema_path.exists():
        print(f"FAIL: schema not found at {schema_path}", file=sys.stderr)
        sys.exit(1)

    with open(schema_path) as f:
        schema = json.load(f)

    # Validate that the schema itself is valid
    Draft202012Validator.check_schema(schema)
    print(f"PASS: {schema_path.name} is valid JSON Schema draft 2020-12")


if __name__ == "__main__":
    main()
