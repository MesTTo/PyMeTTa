"""Purpose: what one shipped library says about itself.

A card is one query over the library's own sources with renderers over it.
A library card is a model card for a `lib_*`: what it is, which heads it
publishes and what each is declared, documented, classified and priced as,
which examples exercise it, what it needs from the platform, and the digest
that identifies the exact source all of that was read from. The section
mapping is Mitchell et al.'s, one to one -- model details to name, files,
version and digest; intended use to the prose and the head roster; factors to
the effect classes and the platform capabilities; metrics to the declared cost
classes; evaluation data to the examples that run under the gate; caveats to
the deprecation rows -- with training data and ethical considerations omitted
because a library has no counterpart to either
[source: https://arxiv.org/abs/1810.03993, "Model Cards for Model Reporting",
FAT* 2019, sections 4.1-4.9].

`rows()` is the query and `card()` is one renderer over it;
`extensions/python/tools/libdoc.py` is the other, which is what keeps a card
and the generated reference page from disagreeing about the same library.

Assumes:
  - the roster is `lib/*/lib_*.metta` and `lib/*/lib_*.pl` under the running
    engine's tree, the same discovery `dir(metta.lib)` lists
    [source: extensions/python/metta/_library.py, _library_source_files]
  - the engine answers which heads a form REGISTERS, so no spelling of
    `import_prolog_function` is written down here
    [source: engine/metta/interop.pl, metta_string_registrations/2]
Guarantees:
  - reading a library neither loads nor runs it: the sources are parsed, so a
    library whose Prolog half this build cannot load still describes itself,
    and asking for a card cannot register a head [tested:
    test_a_card_reads_a_library_without_running_it; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
  - a head published only through a runnable registration form is on the card
    and in the coverage count, which is the gap that reported lib_memo as
    empty while nine of its heads were callable [tested:
    test_a_card_lists_the_heads_a_registration_form_publishes; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
  - the effect class, cost class and deprecation of every head are the engine's
    own resolutions, read in ONE crossing for the whole roster, so a card and
    `(explain ...)` cannot answer differently [tested:
    test_a_card_carries_the_engines_own_effect_and_cost_answers; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
  - a name outside the roster refuses with the roster [tested:
    test_a_card_for_a_name_outside_the_roster_refuses_with_it; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
Fails when:
  - a library publishes heads through a form whose names are computed rather
    than written: the engine reports nothing for such a form and the card is
    short by those names, because the alternative is to guess.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import functools
import hashlib
import html
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._atom_namespace import _Namespace
from ._declarations import Declaration, Written, declarations, is_arrow
from ._engine import _resolve_metta_path, runtime
from ._library import _library_source_files
from ._name_mapping import generated_aliases
from ._source_forms import Origin, positioned_forms
from ._space_objects import _format_doc_atom
from ._version import __version__
from .atoms import Atom, Expression, Symbol, parse
from .errors import MettaError, Remedy

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

_LIBRARY = Symbol("library")
_IMPORT = Symbol("import!")

#: A `; Field: text` line of a source's own header block, which is where a
#: library says what it is. Only `Purpose` ends the summary early; the other
#: fields are the file contract rather than the library's description.
_FIELD = re.compile(r"^;+\s*([A-Z][A-Za-z ]*):\s*(.*)$")


def roster(root: str | os.PathLike[str] | None = None) -> dict[str, tuple[Path, ...]]:
    """Every shipped library, name to the source files that implement it.

        for name, files in metta.library.roster().items():
            print(name, len(files))

    The discovery is the runtime's own, so this roster, `dir(metta.lib)` and
    the generated reference page cannot name different libraries. `root`
    names an engine tree other than the running one.
    """
    known: dict[str, list[Path]] = {}
    for path in _library_source_files(_root(root)):
        known.setdefault(path.stem, []).append(path)
    return {name: tuple(sorted(files)) for name, files in sorted(known.items())}


def _root(root: str | os.PathLike[str] | None) -> str:
    """The engine tree to read, the running one unless another is named.

    A live runtime always has a tree; the fallback resolves the same one the
    runtime would have, so this answers before a boot as well as after
    [source: extensions/python/metta/_engine.py, _resolve_metta_path].
    """
    if root is not None:
        return os.fspath(root)
    return runtime().metta_path or _resolve_metta_path()


def _files(name: str, root: str | os.PathLike[str] | None) -> tuple[Path, ...]:
    """One library's source files, refusing a name the roster does not hold."""
    known = roster(root)
    files = known.get(name)
    if files is None:
        listed = ", ".join(known)
        msg = (
            f"{name!r} is not a shipped library. The roster is: {listed}. "
            f"A library outside the engine tree is imported by its path, "
            f"`m += lib(S['path/to/module'])`, and has no card"
        )
        raise MettaError(msg)
    written = [path for path in files if path.suffix == ".metta"]
    if len(written) > 1:
        # `(library lib_x)` resolves to ONE file, so two under the roster's
        # name are an ambiguity a description would silently pick a side in.
        joined = ", ".join(str(path) for path in written)
        msg = f"{name} has more than one MeTTa source: {joined}"
        raise MettaError(msg)
    return files


