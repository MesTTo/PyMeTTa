"""Purpose: expose MeTTa's narrow Python core and lazily load satellites.

Assumes:
  - ``metta._space.MeTTa`` owns runtime context and ``metta._space.Space``
    owns storage and query verbs [source:
    extensions/python/metta/_space.py:306 and :3090; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Guarantees:
  - the R5 root exports the term builders, relational solve, and lazy State
    handle while ``record`` and atom-specialist ``order_key`` stay absent
    [tested: test_m7_narrow_core_surface,
    test_solve_retires_the_five_relational_let_workarounds,
    test_keyword_builders_retire_53_raw_if_mentions, and
    test_state_retires_three_state_function_strings; commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - ``dir(metta)`` is exactly the curated public surface and loads no
    satellites [tested: test_m7_narrow_core_surface; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - satellite modules are imported only by attribute access, following PEP
    562 with their real module identity intact [tested:
    test_m7_satellites_are_lazy_and_identity_stable; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``space()`` is the only space-creation function and cannot be overwritten by
    an implementation submodule [tested: test_m7_space_factory_keeps_identity;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - ``space()`` accepts both text and a space-name Symbol returned by the
    engine [tested: test_space_factory_accepts_a_name_symbol; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - ``fn`` is an inert, generated, statically typed mention namespace and
    importing it never starts the engine [tested:
    test_the_fn_namespace_is_generated; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - package ``match`` reads the default space while ``superpose`` evaluates
    its expression form; compiled definitions lower their syntactic match
    calls before either Python function executes [tested:
    test_module_tier_exposes_the_mode_and_definition_family; commit=b2527d32dc851615e6cf1e11c94ac017d4e78c86]
  - ``unify`` keeps the symmetric two-atom matcher at arity two and evaluates
    the engine's conditional form at arity four [tested:
    test_expression_position_unify_uses_the_engine_conditional_in_both_contexts;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - ``view`` lazily opens a live provider space over Python mappings, sets,
    and sequences [tested: test_view_is_a_live_queryable_space;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - the root exports ``seg``, the named segment builder, beside the ``...``
    spelling Python already has [tested: test_seg_builds_a_named_segment;
    commit=a3dff3abc83b9d82f3652093246e1d693d526cdb]
  - coordination functions are lazy satellite exports and Timeout remains
    catchable as builtin TimeoutError [tested:
    test_the_coordination_family_is_python_shaped; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - module define/stats/limits/trace verbs defer engine creation
    until called and target the default self space [tested:
    test_module_tier_exposes_the_mode_and_definition_family; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - ``op`` forwards unchanged to the lazy default receiver and therefore keeps
    its required five-rank ``effect=`` contract [tested:
    test_module_tier_op_forwards_identity_to_the_default_receiver,
    test_module_tier_op_registration_precedes_definition_compilation;
    commit=fc7ec0b08cd8b5876a3f4105211c487185f6a9bf]
  - ``py(expr)`` is an identity in ordinary Python and the exact visible marker
    the definition compiler recognizes for an inline host island [tested:
    test_py_is_identity_outside_a_compiled_body,
    test_py_host_island_executes_per_engine_application; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - under scopes an algebra through ContextVar state and the exact counting,
    tropical, probability, provenance, and ranking carriers stay lazy root
    exports [tested:
    test_scoped_under_is_task_local_and_explicit_under_wins,
    test_requested_carrier_spellings_are_declared; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - ``speculate()`` is the exact module-tier spelling for the default
    receiver's discarded execution scope [tested:
    test_speculative_execution_discards_its_event_segment; commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - ``strategies`` is a lazy satellite whose exports are reified Symbols rather
    than promoted root callbacks [tested:
    test_m7_satellites_are_lazy_and_identity_stable and
    test_strategy_exports_are_reified_atoms; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa]
  - ``catalog`` names the queryable ``&metta`` space and ``fresh()`` supplies
    hygienic variables for helper-authored patterns [tested:
    test_catalog_is_the_root_queryable_reflection_space and
    test_fresh_variables_keep_library_patterns_hygienic; commit=46ae646e5efe14320c01e1e110d9cfd6cd0fc7e1]
  - ``forms`` reads every top-level form without evaluation and is explicitly
    distinct from singular ``parse`` [tested:
    test_forms_reads_a_whole_source_without_running_it,
    test_the_reader_docstrings_cross_reference_each_other;
    commit=9c03403aaaca9f1a1ec52e5898dd547eb80c8e82]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""
# The generated module functions carry Space's own parameter names, and two of
# them (fn, under) are also module objects; inside a function the parameter is
# the meaning, which is the point.
# pylint: disable=redefined-outer-name


from __future__ import annotations

import builtins as _builtins
import functools as _functools
import importlib as _importlib
import os as _os
from collections.abc import Mapping as _Mapping
from typing import TYPE_CHECKING
from typing import Any as _Any
from typing import overload as _overload

if TYPE_CHECKING:
    from collections.abc import Callable as _Callable
    from collections.abc import Iterable as _Iterable
    from typing import Literal as _Literal

    # The static faces of _LAZY_ATTRIBUTES below, name for name: the lazy
    # __getattr__ keeps `import metta` narrow at runtime, and without these
    # a checker types every root export Any, py.typed notwithstanding.
    from ._rules import equation, rules
    from ._space import _P, _R, MeTTa, Space
    from ._space_execution import ScopedExecution as _ScopedExecution
    from ._space_objects import ScopedLimits as _ScopedLimits
    from ._space_objects import _StatsBlock
    from ._state import State
    from .algebra import counting, prob, prov, ranked, tropical
    from .answer import Answer, Bindings
    from .define import Defined
    from .define import Defined as _Defined
    from .define import PrologBacked as _PrologBacked
    from .foreign import SpaceProvider
    from .manifest import boot
    from .parallel import channel, every, par_map, race, spawn
    from .results import Answers as _Answers
    from .spaces import view
    from .vocabularies import EffectClass as _EffectClass

from ._config import Config, config
from ._fn import fn
from ._host_island import py
from ._library import Library, lib
from ._under import _UNSET
from ._version import __version__
from .atoms import (
    FALSE,
    TRUE,
    UNIT,
    Atom,
    Expression,
    G,
    Grounded,
    Handle,
    S,
    Symbol,
    Undefined,
    V,
    Variable,
    and_,
    arrow,
    fresh,
    ground,
    if_,
    in_,
    not_,
    or_,
    parse,
    seg,
    typed,
)
from .atoms import unify as _unify_atoms
from .errors import MettaError, NotReducible, Timeout

_SATELLITES = frozenset(
    {
        "aio",
        "algebra",
        "arrays",
        "casting",
        "convert",
        "derivation",
        "events",
        "foreign",
        "integrate",
        "lint",
        "manifest",
        "parallel",
        "paths",
        "remote",
        "spaces",
        "strategies",
        "structures",
        "subscribe",
        "tables",
        "testing",
        "vocabularies",
        "wire",
    }
)

_LAZY_ATTRIBUTES = {
    "Answer": ("answer", "Answer"),
    "Bindings": ("answer", "Bindings"),
    "Defined": ("define", "Defined"),
    "MeTTa": ("_space", "MeTTa"),
    "Space": ("_space", "Space"),
    "SpaceProvider": ("foreign", "SpaceProvider"),
    "State": ("_state", "State"),
    "counting": ("algebra", "counting"),
    "prob": ("algebra", "prob"),
    "prov": ("algebra", "prov"),
    "ranked": ("algebra", "ranked"),
    "tropical": ("algebra", "tropical"),
    "boot": ("manifest", "boot"),
    "equation": ("_rules", "equation"),
    "rules": ("_rules", "rules"),
    "channel": ("parallel", "channel"),
    "every": ("parallel", "every"),
    "par_map": ("parallel", "par_map"),
    "race": ("parallel", "race"),
    "spawn": ("parallel", "spawn"),
    "view": ("spaces", "view"),
}

_HIDDEN_IMPLEMENTATION_MODULES = {
    "answer",
    "atoms",
    "define",
    "errors",
    "ops",
    "results",
}

_OMITTED = object()


def _path_exists(path: str) -> bool:
    """Check a runtime path without importing pathlib into the narrow root."""
    return _os.path.exists(path)  # noqa: FURB141 -- pathlib adds eager imports to plain ``import metta``


def _resolve_metta_path() -> str:
    """Locate either the upstream or current bundled/source runtime tree."""
    env_path = _os.environ.get("METTA_PATH")
    if env_path:
        return _os.path.abspath(env_path)

    here = _os.path.dirname(_os.path.abspath(__file__))
    bundled = _os.path.join(here, "_runtime")
    if _path_exists(_os.path.join(bundled, "src", "main.pl")) or _path_exists(
        _os.path.join(bundled, "engine", "main.pl")
    ):
        return bundled

    return _os.path.abspath(_os.path.join(here, _os.pardir, _os.pardir, _os.pardir))


def __getattr__(name: str) -> _Any:
    """Load one advertised satellite or lazy core object on first access."""
    if name in _SATELLITES:
        value = _importlib.import_module(f".{name}", __name__)
    elif name in _LAZY_ATTRIBUTES:
        module_name, attribute = _LAZY_ATTRIBUTES[name]
        module = _importlib.import_module(f".{module_name}", __name__)
        value = getattr(module, attribute)
    # policy-inventory-exempt: mechanism-internal; reason=one handle's two documented module-attribute names for the &metta space, not a vocabulary a program selects from; evidence=extensions/python/metta/__init__.py:__getattr__
    elif name in {"catalog", "reflection"}:
        value = engine().space("&metta")
    else:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    _rehide_implementation_modules()
    globals()[name] = value
    return value


def _rehide_implementation_modules() -> None:
    """Restore each root verb an implementation-module import shadowed.

    Importing a submodule writes it onto its parent package, so any import
    that pulls in ``metta.define`` and its siblings replaces the root VERB
    with the module object. This puts the verb back. A name with no verb is
    removed. During partial package initialization the verbs table is not
    bound yet; popping then would delete the verb with nothing to restore
    it, which is how ``metta.define`` once vanished for the life of the
    process, so the pass defers to the end-of-init sweep instead.
    """
    verbs = globals().get("_ROOT_IMPLEMENTATION_VERBS")
    if verbs is None:
        return
    for implementation_name in _HIDDEN_IMPLEMENTATION_MODULES:
        replacement = verbs.get(implementation_name)
        if replacement is None:
            globals().pop(implementation_name, None)
        else:
            globals()[implementation_name] = replacement


def __dir__() -> list[str]:
    """Return only the designed public surface without resolving it."""
    return sorted(__all__)


@_functools.cache
def engine():
    """Return the process-default runtime context, creating it on first use.

    This is the one context whose home is the engine's own ``&self``; a bare
    ``MeTTa()`` is a fresh isolated context instead.
    """
    return __getattr__("MeTTa")(__getattr__("Space")())


def space(
    name: str | Atom | None = None,
    backing: _Any = None,
    *,
    inherits: _Any = None,
    restricted: bool = False,
    grants: _Any = (),
    journal: str | None = None,
    schema: _Any = None,
    sync: str = "none",
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
    )


def attach(name: str | Symbol, backing: _Any):
    """Attach a provider or remote URL through the unified creation function."""
    return space(name, backing=backing)


def current_space():
    """Return the ambient space selected by an enclosing space context."""
    space_api = _importlib.import_module(f"{__name__}._space")
    value = space_api.current_space()
    _rehide_implementation_modules()
    return value


def forms(source: str) -> list[Atom]:
    """Parse every top-level form without evaluating any of them.

    Use ``parse()`` when exactly one form is required. ``forms()`` returns one
    atom per top-level form and does not execute terms marked with ``!``.
    """
    source_forms = _importlib.import_module(f"{__name__}._source_forms")
    return [parse(form.text) for form in source_forms.positioned_forms(source)]


# ------------------------------------------------- generated module tier
# Every method below is GENERATED by tools/aiogen.py from the synchronous Space
# method it delegates to, whose signature, return annotation and docstring it
# carries, each with the tier note appended. Do not edit them here: change
# Space, or remove the method's row from MODULE_DOORS in tools/aio_divergences.py.

def run(
    source: str,
    *,
    timeout: float | None = None,
    inferences: int | None = None,
) -> list[list[Atom]]:
    """Run MeTTa source: one list of answers per ! directive.

    The pipeline is the engine's own reader, compiler and evaluator, so
    the answers are exactly what the CLI would print, kept grouped per
    directive instead of flattened. Equations and facts in the source
    land in this space.

    `bind()` names Python values the source refers to by bare symbol,
    the way DuckDB reads a local dataframe by its variable name:

        with m.bind({"graph": my_graph}):
            m.run("!(py-len graph)")

    Each named symbol substitutes to its value (objects by identity),
    after reading, before anything runs. It is a BLOCK rather than a
    keyword because a binding mapping is the kind of value that grows,
    and a block grows down the page where a keyword has to fit beside
    everything else on the call. Every call that accepts a target reads the
    same scope, so one block covers run(), eval(), and answers() together.

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
    Runs against the default context's self space.
    """
    return engine().self.run(source, timeout=timeout, inferences=inferences)


def load(
    path: str | _os.PathLike[str],
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
    Runs against the default context's self space.
    """
    return engine().self.load(path, timeout=timeout, inferences=inferences)


