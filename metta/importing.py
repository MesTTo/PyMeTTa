"""Purpose: a `.metta` file is a Python module. `install()` puts a
`sys.meta_path` finder and its loader in place, so `import lib_list` finds
`lib_list.metta` on the search path, loads it into a space through the
engine's own `import!`, and answers a module whose attributes are the heads
that file declares. `importlib.reload(lib_list)` is that same `import!` under
Python's word: the digest reload withdraws the file's atoms and definitions
and replaces them, and the module's attributes answer the new bodies.
Assumes:
  - `import!` takes an absolute path atom, loads a file that is new or edited
    and skips one that is neither, and its withdrawal forgets a head the edit
    removed [source: engine/metta/interop.pl resolve_existing_import_path/3,
    import_when/4; engine/filereader/source_lifecycle.pl
    replacing_previous_load/4; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]
  - the import system consults `sys.meta_path` in order and stops at the first
    finder that answers a spec, so a finder appended after Python's own can
    never shadow a `.py` [source:
    https://docs.python.org/3.12/reference/import.html#the-meta-path]
  - `importlib.reload` re-runs `find_spec` and then `exec_module` over the
    SAME module object, and "its dictionary (containing the module's global
    variables) is retained", so what the previous load set survives until
    this loader overwrites or drops it [source:
    https://docs.python.org/3.12/library/importlib.html#importlib.reload]
Guarantees:
  - a `.metta` file on the search path imports as a module whose attributes
    are the heads it declares, each an `_EngineFunction` on the loading space
    that builds the same term `m.fn` builds for that head [tested:
    test_a_metta_file_imports_as_a_module_of_its_own_heads,
    test_a_module_attribute_and_the_namespace_build_one_term; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]
  - `importlib.reload` performs the digest reload: an edited file's new bodies
    answer, a head the edit removed leaves `__all__` and the module, and a
    head it added arrives [tested:
    test_reload_is_the_digest_reload_under_pythons_word; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]
  - a name that resolves to both a `.py` and a `.metta` on one search path is
    Python's, because the finder is appended and never prepended [tested:
    test_a_python_module_of_the_same_name_wins; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]
  - a file whose load fails raises `ImportError` chaining the engine's own
    error, and leaves no module behind [tested:
    test_a_file_that_cannot_load_raises_import_error; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]
  - a package advertising a directory under the `metta.libraries` entry-point
    group makes its own name importable, consulted only after the search path
    misses and only for that exact name [tested:
    test_a_package_declared_library_imports_by_its_declared_name; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]
Owns resources:
  - one `sys.meta_path` entry per `install()`, and the `sys.modules` entries
    the modules it loaded occupy. `Finder.uninstall()`, which the finder's own
    `with` block calls on every exit path, releases both; a module reference
    already held goes on working, because the space it reads is still there.
    An abandoned finder holds its space alive and answers imports until the
    process ends, which is what a process-wide hook means [tested:
    test_a_finder_is_a_value_installed_and_uninstalled,
    test_a_run_leaves_no_import_hook_behind; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]
Decides:
  - the hook is not installed by `import metta`. Changing how every `import`
    statement in a process resolves is the program's decision to make, not a
    library's to make on its behalf, which is the rule `pytest`'s plugins and
    `metta.integrate`'s entry points already follow: discovery answers names
    and registration stays an explicit call.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from ._api_types import SpaceLike
from ._declarations import declarations_in
from ._name_mapping import python_name
from ._source_forms import _source_text, positioned_forms
from ._space_objects import _format_doc_atom
from .atoms import Symbol, parse
from .errors import MettaError
from .integrate import LIBRARIES_GROUP, entry_points, load_entry_point

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from types import TracebackType

    from ._declarations import Declaration

__all__ = ["Finder", "Loader", "Module", "install", "installed"]

#: The suffixes a MeTTa source file has, in the order a directory is searched.
#: `.metta.gz` is the compressed form `import!` and the CLI already read under
#: the same name, so the finder recognises exactly what the engine loads
#: [source: engine/metta/interop.pl, ensure_metta_ext/2; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451].
SUFFIXES = (".metta", ".metta.gz")


def _candidates(root: Path, name: str) -> Iterable[Path]:
    """Where one directory could hold the source for one module name.

    The file beside the directory first, `rules.metta`, then the engine's own
    library layout, `rules/rules.metta`: a shipped library is a directory
    named for the library holding its surface, which is also the shape
    Python's own `FileFinder` gives a package in `<name>/__init__.py`
    [source: engine/metta.pl, library_within/2; commit=d7ab3cb20fe2353872139ecb36710f7e880c1451].
    """
    for suffix in SUFFIXES:
        yield root / f"{name}{suffix}"
    for suffix in SUFFIXES:
        yield root / name / f"{name}{suffix}"


def _in_directories(directories: Iterable[Any], name: str) -> str | None:
    """The first source file for `name` under these directories, or None.

    An entry that is not a path is skipped rather than refused, because
    `sys.path` carries whatever a program put there and the import system
    itself skips what it cannot read. An empty entry is the working
    directory, which is what `''` means on `sys.path`.
    """
    for entry in directories:
        if not isinstance(entry, (str, os.PathLike)):
            continue
        root = Path(entry)
        for candidate in _candidates(root, name):
            if candidate.is_file():
                return str(candidate.resolve())
    return None


def _file_rows(text: str) -> tuple[Declaration, ...]:
    """What the FILE declares, read with the engine's reader and nothing run.

    `declarations(space)` is the same projection over a space's store. The
    file's own is the one a module needs: `import!` unions its atoms into a
    space that already holds others, so the space cannot say which heads came
    from this file and the file can.

    One `parse` per non-runnable form. The crossing count is the form count,
    and it stays there: a door answering the reader's own terms for the whole
    file in one crossing measured 17,460 inferences against 13,831 for the 82
    forms of `lib/lib_pln/lib_pln.metta` parsed one at a time, because the
    atoms cross either way and only a RUNNABLE form's parse captures its
    variable names, so the whole-file terms arrive as `$_1 $_2` and pay to
    have those minted [measured 2026-09-07, three runs, no spread;
    commit=d7ab3cb20fe2353872139ecb36710f7e880c1451]. The projection is 13,831 inferences against the 34,441
    that same file's load costs, once per import.
    """
    forms = positioned_forms(text)
    return declarations_in(parse(form.text) for form in forms if form.kind != "runnable")


def _leading_comment(text: str) -> str | None:
    """The file's first comment block, its docstring when it documents no head.

    A Python module's docstring is its first string literal; MeTTa has no
    string literal in that position, and the comment block at the top of a
    file is where its authors already write the same paragraph. The block
    ends at the first line that is not a comment, so a comment above the
    first definition is that definition's, never the module's.
    """
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped and not lines:
            continue
        if not stripped.startswith(";"):
            break
        lines.append(stripped.lstrip(";").removeprefix(" "))
    return "\n".join(lines).strip() or None


def _module_doc(rows: Sequence[Declaration], name: str, text: str) -> str | None:
    """The file's own documentation: its doc atom, else its first comment block.

    `(@doc <module name> ...)` wins when the file documents itself, formatted
    the way `help()` formats a doc atom, so one `(@doc ...)` reads the same
    through every door.
    """
    for row in rows:
        if row.name == name and row.documentation is not None:
            return _format_doc_atom(row.documentation)
    return _leading_comment(text)


class Module(types.ModuleType):
    """The module a `.metta` file becomes.

    Its attributes are the heads the file declares, each the `_EngineFunction`
    the loading space's own `fn` namespace answers for that head, so
    `lib_list.length(...)` and `m.fn.length(...)` build the same term. A name
    the file does not declare falls through to that namespace too, under
    Python's underscore-to-hyphen map: `rules.car_atom` reaches `car-atom`
    whether or not this file wrote it, because the module reads a live space
    rather than a snapshot of one. `__all__` stays the file's own heads, which
    is what `from rules import *` takes and what `dir()` lists.

    No `__slots__`: a module IS its `__dict__`, which is where the heads go
    and where `sys.modules` and every tool reading `vars(module)` look.
    """

    def __getattr__(self, name: str) -> Any:
        """Resolve a name the file did not declare through the space itself."""
        space = self.__dict__.get("__metta_space__")
        if space is None or name.startswith("_"):
            raise AttributeError(name)
        try:
            return getattr(space.fn, name)
        except AttributeError as error:
            # The namespace's own refusal is the chained cause and carries the
            # remedy; what this adds is the module's side of the question,
            # which heads its FILE declares, since that is the set a reader of
            # `import rules` expects the name to be in.
            declared = ", ".join(self.__dict__.get("__all__", ())) or "no head"
            msg = (
                f"{self.__name__} has no {name!r}: {self.__file__} declares "
                f"{declared}, and {space.name} cannot call {name!r} either; "
                f"{space.name}.fn[...] is the exact-name door"
            )
            raise AttributeError(msg, name=name, obj=self) from error

    def __repr__(self) -> str:
        """Python's own module line, plus the space this one's heads answer in.

        A module whose load has not finished has no space yet, which is the
        state a traceback raised inside `exec_module` renders.
        """
        space = self.__dict__.get("__metta_space__")
        where = "no space yet" if space is None else space.name
        return f"<module {self.__name__!r} from {self.__file__!r} in {where}>"


class Loader(importlib.abc.Loader):
    """Loads one `.metta` file into one space, and populates its module.

    The load is `!(import! <space> <absolute path>)` and nothing else, so the
    module and `m += lib.x` and a `!(import! ...)` inside another file all go
    through the one loader with the one lifecycle: a file already loaded and
    unchanged is skipped, an edited one replaces what it put in every space
    holding it, and a load that raises leaves the previous definitions
    standing.
    """

    def __init__(self, origin: str, space: Any, finder: Finder) -> None:
        """Hold the file, the space it loads into, and the finder that made it."""
        self.origin = origin
        self.space = space
        self.finder = finder

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> Module:
        """Answer the module class that reads its space, not a plain one."""
        return Module(spec.name)

    def exec_module(self, module: types.ModuleType) -> None:
        """Load the file into the space, then say what the file declares.

        A reload arrives here with the module that was loaded before, so the
        names the previous load exported are dropped first: a head the edit
        removed must leave the module the way it left the space.
        """
        try:
            self.space.fn["import!"](self.space, Symbol(self.origin))
        except (MettaError, OSError) as error:
            msg = f"{module.__name__} could not load {self.origin}: {error}"
            raise ImportError(msg, name=module.__name__, path=self.origin) from error
        for stale in module.__dict__.get("__all__", ()):
            module.__dict__.pop(stale, None)
        # One read, for both the rows and the docstring the comment block can
        # supply, since the load has just read the same bytes itself.
        text = _source_text(self.origin)
        rows = _file_rows(text)
        exported: list[str] = []
        for row in rows:
            name = python_name(row.name)
            if name is None:
                continue
            try:
                # The space's own namespace decides: a head the file DECLARES
                # and never defines is a promise the space cannot answer, so
                # it is not an attribute and asking for it gets that
                # namespace's refusal with its remedy.
                head = self.space.fn[row.name]
            except AttributeError:
                continue
            module.__dict__[name] = head
            exported.append(name)
        # Through the dict, the way the heads went in: `__all__` and
        # `__metta_space__` are this module class's own attributes and a
        # plain `ModuleType` is what the loader protocol is handed.
        module.__dict__["__all__"] = exported
        module.__dict__["__metta_space__"] = self.space
        module.__doc__ = _module_doc(rows, module.__name__.rpartition(".")[2], text)

    def get_source(self, fullname: str) -> str:
        """The file's own text, which is what a traceback and `inspect` read."""
        del fullname
        return _source_text(self.origin)