class LibrarySource:
    """One library's own sources, as a subject the declarations reader takes.

    It answers `written()` with every top-level form the engine's reader
    parses, in source order, each carrying the file and line it sits on and
    the head names the engine says that form registers. Nothing is loaded and
    nothing runs, which is what lets a library whose backend this build has
    not got still describe itself.

    Its longhand is the reader itself: `positioned_forms(text)` for the forms
    and `parse(form.text)` for each one's atom, which is what this composes.
    """

    __slots__ = ("_files",)

    def __init__(self, files: tuple[Path, ...]) -> None:
        """Hold one library's sources, in the order they will be read."""
        self._files = files

    @property
    def files(self) -> tuple[Path, ...]:
        """The sources read, in the order they are read."""
        return self._files

    def written(self) -> Iterator[Written]:
        """Every form of every file, with its position and what it registers."""
        for path in self._files:
            if path.suffix != ".metta":
                # A Prolog half declares its surface to the engine rather than
                # to this reader; `Card.needs` and `Card.since` read it through
                # the engine's own source scan.
                continue
            text = path.read_text(encoding="utf-8")
            forms = positioned_forms(text)
            registered: dict[int, list[str]] = {}
            for name, index in runtime().apply_must("metta_py_registrations", text):
                registered.setdefault(int(index), []).append(str(name))
            for index, form in enumerate(forms):
                origin = Origin(str(path), form.line)
                yield Written(
                    parse(form.text),
                    origin,
                    tuple(registered.get(index, ())),
                )


def rows(
    name: str, *, root: str | os.PathLike[str] | None = None
) -> tuple[Declaration, ...]:
    """One library's declaration rows, the query every renderer reads.

        for row in metta.library.rows("lib_he"):
            print(row.name, row.arrows, row.origin)

    One row per head the library declares, defines, documents or registers, in
    the order its sources first mention each. Sugar over
    `metta._declarations.declarations` applied to the library's own sources;
    `card()` renders these with what the live engine says about each head, and
    `tools/libdoc.py` renders them as the reference page.

    Cost: O(the library's source bytes), one crossing for the forms and one
    for the registrations per `.metta` file, plus one parse per form. Nothing
    is cached, so an edited library answers its new rows.
    """
    return declarations(LibrarySource(_files(name, root)))


def face(name: str, *, root: str | os.PathLike[str] | None = None) -> Any:
    """One library's heads as Python names, projected from its own rows.

        strategy = metta.library.face("lib_strategy")
        m += metta.lib.strategy
        m.eval(strategy.strategy_apply(strategy.try_(S.step), S.a))

    Every head the library declares, defines, documents or registers is an
    attribute here under Python's own casing of it, so `try_` reaches `try` and
    `stratego_all` reaches `stratego-all`; `face("lib_strategy")["◁"]` is the
    exact door for a head outside identifier grammar, and `dir()` lists what
    there is. A name the library does not declare refuses with the library's
    own roster, which is the whole reason to hold a face rather than to write
    `S["try"]`: the typo is caught on the line that makes the atom.

    Its longhand is `S[<head>]`, which mints the same symbol and checks
    nothing. The rung above is `m.fn[<head>]`, the LIVE namespace, which sees
    every head the running engine knows including the ones no library wrote:
    `id` is the engine's own identity operation and is not in `lib_strategy`'s
    face, because the library says in its own source that it does not define it.

    The face is the same `_Namespace` machinery `metta.fn` is, over one
    library's catalog instead of the engine's, with Python's operator words
    left OUT: they name engine heads, and a library that declared `add` itself
    would otherwise find `+` answering in its place. A head's `(@doc ...)`
    prose rides on the minted symbol, so `help(strategy.seq)` prints what the
    library wrote with no engine running.

    Cost: one `rows()` read per call, which is the library's source bytes.
    Nothing is cached, so an edited library answers its new heads; bind the
    result once rather than calling it in a loop.
    """
    heads = rows(name, root=root)
    aliases = generated_aliases([row.name for row in heads], operators=False)
    documentation = {
        row.name: _format_doc_atom(row.documentation)
        for row in heads
        if row.documentation is not None
    }
    return _Namespace(
        Symbol,
        allowed=frozenset(row.name for row in heads),
        aliases=aliases,
        documentation=documentation,
        label=f"{name} head",
        remedy=(
            f"; {name} declares "
            f"{', '.join(sorted(row.name for row in heads)) or 'nothing'}. A head "
            f"the running engine knows and this library does not write is "
            f"m.fn[<head>]"
        ),
        fix=Remedy(
            title=f"reach a head outside {name} through the live namespace",
            kind="quickfix",
            applicability="prose",
            python="m.fn['<head>']",
        ),
        operators=False,
    )


