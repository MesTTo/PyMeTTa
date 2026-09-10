"""Purpose: resolve engine functions and describe their live declarations.

Guarded by: _BUILTINS_CACHE_LOCK protects the shared callable catalog cache
[source: extensions/python/metta/_declare/functions.py:562; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

import functools
import inspect
import json
import threading
import warnings
import weakref
from collections.abc import Mapping, Sequence
from difflib import get_close_matches
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import metta._declare.definitions as _declare_definitions_module
import metta.doors as _doors
from metta._atoms.calls import bind_positional_call, refuse_unknown_keywords
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    _atom_from_wire,
    _decode,
    _encode,
    parse,
)
from metta._atoms.names import OperatorRecipe, operator_attribute_target
from metta._binding.positions import Origin, head_origins
from metta._binding.runtime import Runtime
from metta._catalog.declarations import INFERRED_NOTE, inferred, is_arrow
from metta._errors.errors import MettaError, Remedy, refusing
from metta._lazy import lazy
from metta._spaces.handle import _require_name

_UNDEFINED_TYPE = Symbol("%Undefined%")

def _doc_text(atom: object) -> str:
    """The prose inside a doc part: a string value decodes, anything
    else renders as written.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(atom, Grounded):
        value = _decode(atom)
        if isinstance(value, str):
            return value
    return str(atom)

def _doc_part_text(parts: Sequence[Atom]) -> str:
    """The reader's prose from one documentation part's children.

    A `@param` or `@return` is written either as bare prose, `(@param "the
    radius")`, or with the type beside it, `(@param (@type Number) (@desc "the
    radius"))`, which is the shape a Python docstring's parsed arguments
    produce. Taking the first child answered `(@type Number)` for the second
    shape, so help() printed the type where the description belongs and the
    description was unreachable [measured 2026-09-07: an annotated @m.define
    listed its one parameter as `(@type Number)` under `Parameters:`].
    """
    for part in parts:
        if (
            isinstance(part, Expression)
            and len(part.children) > 1
            and part.children[0] == Symbol("@desc")
        ):
            return _doc_text(part.children[1])
    return _doc_text(parts[0])