def match(
    *patterns: _Any,
    where: _Any | None = None,
    limit: int | None = None,
    timeout: float | None = None,
    inferences: int | None = None,
    under: _Any = _UNSET,
    into: _builtins.type | None = None,
) -> _Any:
    """Lazily match patterns against this space as one conjunction.

    Variables shared between patterns join, the engine's own match/4
    doing the joining. Columns are the variable names in first
    appearance order. `where` is a guard term over the same variables,
    evaluated per join and required true, so restrictions a pattern
    cannot spell (an inequality) compose onto the match:

        m.match(S.person(V.name, V.age), where=V.age.ge(18))

    `limit` bounds the answers, the engine stopping at the count
    rather than trimming afterwards. `timeout` (seconds) and
    `inferences` (engine steps) bound the whole call, raising
    TimeLimitError or InferenceLimitError when hit, for joins whose
    size is not known in advance.

    The returned Answers view pulls only what Python observes. ``bool``
    pulls one row, exact-one operations pull at most two, and slicing
    retains an Answers view. ``len`` uses an engine-side aggregate when
    no row has yet been pulled.

    ``under=`` interprets the same ask through an annotation algebra.
    ``under=counting`` answers one integer computed by an engine
    aggregate, including duplicate derivations without crossing their
    rows into Python. Ordered carriers sort in their declared direction
    before slicing, so ``m.match(q, under=ranked)[:3]`` is top-k and
    ``under=tropical`` puts the cheapest annotation first. Other carriers
    answer ``TaggedAnswer`` values with ``annotation``, ``why()`` and
    ``under(other)``; the latter two reuse the retained derivation rather
    than querying the space again. ``with metta.under(carrier)`` supplies
    the carrier when this call has no explicit ``under=``.

    `into=Rows` explicitly chooses the eager Rows face. Other `into=`
    values shape each row into a dataclass, NamedTuple, or
    TypedDict matched by field name, sqlite3's row_factory reading:
    `m.match(S.edge(V.a, V.b), into=Edge)` answers `list[Edge]`,
    and Rows stays the default so nothing is lost. A one-variable query
    whose column holds complete constructor expressions rebuilds those
    expressions instead: `m.match(V.edge, into=Edge)`.

        m.match(S.Edge(V.x, V.y), S.Edge(V.y, V.z))
    Runs against the default context's self space.
    """
    return engine().self.match(
        *patterns, where=where, limit=limit, timeout=timeout, inferences=inferences, under=under, into=into
    )