@dataclass(frozen=True)
class CostRow:
    """One head's declared cost class, as the engine resolved it.

    `measure` is what the size of `$n` means -- `int` for a number's value,
    `length` for an expression's children -- and comes from the row's own
    fourth field or from the head's arrow at the hole's position, which is the
    engine's derivation rather than a second one here
    [source: engine/metta/effects.pl, metta_cost_declaration/4].
    """

    head: str
    cost_class: str
    measure: str

    def __str__(self) -> str:
        """`nrev: quadratic in $n (length)`, the line a card prints."""
        return f"{self.head}: {self.cost_class} in $n ({self.measure})"


@dataclass(frozen=True)
class Deprecation:
    """One head's standing `(deprecated name since remedy)` row."""

    head: str
    since: str
    remedy: str

    def __str__(self) -> str:
        """`old-name: deprecated since 0.7.0, use new-name`."""
        return f"{self.head}: deprecated since {self.since}, use {self.remedy}"


@dataclass(frozen=True)
class HeadCard:
    """One head, as its library declares it and this engine classifies it.

    `arrow` is the type the library declares: an arrow for a function, which
    is the case the name is for, `Type` for a type it defines, a plain type
    for a value, and the LAST `(: ...)` row where a library writes more than
    one, which is the declaration a reader of the source ends up with. `doc`
    is the `(@doc ...)` prose formatted the way `help()` prints it. `effect`
    and `cost` are the live engine's answers and are None for a head it has
    not classified, which includes every head of a library this process has
    not imported.
    """

    name: str
    arrow: Atom | None = None
    doc: str | None = None
    effect: str | None = None
    cost: CostRow | None = None
    origin: Origin | None = None
    registered: bool = False

    @property
    def signature(self) -> str:
        """The head with its declared type, or the head alone."""
        return f"(: {self.name} {self.arrow})" if self.arrow is not None else self.name

    def __str__(self) -> str:
        """One line: the signature, then every classifier that answered."""
        parts = [self.signature]
        if self.effect is not None:
            parts.append(f"effect {self.effect}")
        if self.cost is not None:
            parts.append(f"cost {self.cost.cost_class} in $n ({self.cost.measure})")
        return "  ".join(parts)