def _format_doc_atom(doc: Expression) -> str:
    """`(@doc name (@desc ...) (@params (...)) (@return ...))` as help()
    text: one summary line, then the parameters, then the return.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    name = doc.children[1] if len(doc.children) > 1 else ""
    lines: list[str] = []
    parameters: list[str] = []
    returns: str | None = None
    for part in doc.children[2:]:
        if not (isinstance(part, Expression) and part.children):
            continue
        head, *rest = part.children
        if head == Symbol("@desc") and rest:
            lines.append(f"{name}: {_doc_text(rest[0])}")
        elif head == Symbol("@params") and rest and isinstance(rest[0], Expression):
            parameters = [
                _doc_part_text(param.children[1:])
                for param in rest[0].children
                if isinstance(param, Expression) and len(param.children) > 1
            ]
        elif head == Symbol("@return") and rest:
            returns = _doc_part_text(rest)
    if not lines:
        lines.append(str(name))
    if parameters:
        lines.extend(("", "Parameters:"))
        lines.extend(f"  - {parameter}" for parameter in parameters)
    if returns is not None:
        lines.append(f"Returns: {returns}")
    return "\n".join(lines)

_COST_LEDGER = Path(__file__).resolve().parents[2] / "benchmarks" / "cost-baseline.json"

@functools.cache
def _cost_measurement_dates() -> Mapping[str, str]:
    """Each measured head's date from the ledger, empty when it is not on disk.

    Read once per process. The ledger is a build artifact that a gate run
    rewrites, not live state, so a process that started before a re-record
    keeps showing the date it started with; `help()` in a fresh process shows
    the new one.
    """
    try:
        document = json.loads(_COST_LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    rows = document.get("rows", {})
    return {
        str(head): str(row["measured"])
        for head, row in rows.items()
        if isinstance(row, dict) and "measured" in row
    }

class _EngineFunction:
    """One engine function, callable the way Python callables are.

    Beyond calling, it carries the function protocol's introspection:
    __name__ and __qualname__ as data, __doc__, __signature__, .type,
    .equations and .compiled as live reads of the space, so help() and
    inspect.signature() answer from MeTTa's own declarations.
    functools.partial composes because this is an ordinary callable,
    which is the whole bound-method story; there is deliberately no
    __defaults__ or __annotations__, because MeTTa has no default
    arguments and the annotations live on the arrow type.
    """

    # A slot named __qualname__ is the one pure-Python spelling of
    # method.__qualname__'s C getset: the member descriptor answers per
    # instance, while class access keeps resolving through the
    # type.__qualname__ metaclass data descriptor, so the class still
    # answers _EngineFunction (verified in test_name_and_qualname_...).
    # Assigning a property after class creation is refused by that same
    # metaclass setter, which only accepts str. pylint flags the
    # shadowing it cannot see resolves correctly.
    __slots__ = (
        "__name__",
        "__qualname__",  # pylint: disable=class-variable-slots-conflict
        "_name",
        "_space",
    )

    def __init__(self, space: _root.Space, name: str) -> None:
        self._space = space
        self._name = name
        self.__name__ = name
        self.__qualname__ = f"{space.name}.{name}"

    def __metta__(self) -> Symbol:
        """A bound function in term position mentions as its own head symbol."""
        return Symbol(self._name)

    def _term(self, args: tuple) -> Expression:
        return Expression([Symbol(self._name), *(_encode(a) for a in args)])

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Evaluate this call and return its replayable Answers.

        MeTTa's trailing ``!`` is its effect marker, not a Python convention
        invented by this namespace.  A resolved bang name therefore drains
        at the call boundary so the statement has happened when its line
        completes.  Non-bang calls retain demand-driven evaluation.
        """
        frame = inspect.currentframe()
        try:
            caller = None if frame is None else frame.f_back
            if caller is not None:
                # intent recording runs after the definition exists
                from metta._spaces.intents import record_sync_engine_call  # noqa: PLC0415

                record_sync_engine_call(self._space, self._name, caller)
        finally:
            del frame
        if kwargs:
            parameters = _declare_definitions_module.call_parameter_names(
                self._space, self._name, len(args) + len(kwargs)
            )
            if parameters is None:
                raise refuse_unknown_keywords(self._name, tuple(kwargs))
            args = bind_positional_call(self._name, parameters, args, kwargs)
        _warn_deprecated(self._space, self._name, stacklevel=3)
        answers = self._space.answers(self._term(args))
        if self._name.endswith("!"):
            answers._materialize()
            _invalidate_builtins(self._space)
        return answers

    # ------------------------------------------------------- introspection

    @property
    def type(self) -> Atom | None:
        """The declared type atom, or None when undeclared.

        get-type's own answer through this space's context, so a named
        space's declarations count; %Undefined% reads as None because
        the function protocol spells absence that way. MeTTa allows
        several declarations for one name; this answers the first.
        """
        answers = self._space.eval(Expression([Symbol("get-type"), Symbol(self._name)]))
        for answer in answers:
            if isinstance(answer, Atom) and answer != _UNDEFINED_TYPE:
                return answer
        return None

    @property
    def equations(self) -> list[Expression]:
        """The stored `(= (f ...) body)` atoms, live from the space."""
        wires = self._space._rt.apply_must(
            "metta_py_equations", self._space.name, self._name
        )
        return [cast(Expression, _atom_from_wire(w)) for w in wires]

    @property
    def compiled(self) -> str:
        """The Prolog clauses this name compiled to: dis for the
        translator, exposed from the function handle as a property.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        return _disassemble(self._space, self._name)

    @property
    def origin(self) -> tuple[Origin | None, ...]:
        """Where each clause of this head was written, in clause order.

        One `Origin(file, line)` per compiled clause, or None in that
        position for a clause with no source. A head defined in a `.metta`
        file answers that file and the line its equation sits on; a head
        registered from a Prolog file answers that file and line, which is
        every builtin; a head defined from Python text has no source and
        answers None.

        `inspect.getsourcefile` cannot reach these, because a MeTTa head has
        no Python code object. This is the door that answers the same
        question, one row per clause because MeTTa spreads a definition
        across equations the way Prolog spreads it across clauses.

        It is a diagnostic: answering a `.metta` line reads and parses that
        file, once per file per call, so it costs what reading the source
        costs rather than what a lookup costs.
        """
        return head_origins(self._space, self._name)

    @property
    def __signature__(self) -> inspect.Signature:
        """Built from the arrow type when one is declared, so
        inspect.signature() and completion show the arity with the
        parameter types as annotations.

        A head nothing declares falls back to the arrow its stored atoms
        justify, `Space.infer_types()`'s own proposal, and `__doc__` says
        that one is inferred. A head with neither is (*args). Reading an
        inferred signature walks the space once, the cost `infer_types`
        states, and `origin` already prices introspection the same way.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        declared = self.type
        arrow = (
            declared
            if declared is not None and is_arrow(declared)
            else self._inferred_arrow()
        )
        if arrow is None:
            return inspect.Signature(
                [inspect.Parameter("args", inspect.Parameter.VAR_POSITIONAL)]
            )
        parts = arrow.children[1:]
        parameters = [
            inspect.Parameter(
                f"x{position}",
                inspect.Parameter.POSITIONAL_ONLY,
                annotation=str(part),
            )
            for position, part in enumerate(parts[:-1], start=1)
        ]
        return inspect.Signature(
            parameters, return_annotation=str(parts[-1]) if parts else ""
        )

    def _cost_line(self) -> str | None:
        """`cost: <class> in $n (<measure>)`, when a (cost ...) row names this head.

        The longhand is the row itself: `(match &metta (cost ($head $n) $class)
        $class)` reads what this reports, and `(explain (<head> ...))` answers
        the same pair beside every other declaration the call consults. What is
        added here is the ledger's date, which says when the cost-rows lane last
        measured the head against its claim rather than merely that the claim is
        written down.
        """
        claim = self._space._rt.apply_must(
            "metta_py_cost_declaration", self._space._space, self._name
        )
        if not isinstance(claim, list):
            return None
        cost_class, measure = claim
        measured = _cost_measurement_dates().get(self._name)
        stamp = f"measured {measured}" if measured else "declared"
        return f"cost: {cost_class} in $n ({measure}), {stamp}"

    @property
    def __doc__(self) -> str | None:  # type: ignore[override]
        """MeTTa's own documentation, formatted for help(): the space's
        `(@doc name ...)` atom when one exists (the engine's register
        documents every prelude form, so builtins answer too), else the
        declaration and equations, else None as Python spells absence.
        A head with no declaration says the arrow its stored atoms justify
        instead, marked inferred, so a reader can tell a proposal from a
        promise; nothing is added to the space by reading it. A declared
        cost class is appended to whichever of those answered, and is
        documentation on its own for a head that has no other.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        cost = self._cost_line()
        answers = self._space.eval(Expression([Symbol("get-doc"), Symbol(self._name)]))
        if answers and isinstance(answers[0], Expression):
            documented = _format_doc_atom(answers[0])
            return f"{documented}\n\n{cost}" if cost else documented
        lines = []
        declared = self.type
        if declared is not None:
            lines.append(f"{self._name}: {declared}")
        else:
            proposed = self._inferred_arrow()
            if proposed is not None:
                lines.append(f"{self._name}: {proposed}   {INFERRED_NOTE}")
        equations = self.equations
        if equations:
            if not lines:
                lines.append(self._name)
            lines.extend(("", "Equations:"))
            lines.extend(f"  {equation}" for equation in equations)
        if cost:
            if not lines:
                lines.append(self._name)
            lines.extend(("", cost))
        return "\n".join(lines) if lines else None

    def _inferred_arrow(self) -> Expression | None:
        """The arrow this space's stored atoms justify for this head, or None.

        The first row for the name, which for a head observed at two arities
        is the arity the space mentions first; `metta.stubs()` renders every
        row as its own overload where one signature cannot.
        """
        for row in inferred(self._space):
            if row.name == self._name:
                return row.arrow
        return None

    def __repr__(self) -> str:
        return f"<engine function {self._name} on {self._space.name}>"

class _CompositeEngineFunction:
    """One bound word whose public call expands to a composite MeTTa term."""

    __slots__ = (
        "__name__",
        # The same pure-Python spelling of method.__qualname__'s C getset the
        # bound-function class documents above its own slot.
        "__qualname__",  # pylint: disable=class-variable-slots-conflict
        "_recipe",
        "_space",
    )

    def __init__(self, space: _root.Space, recipe: OperatorRecipe) -> None:
        self._space = space
        self._recipe = recipe
        self.__name__ = recipe.word
        self.__qualname__ = f"{space.name}.{recipe.word}"

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        _warn_deprecated(self._space, self._recipe.word, stacklevel=3)
        return self._space.answers(self._recipe(*args, **kwargs))

    def __repr__(self) -> str:
        return f"<composite engine function {self._recipe.word} on {self._space.name}>"

class _FunctionNamespace:
    """Functions visible to one space, resolved when an attribute is read.

    MeTTa marks effects with a trailing ``!``.  Calls whose resolved name has
    that marker execute eagerly when called; all other calls stay lazy.
    """

    __slots__ = ("_space",)

    def __init__(self, space: _root.Space) -> None:
        self._space = space

    def _known(self, name: str) -> bool:
        # A point probe, not the catalogue list: the list rebuild after any
        # definition measured 1,347 inferences on the next attribute access
        # (the whole of one twin's band overrun); membership is double
        # digits and answers the same union.
        return _is_catalogued(self._space, name) or self._space.is_function_here(name)

    def _resolve(self, name: str, *, attribute: str | None = None) -> _EngineFunction:
        resolved = name
        if not self._known(resolved):
            bang = f"{resolved}!"
            if attribute is not None and self._known(bang):
                resolved = bang
            else:
                asked = attribute if attribute is not None else name
                # The remedy, for the same reason the GENERATED namespace names
                # one: a caller who reaches a function namespace wants the
                # function, and "no such name" alone leaves them hunting a
                # typo. This namespace is the LIVE one, so a miss here means the
                # name is not defined or registered anywhere this space can
                # see, which is a different answer from the generated namespace's.
                #
                # The SUGGESTION IS THE LIBRARY'S OWN, and that is the whole
                # difference from every other refusal here, which sets `name`
                # and `obj` and lets the interpreter render the sentence.
                # CPython's renderer declines a candidate pool of 750 or more
                # and answers nothing at all [source: CPython 3.14.4
                # Lib/traceback.py _MAX_CANDIDATE_ITEMS, and _suggestions.
                # _generate_suggestions, which answers None at 750 and a name
                # at 749]. This pool is what THIS space can call, which
                # includes every unscoped name the process has registered, so
                # it crosses that line in any long-lived program: a suite
                # measured 1,034 for a space that defines one function
                # [measured 2026-09-07: tests/ch11_python_as_a_notation/
                # test_fn_protocol.py, len(dir(here.fn))], and the sentence
                # then disappeared on some orderings and not others. difflib
                # is what results.py and _head_meaning.py already use for the
                # same job, and it has no such ceiling. The two fields stay
                # set, so the interpreter still adds its own line wherever it
                # can.
                close = get_close_matches(asked, dir(self), n=1, cutoff=0.6)
                suggestion = f"; did you mean {close[0]!r}?" if close else ""
                msg = (
                    f"{self._space.name}.fn has no function {asked!r}; define "
                    f"it with @space.define, register it with @space.op, or "
                    f"build the term directly with S[{asked!r}](...){suggestion}"
                )
                raise AttributeError(msg, name=asked, obj=self)
        return _EngineFunction(self._space, resolved)

    def __getattr__(self, name: str) -> _EngineFunction | _CompositeEngineFunction:
        if name.startswith("_"):
            raise AttributeError(name)
        resolved = operator_attribute_target(name)
        if isinstance(resolved, OperatorRecipe):
            return _CompositeEngineFunction(self._space, resolved)
        target = name.replace("_", "-") if resolved is None else resolved
        return self._resolve(target, attribute=name)

    def __getitem__(self, name: str) -> _EngineFunction:
        if not isinstance(name, str) or not name:
            msg = f"a function name must be a nonempty str, got {name!r}"
            raise TypeError(msg)
        return self._resolve(name)

    def __dir__(self) -> list[str]:
        # builtins() is what THIS space can call, so the directory, which is
        # also the interpreter's suggestion pool, never names a head another
        # space defines and stays inside the 750 candidates CPython accepts.
        names = {
            name.removesuffix("!").replace("-", "_")
            for name in self._space.builtins()
            if name and name.replace("-", "_").removesuffix("!").isidentifier()
        }
        names.update(
            name
            for name in ("neg",)
            if isinstance(operator_attribute_target(name), OperatorRecipe)
        )
        return sorted(set(super().__dir__()) | names)

    def __repr__(self) -> str:
        return f"<function namespace for {self._space.name}>"

_BUILTINS_CACHE_LOCK = threading.RLock()

_BUILTINS_CACHE: weakref.WeakKeyDictionary[
    Runtime, tuple[int, int, dict[str, tuple[str, ...]]]
] = weakref.WeakKeyDictionary()

_DEPRECATION_CACHE: weakref.WeakKeyDictionary[
    Runtime, dict[str, tuple[str, Remedy] | None]
] = weakref.WeakKeyDictionary()

_DEPRECATION_ANY: weakref.WeakKeyDictionary[Runtime, bool] = (
    weakref.WeakKeyDictionary()
)

def _invalidate_builtins_cache(rt: Runtime) -> None:
    """Advance the Python API epoch and discard every cached space view."""
    with _BUILTINS_CACHE_LOCK:
        epoch, function_generation, _ = _BUILTINS_CACHE.get(rt, (0, -1, {}))
        _BUILTINS_CACHE[rt] = (epoch + 1, function_generation, {})
        _DEPRECATION_CACHE.pop(rt, None)
        _DEPRECATION_ANY.pop(rt, None)

def _catalog_text(value: Any) -> str:
    """Render a catalog term the way its MeTTa source reads."""
    if isinstance(value, list):
        return f"({' '.join(_catalog_text(child) for child in value)})"
    return str(value)

def _decoded_remedy(term: Any) -> Remedy:
    """The catalog's remedy TERM as a Remedy, at the crossing that reads it.

    `(deprecated old "0.2.0" (use new))` keeps its third part as a term on
    purpose, so `explain` and a host warning render one declaration rather
    than two stringly registries. This is where that term becomes the same
    structured repair a Python-side refusal carries: `edit` is the term
    itself, and the title is its own MeTTa spelling, which is exactly the
    clause the warning already printed.

    Applicability is `prose` because a deprecation names the new head and
    not the call sites: writing `(use new)` into a program is a rename, and
    the catalog row says nothing about the arguments.
    """
    text = _catalog_text(term)
    return Remedy(text, "refactor", "prose", edit=parse(text))

def _deprecation(rt: Runtime, name: str) -> tuple[str, Remedy] | None:
    """Read one live declaration and cache it until the next explicit write."""
    with _BUILTINS_CACHE_LOCK:
        cache = _DEPRECATION_CACHE.setdefault(rt, {})
        if name in cache:
            return cache[name]
        any_declared = _DEPRECATION_ANY.get(rt)
    if any_declared is None:
        any_declared = bool(int(rt.apply_must("metta_py_deprecation_declared")))
        with _BUILTINS_CACHE_LOCK:
            _DEPRECATION_ANY[rt] = any_declared
    if not any_declared:
        with _BUILTINS_CACHE_LOCK:
            _DEPRECATION_CACHE.setdefault(rt, {})[name] = None
        return None
    row = rt.once("metta_deprecation(Name, Since, Remedy)", Name=name)
    declaration = (
        None
        if not row
        else (_catalog_text(row["Since"]), _decoded_remedy(row["Remedy"]))
    )
    with _BUILTINS_CACHE_LOCK:
        _DEPRECATION_CACHE.setdefault(rt, {})[name] = declaration
    return declaration

def _function_generation(rt: Runtime) -> int:
    """Read the engine's fun/1 generation through its Janus bridge.

    The service is the sum of SWI's ``last_modified_generation`` for the
    dynamic facts the per-space catalogue reads, ``fun/1``, ``fun_in/2``,
    ``fun_scoped/1`` and the exec-module parent chain, so a second space
    defining an already-registered name advances it although ``fun/1`` did
    not move; translator rules are static catalogue-neutral metadata
    [source: engine/metta.pl:metta_host_function_generation/1;
    commit=1f32a7c85d5c3bcbd8797218694ae5550c362e9a].
    """
    return int(rt.apply_must("metta_py_function_generation"))

def _space_builtins(rt: Runtime, space_name: str) -> list[str]:
    """Read one engine-generation-stamped per-space callable catalogue.

    Keyed by space because the answer differs by space: a head whose
    equations live in another space's module is registered process-wide
    but is not callable from here, and a namespace that listed it resolved
    calls that answered themselves unreduced [tested:
    test_a_namespace_lists_and_resolves_only_what_its_space_can_call;
    commit=1f32a7c85d5c3bcbd8797218694ae5550c362e9a].
    """
    while True:
        observed_generation = _function_generation(rt)
        with _BUILTINS_CACHE_LOCK:
            epoch, cached_generation, catalogues = _BUILTINS_CACHE.setdefault(
                rt, (0, observed_generation, {})
            )
            if cached_generation != observed_generation:
                catalogues = {}
                _BUILTINS_CACHE[rt] = (epoch, observed_generation, catalogues)
            cached = catalogues.get(space_name)
            if cached is not None:
                return list(cached)
        discovered = tuple(rt.builtins(space_name))
        confirmed_generation = _function_generation(rt)
        if confirmed_generation != observed_generation:
            continue
        with _BUILTINS_CACHE_LOCK:
            current_epoch, current_generation, current = _BUILTINS_CACHE.get(
                rt, (0, -1, {})
            )
            if current_epoch != epoch or current_generation != confirmed_generation:
                continue
            current[space_name] = discovered
            return list(discovered)

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_mention_doors.py::test_catalogue_membership_answers_the_builtins_union', 'extensions/python/tests/ch18_performance/test_builtins_generation_cache.py::test_eval_definitions_reach_the_next_namespace_access', 'extensions/python/tests/ch20_extending_the_engine/test_builtins.py::test_builtins_equals_the_union_of_functions_and_special_forms'),
)
def builtins(space: _root.Space) -> list[str]:
    """Every function callable from this space, plus every special form.

    Its own equations, the ones it inherits, ``&self``'s shared ones and
    the engine's builtins, with the translator's special-form heads,
    sorted without duplicates. A head another space defines is
    registered process-wide (the translator's call-or-data question,
    which ``is_function`` answers) but is not callable here and is not
    listed here.
    """
    return _space_builtins(space._rt, str(space._space))

def _invalidate_builtins(space: _root.Space) -> None:
    """Discard cached catalogues after an engine-side mutation."""
    _invalidate_builtins_cache(space._rt)

def _warn_deprecated(space: _root.Space, name: str, *, stacklevel: int) -> None:
    """Warn from the caller's frame when the catalog retires ``name``."""
    declaration = _deprecation(space._rt, name)
    if declaration is None:
        return
    since, remedy = declaration
    #: The warning is an instance rather than a class so the decoded
    #: remedy rides on it: `warnings.warn` uses the instance's own class
    #: as the category, so `pytest.warns(DeprecationWarning)` and
    #: `except DeprecationWarning` are unchanged, and a caller recording
    #: warnings reads `record[0].message.remedy`.
    warnings.warn(
        refusing(
            DeprecationWarning(f"{name} is deprecated since {since}; {remedy}"),
            remedy=remedy,
        ),
        stacklevel=stacklevel,
    )

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.boolean,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_registration_failure_leaves_nothing_half_registered', 'extensions/python/tests/ch11_python_as_a_notation/test_adoptions.py::test_union_expansion_is_bounded', 'extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_a_namespace_lists_and_resolves_only_what_its_space_can_call'),
    binding=_doors.Binding('metta_py_is_function', _doors.Wire.goal),
)
def is_function(space: _root.Space, name: str) -> bool:
    """Report whether the name is registered as a function anywhere.

    This is the translator's call-or-data question and holds wherever a
    term compiles; ``is_function_here`` asks whether the head answers
    from THIS space, and ``builtins()`` lists what this space can call.
    """
    _require_name(name, "is_function")
    return bool(space._rt.once("metta_py_is_function(Name)", Name=name))

