"""Purpose: represent lint findings and cache one engine registry snapshot.
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
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .atoms import Atom
from .errors import EngineError

#: The guide's lint section is the catalogue: every kind, what it means and
#: which severity it carries. One link serves the whole family rather than
#: one per kind, because a reader who has one finding usually wants the
#: neighbouring kinds too. NOT the generated reference page, which
#: reproduces signatures and docstrings and names no kind at all.
_LINT_DOCS = (
    "https://github.com/trueagi-io/PeTTa/blob/main/website/guide/run-query.md"
    "#lint-a-space"
)


@dataclass(frozen=True)
class Finding:
    """One diagnostic in the LSP's own vocabulary: what and where in the
    first four fields, and how much, what instead, where to read, the
    structured parts, and the machine-applicable edit in the next five.

    severity is LSP's: "error" (the program is wrong), "warning" (almost
    certainly not what was meant), "information" (true and worth knowing),
    "hint" (a heuristic). autofix, when present, is an ATOM: the stored
    atom rewritten with the simplification applied, so applying the fix
    is remove(finding.atom) then add(finding.autofix), no source
    positions needed.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    kind: str
    subject: str
    detail: str
    atom: Atom
    severity: str = "warning"
    suggestion: str | None = None
    docs_link: str = _LINT_DOCS
    payload: Mapping[str, Any] | None = None
    autofix: Atom | None = None

    def __str__(self) -> str:
        rendered = f"[{self.kind}] {self.subject}: {self.detail}"
        if self.suggestion is not None:
            rendered += f" (did you mean {self.suggestion}?)"
        if self.autofix is not None:
            rendered += f" (fix: {self.autofix})"
        return rendered


class EngineRegistry:
    """One cached view of engine function facts during a lint pass."""

    __slots__ = (
        "_arities",
        "_functions",
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
        self._arities: dict[str, frozenset[int]] = {}
        self._tabled: frozenset[str] | None = None
        self._known: frozenset[str] | None = None
        self._operations: dict[str, str | None] = {}
        self._types: dict[str, str] = {}

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

    def known_names(self) -> frozenset[str]:
        """Every name fun/1 enumerates, once per pass: the pool a typo
        suggestion draws from. metta_translated_head/1 is a checking
        predicate and does not enumerate, so special forms come from the
        caller's own vocabulary instead.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        if self._known is None:
            row = self._runtime.once("findall(_F, fun(_F), L)")
            raw = row.get("L")
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
                "petta_py_decode_shared(W, X, _), 'get-type'(X, T0), swrite(T0, T)",
                W=atom.to_wire(),
            )
            cached = str(row.get("T"))
            self._types[key] = cached
        return cached