@dataclass(frozen=True)
class Card:
    """Everything one shipped library says about itself.

        card = metta.library.card("lib_memo")
        print(card)
        for head in card.heads:
            print(head.name, head.effect)

    `digest` identifies the exact sources this was read from: the engine's own
    `metta_source_digest` of each file, sorted by path and joined with a
    newline, hashed as one document, so two checkouts agree exactly when every
    file agrees. `since` is the version the library declares for itself,
    falling back to the engine version that ships it. `needs` names the
    platform capabilities its sources declare; `metta.engine().info()` and the
    engine's own census say whether this build has them, which is what the
    rendered card notes beside a capability that is absent here.
    """

    name: str
    files: tuple[Path, ...]
    digest: str
    since: str
    doc: str | None
    heads: tuple[HeadCard, ...]
    effects: Mapping[str, str]
    costs: tuple[CostRow, ...]
    examples: tuple[Path, ...]
    deprecations: tuple[Deprecation, ...]
    needs: tuple[str, ...]

    @property
    def documented(self) -> tuple[HeadCard, ...]:
        """The heads that carry their own `(@doc ...)` prose."""
        return tuple(head for head in self.heads if head.doc is not None)

    def _absent(self) -> frozenset[str]:
        """Which of this card's needs this build has not got, asked now.

        A live question, so it is asked at render time rather than frozen into
        the card: the same card read in a build with `library(redis)` and in
        one without describes the same library and a different platform.
        """
        if not self.needs:
            return frozenset()
        row = runtime().once(
            "findall(_C, metta_platform_absent(_C), L)"
        )
        absent = {str(name) for name in row.get("L") or ()}
        return frozenset(need for need in self.needs if need in absent)

    def _lines(self) -> list[str]:
        """The card as text, one section a line, empty sections omitted."""
        absent = self._absent()
        needs = ", ".join(
            f"{need} (absent here)" if need in absent else need for need in self.needs
        )
        lines = [f"{self.name} {self.since}", f"  digest sha256:{self.digest}"]
        if self.doc:
            lines.append(f"  {self.doc}")
        lines.append("  files: " + ", ".join(path.name for path in self.files))
        if needs:
            lines.append(f"  needs: {needs}")
        if self.examples:
            lines.append(f"  examples: {len(self.examples)}")
        lines.extend(f"  {head}" for head in self.heads)
        lines.extend(f"  {row}" for row in self.deprecations)
        return lines

    def __str__(self) -> str:
        """The whole card as text, which is what `metta card` prints."""
        return "\n".join(self._lines())

    def __rich__(self):
        """A real table in rich-using terminals, one row per head.

        Only rich itself calls this, so the import cannot miss and a plain
        terminal never pays it; `str(card)` is the same content as lines.
        """
        from rich.table import Table  # noqa: PLC0415  rich's own protocol call

        absent = self._absent()
        caption = f"sha256:{self.digest}"
        if absent:
            caption += "  absent here: " + ", ".join(sorted(absent))
        table = Table("head", "type", "effect", "cost", title=self.name, caption=caption)
        for head in self.heads:
            table.add_row(
                head.name,
                "" if head.arrow is None else str(head.arrow),
                head.effect or "",
                "" if head.cost is None else f"{head.cost.cost_class} ({head.cost.measure})",
            )
        return table

    def _repr_html_(self) -> str:
        """Notebook display: the same table, every cell escaped."""
        absent = self._absent()
        header = "".join(
            f"<th>{column}</th>" for column in ("head", "type", "effect", "cost")
        )
        body = "".join(
            "<tr>"
            + "".join(
                f"<td>{html.escape(cell)}</td>"
                for cell in (
                    head.name,
                    "" if head.arrow is None else str(head.arrow),
                    head.effect or "",
                    ""
                    if head.cost is None
                    else f"{head.cost.cost_class} ({head.cost.measure})",
                )
            )
            + "</tr>"
            for head in self.heads
        )
        note = html.escape(
            f"{self.name} {self.since} sha256:{self.digest}"
            + ("  absent here: " + ", ".join(sorted(absent)) if absent else "")
        )
        return (
            "<table style='font-family: monospace; border-collapse: collapse;'>"
            f"<caption>{note}</caption><thead><tr>{header}</tr></thead>"
            f"<tbody>{body}</tbody></table>"
        )


def digest(name: str, *, root: str | os.PathLike[str] | None = None) -> str:
    """One library's content digest: its files' own digests, sorted and joined.

        metta.library.digest("lib_he")

    Each file's digest is the engine's `metta_source_digest`, which is the
    identity a reload compares, so a library whose every file is unchanged has
    an unchanged digest in any process and on any machine. Sugar over that
    predicate; the lock file writes exactly this value in its `[[library]]`
    rows.
    """
    return _digest_of(_files(name, root))