def add(*atoms: _Any) -> None:
    """Add atoms to this space, one engine round-trip for the lot.
    An (= ...) atom compiles as an equation. Every Atom shape the engine's
    add-atom accepts crosses unchanged, including a bare Symbol, Grounded
    value, and empty Expression; a free Variable receives the engine's own
    insufficient-instantiation refusal.

    A variable's NAME is not stored. `(rule $x $y)` reads back as
    `(rule $_17902 $_17904)`, because a variable is an identity and not a
    spelling. That is the right property for a logic engine and it is the
    one thing about storage that surprises everybody once.

    A library IS knowledge, so the same operator imports it: ``m += lib.he``
    performs ``!(import! <m> (library lib_he))`` with this space as the
    target. An import is an effect, so it refuses to hide inside an atom
    batch or share a call with stored atoms.
    Runs against the default context's self space.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return engine().self.add(*atoms)


def remove(atom: _Any, *more: _Any) -> bool | int:
    """Remove ONE unifying occurrence and say whether one was there,
    which is Python's own `list.remove` grain.

    Variadic like `add` and `transfer`: several atoms ride one engine
    crossing inside one transaction, and the answer counts the found,
    so the one-atom call still reads as the truth value it always
    was.

    `space -= atom` is this same grain without the report, the way
    `+=` is `add` without one: Python's in-place difference over a
    MULTISET, whose own Python spelling is `collections.Counter`,
    subtracts the multiplicity given rather than clearing the key.
    That is the only reading under which the operators are inverses,
    so `s += a; s -= a` leaves the space it found. `-=` classifies its
    operand exactly as `+=` does, so `-=` subtracts the same fact stream
    `+=` stores, one occurrence per element, in one
    transactional crossing.

    `del m[pattern]` is the draining form: it takes every
    unifying occurrence in one crossing and raises when nothing
    matched, as Python's `del` does, and MeTTa spells it `remove-atom`
    [source: engine/spaces/foreign.pl, remove_matching_atoms/2].
    MeTTa spells this method's grain `subtract-atom`. This is the one
    method that reports absence.

    A bare variable is the remove-everything reading a multiset space
    gives it, each atom leaving through its own proper path, equations
    and their compiled clauses included.
    Runs against the default context's self space.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return engine().self.remove(atom, *more)


