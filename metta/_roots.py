"""Purpose: answer where this checkout's roots are, without counting directory levels.

`Path(__file__).resolve().parents[N]` is a literal count of the levels between one
file and a root, and it is wrong the moment that file moves. There were 243 such
counts across 203 files at six different depths, and 167 of them resolved to just
two directories under ten different names: `ROOT`, `REPO`, `_REPO`, `root`, `_ROOT`,
`SEAT`, `BINDING_ROOT` and more [measured 2026-09-19]. The split made it worse rather
than better, because moving a file between components changes its depth.

A count is silent when it is wrong: the path simply points somewhere that does not
exist, and what fails is whatever reads it, far from the cause. The move to a
top-level `ext/` left five files counting to the old depth and cost 22 collection
errors and 12 setup errors before `_workspace.py` made that one count once.

So this does not centralise the count, it removes it. Both roots are DERIVED from
what they are:

  - a component is a distribution or a repository, so its root is the nearest
    ancestor holding a `pyproject.toml` or a `.git`. Both, because neither alone is
    enough: a Prolog component ships no `pyproject.toml`, and a tree copied without
    its history has no `.git`. The second case is not hypothetical, it is how every
    gate in this repository runs, in a worktree populated by `rsync` [measured
    2026-09-19: `tests/repository/test_roots.py` failed in exactly that tree when
    `.git` was the only marker];
  - the workspace is the thing that MOUNTS the components, so its root is the
    nearest ancestor holding both `engine/` and `lib/`. `.gitmodules` will not do:
    the Python seat has one of its own, for the examples corpus nested inside it.

Both fall back the way `runtime.py`'s own three-tier protocol already does, which
this follows rather than replaces: an explicit environment override first, because
an operator who says where the tree is outranks anything inferred; then the search;
and a wheel with no checkout at all raises rather than guessing, because a guessed
root is what silently reads the wrong tree.

Assumes: a checkout, or `METTA_WORKSPACE`/`METTA_PATH` naming one. An installed
  wheel has no workspace and asks for the bundled runtime instead, which
  `metta._binding.runtime` answers.
Guarantees:
  - `seat()` and `workspace()` answer the same directories the counts did, from any
    file at any depth, and keep answering after a file moves [tested:
    tests/repository/test_roots.py; commit=WORKTREE]
  - `workspace()` refuses rather than guessing when no checkout is above this file,
    naming the two environment variables that would settle it [tested:
    tests/repository/test_roots.py; commit=WORKTREE]
Fails when: a component is vendored with its `.git` stripped and no marker put in
  its place, where `seat()` answers the nearest ancestor that does have one.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

#: What the workspace IS: the directory that mounts the components. Named here
#: rather than counted anywhere, and checked as a pair because either alone
#: appears inside components too.
_MOUNTS = ("engine", "lib")

#: What a COMPONENT is, in either of the two ways a checkout can show it. A
#: `pyproject.toml` travels with a copied tree and a `.git` does not; a Prolog
#: component has the second and not the first.
_COMPONENT = ("pyproject.toml", ".git")


def _ascend(start: Path, holds) -> Path | None:
    """The nearest ancestor of `start`, itself included, for which `holds` is true."""
    for candidate in (start, *start.parents):
        if holds(candidate):
            return candidate
    return None


@cache
def seat(start: str | None = None) -> Path:
    """The component THIS package ships from, or the one above `start` when given.

    Without an argument it answers the seat, because that is where this module lives,
    and that is what a caller inside the seat means by "the repository". A caller
    elsewhere passes its own `__file__` and gets its own component. A submodule's
    `.git` is a FILE naming the real directory and a plain checkout's is a directory,
    so the test is existence rather than kind.
    """
    origin = Path(start).resolve() if start else Path(__file__).resolve()
    found = _ascend(origin.parent if origin.is_file() else origin,
                    lambda path: any((path / mark).exists() for mark in _COMPONENT))
    if found is None:
        message = (
            f"no component above {origin}: nothing holding a "
            f"{' or a '.join(_COMPONENT)}, which is what makes a directory one"
        )
        raise RuntimeError(message)
    return found


@cache
def workspace() -> Path:
    """The checkout that mounts the components, which holds both `engine/` and `lib/`."""
    for variable in ("METTA_WORKSPACE", "METTA_PATH"):
        configured = os.environ.get(variable)
        if configured:
            return Path(configured).resolve()
    found = _ascend(Path(__file__).resolve().parent,
                    lambda path: all((path / mount).is_dir() for mount in _MOUNTS))
    if found is None:
        message = (
            "no workspace above this package: nothing holding both "
            f"{' and '.join(_MOUNTS)}. An installed wheel has none and wants the "
            "bundled runtime instead; set METTA_WORKSPACE or METTA_PATH to name a checkout."
        )
        raise RuntimeError(message)
    return found