def _digest_of(files: tuple[Path, ...]) -> str:
    """The joined digest of a sorted file list, the one derivation."""
    engine = runtime()
    lines = sorted(
        f"{path}\t{engine.apply_must('metta_py_source_digest', str(path.resolve()))}"
        for path in files
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _summary(files: tuple[Path, ...]) -> str | None:
    """The library's own opening prose, or None when it opens with code.

    The first paragraph of the leading comment block of its MeTTa source,
    which is where every library that says what it is says it. A block opening
    with the file contract's `Purpose:` field ends at the next field, because
    the fields after it are the contract rather than the description.
    """
    for path in files:
        if path.suffix != ".metta":
            continue
        collected: list[str] = []
        purpose = False
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped and not collected:
                continue
            if not stripped.startswith(";"):
                break
            text = stripped.lstrip(";").strip()
            if not text:
                break
            field = _FIELD.match(stripped)
            if field is not None and collected:
                break
            if field is not None and field.group(1) == "Purpose":
                purpose = True
                text = field.group(2)
            elif field is not None and not purpose:
                break
            collected.append(text)
        return " ".join(collected) or None
    return None


def _declared(files: tuple[Path, ...]) -> tuple[str, tuple[str, ...]]:
    """The version and platform capabilities the Prolog half declares.

    Read through the engine's own source scan, which reads the directives and
    never consults the file, so a library needing a capability this build has
    not got still answers what it needs
    [source: engine/metta/interop.pl, metta_source_declarations/2].
    """
    version = __version__
    needs: list[str] = []
    engine = runtime()
    for path in files:
        if path.suffix != ".pl":
            continue
        for kind, value in engine.apply_must(
            "metta_py_source_declarations", str(path.resolve())
        ):
            if kind == "version":
                version = str(value)
            elif kind == "requires":
                needs.append(str(value))
    return version, tuple(sorted(set(needs)))


@functools.cache
def _example_imports(root: str) -> Mapping[str, tuple[Path, ...]]:
    """Which example programs import each library, built once per process.

    The corpus is read once and the index answers every card, because a card
    asking on its own would read 266 files for one answer. A file whose text
    does not contain the library's name cannot import it -- the module form
    spells the name literally -- so the scan parses only the candidates, which
    is what keeps the pass linear in the corpus bytes rather than a parse of
    every file [source: engine/metta/interop.pl, resolve_module_form/2 reads
    the same `(library Name)` form this recognises].
    """
    names = set(roster(root))
    found: dict[str, list[Path]] = {}
    corpus = sorted(Path(root, "examples").rglob("*.metta"))
    for path in corpus:
        text = path.read_text(encoding="utf-8")
        candidates = {name for name in names if name in text}
        if not candidates:
            continue
        for form in positioned_forms(text):
            for imported in _imported_libraries(parse(form.text)):
                if imported in candidates:
                    found.setdefault(imported, []).append(path)
    return {name: tuple(paths) for name, paths in found.items()}


def _imported_libraries(atom: Atom) -> Iterator[str]:
    """Every library name an `(import! <space> (library name ...))` form names.

    The walk is over the whole form because an import can sit inside a `let`
    or a `case` arm, and the shape it looks for is the module form the engine
    resolves rather than a spelling of this side's own.
    """
    if not isinstance(atom, Expression) or not atom.children:
        return
    if atom.children[0] == _IMPORT and len(atom.children) > 2:
        module = atom.children[2]
        if (
            isinstance(module, Expression)
            and len(module.children) > 1
            and module.children[0] == _LIBRARY
            and isinstance(module.children[1], Symbol)
        ):
            yield module.children[1].name
    for child in atom.children:
        yield from _imported_libraries(child)


def card(name: str, *, root: str | os.PathLike[str] | None = None) -> Card:
    """One shipped library's card: what it is, and what its heads are.

        print(metta.library.card("lib_memo"))
        python -m metta card lib_memo

    The heads and their documentation are read from the library's own sources
    and nothing is loaded; the effect class, cost class and deprecation of
    each head are what THIS engine currently answers, so a card taken after
    `m += lib.memo` can say more than one taken before it. Sugar over
    `rows()` for the first half and one `metta_py_head_claims` crossing for
    the second.

    Cost: O(the library's source bytes) for the rows, one crossing for every
    head's live claims, and, the first time any card is asked for, one pass
    over the example corpus to index which programs import which library.
    """
    files = _files(name, root)
    declared = rows(name, root=root)
    since, needs = _declared(files)
    claims = {
        str(row[0]): row[1:]
        for row in runtime().apply_must(
            "metta_py_head_claims", [row.name for row in declared]
        )
    }
    heads: list[HeadCard] = []
    effects: dict[str, str] = {}
    costs: list[CostRow] = []
    deprecations: list[Deprecation] = []
    for row in declared:
        effect, cost_class, measure, since_row, remedy = claims.get(
            row.name, (None, None, None, None, None)
        )
        cost = (
            CostRow(row.name, str(cost_class), str(measure))
            if cost_class is not None
            else None
        )
        if effect is not None:
            effects[row.name] = str(effect)
        if cost is not None:
            costs.append(cost)
        if since_row is not None:
            deprecations.append(
                Deprecation(row.name, str(since_row), str(remedy))
            )
        heads.append(
            HeadCard(
                name=row.name,
                arrow=row.types[-1] if row.types else None,
                doc=(
                    _format_doc_atom(row.documentation)
                    if row.documentation is not None
                    else None
                ),
                effect=None if effect is None else str(effect),
                cost=cost,
                origin=row.origin,
                registered=row.registered,
            )
        )
    return Card(
        name=name,
        files=files,
        digest=_digest_of(files),
        since=since,
        doc=_summary(files),
        heads=tuple(heads),
        effects=effects,
        costs=tuple(costs),
        examples=_example_imports(_root(root)).get(name, ()),
        deprecations=tuple(deprecations),
        needs=needs,
    )


__all__ = [
    "Card",
    "CostRow",
    "Declaration",
    "Deprecation",
    "HeadCard",
    "LibrarySource",
    "card",
    "digest",
    "face",
    "is_arrow",
    "roster",
    "rows",
]