@_overload
def eval(  # noqa: A001 -- eval is the ruled public verb
    target: _Any,
    *,
    timeout: float | None = ...,
    inferences: int | None = ...,
    under: _Any = ...,
    theory: _Any | None = ...,
    interpreter: _Any | None = ...,
) -> list[Atom | Undefined]: ...
@_overload
def eval(  # noqa: A001 -- eval is the ruled public verb
    target: _Any,
    second: _Any,
    /,
    *more: _Any,
    timeout: float | None = ...,
    inferences: int | None = ...,
    under: _Any = ...,
    theory: _Any | None = ...,
    interpreter: _Any | None = ...,
) -> list[list[Atom | Undefined]]: ...
def eval(  # noqa: A001 -- eval is the ruled public verb
    target: _Any,
    *more: _Any,
    timeout: float | None = None,
    inferences: int | None = None,
    under: _Any = _UNSET,
    theory: _Any | None = None,
    interpreter: _Any | None = None,
) -> list[Atom | Undefined] | list[list[Atom | Undefined]]:
    """Evaluate a term, returning every answer.

    This is what !(...) runs, minus the printing: the engine's
    translate_expr over the term, then its goals. Nondeterminism means
    the list can hold any number of answers, including none.

    Variadic, and that is how evaluation BATCHES: several terms ride
    one engine crossing and the answer is one group per term in call
    order, run()'s own grouping carried to the term form. One term
    keeps its flat list, so the scalar reading never changes shape.

    Every answer carries its truth: an answer that is undefined under
    Well Founded Semantics (a tabled loop through tnot, reachable via
    translatePredicate or injected Prolog) arrives as an Undefined
    holding the answer and the delay condition that makes it
    undefined, never as an ordinary-looking value. A term to which no
    rule applies is the ordinary answer itself; `eval_status()` names
    that path `not-reducible`. run() does not carry the third truth
    value; evaluate through eval() when it matters.

    `bind()` binds named host values into the term before it evaluates,
    exactly as it does for run(): inside `with m.bind({"x": tensor})`,
    `m.eval("(decide x)")` hands the tensor itself to the rule, by
    identity, rather than a printed form of it. The name is the SYMBOL x
    and not the variable $x, in this call and the source form alike. The
    evaluation calls take the same vocabulary as the source form, so using
    a term instead of source text costs no change of spelling.

    A key may be a NAME or an ATOM. A name means the symbol of that name,
    which is what the engine's own substitution matches and what run()
    takes. An atom means exactly that atom, so `bind({V.x: 5})` fills a
    VARIABLE hole -- the one substitution `unify` reports and the one no
    evaluation call could apply, because a variable crosses the wire as ['v', 'x']
    where a symbol crosses as ['s', 'x'] and the engine matches names.

    `timeout` (seconds) and `inferences` (engine steps) bound the call,
    raising TimeLimitError or InferenceLimitError when hit. A surrounding
    `capture()` scope collects printed text without changing the list.

    `under`, `theory` and `interpreter` are answers()' three, and mean
    exactly what they mean there; `eval()` materialises that query as a list. A
    surrounding `with metta.under(carrier)` reaches here too, which it did
    not before: match() and answers() both honoured such a scope while
    eval() ignored it in silence.
    Runs against the default context's self space.
    """
    return engine().self.eval(
        target, *more, timeout=timeout, inferences=inferences, under=under, theory=theory, interpreter=interpreter
    )


