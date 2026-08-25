"""Check presence and integrity of documentation links (§13, check 13.12)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_DOCS = [
    Path("README.md"),
    Path("ARCHITECTURE.md"),
    Path("VERIFICATION.md"),
    Path("ANTI_SLOP.md"),
    Path("docs/EVALUATION.md"),
    Path("docs/FALSIFICATION.md"),
    Path("PROGRESS.md"),
    Path("CHANGELOG.md"),
    Path("IMPLEMENTATION_PLAN.md"),
]

LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def check_docs() -> list[str]:
    """Verify presence of required docs and correctness of file links."""
    errors: list[str] = []

    # 1. Check required docs exist
    for doc in REQUIRED_DOCS:
        if not doc.is_file():
            errors.append(f"Required document missing: {doc.as_posix()}")

    # 2. Check markdown links in existing docs
    for doc in REQUIRED_DOCS:
        if not doc.is_file():
            continue
        text = doc.read_text(encoding="utf-8")
        parent = doc.parent

        for match in LINK_PATTERN.finditer(text):
            target = match.group(2).strip()
            # Ignore URL links, fragments (#), mailto
            if (
                target.startswith("http://")
                or target.startswith("https://")
                or target.startswith("#")
                or target.startswith("mailto:")
            ):
                continue

            # Strip query params or anchors from relative paths
            clean_target = target.split("#")[0].split("?")[0]
            if not clean_target:
                continue

            target_path = (parent / clean_target).resolve()
            # Also check relative to repo root
            root_target_path = Path(clean_target).resolve()

            if not target_path.exists() and not root_target_path.exists():
                errors.append(f"{doc.as_posix()}: broken file link '{target}'")

    return errors


def main() -> None:
    """CLI entrypoint for doc checks."""
    errors = check_docs()
    if errors:
        print("Documentation integrity check failed:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    print("PASS: All required docs exist and all file links are valid.")


if __name__ == "__main__":
    main()
