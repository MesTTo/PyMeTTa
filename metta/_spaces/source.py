"""Purpose: read, run and serialize program text with scoped hole bindings.

Guarantees: source() and text save() expose authored occurrences; reference
projections regenerate from their source rows [tested:
test_source_is_the_exact_round_trippable_text_save_view,
test_program_source_preserves_reference_cycles_and_lexical_bindings;
commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1].
"""

from __future__ import annotations

import html
import os
import re as _re
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import metta._spaces.execution as _spaces_execution_module
import metta._spaces.intents as _spaces_intents_module
import metta._spaces.scope as _spaces_scope_module
import metta._spaces.snapshot as _spaces_snapshot_module
import metta.doors as _doors
from metta._atoms.designation import TemplateLike
from metta._atoms.factories import Atom, _to_atom
from metta._atoms.factories import parse as _imported_parse
from metta._atoms.templates import apply as _apply_holes
from metta._atoms.templates import is_template as _is_template
from metta._atoms.templates import read_source as _read_source
from metta._atoms.templates import refuse_template as _refuse_template
from metta._errors.errors import Remedy
from metta._lazy import lazy
from metta.vocabularies import SaveFormat

_READER_PATTERN_FLAGS = (
    (_re.IGNORECASE, "i"),
    (_re.MULTILINE, "m"),
    (_re.DOTALL, "s"),
    (_re.VERBOSE, "x"),
)

_READER_PATTERN_SUPPORTED = _re.NOFLAG

for _reader_flag, _reader_letter in _READER_PATTERN_FLAGS:
    _READER_PATTERN_SUPPORTED |= _reader_flag

def _reader_pattern(pattern: str | _re.Pattern[str]) -> str:
    """Normalize Python's compiled regex contract to the engine's PCRE text."""
    if isinstance(pattern, str):
        return pattern
    if not isinstance(pattern, _re.Pattern):
        msg = f"a reader-token pattern is str or re.Pattern, not {type(pattern).__name__}"
        raise TypeError(msg)
    if not isinstance(pattern.pattern, str):
        msg = "a reader-token re.Pattern must compile text, not bytes"
        raise TypeError(msg)
    flags = _re.RegexFlag(pattern.flags) & ~_re.UNICODE
    unsupported = flags & ~_READER_PATTERN_SUPPORTED
    if unsupported:
        msg = (
            f"reader-token re.Pattern flags {unsupported!s} have no exact PCRE "
            "translation; use IGNORECASE, MULTILINE, DOTALL, VERBOSE, or "
            "write an inline PCRE pattern"
        )
        raise ValueError(msg)
    letters = "".join(
        letter for flag, letter in _READER_PATTERN_FLAGS if flags & flag
    )
    return f"(?{letters}){pattern.pattern}" if letters else pattern.pattern

def _require_source(source: Any, called: str) -> None:
    """Refuse non-text source here rather than at the engine's reader.

    The doors that CAN carry a hole's value take program text with holes
    instead of calling this. The one that cannot is run_status, whose engine
    door metta_host_run_source_status/3 takes no bindings argument, so a hole
    there would have nowhere to land and `bind()` does not reach it either
    [source: engine/filereader.pl:674, metta_host_run_source_status/3].
    """
    if isinstance(source, str):
        return
    if _is_template(source):
        msg = (
            f"{called} does not take program text with holes: the engine's "
            f"status door carries no bindings, which is also why bind() does "
            f"not reach it. Use run() for holes, and run_status() for plain "
            f"source."
        )
        raise TypeError(msg)
    msg = f"{called} takes MeTTa source as a string, got {source!r}"
    raise TypeError(msg)

def _with_holes(
    scope: dict[Any, Any] | None, holes: dict[str, Any] | None
) -> dict[Any, Any] | None:
    """One binding map from the surrounding bind() scope and this call's holes.

    A hole wins over a same-named scope entry, which cannot actually happen:
    the hole names are reserved and bind() refuses them. The order says which
    one would, rather than leaving it to dict iteration.
    """
    if not holes:
        return scope
    return {**(scope or {}), **holes}

