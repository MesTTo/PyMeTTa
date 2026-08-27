"""Purpose: the library namespace and its import handles. A library IS
knowledge, so the write door imports it: `m += lib.he` performs
`!(import! <m> (library lib_he))` with the receiver as the target space,
which is why no `&self` symbol and no new verb appears anywhere.
Assumes:
  - the engine's `'import!'/3` resolves `(library Name)`,
    `(library Alias Inner)`, and bare path atoms, skips an unchanged
    already-imported module, and refuses a missing one with
    existence_error(source_sink) [source: engine/metta/interop.pl,
    resolve_module_form/2 and importer_helper/2;
    commit=e58229e98b31843c14507003dc83bf6bce127121].
Guarantees:
  - `lib.he` names the shipped library `lib_he`: the attribute map is the
    `lib_` family prefix with underscores KEPT, never the hyphen map,
    because a library is a FILE name (`S.lib_he` is the atom `lib-he`,
    which no library answers) [tested: test_the_attribute_map_is_the_family_prefix]
  - `lib["minimal_metta_lib"]` is the exact-name door for a library
    outside the family, `lib.x.part` is the two-argument
    `(library x part)` form, and `lib(S["path/to/module"])` is the
    exact-module-form escape for a path import: the path is an ATOM the
    engine resolves by its own rules (the importing file, the repo root
    for a host program), never against the host's working directory, so
    it takes the same S[...] bracket every unspeakable name takes
    (user-ruled 2026-08-25); str and os.PathLike stay accepted one rung
    down [tested: test_the_exact_doors_build_the_engine_forms]
  - a handle refuses every atom position: encoding one raises with the
    import spelling as the remedy, so a library can never silently become
    an opaque grounded box inside a stored term
    [tested: test_a_library_handle_refuses_atom_positions]
Fails when:
  - the import must run inside an atom batch: an import is an effect and a
    batch is one deferred bulk write, so the write door refuses the mix
    loudly rather than reorder either.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import keyword
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._atoms_core import Atom, Expression, Symbol, _encode_value

if TYPE_CHECKING:
    from ._space import Space

_LIBRARY = Symbol("library")


def _attribute_safe(suffix: str) -> bool:
    """Whether a family suffix can be a dotted attribute, the same safety
    generated_aliases/1 applies to closed namespaces (identifier, not a
    keyword, no leading underscore, lowercase ASCII); an unsafe suffix stays
    bracket-reachable [source: metta/_name_mapping.py, generated_aliases].
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return (
        suffix.isidentifier()
        and not keyword.iskeyword(suffix)
        and not suffix.startswith("_")
        and suffix == suffix.lower()
        and suffix.isascii()
    )


class Library:
    """One module form `import!` resolves, held as the atom it will cross as.

    `m += handle` performs the import into `m`. The handle itself is not an
    atom: it names an ACT, and the write door is where the act happens.
    """

    __slots__ = ("_form", "_spelling")

    # Declared for the type checker: with __getattr__ defined, an
    # unannotated slot read would resolve through it and type as Library.
    _form: Atom
    _spelling: str

    def __init__(self, form: Atom, spelling: str) -> None:
        object.__setattr__(self, "_form", form)
        object.__setattr__(self, "_spelling", spelling)

    @property
    def form(self) -> Atom:
        """The module-form atom `import!` receives."""
        return self._form

    def __getattr__(self, part: str) -> Library:
        """`lib.x.part` is the two-argument `(library x part)` form: a
        registered alias and a file inside it. The part is a file name and
        stays exact. Only a one-argument library has files inside it.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if part.startswith("_"):
            raise AttributeError(part)
        form = self._form
        if (
            not isinstance(form, Expression)
            or len(form.children) != 2
            or form.children[0] != _LIBRARY
        ):
            msg = (
                f"{self._spelling} does not contain files: only a "
                f"one-argument library form has a `(library alias inner)` "
                f"two-argument spelling"
            )
            raise TypeError(msg)
        inner = Expression((_LIBRARY, form.children[1], Symbol(part)))
        return Library(inner, f"{self._spelling}.{part}")

    def __setattr__(self, name: str, value: Any) -> None:
        msg = f"{self._spelling} is a library handle and holds nothing"
        raise AttributeError(msg)

    def __repr__(self) -> str:
        return self._spelling

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Library) and self._form == other._form

    def __hash__(self) -> int:
        return hash((Library, self._form))


@_encode_value.register
def _(value: Library) -> Atom:
    # Loud by design: without this a handle inside a stored term would fall
    # to the opaque-object default and become a grounded box, silently.
    msg = (
        f"{value!r} is a library handle, not an atom: `m += {value!r}` "
        f"imports it, and inside a term the library is named by its own "
        f"symbol"
    )
    raise TypeError(msg)


class _LibraryNamespace:
    """`lib.he` is the shipped library `lib_he`; brackets and calls are the
    exact doors, one rung down each: `lib["minimal_metta_lib"]` for an exact
    library name outside the `lib_` family, `lib(S["path/to/module"])` for
    an exact module form such as a source path, named by its atom.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ()

    def __getattr__(self, name: str) -> Library:
        if name.startswith("_"):
            raise AttributeError(name)
        return self[f"lib_{name}"]

    def __getitem__(self, exact: str) -> Library:
        # The dotted spelling only exists where Python can say it: lib_import
        # strips to the keyword `import`, so its handle keeps the bracket.
        suffix = exact[4:] if exact.startswith("lib_") else None
        dotted = suffix is not None and _attribute_safe(suffix)
        spelling = f"lib.{suffix}" if dotted else f'lib["{exact}"]'
        return Library(Expression((_LIBRARY, Symbol(exact))), spelling)

    def __call__(self, module: str | os.PathLike[str] | Atom) -> Library:
        if isinstance(module, Atom):
            return Library(module, f"lib({module!r})")
        path = str(module)
        return Library(Symbol(path), f"lib({path!r})")

    def __dir__(self) -> list[str]:
        """The shipped catalog, read from the engine tree's own lib/
        directory rather than a hand-list; family names appear in their
        attribute spelling and out-of-family ones stay bracket-reachable.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        # Lazy on purpose: `import metta` must not import the engine
        # module, and dir() is interactive, so the cost lands only where
        # a person is already exploring
        # [tested: test_the_fn_namespace_is_generated].
        from ._engine import (  # noqa: PLC0415  -- the import-lightness contract above
            _STATE,
            _resolve_metta_path,
        )

        active = getattr(_STATE, "runtime", None)
        root = active.metta_path if active is not None else _resolve_metta_path()
        names = set()
        # A shipped library is a DIRECTORY under lib/ named for the library,
        # holding its MeTTa surface beside the Prolog it rides on, so the
        # source files are one level down [source: engine/metta.pl:library_within/2].
        for entry in Path(root, "lib").glob("*/*"):
            stem = entry.stem
            # policy-inventory-exempt: mechanism-internal; reason=the two source suffixes a shipped library file can have, the catalog filter rather than an operator policy; evidence=engine/metta/interop.pl:resolve_module_form/2
            if entry.suffix in {".metta", ".pl"} and stem.startswith("lib_"):
                suffix = stem[4:]
                if _attribute_safe(suffix):
                    names.add(suffix)
        return sorted(names)


lib = _LibraryNamespace()


def import_library(space: Space, handle: Library) -> None:
    """Perform `!(import! <space> <form>)`: the receiver is the target."""
    space.fn["import!"](space, handle.form)