def _is_catalogued(space: _root.Space, name: str) -> bool:
    """Point membership in this space's callable catalogue, no list build."""
    return bool(
        space._rt.once(
            "metta_py_catalogue_member(Space, Name)", Space=space._space, Name=name
        )
    )

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.boolean,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_r2_space_handle.py::test_a_space_is_the_grounded_handle_species_and_import_operand', 'extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_a_namespace_lists_and_resolves_only_what_its_space_can_call', 'extensions/python/tests/ch11_python_as_a_notation/test_host_island.py::test_unknown_host_callee_islands_implicitly'),
    binding=_doors.Binding('metta_py_function_visible', _doors.Wire.goal),
)
def is_function_here(space: _root.Space, name: str) -> bool:
    """Whether a function would answer from THIS space: it has clauses
    this space's module sees, its own or the shared ones in user.
    Another space's equations are invisible here and do not count.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    _require_name(name, "is_function_here")
    return bool(
        space._rt.once(
            "metta_py_function_visible(Space, Name)", Space=space._space, Name=name
        )
    )

def _is_function_inherited(space: _root.Space, name: str) -> bool:
    """Whether a head answers here through the space chain while this
    space defines nothing of its own for it: a space this one inherits
    from defines it, or `&self` does and this is another space. An engine
    builtin is not an answer, because shadowing one is the same-space
    collision `is_function_here` already refuses. This is the question
    `@typing.override` asks, and the reason `is_function` cannot answer
    it: that one is process-wide and says yes for a head defined in an
    unrelated space [tested: test_override_is_refused_when_nothing_is_shadowed;
    commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49].
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    _require_name(name, "is_function_inherited")
    return bool(
        space._rt.once(
            "metta_py_function_inherited(Space, Name)",
            Space=space._space,
            Name=name,
        )
    )

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.sequence,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync, _doors.Tier.async_),
    evidence=('extensions/python/tests/ch11_python_as_a_notation/test_ide_surface.py::test_declarations_carry_arrows_arities_and_documentation', 'extensions/python/tests/ch17_concurrency_and_the_loop/test_aio.py::test_aio_plain_methods_forward_on_the_worker'),
    binding=_doors.Binding('metta_py_arities', _doors.Wire.goal),
)
def arities(space: _root.Space, name: str) -> list[int]:
    """Compiled predicate arities for a name: MeTTa arity plus one each."""
    row = space._rt.once("metta_py_arities(Name, As)", Name=name)
    return list(row.get("As", []))

