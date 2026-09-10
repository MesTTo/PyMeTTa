"""Purpose: apply root conveniences to the default or ambient runtime context.

Guarantees: engine() creates one cached default context on first use; ordinary
imports create no runtime [tested: test_m7_satellites_are_lazy_and_identity_stable;
commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Owns resources: the process-default context retains its borrowed &self space;
temporary contexts remain the caller's responsibility [source:
extensions/python/metta/_spaces/ambient.py:50; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import collections.abc as _collections_abc
import functools as _functools
import importlib as _importlib
import os as _os
from collections.abc import Mapping as _Mapping
from typing import TYPE_CHECKING
from typing import Any as _Any
from typing import overload as _overload

from metta._atoms.factories import Atom, Expression, S, Symbol, parse
from metta._atoms.factories import unify as _unify_atoms
from metta._lazy import lazy
from metta.vocabularies import JournalSync

_OMITTED = object()

def _path_exists(path: str) -> bool:
    """Check a runtime path without importing pathlib into the narrow root."""
    return _os.path.exists(path)  # noqa: FURB141 -- pathlib adds eager imports to plain ``import metta``


def _resolve_metta_path() -> str:
    """Locate either the upstream or current bundled/source runtime tree."""
    env_path = _os.environ.get("METTA_PATH")
    if env_path:
        return _os.path.abspath(env_path)

    here = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    bundled = _os.path.join(here, "_runtime")
    if _path_exists(_os.path.join(bundled, "src", "main.pl")) or _path_exists(
        _os.path.join(bundled, "engine", "main.pl")
    ):
        return bundled

    return _os.path.abspath(_os.path.join(here, _os.pardir, _os.pardir, _os.pardir))


@_functools.cache
def engine() -> _root.MeTTa:
    """Return the process-default runtime context, creating it on first use.

    This is the one context whose home is the engine's own ``&self``; a bare
    ``MeTTa()`` is a fresh isolated context instead.
    """
    return lazy('metta._faces.metta').MeTTa(lazy('metta._faces.space').Space())


def space(
    name: str | Symbol | Expression | _root.Space | None = None,
    backing: _Any = None,
    *,
    inherits: _Any = None,
    restricted: bool = False,
    grants: _Any = (),
    journal: str | _os.PathLike[str] | None = None,
    schema: _Any = None,
    sync: JournalSync = JournalSync.none,
    rename: _Any = None,
):
    """Create or open a space; the backing value derives its implementation."""
    return engine().space(
        name,
        backing,
        inherits=inherits,
        restricted=restricted,
        grants=grants,
        journal=journal,
        schema=schema,
        sync=sync,
        rename=rename,
    )


def attach(name: str | Symbol, backing: _Any):
    """Attach a provider or remote URL through the unified creation function."""
    return space(name, backing=backing)


def current_space():
    """Return the ambient space selected by an enclosing space context."""
    from metta._spaces import handle  # noqa: PLC0415 -- a root import does not request a handle

    return handle.current_space()


def current_algebra() -> str | None:
    """Return the algebra selected for the current context, if one exists."""
    algebra_api = lazy("metta.algebra")
    return algebra_api.current_algebra()


def forms(source: str) -> list[Atom]:
    """Parse every top-level form without evaluating any of them.

    Use ``parse()`` when exactly one form is required. ``forms()`` returns one
    atom per top-level form and does not execute terms marked with ``!``.
    """
    source_forms = _importlib.import_module("metta._binding.positions")
    return [parse(form.text) for form in source_forms.positioned_forms(source)]


def llms() -> None:
    """Print `llms.txt`, the sheet that teaches this library, to stdout.

    The `help()` analogy is exact: it PRINTS and answers None, so the
    document is on stdout rather than in a string somebody still has to
    print. `llms.txt` is the whole language and library surface in one
    read, and it ships inside the wheel, so a checkout and an install
    print the same bytes and nobody has to find the source tree:

        python -c "import metta; metta.llms()"
        python -m metta llms          # the same document, from a shell

    Unlike `help()` this never pages. CPython's `license()` hands its text
    to `_pyrepl.pager.get_pager()`, which spawns `less` on a terminal; the
    reader here is usually a program with a pipe, for which that pager is
    already `sys.stdout.write`, and a library call that starts a pager is
    a surprise the one interactive reader can arrange for themselves.
    """
    path = _os.path.join(_resolve_metta_path(), "llms.txt")
    if not _path_exists(path):
        msg = (
            f"the cheat sheet is not at {path}; a checkout carries it at "
            f"llms.txt and a wheel carries it beside the engine tree"
        )
        raise FileNotFoundError(msg)
    # open() rather than Path.read_text() for the reason _path_exists gives:
    # pathlib adds eager imports to a plain ``import metta``.
    with open(path, encoding="utf-8") as sheet:
        print(sheet.read(), end="")


def stubs(space: _Any = None, *, sources: _collections_abc.Iterable[str | _os.PathLike[str]] = ()) -> str:
    """Return a space's declared heads as the text of a Python stub file.

    An arrow is a type, and a `.pyi` is where Python keeps the types of things
    with no runtime object to hang them on. One `def` per declared head with
    the arrow projected to annotations, one `class` per declared type, and each
    `(@doc ...)` as the docstring, so an editor completes a MeTTa program's
    heads and a checker refuses a call that passes the wrong thing:

        metta.load("geometry.metta")
        print(metta.stubs())                      # this context's own space
        print(metta.stubs(other, sources=["geometry.metta"]))

    `python -m metta stubs geometry.metta -o geometry.pyi` is the same
    generator from a shell. Without an argument it reads the space the active
    context selects; `sources` names the files the module docstring credits.
    """
    projection = lazy("metta._declare.stubs")
    return projection.stubs(_ambient_space() if space is None else space, sources=sources)


def _ambient_space():
    """Open the space selected by the active Python or engine context."""
    return engine().space(current_space())


@_overload
def unify(left: _Any, right: _Any) -> _Mapping[Atom, Atom] | None: ...


@_overload
def unify(left: _Any, right: _Any, then: _Any, els: _Any) -> _root.Answers[Atom]: ...


def unify(
    left: _Any,
    right: _Any,
    then: _Any = _OMITTED,
    els: _Any = _OMITTED,
) -> _Any:
    """Unify two atoms, or evaluate the four-argument engine conditional.

    ``unify(a, b)`` returns a symmetric bindings mapping or ``None`` without
    starting the engine. ``unify(a, b, then, els)`` evaluates
    ``(unify a b then els)`` in the ambient space, once per binding set on
    success and through ``els`` only when no binding exists. A compiled body
    lowers the same four-argument spelling directly to that engine form.
    """
    if then is els is _OMITTED:
        return _unify_atoms(left, right)
    if then is not _OMITTED and els is not _OMITTED:
        return _ambient_space().answers(S.unify(left, right, then, els))
    given = 3
    msg = f"unify() takes exactly 2 or 4 arguments ({given} given)"
    raise TypeError(msg)


def superpose(*alternatives: _Any):
    """Evaluate expression-position alternatives in the ambient space.

    With no alternatives this evaluates ``(empty)``. Inside a compiled
    definition the compiler lowers this same function spelling directly to
    ``(superpose (...))``.
    """
    target = S.empty() if not alternatives else S.superpose(Expression(alternatives))
    return _ambient_space().answers(target)


def accept(atom: _Any = _OMITTED) -> Expression:
    """Build a pre-add verdict that keeps or replaces the offered atom."""
    return S.accept() if atom is _OMITTED else S.accept(atom)


def refuse(words: _Any) -> Expression:
    """Build a pre-add verdict that rejects a write with the judge's words."""
    return S.refuse(words)


def drop() -> Expression:
    """Build a pre-add verdict that silently skips the offered atom."""
    return S.drop()


def under(algebra: _Any):
    """Scope the default algebra for match, call-answer, and fold carriers.

    The scope is task-local, nests with token restoration, and never mutates
    the catalog. An explicit ``under=`` on a carrier outranks this default.
    """
    scoped = _importlib.import_module("metta._spaces.scope")
    return scoped.ScopedUnder(algebra)

# Resolve annotations after definitions so peer imports can finish.

if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