class Finder(importlib.abc.MetaPathFinder):
    """Resolves an import name to a `.metta` file, for one space.

    The finder is APPENDED to `sys.meta_path`, so Python's own finders answer
    first and a name with both a `.py` and a `.metta` on the path is Python's.
    Its search is `path`, then `sys.path` read live, then the directory a
    package advertises for that exact name under `metta.libraries`.

    One finder names one space for its whole life. `sys.modules` is
    process-wide and answers a second `import lib_list` from its cache without
    consulting any finder, so a module could not belong to whichever space
    happened to be current; a second space loads the same file with
    `m += lib(S["path/to/file"])`, or through a finder of its own after this
    one is uninstalled.
    """

    def __init__(self, space: Any, path: Sequence[Any]) -> None:
        """Hold the space every import lands in and the directories searched first."""
        self.space = space
        self.path = tuple(path)

    @property
    def modules(self) -> dict[str, types.ModuleType]:
        """The modules in `sys.modules` this finder loaded, by name.

        Derived rather than recorded, so it cannot drift from what the import
        system actually holds: a module names its loader and a loader names
        its finder.
        """
        found = {}
        for name, module in list(sys.modules.items()):
            loader = getattr(getattr(module, "__spec__", None), "loader", None)
            if isinstance(loader, Loader) and loader.finder is self:
                found[name] = module
        return found

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: types.ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        """The spec for a `.metta` file with this name, or None to defer.

        `path` is the parent package's `__path__` for a submodule, which is
        the only place a submodule may come from: a `.metta` file has no
        `__path__` of its own, so `import rules.part` reaches a file only when
        `rules` is a Python package shipping one.
        """
        del target  # the module a reload will re-execute; this finder reads the file either way
        origin = self._resolve(fullname, path)
        if origin is None:
            return None
        return importlib.util.spec_from_file_location(
            fullname, origin, loader=Loader(origin, self.space, self)
        )

    def _resolve(self, fullname: str, path: Sequence[str] | None) -> str | None:
        """Which file this name names, under this finder's search."""
        tail = fullname.rpartition(".")[2]
        if path is not None:
            return _in_directories(path, tail)
        found = _in_directories([*self.path, *sys.path], tail)
        if found is not None:
            return found
        return self._declared(fullname)

    def _declared(self, fullname: str) -> str | None:
        """The file a package advertises for this exact name.

        Discovery is free and loads nothing: `entry_points` reads the
        installed metadata, and only a name that matches loads its own entry
        point to ask where the package keeps its sources.
        """
        if fullname not in entry_points(LIBRARIES_GROUP):
            return None
        try:
            directory = load_entry_point(fullname, group=LIBRARIES_GROUP)
        except MettaError as error:
            msg = (
                f"the {LIBRARIES_GROUP} entry point {fullname!r} could not "
                f"answer the directory its sources live in: {error}"
            )
            raise ImportError(msg, name=fullname) from error
        return _in_directories([directory], fullname)

    def uninstall(self) -> None:
        """Take this finder off `sys.meta_path` and forget what it loaded.

        The `sys.modules` entries go with it, because a module left behind
        would answer a later `import` from a finder that is no longer there
        and would fail `importlib.reload` with a spec nobody can find. A
        reference already held goes on working: its heads read a space, and
        the space is still there.
        """
        sys.meta_path[:] = [finder for finder in sys.meta_path if finder is not self]
        for name in self.modules:
            del sys.modules[name]

    def __enter__(self) -> Self:
        """Answer the finder; `install()` already put it in place."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Uninstall on every exit path.

        A hook installed for one program's run must not outlive that run.
        """
        self.uninstall()

    def __repr__(self) -> str:
        """The space this finder loads into, and the directories it looks in."""
        where = ", ".join(str(entry) for entry in self.path) or "sys.path"
        return f"<metta import finder for {self.space.name} over {where}>"