def _disassemble(space: _root.Space, name: str) -> str:
    """The Prolog clauses a function name compiled to, dis for the
    translator: one listing per registered arity, resolved in this
    space's module. What the engine RUNS for a call, which is the
    debuggability bytecode has and homoiconicity alone does not
    give, since (= ...) atoms are the source, not the compilation.
    Also reachable as m.fn[name].compiled.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    _require_name(name, "disassemble")
    row = space._rt.once(
        "metta_py_disassemble(Space, Name, Text)", Space=space._space, Name=name
    )
    if not row:
        msg = (
            f"{name!r} has no compiled clauses here; is_function() "
            f"tells whether the engine knows the name at all"
        )
        raise MettaError(
            msg
        )
    return str(row["Text"])

@_doors.door(
    kind=_doors.Kind.introspection,
    answers=_doors.AnswersAs.value,
    effect=_doors.EffectClass.readOnlyLookup,
    determinism=_doors.Determinism.det,
    tiers=(_doors.Tier.sync,),
    evidence=('extensions/python/tests/ch04_spaces_and_matching/test_answer_protocol.py::test_fn_decodes_exactly_as_value', 'extensions/python/tests/ch10_errors_and_refusals/test_error_answers.py::test_fn_doors_split_the_same_way', 'extensions/python/tests/ch11_python_as_a_notation/test_fn_protocol.py::test_a_namespace_lists_and_resolves_only_what_its_space_can_call'),
    is_property=True,
)
def fn(space: _root.Space) -> _FunctionNamespace:
    """Functions visible here, as bound attribute or exact-name handles.

        car = m.fn.car_atom
        car(m.parse("(1 2 3)"))     # [1]
        m.fn["=="](1, 1).one()      # True

    Underscores transliterate to hyphens. Brackets preserve exact
    punctuation, and an unknown name raises at access rather than
    becoming a later empty evaluation.
    """
    return _FunctionNamespace(space)

# Resolve annotations after definitions so peer imports can finish.
if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