def _held(target: Any, holes: dict[str, Any] | None, *, handed_on: bool) -> Any:
    """A target with its holes already in it, when this call hands it onward.

    The engine substitutes a binding pair once, at the door it was given to.
    A theory, an interpreter or a carrier makes this door ask ANOTHER door,
    sometimes lazily inside a generator, and a pair cannot follow a target
    through an arbitrary number of hand-offs; the value in the TERM can. So a
    delegating branch pays one reader crossing to put it there, and a plain
    branch keeps the cheaper pair, which is the same split match() and parse()
    sit on permanently.
    """
    return _apply_holes(_to_atom(target), holes) if handed_on and holes else target

@_doors.door(
    kind=_doors.Kind.evaluation,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.nondet,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_run_groups_answers_per_directive',),
    alias='run',
    binding=_doors.Binding('metta_py_run', _doors.Wire.goal),
)
def run(
    space: _root.Space,
    source: str | TemplateLike,
    /,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
    **values: Any,
) -> list[list[Atom]]:
    """Run MeTTa source: one list of answers per ! directive.

    The pipeline is the engine's own reader, compiler and evaluator, so
    the answers are exactly what the CLI would print, kept grouped per
    directive instead of flattened. Equations and facts in the source
    land in this space.

    The source may carry HOLES, which are bindings by position:

        m.run(t"!(fib {n})")            # a 3.14 t-string literal
        m.run("!(fib {n})", n=10)       # the same on every version

    Each hole is spliced into the text as a generated symbol and bound to
    its value, so a str stays one String atom and never has to be escaped.
    Values enter through `encode`: an int is a Number, a str a String, an
    Atom itself, a Space its handle. The markers at a hole are the atom
    constructors, `{Symbol(name)}`, `{Grounded(obj)}` and `{parse(text)}`,
    with the specs `:sym`, `:py` and `:expr` as their short forms; `!r`
    and `!s` convert in Python first and enter the result as text. A hole
    inside a string literal, a comment or a symbol is refused with its
    line and column.

    `bind()` is the same substitution by NAME, for a value several calls
    share, the way DuckDB reads a local dataframe by its variable name:

        with m.bind({"graph": my_graph}):
            m.run("!(py-len graph)")

    Each named symbol substitutes to its value (objects by identity),
    after reading, before anything runs. It is a BLOCK rather than a
    keyword because a binding mapping is the kind of value that grows,
    and a block grows down the page where a keyword has to fit beside
    everything else on the call. Every call that accepts a target reads the
    same scope, so one block covers run(), eval(), and answers() together.
    A binding names a symbol and so replaces EVERY occurrence of it,
    including one the author meant as a symbol; a hole is positional and
    cannot reach anything but itself.

    `timeout` (seconds) and `inferences` (engine steps) bound the call
    with the engine's own guards; passing either raises TimeLimitError
    or InferenceLimitError when the bound is hit, and whatever the
    source completed before the stop, writes included, stands.

    `with m.capture() as output` collects printed text in `output.text`
    without changing this method's return shape. `with m.atomic()`
    and `with m.speculative()` scope execution policy without boolean
    combinations on each call. Atomic commits or rolls
    back each complete source; speculative answers and discards its
    writes. Both cover engine state; Python side effects and subscription
    callbacks already fired stay where they happened.

    A term the engine hands back unevaluated is an ordinary MeTTa value,
    not a failure: `!(hello world)` answers `(hello world)` and that is
    the whole of hello world in this language. eval_status() reports
    which answers reduced and which did not, as data, for a caller who
    wants to decide about it.
    """
    source, holes = _read_source(
        source, values, called="run", reserved=_spaces_execution_module._SOURCE_KEYWORDS
    )
    _spaces_intents_module.record_sync_engine_call(space, "run", sys._getframe(1))
    try:
        return _spaces_execution_module.run_source(
            space._rt,
            space._space,
            source,
            _with_holes(_spaces_scope_module._RUN_BINDINGS.get(), holes),
            timeout=timeout,
            inferences=inferences,
        )
    finally:
        lazy('metta._declare.functions')._invalidate_builtins_cache(space._rt)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.integer,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_a_specialized_program_saves_and_digests', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_save_keeps_every_number_it_accepts', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_save_keeps_every_symbol_it_accepts'),
)
def save(
    space: _root.Space,
    path: str | os.PathLike[str],
    *,
    format: SaveFormat = SaveFormat.metta,  # noqa: A002  -- format is the documented public save keyword
    timeout: float | None = None,
    inferences: int | None = None,
) -> int:
    """Write the authored atoms of this space, equations included, as
    MeTTa source by default. ``format="fast"`` writes a version-pinned
    image of the receiver's equation world: its own atoms, owned child
    spaces, aliases bound to those spaces, and translator rules. Loading
    the image mints fresh runtime space identities and preserves their
    graph relationships. The returned count remains the receiver's own
    authored atom count. Reference projections are regenerated from their
    source rows. Text variables are numbered by first occurrence within
    each atom, so saving unchanged content twice is byte-stable. A path
    ending .gz writes gzip compressed in either format, and load and
    import! read it back under the same name. The completed sibling file
    is synced and then atomically replaces the target, so a failed save
    leaves the old file intact. Atoms carrying live host objects cannot
    survive either file and are refused.

    `timeout` (seconds) and `inferences` (engine steps) bound the save with
    the engine's own guards, exactly as they bound load(). A text save
    examines the receiver; a fast save also traverses its reachable
    equation-world graph and registries. Those guards therefore bound all
    state the chosen format writes, and the atomic replace above makes a
    stopped save safe: the sibling is never moved into place.

    There is no `format` on load(), and that is not an omission. When you
    save, the file does not exist and something has to say which of the two
    to write; when you load, load() reads which it is, `.gz` included.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return _spaces_snapshot_module.save_space(
        space._rt,
        space._space,
        path,
        format,
        timeout=timeout,
        inferences=inferences,
    )

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.text,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch18_performance/test_fast_bindings.py::test_fast_images_preserve_each_equations_binding',),
)
def source(space: _root.Space) -> str:
    """Return this space's authored atoms as loadable MeTTa text.

    This is exactly the text that ``save(path, format="metta")`` writes:
    one atom per line, including equations, with a final newline when the
    space is nonempty. Variables are numbered by first occurrence within
    each atom, making independent views of unchanged content byte-stable.
    Inherited prelude and library atoms, the global
    ``&metta`` catalog, and child spaces are outside that save boundary.
    A reference row stays in the source; its projected declarations and
    documentation are regenerated when that row loads.
    Live host objects and atoms whose printed form cannot round-trip are
    refused for the same reason a text save refuses them.
    """
    return _spaces_snapshot_module.source_space(space._rt, space._space)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_, _doors.Tier.module, _doors.Tier.context),
    evidence=('extensions/python/tests/ch01_getting_started/test_lock.py::test_a_lock_refuses_while_a_load_is_in_flight', 'extensions/python/tests/ch04_spaces_and_matching/test_digest.py::test_a_second_load_of_a_specialized_program_still_round_trips', 'extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_load_adds_to_existing_space'),
    alias='load',
)
def load(
    space: _root.Space,
    path: str | os.PathLike[str],
    *,
    timeout: float | None = None,
    inferences: int | None = None,
) -> list[list[Atom]]:
    """Add a text program or trusted fast cache to this space.

    This is a consult, so it always loads and what it loads REPLACES
    what the same file put in this space before. Edit the file, load it
    again, and the space holds the new definitions and not both; the
    engine says on stderr which file it replaced and how many atoms
    went. Atoms from other sources, and ones you added yourself, stay.
    A load that raises leaves the previous definitions standing, so a
    broken edit costs nothing but the error.

    `!(import! &self path)` is the other form and loads a file that is
    new or edited, skipping one that is neither. The two agree on what
    a reload means and differ only in whether an unchanged file runs
    again, which is SWI's consult/1 against its if(changed).

    A .gz path is detected and read through the decompressed bytes.

    `timeout` (seconds) and `inferences` (engine steps) bound the load
    with the engine's own guards, raising TimeLimitError or
    InferenceLimitError. A load is all or nothing: a stop takes back
    everything the file had put in a space, the same way a load that
    fails on a bad form does, because a file the space holds half of is
    not a file it can replace later. run() is the entry point that
    keeps finished work when a bound stops it. This is the one most
    likely to be handed code the caller did not write, since a file can
    carry `!` directives and an import graph, so it takes the same pair
    its siblings take.

    Program text with holes is refused here. A hole is a binding, and a
    PATH has nowhere to bind one: run() takes holes, and an f-string or a
    Path builds a computed filename.
    """
    _refuse_template(
        path,
        "load",
        "it takes a PATH, and a hole is a binding a filename has nowhere "
        "to put. Use run() for program text with holes, or an f-string "
        "for a computed path.",
        Remedy(
            "run() takes program text with holes; an f-string builds a "
            "computed path",
            "quickfix",
            "prose",
            python="m.run(t'(= (f $x) {value})')",
        ),
    )
    try:
        return _spaces_snapshot_module.load_space(
            space._rt, space._space, path, timeout=timeout, inferences=inferences
        )
    finally:
        lazy('metta._declare.functions')._invalidate_builtins_cache(space._rt)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.atom,
    effect=_doors.EffectClass.oracleIO,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_registered_token_class_parses_like_a_shipped_one', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_token_constructor_failure_is_a_reader_error_not_a_symbol_fallback'),
    binding=_doors.Binding('metta_py_parse', _doors.Wire.goal),
)
def parse(_space: _root.Space, source: str | TemplateLike, /, **values: Any) -> Atom:
    """Read one form into an atom without evaluating it.

    Holes work here as they do at run(), and land in the term this
    answers rather than crossing to the engine, since nothing runs:
    `m.parse(t"(person {name} 36)")` is the built term with the value
    already in it.
    """
    return _imported_parse(source, **values)

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.none,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_registered_token_class_parses_like_a_shipped_one', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_compiled_reader_patterns_preserve_flags_and_unregister', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_token_constructor_failure_is_a_reader_error_not_a_symbol_fallback'),
    binding=_doors.Binding('metta_py_register_token', _doors.Wire.goal),
    refuses=(_doors.Refusal(_doors.RefusalKind.type, 'extensions/python/tests/repository/test_door_refusals.py::test_door_type_refusals[space:register-token]'),),
)
def register_token(
    space: _root.Space,
    pattern: str | _re.Pattern[str],
    constructor: Callable[[str], Any],
) -> None:
    """Register a full-token regex and its Atom constructor.

    The constructor receives the complete matched lexeme. It may return an
    Atom or any value accepted by :func:`metta.ground`. A later registration
    of the same pattern replaces the constructor. Only future parses read
    the new mapping; atoms already returned are immutable values.
    """
    normalized = _reader_pattern(pattern)
    if not callable(constructor):
        msg = "a reader-token constructor must be callable"
        raise TypeError(msg)
    space._rt.must(
        "metta_py_register_token(Pattern, Constructor)",
        Pattern=normalized,
        Constructor=constructor,
    )

@_doors.door(
    kind=_doors.Kind.provider,
    answers=_doors.AnswersAs.none,
    effect=_doors.EffectClass.writesState,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_compiled_reader_patterns_preserve_flags_and_unregister', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_registered_token_class_parses_like_a_shipped_one', 'extensions/python/tests/ch03_atoms_and_expressions/test_reader_tokens.py::test_a_token_constructor_failure_is_a_reader_error_not_a_symbol_fallback'),
    binding=_doors.Binding('metta_py_unregister_token', _doors.Wire.goal),
)
def unregister_token(space: _root.Space, pattern: str | _re.Pattern[str]) -> None:
    """Remove a reader-token class; an absent pattern is already removed."""
    space._rt.must(
        "metta_py_unregister_token(Pattern)", Pattern=_reader_pattern(pattern)
    )


@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.text,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync,),
    evidence=('extensions/python/tests/ch18_performance/test_fast_io.py::test_source_is_the_exact_round_trippable_text_save_view',),
    async_excluded='notebook display is a synchronous protocol; an async view reads its materialized result',
)
def _repr_html_(space: _root.Space) -> str:
    """Show this space's loadable MeTTa source in rich notebooks."""
    return f"<pre>{html.escape(source(space))}</pre>"

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
