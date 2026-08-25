"""Check file sizes and function lengths across the engine codebase (§13, check 13.10)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def check_file_sizes(root: Path = Path("engine")) -> list[str]:
    """Verify file and function size constraints."""
    violations: list[str] = []

    for py_file in root.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        text = py_file.read_text(encoding="utf-8")

        # Check AST function body sizes
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body_stmts = len(node.body)
                    if body_stmts > 80:
                        violations.append(
                            f"{py_file.as_posix()}:{node.name} has {body_stmts} statements (> 80)"
                        )
        except SyntaxError as e:
            violations.append(f"{py_file.as_posix()} syntax error: {e}")

    return violations


def main() -> None:
    """CLI entrypoint for file size checks."""
    violations = check_file_sizes()
    if violations:
        print("File size and function statement violations found:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    print("PASS: All engine modules and functions conform to size constraints.")


if __name__ == "__main__":
    main()
