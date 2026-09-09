"""Purpose: exercise reference discovery, public identities and drift refusals.

Guarantees: new modules, source edits, inherited protocols and independent
page/navigation defects reach the real generator [tested: this file;
commit=WORKTREE].
"""

from __future__ import annotations

import sys
from pathlib import Path

import griffe
import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "extensions/python/tools"))

import reference  # noqa: E402 -- this test exercises the checkout's tool


@pytest.fixture
def source_tree(tmp_path):
    """A package that refuses execution and exports an inherited class alias."""
    files = {
        "extensions/python/metta/__init__.py": (
            'from .facade import Child as Child\n__all__ = ["Child"]\n'
            'raise RuntimeError("documented source must not execute")\n'
        ),
        "extensions/python/metta/_implementation.py": '''\
from dataclasses import dataclass
from typing import overload

class Base:
    @property
    def name(self) -> str:
        """The inherited name."""
        return "name"

    def __enter__(self):
        """Enter the inherited protocol."""
        return self

    def run(self, value: str, *, limit: int = 2) -> str:
        """Original inherited documentation."""
        return value

@dataclass
class Actual(Base):
    """The exported child."""

    @overload
    def get(self, value: str) -> str: ...
    @overload
    def get(self, value: int) -> int: ...
    def get(self, value: str | int) -> str | int:
        """The implementation is documented once."""
        return value
''',
        "extensions/python/metta/facade.py": (
            'from ._implementation import Actual as Child\n__all__ = ["Child"]\n'
        ),
        "website/.vitepress/config.ts": (
            "          // begin generated reference navigation\n"
            "          // end generated reference navigation\n"
        ),
        "metta": "This executable is not the Python package.\n",
    }
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / "website/reference").mkdir()
    return tmp_path


def test_reference_discovers_exports_inheritance_and_new_modules(source_tree):
    """A new public module needs neither a pre-existing page nor a sidebar row."""
    assert reference.main(["--write"], root=source_tree) == 0
    page = source_tree / "website/reference/metta-facade.md"
    text = page.read_text()
    assert "## `Child`" in text
    assert "### `Child.name`" in text
    assert "### `Child.__enter__`" in text
    assert text.count("### `Child.get`") == 1
    assert "limit: int = 2" in text
    assert "Original inherited documentation." in text
    implementation = source_tree / "extensions/python/metta/_implementation.py"
    implementation.write_text(implementation.read_text().replace("limit: int = 2", "limit: int = 3")
                              .replace("Original inherited", "Changed inherited"))
    added = source_tree / "extensions/python/metta/added.py"
    added.write_text('def published() -> int:\n    """A new public function."""\n    return 1\n')
    assert reference.main([], root=source_tree) == 1
    assert reference.main(["--write"], root=source_tree) == 0
    assert reference.main([], root=source_tree) == 0
    assert "limit: int = 3" in page.read_text()
    assert "Changed inherited documentation." in page.read_text()
    assert "published" in (source_tree / "website/reference/metta-added.md").read_text()
    assert "metta-added" in (source_tree / "website/reference/index.md").read_text()
    assert "/reference/metta-added" in (source_tree / "website/.vitepress/config.ts").read_text()


def test_reference_detects_each_output_defect(source_tree):
    """Plant each API page, index and sidebar defect independently."""
    assert reference.main(["--write"], root=source_tree) == 0
    for path, pristine in reference.projections(source_tree).items():
        planted = (pristine.replace("// end generated reference navigation",
                                    '// planted\n          // end generated reference navigation')
                   if path.suffix == ".ts" else
                   pristine.replace("<!-- end generated reference index -->", "planted stale text\n<!-- end generated reference index -->")
                   if path.name == "index.md" else pristine + "\nplanted stale text\n")
        assert planted != pristine
        path.write_text(planted)
        try:
            assert reference.main([], root=source_tree) == 1, path
        finally:
            path.write_text(pristine)
    assert reference.main([], root=source_tree) == 0


def test_reference_refuses_an_unresolved_declared_export(source_tree):
    """A public alias cannot silently disappear when its implementation moves."""
    source = source_tree / "extensions/python/metta/facade.py"
    source.write_text('from ._implementation import Missing as Child\n__all__ = ["Child"]\n')
    with pytest.raises(griffe.AliasResolutionError, match="Missing"):
        reference.projections(source_tree)


def test_reference_keeps_the_source_of_a_callable_module(source_tree):
    """A Protocol annotation in a stub does not erase a real submodule."""
    core = source_tree / "extensions/python/metta"
    (core / "callable.py").write_text('def carrier() -> int:\n    """The carrier."""\n    return 1\n')
    (core / "__init__.pyi").write_text(
        'from typing import Protocol\nfrom .callable import carrier as carrier\n'
        'class _Callable(Protocol):\n    def __call__(self) -> int: ...\n'
        'callable: _Callable\n__all__ = ["carrier"]\n'
    )
    projections = reference.projections(source_tree)
    assert "## `carrier`" in projections[source_tree / "website/reference/metta.md"]
    assert "## `carrier`" in projections[source_tree / "website/reference/metta-callable.md"]