def solve(pattern: _Any, subject: _Any) -> _Any:
    """Run relational ``let`` and return bindings keyed by its variables.

    ``solve(4, V.x - 1).x`` places the known value on let's pattern side,
    lets the arithmetic relation solve backwards, and projects ``x``.
    The answer template is derived from the pattern's variables followed
    by any new subject variables, so either relational direction can
    introduce the bindings and the third hand-written ``let`` argument
    disappears.
    Runs against the default context's self space.
    """
    return engine().self.solve(pattern, subject)


def doc(atom: _Any) -> Atom:
    """Return this space's structured ``get-doc`` answer for one subject.

    The answer is the ``(@doc ...)`` atom the engine holds for the
    subject, whether it was documented in MeTTa source or built from a
    Python docstring:

        m.doc(S.area)
        # (@doc-formal (@item area) (@kind function) (@desc "Circle area.") ...)

    A subject with no documentation raises, exactly as ``type`` raises
    for a subject ``get-type`` cannot answer.
    Runs against the default context's self space.
    """
    return engine().self.doc(atom)


@_overload
def define(fn: _builtins.type, /, *, accessors: bool = ..., methods: bool = ...) -> _builtins.type: ...  # type: ignore[overload-overlap]
@_overload
def define(
    fn: _Callable[_P, _R],
    /,
    *,
    name: str | None = ...,
    accessors: bool = ...,
    methods: bool = ...,
) -> _Defined[_P, _R]: ...
@_overload
def define(*, name: str) -> _Callable[[_Callable[_P, _R]], _Defined[_P, _R]]: ...
@_overload
def define(
    *,
    prolog: str | _os.PathLike[str],
    name: str | None = None,
) -> _Callable[[_Callable[_P, _R]], _PrologBacked[_P, _R]]: ...
def define(
    fn: _Callable[..., _Any] | None = None,
    *,
    prolog: str | _os.PathLike[str] | None = None,
    name: str | None = None,
    accessors: bool = True,
    methods: bool = True,
) -> _Any:
    """Compile a Python function into MeTTa equations, decorator-style.

    With `prolog=`, the Prolog file is registered and becomes the
    function, and the Python stays as the reference twin rather than
    being compiled:

        @m.define(prolog=Path(__file__).parent / "fast.pl")
        def vec_dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        m.eval("(vec-dot (1 2) (3 4))")[0] # the Prolog answer
        vec_dot.py((1, 2), (3, 4))          # the reference answers

    Rewriting a defined function in Prolog for speed used to mean
    deleting the Python and the differential oracle with it. Here both
    are declared together and `metta.testing.check_twin` proves they
    agree on ground inputs. The file must register the function's own
    MeTTa name and at the twin's arity, inputs then one output, and
    says so if it does not; its `metta_export` declaration owns the
    types, so annotations on the Python are documentation only.

    Written for whoever is fluent in Python rather than s-expressions:
    the body is read as syntax and lowered deterministically, refusals
    name the construct, the line and what to write instead, and the
    original stays reachable as .py, a twin the equations can be checked
    against on any ground input.

        @m.define
        def add_one(n):
            return n + 1

        add_one(5)                  # [6], evaluated by the engine
        S.add_one(5)                # (add_one 5), staged as data
        add_one.py(5)               # 6, ordinary Python

    The equation's implicit name applies the factories' total mechanical
    map, replacing each underscore with a hyphen. ``name=`` is the exact
    quoted-name escape for punctuation that map cannot preserve:

        @m.define(name="add-one")
        def add_one(n):
            return n + 1

    The same attribute mapping applies to the definition name itself:
    ``def not_provable`` lands as ``not-provable``. An authored
    MeTTa underscore therefore uses explicit ``name="not_provable"``.

    A generator compiles to nondeterminism (each yield one answer), a
    lambda to the engine's own |->, a comprehension to map-atom and
    filter-atom, and match(Pattern(x, y), template) to a match against
    the running space, lowercase free names in the pattern binding as
    variables.
    Runs against the default context's self space.
    """
    return engine().self.define(fn, prolog=prolog, name=name, accessors=accessors, methods=methods)


