"""Guard: every third-party module the app imports is declared in requirements.txt
(RNG-18).

build123d has been the shipping geometry kernel since RNG-15 but was never added
to requirements.txt, so a clean checkout could not import the kernel or collect
the geometry tests. pydantic had drifted the same way, installing only because
anthropic happens to depend on it. Both are invisible to a developer with an
existing environment, which is exactly why they survived so long.

This test walks the real imports rather than trusting a hand-kept list, so the
next module added to ringcad/ is checked automatically.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = REPO_ROOT / "requirements.txt"
PACKAGE = REPO_ROOT / "ringcad"

# Import name -> distribution name, where they differ.
_DISTRIBUTION_NAMES = {"dotenv": "python-dotenv"}

# First-party and tooling names that are not third-party runtime dependencies.
_NOT_DEPENDENCIES = {"ringcad"}


def _declared() -> set[str]:
    """Distribution names pinned in requirements.txt, lowercased."""
    names = set()
    for line in REQUIREMENTS.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        # Split on the first version specifier character.
        name = line
        for sep in ("==", ">=", "<=", "~=", ">", "<"):
            name = name.split(sep)[0]
        names.add(name.strip().lower())
    return names


def _imported() -> set[str]:
    """Top-level module names imported anywhere under ringcad/, excluding the
    standard library and first-party packages."""
    found = set()
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                # level > 0 is a relative import, always first-party.
                if node.level == 0 and node.module:
                    found.add(node.module.split(".")[0])
    return {
        name
        for name in found
        if name not in sys.stdlib_module_names and name not in _NOT_DEPENDENCIES
    }


def test_every_imported_package_is_declared():
    declared = _declared()
    missing = sorted(
        name
        for name in _imported()
        if _DISTRIBUTION_NAMES.get(name, name).lower() not in declared
    )
    assert not missing, (
        f"imported by ringcad/ but absent from requirements.txt: {missing}. "
        "A clean checkout cannot run the app until these are declared."
    )


def test_requirements_are_pinned_exactly():
    """Every dependency is pinned with == so a clean install is reproducible.

    This app's correctness rests on stable geometry-kernel output (parity and
    watertightness tests), so an unpinned dependency means a clean install months
    apart could silently produce different meshes.
    """
    unpinned = []
    for line in REQUIREMENTS.read_text().splitlines():
        line = line.split("#")[0].strip()
        if line and "==" not in line:
            unpinned.append(line)
    assert not unpinned, f"not pinned exactly: {unpinned}"
