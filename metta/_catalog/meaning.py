"""Purpose: the engine's own answer to "what gives this head meaning", and the
verdict both head diagnostics draw from it. EngineRegistry caches the function,
special-form, arity and type facts for one pass; head_meaning turns them into
one HeadMeaning that lint() renders as findings and why() renders as a
sentence.
Assumes:
  - translator.pl's metta_translated_head/1 answers true for every head the
    translator compiles instead of a function defining it, across both of
    its routes [source engine/translator.pl:895]
Guarantees:
  - each function, special-form and arity query crosses the engine once per
    distinct name in a lint pass [tested
    test_registry_queries_are_native_and_cached_per_name]
  - a head the translator compiles is known to the registry even though it
    answers false to fun/1 [tested test_a_special_form_is_a_known_head]
  - malformed engine arity rows raise EngineError instead of changing a
    diagnosis [tested test_registry_queries_are_native_and_cached_per_name]
  - operation effects are read from the reflected ``op`` and ``effect`` facts,
    so crossing diagnostics consume the lattice instead of recreating it
    [tested: test_known_map_filter_and_fold_111x_shapes_are_linted;
    commit=acb40f1912f131ae088083d1af29b4b283019bea]
  - lint() and why() reach the same verdict about the same head, so a
    special form is never reported as an unknown name and a call at an
    undefined arity is named by both [tested:
    test_why_and_lint_agree_about_a_special_form,
    test_why_and_lint_agree_about_a_call_at_an_undefined_arity,
    test_why_and_lint_draw_suggestions_from_one_pool; commit=bd3a1bbad63952fc7c0d7367f38237dd1c219d8b]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
from typing import Any

from metta._atoms.factories import Atom
from metta._errors.errors import EngineError

#: How alike two names have to be before one is offered for the other. It is
#: ONE number because two diagnostics answering the same question at different
#: thresholds is the drift this module exists to remove; 0.8 is the tighter of
#: the two it replaces, and every near miss the suite pins clears it
#: (car-atmo/car-atom 0.875, car-atomm/car-atom 0.941, doubl/double 0.909).
_SUGGESTION_CUTOFF = 0.8


@dataclass(frozen=True)
class HeadMeaning:
    """What gives one head meaning here, and what to say when nothing does.

    ``route`` is the engine's own vocabulary: "function" for a name fun/1
    answers to, "translated" for one the translator compiles, "data" for a
    head only stored atoms carry, and None when nothing carries it at all.
    ``arities`` holds the MeTTa ARGUMENT counts a function is defined for,
    already converted from the predicate arities the engine registers, so no
    consumer subtracts the output slot for itself.
    """

    name: str
    arguments: int
    route: str | None
    arities: frozenset[int]
    suggestion: str | None

    @property
    def carried(self) -> bool:
        """Whether anything at all gives this head meaning."""
        return self.route is not None

    @property
    def wrong_arity(self) -> bool:
        """Whether a function is called at an argument count it has no clause for."""
        return bool(self.arities) and self.arguments not in self.arities


def head_meaning(
    name: str,
    arguments: int,
    registry: EngineRegistry,
    data_heads: frozenset[str] | set[str] = frozenset(),
) -> HeadMeaning:
    """Decide what carries one head, asking every question the engine answers.

    The engine gives a head meaning two ways and the check has to ask both:
    fun/1 for a function and metta_translated_head/1 for a form the
    translator compiles. Asking fun/1 alone reported every correct use of
    `if`, `case` and `collapse` as undefined, 723 of them over this
    repository's examples/, and why() was still asking it alone in 0.7.3,
    answering "nothing here is headed by if, and no function has that name;
    did you mean if?".
    """
    if registry.is_function(name):
        route: str | None = "function"
    elif registry.is_special_form(name):
        route = "translated"
    elif name in data_heads:
        route = "data"
    else:
        route = None
    #An engine arity counts the output slot; a call site counts arguments.
    arities = (
        frozenset(arity - 1 for arity in registry.arities(name))
        if route == "function"
        else frozenset()
    )
    return HeadMeaning(name, arguments, route, arities, _closest(name, registry, data_heads))


def _closest(
    name: str, registry: EngineRegistry, data_heads: frozenset[str] | set[str]
) -> str | None:
    """The one name close enough to be worth offering, or None.

    The pool is the whole language catalogue plus whatever the caller can see
    stored, so a mistyped SPECIAL FORM is suggested too: fun/1 does not
    enumerate them, and drawing from it alone left `collapes` with nothing to
    offer. The name itself is never a candidate, which is what produced
    "did you mean if?" for `if`.
    """
    pool = (registry.catalogue() | frozenset(data_heads)) - {name}
    close = get_close_matches(name, pool, n=1, cutoff=_SUGGESTION_CUTOFF)
    return close[0] if close else None


class EngineRegistry:
    """One cached view of engine function facts during a lint pass."""

    __slots__ = (
        "_arities",
        "_builtin",
        "_functions",
        "_honoured",
        "_known",
        "_operations",
        "_runtime",
        "_special",
        "_tabled",
        "_types",
    )

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime
        self._functions: dict[str, bool] = {}
        self._special: dict[str, bool] = {}
        self._builtin: dict[str, bool] = {}
        self._arities: dict[str, frozenset[int]] = {}
        self._tabled: frozenset[str] | None = None
        self._known: frozenset[str] | None = None
        self._operations: dict[str, str | None] = {}
        self._types: dict[str, str] = {}
        self._honoured: dict[str, bool] = {}

    def tabled(self) -> frozenset[str]:
        """The function names tabled right now, in any space.

        lib_tabling reflects each live declaration into &metta as a
        (tabled Space Name Arity) fact, so this is one query rather than a
        walk. A space with tabling never loaded holds none and answers the
        empty set, which is why the query is over &metta and not over a
        predicate that would not exist.
        """
        if self._tabled is None:
            row = self._runtime.once(
                "findall(_N, 'get-atoms'('&metta', [tabled, _S, _N, _A]), L)"
            )
            raw = row.get("L")
            names = raw if isinstance(raw, (list, tuple)) else []
            self._tabled = frozenset(str(name) for name in names)
        return self._tabled

    def types_a_call(self, head: str) -> bool:
        """Whether the engine reads a declaration under this head as a CALL type.

        Asked, never copied. `_is_arrow_head` matches the arrow FRAME, which is
        what an author's intent looks like and what the arity and
        declared-function diagnostics want. This is the narrower question of
        what the engine will HONOUR, and the two differ today: `-[det]->`
        parses through `metta_arrow_type_shape/5` and is still refused by
        `untypable_declarations/2`, whose literal `[->|_]` decides it. A
        function declared with one therefore compiles unchecked and answers
        IncorrectNumberOfArguments for every call. When the engine learns the
        annotated spelling this answer follows it with nothing here to change,
        which is why it is a query and not a table.
        """
        known = self._honoured.get(head)
        if known is None:
            row = self._runtime.once(
                "(   untypable_declarations([[Head, 'Number', 'Number']], _)"
                " -> Answer = no"
                " ;   Answer = yes"
                " )",
                Head=head,
            )
            known = str(row.get("Answer")) == "yes"
            self._honoured[head] = known
        return known

    def is_function(self, name: str) -> bool:
        known = self._functions.get(name)
        if known is None:
            row = self._runtime.once("( fun(F) -> T = true ; T = false )", F=name)
            known = row.get("T") in ("true", True)
            self._functions[name] = known
        return known

    def is_special_form(self, name: str) -> bool:
        """Whether the translator compiles this head rather than equations defining it.

        fun/1 alone is not the question "does anything give this head
        meaning". A special form is compiled by the translator, and most are
        never registered as functions: of the 47 heads translate_special_dl/5
        carries, 29 answer false to fun/1, `if`, `case`, `collapse`, `unify`,
        `chain`, `once` and `forall` among them, and the 6 heads
        rewrite_streamops/2 carries answer false as well [measured
        2026-08-17]. The engine already asks this question for its own
        reasons, and metta_translated_head/1 reads both sets of clause heads
        rather than keeping a list, so a form added to the translator is
        covered the day it is added.
        """
        known = self._special.get(name)
        if known is None:
            row = self._runtime.once(
                "( metta_translated_head(F) -> T = true ; T = false )", F=name
            )
            known = row.get("T") in ("true", True)
            self._special[name] = known
        return known

    def is_builtin(self, name: str) -> bool:
        """Whether the engine ships this head, as opposed to a space defining it.

        `builtin_fun/1` rather than `fun/1`, because `fun/1` enumerates user
        functions too: defining one takes the count from 298 to 299. The
        engine keeps the two facts apart deliberately and says why at
        `engine/metta/registration.pl:596-607` -- a builtin stays visible from
        every space even when a named space defines its name, which `fun_in/2`
        cannot carry, and the pair is what `runtime_guarded_builtin_call/1`
        uses to decide a builtin was overridden.
        """
        known = self._builtin.get(name)
        if known is None:
            row = self._runtime.once(
                "( builtin_fun(F) -> T = true ; T = false )", F=name
            )
            known = row.get("T") in ("true", True)
            self._builtin[name] = known
        return known

    def arities(self, name: str) -> frozenset[int]:
        cached = self._arities.get(name)
        if cached is not None:
            return cached
        row = self._runtime.once("findall(_A, arity(F, _A), L)", F=name)
        raw = row.get("L")
        if not isinstance(raw, (list, tuple)) or any(
            isinstance(value, bool) or not isinstance(value, int) for value in raw
        ):
            msg = f"engine arity registry returned an invalid list for {name!r}: {raw!r}"
            raise EngineError(
                msg
            )
        result = frozenset(raw)
        self._arities[name] = result
        return result

    def operation_effect(self, name: str) -> str | None:
        """Return one Python operation's published effect, or None."""
        if name in self._operations:
            return self._operations[name]
        row = self._runtime.once(
            "findall(_E, ('get-atoms'('&metta', [op, F, _A, _K]), "
            "             'get-atoms'('&metta', [effect, F, _E])), L)",
            F=name,
        )
        raw = row.get("L")
        effects = {str(effect) for effect in raw} if isinstance(raw, (list, tuple)) else set()
        if len(effects) > 1:
            msg = f"operation effect registry returned conflicting ranks for {name!r}: {effects!r}"
            raise EngineError(msg)
        effect = next(iter(effects), None)
        self._operations[name] = effect
        return effect

    def catalogue(self) -> frozenset[str]:
        """Every name the language knows, read once per pass.

        This is the pool a typo suggestion draws from: the union of fun/1
        and the translator's own special-form heads, which is what
        metta_py_builtins/1 already answers for m.builtins(). Reading fun/1
        alone left a mistyped `collapes` with nothing to offer, because
        metta_translated_head/1 is a checking predicate and does not
        enumerate, so 29 of the 47 forms translate_special_dl/5 carries are
        invisible to it.
        """
        if self._known is None:
            row = self._runtime.once("metta_py_builtins(Names)")
            raw = row.get("Names")
            names = raw if isinstance(raw, (list, tuple)) else []
            self._known = frozenset(str(name) for name in names)
        return self._known

    def type_of(self, atom: Atom) -> str:
        """The engine's own get-type answer for one atom, printed, cached
        per printed form. Total: an untypable atom answers %Undefined%.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        key = str(atom)
        cached = self._types.get(key)
        if cached is None:
            row = self._runtime.once(
                "metta_py_decode_shared(W, X, _), 'get-type'(X, T0), swrite(T0, T)",
                W=atom.to_wire(),
            )
            cached = str(row.get("T"))
            self._types[key] = cached
        return cached