@_overload
def op(
    fn: _Callable[_P, _R],
    /,
    *,
    name: str | None = ...,
    # policy-inventory-exempt: mechanism-internal; reason=mirrored from the Space method of the same name, whose adjacent exemption carries the reason; evidence=extensions/python/metta/ops.py:_operation_kind
    transport: _Literal['encoded', 'raw'] = ...,
    effect: _EffectClass | str,
    declarations: _Iterable[Atom] = ...,
    arities: list[int] | None = ...,
    inverse: _Callable | None = ...,
) -> _Callable[_P, _R]: ...
@_overload
def op(
    *,
    name: str | None = ...,
    # policy-inventory-exempt: mechanism-internal; reason=mirrored from the Space method of the same name, whose adjacent exemption carries the reason; evidence=extensions/python/metta/ops.py:_operation_kind
    transport: _Literal['encoded', 'raw'] = ...,
    effect: _EffectClass | str,
    declarations: _Iterable[Atom] = ...,
    arities: list[int] | None = ...,
    inverse: _Callable | None = ...,
) -> _Callable[[_Callable[_P, _R]], _Callable[_P, _R]]: ...
def op(
    fn: _Callable | None = None,
    *,
    name: str | None = None,
    # policy-inventory-exempt: mechanism-internal; reason=mirrored from the Space method of the same name, whose adjacent exemption carries the reason; evidence=extensions/python/metta/ops.py:_operation_kind
    transport: _Literal['encoded', 'raw'] = 'encoded',
    effect: _EffectClass | str | None = None,
    declarations: _Iterable[Atom] = (),
    arities: list[int] | None = None,
    inverse: _Callable | None = None,
) -> _Any:
    """Register a Python callable as a MeTTa function, decorator-style.

        @m.op(effect=EffectClass.pureStructural)
        def double(x: int) -> int:
            return 2 * x                    # !(double 21) -> 42

        @m.op(effect=EffectClass.nondeterministicReadOnly)
        def neighbours(n: int):
            yield n - 1                     # a generator is nondeterministic
            yield n + 1

    An implicit Python name maps underscores to MeTTa hyphens. ``name=``
    is exact, for source vocabularies that deliberately use underscores.

    A name must read back as one MeTTa symbol. A space, parenthesis,
    quote, comment opener, variable spelling, number, boolean, or another
    registered reader token is refused before any registry changes, with
    the name and the conflicting character in the error.

    Annotations become ordinary `(: ...)` declarations. An unannotated
    callable makes no type claim. `transport="raw"` skips wire encoding
    both ways and is reflected as raw_det or raw_many in `(op ...)`;
    symbols then reach Python as strings, so encoded transport is the
    fidelity-preserving default. unregister_op(name) removes every
    registered arity and every declaration the registration owns.

    An `Atom` parameter changes evaluation order. The declaration tells
    the compiler to pass the argument as written, before it reduces:

        @m.op(effect=EffectClass.pureStructural)
        def anyatom(term: Atom) -> Atom:
            return term

        # with (= (side) 42), !(anyatom (side)) answers (side)

    An unconstrained parameter receives the evaluated value instead, so
    the otherwise identical `def anyval(term): return term` answers 42.
    Use `Atom` only when the operation deliberately implements syntax or
    a control form; it is not just a static hint.

    An encoded generator may instead yield exact tuples as positional
    relation rows, or exact dicts keyed by parameter name as sparse rows.
    The engine unifies each candidate against the written call, so one
    implementation serves free, partially bound, and ground arguments:

        @m.op
        def route(origin, destination):
            yield (S.paris, S.lyon)
            yield {"destination": S.nice}  # origin is unconstrained

        # route(V.origin, S.lyon).rows[0].origin == S.paris

    Each matching occurrence answers unit and duplicate yields remain
    duplicate answers. Use `Answer(value=...)` when an exact tuple or dict
    is the result value rather than a parameter row. Relational rows
    require encoded transport; raw calls cannot carry unbound argument
    positions.

    When evaluation order stays ordinary but the callable needs the
    resulting Atom wrappers, declare that policy as data:

        m.op(
            inspect_atom,
            name="inspect-atom",
            effect=EffectClass.pureStructural,
            declarations=[parse("(arguments inspect-atom atoms)")],
        )

    The declaration is matchable in &metta and is retired with the
    operation. Raw transport refuses this declaration because it bypasses
    the atom codec entirely.

    The cost ladder, measured on the maintained box in inferences per
    call, explains the transport choice:

        native MeTTa function            9.11   the floor
        transport="raw"                10.11   opaque handles, near-native
        encoded                        17.11   encoded values
        encoded, typed literal         17.11   the check hoists to compile
        py-call, dotted                 22.11   the ad-hoc escape hatch

    The ergonomic default (encoded, typed) costs about 1.7x raw on the
    counter and more on wall clock, since encoding walks the value both
    ways; a registered raw operation measured 0.85us against 2.26us
    encoded. Bulk data should stay opaque: one transparent 64-float
    crossing costs 330 inferences where the handle costs 10.

    `inverse=` remains the distinct-output form. Use it when the forward
    operation returns a result and a separate callable must recover the
    arguments from that result:

        m.op(
            cons,
            name="cons",
            inverse=uncons,
            effect=EffectClass.pureStructural,
        )
        # !(let (cons $h $t) (1 2 3) ($h $t))  ->  (1 (2 3))

    It takes the result and returns the arguments, as a tuple, or the
    bare value at arity one; a generator enumerates every preimage, and
    None or NotReducible means there is none. It runs only when the arguments
    are not ground and the result is, so a forward call never reaches it,
    and an operation without one compiles exactly what it did before.

    A parameter annotated `metta.MeTTa` is the framework's to fill,
    FastAPI's Depends read with the house convention that the
    annotation is the request. The engine injects itself bound to the
    CALLING context's space, so an operation invoked from a program
    running in &kb queries &kb; the slot never counts toward MeTTa
    arities or the declared arrow, and only operations that ask pay
    the weaving:

        @m.op(effect=EffectClass.nondeterministicReadOnly)
        def related(term, engine: metta.MeTTa):
            for row in engine.match(Expression(S.link, term, V.x)):
                yield row[0]

    Every operation declares its strongest observable effect. The five
    ordered choices are ``pureStructural``, ``readOnlyLookup``,
    ``nondeterministicReadOnly``, ``writesState``, and ``oracleIO``:

        m.op(
            len,
            name="size",
            effect=EffectClass.pureStructural,
        )
        # (= (count-of $x) (size $x))  is cacheable

    It is an allow-list on purpose. An operation that does not say so is
    refused by name in a cached body, loudly, rather than cached and
    quietly wrong.
    Runs against the default context's self space.
    """
    return engine().self.op(
        fn, name=name, transport=transport, effect=effect, declarations=declarations, arities=arities, inverse=inverse
    )