def install(space: SpaceLike | None = None, *, path: Any = None) -> Finder:
    """Make `.metta` files importable, and answer the finder that does it.

        with metta.importing.install(m):
            import lib_list                  # loads lib_list.metta into m

        finder = metta.importing.install()   # the ambient space, until uninstalled

    `space` is the space each imported file loads into, a context or a space,
    and defaults to the ambient one, resolved now rather than per import so
    the finder names one space for its whole life. `path` names directories
    searched BEFORE `sys.path`, the way `python script.py` puts the script's
    directory at the front without `sys.path` itself changing; one directory
    may be given bare, so `path="rules"` is `path=["rules"]`. The longhand of
    the whole door is `m += lib(S["rules/lib_list.metta"])`, which performs
    the same `import!` and answers no module.

    The finder is appended, so Python's own finders answer first. It is a
    context manager because a hook is process-wide: `uninstall()` is the
    explicit spelling and the `with` block is the one that cannot be
    forgotten.
    """
    if space is None:
        from . import _ambient_space  # noqa: PLC0415  -- root owns ambient scope

        space = _ambient_space()
    roots: Sequence[Any]
    if path is None:
        roots = ()
    elif isinstance(path, (str, os.PathLike)):
        roots = (path,)
    else:
        roots = tuple(path)
    finder = Finder(space.self, roots)
    sys.meta_path.append(finder)
    return finder


def installed() -> tuple[Finder, ...]:
    """Every finder this door has installed, in the order imports ask them.

    The list is `sys.meta_path` filtered, not a registry kept beside it, so a
    finder removed by hand is gone from here too.
    """
    return tuple(finder for finder in sys.meta_path if isinstance(finder, Finder))