def pure(fn: _Callable | None = None, /, **options: _Any) -> _Any:
    """An operation whose answer depends only on its arguments.

        @m.pure
        def double(x: int) -> int:
            return 2 * x

    The cache-safe class, and the only one memoization and tabling admit
    without an explicit policy.

    A GENERATOR written this way is lifted to `nondeterministicReadOnly`,
    because a generator is nondeterministic whatever it declares, and the
    registration reads that off the function rather than asking. The lift
    only ever raises the rank, so it widens the answer-count claim and
    never weakens the effect claim -- but it does mean a generator is not
    cache-safe, which is the whole reason it is lifted out of this class
    [tested: test_a_generator_is_lifted_to_the_nondeterministic_rank;
    commit=7e5091540a8dc0903bcee24f3e5b8b85a19f805f].

    Every ``op`` keyword applies: ``name``, ``arities``,
    ``declarations``, ``inverse`` and ``transport``. They arrive as
    ``**options`` and forward unchanged, so the signature above shows
    the mechanism and this line shows the surface.
    Runs against the default context's self space.
    """
    return engine().self.pure(fn, **options)


def reads(fn: _Callable | None = None, /, **options: _Any) -> _Any:
    """An operation that reads stable state without changing it.

    Every ``op`` keyword applies: ``name``, ``arities``,
    ``declarations``, ``inverse`` and ``transport``. They arrive as
    ``**options`` and forward unchanged, so the signature above shows
    the mechanism and this line shows the surface.
    Runs against the default context's self space.
    """
    return engine().self.reads(fn, **options)


def writes(fn: _Callable | None = None, /, **options: _Any) -> _Any:
    """An operation that changes engine or host state.

    Every ``op`` keyword applies: ``name``, ``arities``,
    ``declarations``, ``inverse`` and ``transport``. They arrive as
    ``**options`` and forward unchanged, so the signature above shows
    the mechanism and this line shows the surface.
    Runs against the default context's self space.
    """
    return engine().self.writes(fn, **options)


def io(fn: _Callable | None = None, /, **options: _Any) -> _Any:
    """An operation that observes an external oracle.

    A clock, randomness, a network, a file, another runtime.

        @m.io
        def now() -> float:
            return time.time()

    The fail-closed top of the lattice. Declare it when what the operation
    reaches is decided at run time or by a library the engine cannot bound.

    Every ``op`` keyword applies: ``name``, ``arities``,
    ``declarations``, ``inverse`` and ``transport``. They arrive as
    ``**options`` and forward unchanged, so the signature above shows
    the mechanism and this line shows the surface.
    Runs against the default context's self space.
    """
    return engine().self.io(fn, **options)


def stats() -> _StatsBlock:
    """The engine's own counters over a with-block, as deltas.

        with m.stats() as s:
            m.match(S.edge(V.x, V.y), S.edge(V.y, V.z))
        s.inferences        # engine steps the block spent
        s.cputime           # engine CPU seconds
        s.walltime          # wall seconds, Python's clock
        s.gc_count, s.gc_freed, s.gc_time
        s.table_bytes       # answer-table bytes grown, tabling's memory

    The counters are SWI's statistics/2 read on the CALLING thread, so
    a block that runs other threads' engine work counts that work too;
    the honest reading is "what this thread saw the engine do while the
    block ran". A lazy cursor is the exception, and a large one: its
    goal runs in an SWI engine, an engine counts its own inferences,
    and this thread cannot see them. Draining 20,000 rows through the
    match cursor reports 40,049 inferences against about 381,000 the
    cursor's engine really spent, 10.5% of the work; the real cost is
    readable off the `inferences` budget, which does count the engine
    [measured 2026-08-27]. The evaluation cursor behind `answers()`
    does report its engine's spend, so that one is whole. The z3py
    Solver.statistics() reading, on the engine this library actually
    has.
    Runs against the default context's self space.
    """
    return engine().self.stats()


def limits(
    *,
    timeout: float | None = None,
    inferences: int | None = None,
    stack: int | None = None,
) -> _ScopedLimits:
    """Scoped default bounds for every call in the with-block:

        with m.limits(inferences=1_000_000, timeout=2.0):
            m.match(...)      # bounded without saying so again

    decimal.localcontext's shape, contextvars underneath, so the
    scope is async-correct and per-task. A per-call timeout= or
    inferences= still overrides, which is the whole ladder: one
    block replaces the parameter forest, and the forest remains
    for whoever wants per-call control.

    stack= is SWI's combined stack ceiling in BYTES, the bound a
    runaway recursion hits as a StackOverflow error atom. It is NOT
    MeTTa's reduction depth: that is the max-stack-depth pragma,
    `(with-pragma! ((max-stack-depth N)) expr)`, which counts
    reduction steps and is scoped in the program text.
    Runs against the default context's self space.
    """  # noqa: D415  -- the first line deliberately introduces the indented example that follows
    return engine().self.limits(timeout=timeout, inferences=inferences, stack=stack)


def speculate() -> _ScopedExecution:
    """Run each source against a snapshot and discard its writes.

    Runs against the default context's self space.
    """
    return engine().self.speculative()


def trace(source: Atom | str, max_events: int | None = None):
    """Run a TERM, or source, under the engine's reduction trace and
    answer TraceEvent records: what entered reduction at which depth,
    what it answered, and which reductions failed (a call with no
    exit). `m.trace(S.fib(10))` is the ordinary spelling, the same
    argument `answers` and `eval` take; a string is still a string.
    What is traced executes for real, writes included, like run();
    the wrap exists only while tracing, so untraced calls pay
    nothing. max_events bounds the recording; past it the recording
    stops and the result's `truncated` is True, rather
    than accumulating a long run's trace without limit.
    Runs against the default context's self space.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return engine().self.trace(source, max_events)


# ------------------------------------------ end of generated module tier


def _ambient_space():
    """Open the space selected by the active Python or engine context."""
    return engine().space(current_space())


@_overload
def unify(left: _Any, right: _Any) -> _Mapping[Atom, Atom] | None: ...


@_overload
def unify(left: _Any, right: _Any, then: _Any, els: _Any) -> _Answers[Atom]: ...


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
    scoped = _importlib.import_module(f"{__name__}._under")
    return scoped.ScopedUnder(algebra)


_ROOT_IMPLEMENTATION_VERBS = {
    "define": define,
    "trace": trace,
}


__all__ = [
    "FALSE",
    "TRUE",
    "UNIT",
    "Answer",
    "Atom",
    "Bindings",
    "Config",
    "Defined",
    "Expression",
    "G",
    "Grounded",
    "Handle",
    "Library",
    "MeTTa",
    "MettaError",
    "NotReducible",
    "S",
    "Space",
    "SpaceProvider",
    "State",
    "Symbol",
    "Timeout",
    "Undefined",
    "V",
    "Variable",
    "__version__",
    "accept",
    "add",
    "aio",
    "algebra",
    "and_",
    "arrays",
    "arrow",
    "attach",
    "boot",
    "casting",
    "catalog",
    "channel",
    "config",
    "convert",
    "counting",
    "current_space",
    "define",
    "derivation",
    "doc",
    "drop",
    "engine",
    "equation",
    "eval",
    "events",
    "every",
    "fn",
    "foreign",
    "forms",
    "fresh",
    "ground",
    "if_",
    "in_",
    "integrate",
    "io",
    "lib",
    "limits",
    "lint",
    "manifest",
    "match",
    "not_",
    "op",
    "or_",
    "par_map",
    "parallel",
    "parse",
    "paths",
    "prob",
    "prov",
    "pure",
    "py",
    "race",
    "ranked",
    "reads",
    "reflection",
    "refuse",
    "remote",
    "remove",
    "rules",
    "run",
    "seg",
    "solve",
    "space",
    "spaces",
    "spawn",
    "speculate",
    "stats",
    "strategies",
    "structures",
    "subscribe",
    "superpose",
    "tables",
    "testing",
    "trace",
    "tropical",
    "typed",
    "under",
    "unify",
    "view",
    "vocabularies",
    "wire",
    "writes",
]

# Importing a submodule writes it onto its parent package. These concrete
# modules remain explicitly importable, but they are implementation modules,
# not root attributes. The verbs table is bound by here, so this is the
# end-of-init sweep the partial-init guard in the helper defers to.
_rehide_implementation_modules()
