"""Purpose: declare value algebras and run their one generic tagged-rule form.

Assumes:
  - facts and rules rest in a space as ordinary ``(fact tag proposition)``
    and ``(rule tag head (premises ...))`` atoms.
Guarantees:
  - only laws checked over a finite carrier, or trusted shipped preset laws,
    license answer fusion [tested:
    test_a_declared_algebra_without_laws_answers_in_order_and_unfused;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - declared nonnegative rates drive an isolated seeded sampler without
    changing ordinary queries [tested:
    test_declared_rates_make_seeded_selection_match_their_distribution;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a linear algebra refuses overlapping premise-occurrence ledgers before it
    publishes a derived answer [tested:
    test_a_linear_algebra_refuses_the_second_spend_of_one_premise;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the amplitude preset is usable only by a context declaring the finite,
    contractive, staged fragment [tested:
    test_amplitudes_interfere_inside_the_fragment_and_are_refused_outside;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - grounded tensor tags retain their live derivative graph through generic
    rule matching and declared operations [tested:
    test_a_declared_gradient_algebra_propagates_derivatives_through_a_derivation;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - rule premises and evaluation goals retain directional pattern matching
    after public ``unify`` becomes symmetric [tested:
    test_algebra_patterns_do_not_bind_variables_inside_stored_candidates;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - the module object is also the root algebra constructor, and the shipped
    counting, tropical, provenance, and ranking objects are accepted directly
    by every carrier [tested:
    test_algebra_module_is_the_constructor_and_the_old_space_doors_are_retired,
    test_requested_carrier_spellings_are_declared; commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - tagged answers retain their derivation tree so why() and under() do not
    rerun the query [tested:
    test_tagged_derivations_flow_through_match_and_reinterpret_without_requery;
    commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]
  - tagged counts share the positive-limit contract used by ordinary queries
    [tested: test_tagged_count_and_match_refuse_zero_with_the_same_message;
    commit=61e107a8105a5cdaea164f615812a684b12d8fe3]
  - tagged fixpoint evaluation carries one absolute timeout through its Python
    scans; each algebra operation receives the remaining time and remaining
    call-wide inference quota [tested:
    test_tagged_algebra_forwards_bounds_to_every_evaluating_door,
    test_tagged_algebra_debits_inferences_across_operations;
    commit=51e719767e3dd322a9cf88bd096410bbc5647493]
  - certified acyclic integer-tagged programs propagate query demands while
    retaining complete proof bags and the full evaluator's refusal boundaries
    [tested: test_demand_preserves_complete_derivation_bags,
    test_demand_preserves_global_cycle_and_round_failures; commit=c4f52c8ebbe2bd36973b150bf74cf9e54435d58d]
Decides:
  - ``contraction`` is a capability, while the remaining public law names are
    equations checked exhaustively over the declared finite carrier.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import itertools
import math
import random
import sys
import time
from collections.abc import Callable, Generator, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from fractions import Fraction
from numbers import Real
from types import ModuleType
from typing import Any, Final

from ._space import Space
from ._space_execution import evaluate_accounted
from ._space_objects import _limits, _validate_limit
from .atoms import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Undefined,
    Variable,
    _decode,
    _encode,
    _match,
    parse,
    substitute,
)
from .errors import InferenceLimitError, MettaError, TimeLimitError
from .vocabularies import EffectClass, Semiring, SemiringOrder

__all__ = [
    "AlgebraDeclarationError",
    "AlgebraDerivation",
    "AlgebraEvaluation",
    "AlgebraEvaluationError",
    "AlgebraLawError",
    "AlgebraOperationError",
    "AlgebraRequirementError",
    "Amplitude",
    "DeclaredAlgebra",
    "LinearEvidenceError",
    "PlanDecision",
    "RateDeclarationError",
    "TaggedAnswer",
    "counting",
    "declare",
    "evaluate",
    "prob",
    "prov",
    "ranked",
    "resolve",
    "sample",
    "tagged_fact",
    "tagged_rule",
    "tropical",
]


class AlgebraDeclarationError(MettaError, ValueError):
    """A declaration is incomplete, conflicting, or cannot be certified."""


class AlgebraLawError(AlgebraDeclarationError):
    """A named law has a concrete counterexample in the declared carrier."""


class AlgebraRequirementError(AlgebraDeclarationError):
    """A context lacks a capability required by its declared algebra."""


class AlgebraOperationError(MettaError):
    """A declared operation does not answer one value for two carrier values."""


class RateDeclarationError(AlgebraDeclarationError):
    """A rate is not a finite nonnegative real value."""


class LinearEvidenceError(MettaError):
    """One stored premise occurrence was consumed twice in one derivation."""


@dataclass(slots=True)
class _EvaluationBudget:
    """One call's absolute wall deadline and remaining engine-step quota."""

    timeout: float | None
    inferences: int | None
    deadline: float | None
    remaining_inferences: int | None

    @classmethod
    def from_call(
        cls, timeout: float | None, inferences: int | None
    ) -> _EvaluationBudget:
        limits = _limits(timeout, inferences)
        if limits is None:
            return cls(None, None, None, None)
        seconds = None if limits[0] < 0 else limits[0]
        steps = None if limits[1] < 0 else limits[1]
        deadline = None if seconds is None else time.monotonic() + seconds
        return cls(seconds, steps, deadline, steps)

    def checkpoint(self) -> float | None:
        """Raise at expiry, otherwise answer the time left for one engine call."""
        if self.deadline is None:
            return None
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise self._time_limit_error()
        return remaining

    def _time_limit_error(self) -> TimeLimitError:
        msg = f"the {self.timeout} second time limit was reached"
        return TimeLimitError(msg)

    def _inference_limit_error(self) -> InferenceLimitError:
        msg = f"the {self.inferences} inference limit was reached"
        return InferenceLimitError(msg)

    def evaluate_operation(
        self, metta: Space, target: Atom
    ) -> list[Atom | Undefined]:
        """Evaluate one algebra operation and debit its measured engine work."""
        remaining_time = self.checkpoint()
        remaining_steps = self.remaining_inferences
        if remaining_steps is not None and remaining_steps <= 0:
            raise self._inference_limit_error()
        try:
            if remaining_steps is None:
                return metta.eval(target, timeout=remaining_time)
            # Each eager eval is a fresh engine crossing, so giving it the original
            # quota would reset the caller's budget once per algebra operation.
            # The accounted eval reports its own goal's inference delta in the SAME
            # crossing. Sampling with Space.stats() here would add two crossings per
            # operation and spend more on the meter than on a small operation.
            answers, spent = evaluate_accounted(
                metta.runtime,
                metta.name,
                target,
                remaining_time,
                remaining_steps,
            )
        except TimeLimitError as error:
            raise self._time_limit_error() from error
        except InferenceLimitError as error:
            raise self._inference_limit_error() from error
        self.remaining_inferences = remaining_steps - spent
        return answers


@dataclass(frozen=True, slots=True)
class Amplitude:
    """An exact complex value with rational real and imaginary components."""

    real: Fraction
    imag: Fraction = Fraction(0)

    def __init__(
        self, real: int | Fraction, imag: int | Fraction = 0
    ) -> None:
        """Store exact rational components."""
        object.__setattr__(self, "real", Fraction(real))
        object.__setattr__(self, "imag", Fraction(imag))

    def __add__(self, other: Amplitude) -> Amplitude:
        """Add two amplitudes exactly."""
        return Amplitude(self.real + other.real, self.imag + other.imag)

    def __mul__(self, other: Amplitude) -> Amplitude:
        """Multiply two amplitudes exactly."""
        return Amplitude(
            self.real * other.real - self.imag * other.imag,
            self.real * other.imag + self.imag * other.real,
        )

    def __neg__(self) -> Amplitude:
        """Negate both exact components."""
        return Amplitude(-self.real, -self.imag)

    def __complex__(self) -> complex:
        """Convert to Python's inexact complex carrier."""
        return complex(float(self.real), float(self.imag))


@dataclass(frozen=True, slots=True)
class DeclaredAlgebra:
    """One catalog algebra after law and requirement normalization."""

    name: str
    combine: str
    extend: str
    zero: Atom
    one: Atom
    laws: frozenset[str]
    carrier: tuple[Atom, ...]
    requires: frozenset[str]
    order: SemiringOrder | None = None

    def operation(
        self,
        metta: Space,
        name: str,
        left: Atom,
        right: Atom,
        *,
        budget: _EvaluationBudget | None = None,
    ) -> Atom:
        """Apply a declared binary operation and require one answer."""
        if isinstance(left, Grounded) and isinstance(right, Grounded):
            left_value, right_value = _decode(left), _decode(right)
            if (
                not isinstance(left_value, bool)
                and not isinstance(right_value, bool)
                and isinstance(left_value, Real)
                and isinstance(right_value, Real)
            ):
                if name == "+":
                    return _encode(left_value + right_value)
                if name == "*":
                    return _encode(left_value * right_value)
                if name == "min":
                    return _encode(min(left_value, right_value))
                if name == "max":
                    return _encode(max(left_value, right_value))
        # policy-inventory-exempt: mechanism-internal; reason=the two role names a declaration coins for its own combine and extend operations, which _register_operation spells as <algebra>-<role>; evidence=extensions/python/metta/algebra.py:_operation_name
        if name in {"plus", "times"}:
            return Expression((Symbol(name), left, right))
        target = Expression((Symbol(name), left, right))
        answers = (
            metta.eval(target)
            if budget is None
            else budget.evaluate_operation(metta, target)
        )
        if len(answers) != 1:
            msg = (
                f"algebra_operation_not_single({self.name}, {name}, "
                f"{left}, {right}, answers={len(answers)})"
            )
            raise AlgebraOperationError(msg)
        result = answers[0]
        if isinstance(result, Undefined):
            msg = (
                f"algebra_operation_undefined({self.name}, {name}, "
                f"{left}, {right}, why={result.why})"
            )
            raise AlgebraOperationError(msg)
        return result

    def combine_values(
        self,
        metta: Space,
        left: Atom,
        right: Atom,
        *,
        budget: _EvaluationBudget | None = None,
    ) -> Atom:
        """Combine alternative derivations."""
        return self.operation(
            metta,
            self.combine,
            left,
            right,
            budget=budget,
        )

    def extend_values(
        self,
        metta: Space,
        left: Atom,
        right: Atom,
        *,
        budget: _EvaluationBudget | None = None,
    ) -> Atom:
        """Extend one derivation through a premise."""
        return self.operation(
            metta,
            self.extend,
            left,
            right,
            budget=budget,
        )


@dataclass(frozen=True, slots=True)
class PlanDecision:
    """An evaluation choice, including a withheld law-gated optimization."""

    optimization: str
    applied: bool
    missing_laws: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Trace:
    """One retained algebra-neutral derivation node."""

    source: int
    raw: Atom
    children: tuple[_Trace, ...] = ()
    is_rule: bool = False


@dataclass(frozen=True, slots=True)
class AlgebraDerivation:
    """The derivation forest captured while an annotated answer was produced."""

    answer: Any
    algebra: str
    alternatives: tuple[_Trace, ...]

    def render(self) -> str:
        """Render each source tag and rule edge without consulting a space."""
        lines = [f"{self.answer} under {self.algebra}"]

        def visit(trace: _Trace, indent: int) -> None:
            kind = "rule" if trace.is_rule else "source"
            lines.append(
                f"{'  ' * indent}{kind} {trace.source}: {trace.raw}"
            )
            for child in trace.children:
                visit(child, indent + 1)

        for alternative in self.alternatives:
            visit(alternative, 1)
        return "\n".join(lines)

    def __str__(self) -> str:
        """Render the retained derivation in its human-readable form."""
        return self.render()


@dataclass(frozen=True, slots=True)
class TaggedAnswer:
    """A proposition, its annotation, and the retained derivation that made it."""

    value: Any
    tag: Atom
    tokens: frozenset[int]
    proof: tuple[int, ...]
    _derivations: tuple[_Trace, ...] = field(default=(), repr=False, compare=False)
    _space: Space | None = field(default=None, repr=False, compare=False)
    _algebra: str = field(default="unknown", repr=False, compare=False)
    _plan: tuple[PlanDecision, ...] = field(default=(), repr=False, compare=False)

    @property
    def annotation(self) -> Any:
        """The carrier value, decoded when it is an ordinary ground value."""
        return _decode(self.tag) if isinstance(self.tag, Grounded) else self.tag

    @property
    def plan(self) -> tuple[PlanDecision, ...]:
        """Law-gated decisions made while this answer's alternatives fused."""
        return self._plan

    def why(self) -> AlgebraDerivation:
        """Return the derivation captured by the original ask."""
        traces = self._derivations or (_Trace(-1, self.tag),)
        return AlgebraDerivation(self.value, self._algebra, traces)

    def under(self, carrier: Any) -> TaggedAnswer:
        """Interpret this retained derivation under another algebra, no requery."""
        if self._space is None:
            msg = "this answer carries no owning space for algebra reinterpretation"
            raise AlgebraEvaluationError(msg)
        declaration = resolve(self._space, carrier)
        traces = self._derivations or (_Trace(-1, self.tag),)
        annotation = _interpret_alternatives(self._space, declaration, traces)
        return replace(self, tag=annotation, _algebra=declaration.name)


@dataclass(frozen=True, slots=True)
class AlgebraEvaluation:
    """Answers and the observable law decisions that produced them."""

    answers: tuple[TaggedAnswer, ...]
    plan: tuple[PlanDecision, ...]


@dataclass(frozen=True, slots=True)
class _Rule:
    order: int
    tag: Atom
    head: Atom
    premises: tuple[Atom, ...]


_LAW_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "associative": ("combine-associative", "extend-associative"),
    "commutative": ("combine-commutative",),
    "distributive": ("left-distributive", "right-distributive"),
    "idempotent": ("combine-idempotent",),
    "contraction": ("contraction",),
}
_EQUATIONAL_LAWS: Final[frozenset[str]] = frozenset(
    {
        "combine-associative",
        "combine-commutative",
        "extend-associative",
        "extend-commutative",
        "left-distributive",
        "right-distributive",
        "combine-idempotent",
        "combine-zero-identity",
        "extend-one-identity",
        "extend-zero-annihilates",
    }
)
_KNOWN_LAWS: Final[frozenset[str]] = _EQUATIONAL_LAWS | {"contraction"}
_SEMIRING_LAWS: Final[frozenset[str]] = frozenset(
    {
        "combine-associative",
        "combine-commutative",
        "extend-associative",
        "left-distributive",
        "right-distributive",
        "combine-zero-identity",
        "extend-one-identity",
        "extend-zero-annihilates",
        "contraction",
    }
)


def _preset(
    name: str,
    combine: str,
    extend: str,
    zero: Any,
    one: Any,
    *,
    laws: frozenset[str] = _SEMIRING_LAWS,
    requires: Iterable[str] = (),
    order: SemiringOrder | None = None,
) -> DeclaredAlgebra:
    return DeclaredAlgebra(
        name,
        combine,
        extend,
        _encode(zero),
        _encode(one),
        laws,
        (),
        frozenset(requires),
        order,
    )


_PRESETS: Final[dict[str, DeclaredAlgebra]] = {
    "bool": _preset("bool", "max", "*", 0, 1),
    "bag": _preset("bag", "+", "*", 0, 1),
    "counting": _preset("counting", "+", "*", 0, 1),
    "set": _preset(
        "set", "max", "*", 0, 1, laws=_SEMIRING_LAWS | {"combine-idempotent"}
    ),
    "ranked": _preset("ranked", "max", "*", 0, 1, order=SemiringOrder.descending),
    "tropical": _preset(
        "tropical", "min", "+", Symbol("infinity"), 0, order=SemiringOrder.ascending
    ),
    "prob": _preset("prob", "+", "*", 0, 1, order=SemiringOrder.descending),
    "prov": _preset("prov", "plus", "times", Symbol("zero"), Symbol("one")),
    "budget": _preset(
        "budget", "min", "+", Symbol("infinity"), 0, order=SemiringOrder.ascending
    ),
    "amplitude": _preset(
        "amplitude",
        "amplitude-add",
        "amplitude-multiply",
        Amplitude(0),
        Amplitude(1),
        requires=("finite", "contractive", "staged"),
    ),
}

_REGISTRY: dict[tuple[int, str], DeclaredAlgebra] = {}


def _key(metta: Space, name: str) -> tuple[int, str]:
    return id(metta._rt), name


def _carrier_name(carrier: Any) -> str:
    """Normalize a declared object, Symbol, enum member, or exact name."""
    if isinstance(carrier, DeclaredAlgebra):
        return carrier.name
    if isinstance(carrier, Symbol):
        return carrier.name
    if isinstance(carrier, str):
        return carrier
    value = getattr(carrier, "value", None)
    if isinstance(value, str):
        return value
    msg = (
        "under= needs a DeclaredAlgebra, Symbol, semiring enum member, or "
        f"algebra name, not {type(carrier).__name__}"
    )
    raise TypeError(msg)


def resolve(metta: Space, carrier: Any) -> DeclaredAlgebra:
    """Resolve any public carrier spelling against one runtime catalog."""
    if isinstance(carrier, DeclaredAlgebra):
        registered = get(metta, carrier.name)
        return carrier if registered is None else registered
    return require(metta, _carrier_name(carrier))


def _canonical_laws(laws: Iterable[str]) -> frozenset[str]:
    out: set[str] = set()
    for law in laws:
        expanded = _LAW_ALIASES.get(law, (law,))
        unknown = set(expanded) - _KNOWN_LAWS
        if unknown:
            msg = f"algebra_law_unknown({sorted(unknown)!r})"
            raise AlgebraDeclarationError(msg)
        out.update(expanded)
    return frozenset(out)


def _catalog_declaration(metta: Space, name: str) -> DeclaredAlgebra | None:
    """Reify a direct ``&metta`` algebra row through the Python interface."""
    for atom in Space("&metta", _runtime=metta.runtime).atoms():
        if not isinstance(atom, Expression) or len(atom.children) != 9:
            continue
        head, declared_name, combine, extend, zero, one, laws, carrier, requires = (
            atom.children
        )
        if head != Symbol("algebra") or declared_name != Symbol(name):
            continue
        if not isinstance(combine, Symbol) or not isinstance(extend, Symbol):
            msg = f"algebra_catalog_operations_malformed({name})"
            raise AlgebraDeclarationError(msg)
        if (
            not isinstance(laws, Expression)
            or not laws.children
            or laws.children[0] != Symbol("laws")
        ):
            msg = f"algebra_catalog_fields_malformed({name})"
            raise AlgebraDeclarationError(msg)
        if (
            not isinstance(carrier, Expression)
            or not carrier.children
            or carrier.children[0] != Symbol("carrier")
        ):
            msg = f"algebra_catalog_fields_malformed({name})"
            raise AlgebraDeclarationError(msg)
        if (
            not isinstance(requires, Expression)
            or not requires.children
            or requires.children[0] != Symbol("requires")
        ):
            msg = f"algebra_catalog_fields_malformed({name})"
            raise AlgebraDeclarationError(msg)
        law_names = tuple(
            law.name for law in laws.children[1:] if isinstance(law, Symbol)
        )
        requirement_names = tuple(
            requirement.name
            for requirement in requires.children[1:]
            if isinstance(requirement, Symbol)
        )
        return DeclaredAlgebra(
            name=name,
            combine=combine.name,
            extend=extend.name,
            zero=zero,
            one=one,
            laws=_canonical_laws(law_names),
            carrier=tuple(carrier.children[1:]),
            requires=frozenset(requirement_names),
            order=_catalog_order(metta, name),
        )
    return None


def _catalog_order(
    metta: Space, name: str
) -> SemiringOrder | None:
    """Read the direction attached to an ordered semiring claim."""
    expected = (Symbol("claim"), Symbol("semiring"), Symbol(name), Symbol("ordered"))
    for atom in Space("&metta", _runtime=metta.runtime).atoms():
        if not isinstance(atom, Expression) or atom.children[:4] != expected:
            continue
        if len(atom.children) < 5 or not isinstance(atom.children[4], Symbol):
            # A bare `ordered` claim with no direction: the shipped rows all
            # carry one, so this is a claim written by hand, and counting
            # down from the best is what ordered meant before the direction
            # joined the row.
            return SemiringOrder.descending
        try:
            return SemiringOrder(atom.children[4].name)
        except ValueError:
            # A direction outside the declared vocabulary is not this claim's
            # direction; keep looking rather than inventing one.
            continue
    return None


def get(metta: Space, name: str) -> DeclaredAlgebra | None:
    """Find a user declaration or one of the shipped data presets."""
    preset = _PRESETS.get(name)
    if preset is not None:
        return replace(preset)
    catalog = _catalog_declaration(metta, name)
    key = _key(metta, name)
    if catalog is None:
        _REGISTRY.pop(key, None)
        return None
    return _REGISTRY.get(key, catalog)


def require(metta: Space, name: str) -> DeclaredAlgebra:
    declaration = get(metta, name)
    if declaration is None:
        presets = ", ".join(_PRESETS)
        msg = (
            f"algebra_not_declared({name}); shipped presets are {presets}, "
            "or algebra() may add another"
        )
        raise AlgebraDeclarationError(msg)
    return declaration


def _context_capabilities(metta: Space, algebra: str) -> frozenset[str]:
    context = Symbol(str(metta.name))
    for atom in Space("&metta", _runtime=metta.runtime).atoms():
        # policy-inventory-exempt: mechanism-internal; reason=three and four are the only lengths the annotations catalog row is written with, the fourth child being the optional (capabilities ...) field; evidence=extensions/python/metta/_space.py:annotations
        if not isinstance(atom, Expression) or len(atom.children) not in {3, 4}:
            continue
        if atom.children[:3] != (Symbol("annotations"), context, Symbol(algebra)):
            continue
        if len(atom.children) == 3:
            return frozenset()
        declared = atom.children[3]
        if not isinstance(declared, Expression) or not declared.children:
            return frozenset()
        return frozenset(
            capability.name
            for capability in declared.children[1:]
            if isinstance(capability, Symbol)
        )
    return frozenset()


def _require_context_capabilities(
    metta: Space, declaration: DeclaredAlgebra
) -> None:
    missing = declaration.requires - _context_capabilities(metta, declaration.name)
    if not missing:
        return
    refusal = (
        "amplitude_fragment_refused"
        if declaration.name == "amplitude"
        else "algebra_requirements_missing"
    )
    msg = (
        f"{refusal}({metta.name}, {declaration.name}, "
        f"missing={sorted(missing)!r})"
    )
    raise AlgebraRequirementError(msg)


def _same(left: Atom, right: Atom) -> bool:
    try:
        result = left == right
        return result if isinstance(result, bool) else bool(result)
    except (RuntimeError, TypeError, ValueError):
        return left is right


def _member(value: Atom, carrier: Sequence[Atom]) -> bool:
    return any(_same(value, candidate) for candidate in carrier)


def _counterexample(
    declaration: DeclaredAlgebra,
    law: str,
    inputs: tuple[Atom, ...],
    left: Atom,
    right: Atom,
) -> AlgebraLawError:
    return AlgebraLawError(
        f"algebra_law_violation({declaration.name}, {law}, "
        f"inputs={[str(value) for value in inputs]!r}, left={left}, right={right})"
    )


def _check_binary_closure(metta: Space, declaration: DeclaredAlgebra) -> None:
    for operation in (declaration.combine, declaration.extend):
        for left, right in itertools.product(declaration.carrier, repeat=2):
            result = declaration.operation(metta, operation, left, right)
            if not _member(result, declaration.carrier):
                msg = (
                    f"algebra_carrier_not_closed({declaration.name}, {operation}, "
                    f"inputs=({left}, {right}), result={result})"
                )
                raise AlgebraLawError(msg)


def _check_associative(
    metta: Space,
    declaration: DeclaredAlgebra,
    law: str,
    operation: Callable[[Space, Atom, Atom], Atom],
) -> None:
    for a, b, c in itertools.product(declaration.carrier, repeat=3):
        left = operation(metta, operation(metta, a, b), c)
        right = operation(metta, a, operation(metta, b, c))
        if not _same(left, right):
            raise _counterexample(declaration, law, (a, b, c), left, right)


def _check_commutative(
    metta: Space,
    declaration: DeclaredAlgebra,
    law: str,
    operation: Callable[[Space, Atom, Atom], Atom],
) -> None:
    for a, b in itertools.product(declaration.carrier, repeat=2):
        left = operation(metta, a, b)
        right = operation(metta, b, a)
        if not _same(left, right):
            raise _counterexample(declaration, law, (a, b), left, right)


def _check_idempotent(metta: Space, declaration: DeclaredAlgebra, law: str) -> None:
    for value in declaration.carrier:
        result = declaration.combine_values(metta, value, value)
        if not _same(result, value):
            raise _counterexample(declaration, law, (value,), result, value)


def _check_distributive(
    metta: Space, declaration: DeclaredAlgebra, law: str
) -> None:
    combine = declaration.combine_values
    extend = declaration.extend_values
    for a, b, c in itertools.product(declaration.carrier, repeat=3):
        if law == "left-distributive":
            left = extend(metta, a, combine(metta, b, c))
            right = combine(metta, extend(metta, a, b), extend(metta, a, c))
        else:
            left = extend(metta, combine(metta, a, b), c)
            right = combine(metta, extend(metta, a, c), extend(metta, b, c))
        if not _same(left, right):
            raise _counterexample(declaration, law, (a, b, c), left, right)


def _check_identity(
    metta: Space,
    declaration: DeclaredAlgebra,
    law: str,
    operation: Callable[[Space, Atom, Atom], Atom],
    identity: Atom,
) -> None:
    for value in declaration.carrier:
        for left, right in (
            (operation(metta, identity, value), value),
            (operation(metta, value, identity), value),
        ):
            if not _same(left, right):
                raise _counterexample(declaration, law, (value,), left, right)


def _check_zero_annihilates(
    metta: Space, declaration: DeclaredAlgebra, law: str
) -> None:
    extend = declaration.extend_values
    for value in declaration.carrier:
        for left, right in (
            (extend(metta, declaration.zero, value), declaration.zero),
            (extend(metta, value, declaration.zero), declaration.zero),
        ):
            if not _same(left, right):
                raise _counterexample(declaration, law, (value,), left, right)


def _check_law(metta: Space, declaration: DeclaredAlgebra, law: str) -> None:
    combine = declaration.combine_values
    extend = declaration.extend_values
    operation = combine if law.startswith("combine-") else extend
    if law.endswith("-associative"):
        _check_associative(metta, declaration, law, operation)
    elif law.endswith("-commutative"):
        _check_commutative(metta, declaration, law, operation)
    elif law == "combine-idempotent":
        _check_idempotent(metta, declaration, law)
    # policy-inventory-exempt: mechanism-internal; reason=these are the two law names that share one checker, so the dispatcher groups them where its other arms match a single name; evidence=extensions/python/metta/algebra.py:_check_distributive
    elif law in {"left-distributive", "right-distributive"}:
        _check_distributive(metta, declaration, law)
    elif law == "combine-zero-identity":
        _check_identity(metta, declaration, law, combine, declaration.zero)
    elif law == "extend-one-identity":
        _check_identity(metta, declaration, law, extend, declaration.one)
    elif law == "extend-zero-annihilates":
        _check_zero_annihilates(metta, declaration, law)


def _validate_laws(metta: Space, declaration: DeclaredAlgebra) -> None:
    equational = declaration.laws & _EQUATIONAL_LAWS
    if equational and not declaration.carrier:
        msg = (
            f"algebra_law_uncheckable({declaration.name}, "
            f"laws={sorted(equational)!r}, reason=finite_carrier_required)"
        )
        raise AlgebraLawError(msg)
    if not equational:
        return
    _check_binary_closure(metta, declaration)
    for law in sorted(equational):
        _check_law(metta, declaration, law)


def _list(head: str, values: Iterable[Any]) -> Expression:
    return Expression((Symbol(head), *(_encode(value) for value in values)))


def _symbol_list(head: str, values: Iterable[str]) -> Expression:
    return Expression((Symbol(head), *(Symbol(value) for value in values)))


def declare(
    metta: Space,
    name: str,
    *,
    combine: str,
    extend: str,
    zero: Any,
    one: Any,
    laws: Iterable[str] = (),
    carrier: Iterable[Any] = (),
    requires: Iterable[str] = (),
    order: SemiringOrder | None = None,
) -> Atom:
    """Check and add one algebra catalog atom, without replacing an old one."""
    if not name or not isinstance(name, str):
        msg = "algebra_name_must_be_a_nonempty_symbol"
        raise AlgebraDeclarationError(msg)
    if name in _PRESETS or get(metta, name) is not None:
        msg = f"algebra_already_declared({name})"
        raise AlgebraDeclarationError(msg)
    if not combine or not isinstance(combine, str):
        msg = f"algebra_operation_invalid({name}, combine)"
        raise AlgebraDeclarationError(msg)
    if not extend or not isinstance(extend, str):
        msg = f"algebra_operation_invalid({name}, extend)"
        raise AlgebraDeclarationError(msg)
    if order is not None and order not in set(SemiringOrder):
        msg = f"algebra_order_invalid({name}, {order!r})"
        raise AlgebraDeclarationError(msg)
    declaration = DeclaredAlgebra(
        name=name,
        combine=combine,
        extend=extend,
        zero=_encode(zero),
        one=_encode(one),
        laws=_canonical_laws(laws),
        carrier=tuple(_encode(value) for value in carrier),
        requires=frozenset(requires),
        order=order,
    )
    _validate_laws(metta, declaration)
    atom = Expression(
        (
            Symbol("algebra"),
            Symbol(name),
            Symbol(combine),
            Symbol(extend),
            declaration.zero,
            declaration.one,
            _symbol_list("laws", sorted(declaration.laws)),
            _list("carrier", declaration.carrier),
            _symbol_list("requires", sorted(declaration.requires)),
        )
    )
    Space("&metta", _runtime=metta.runtime).add(atom)
    _REGISTRY[_key(metta, name)] = declaration
    return atom


def tagged_fact(tag: Any, proposition: Any) -> Expression:
    """Build the normative stored form for one tagged fact."""
    tag_atom = _encode(tag)
    _validate_rate_tag(tag_atom)
    return Expression((Symbol("fact"), tag_atom, _encode(proposition)))


def tagged_rule(tag: Any, head: Any, *premises: Any) -> Expression:
    """Build the once-ever algebra-agnostic threading form for one rule."""
    tag_atom = _encode(tag)
    _validate_rate_tag(tag_atom)
    return Expression(
        (
            Symbol("rule"),
            tag_atom,
            _encode(head),
            _list("premises", premises),
        )
    )


def _coefficient(tag: Atom) -> Atom:
    """Unwrap the normative ``(rate n)`` declaration to its carrier value."""
    if (
        isinstance(tag, Expression)
        and len(tag.children) == 2
        and tag.children[0] == Symbol("rate")
    ):
        return tag.children[1]
    return tag


def _head(atom: Atom, name: str, arity: int | None = None) -> bool:
    if not isinstance(atom, Expression) or not atom.children:
        return False
    first = atom.children[0]
    return (
        isinstance(first, Symbol)
        and first.name == name
        and (arity is None or len(atom.children) == arity)
    )


def _program(atoms: Sequence[Atom]) -> tuple[list[TaggedAnswer], list[_Rule]]:
    facts: list[TaggedAnswer] = []
    rules: list[_Rule] = []
    for order, atom in enumerate(atoms):
        if not isinstance(atom, Expression):
            continue
        if _head(atom, "fact", 3):
            facts.append(
                TaggedAnswer(
                    value=atom.children[2],
                    tag=_coefficient(atom.children[1]),
                    tokens=frozenset({order}),
                    proof=(order,),
                    _derivations=(_Trace(order, atom.children[1]),),
                )
            )
        elif _head(atom, "rule", 4):
            body = atom.children[3]
            if not isinstance(body, Expression) or not _head(body, "premises"):
                msg = f"tagged_rule_body_malformed({atom}, expected=(premises ...))"
                raise AlgebraDeclarationError(msg)
            rules.append(
                _Rule(
                    order,
                    _coefficient(atom.children[1]),
                    atom.children[2],
                    body.children[1:],
                )
            )
    return facts, rules


def _merge_bindings(
    current: Mapping[str, Atom], additional: Mapping[str, Atom]
) -> dict[str, Atom] | None:
    merged = dict(current)
    for name, value in additional.items():
        previous = merged.get(name)
        if previous is not None and not _same(previous, value):
            return None
        merged[name] = value
    return merged


def _derive_rule(
    metta: Space,
    declaration: DeclaredAlgebra,
    rule: _Rule,
    available: Sequence[TaggedAnswer],
    budget: _EvaluationBudget,
) -> list[TaggedAnswer]:
    derivation = _derive_rule_steps(metta, declaration, rule, budget, {})
    try:
        next(derivation)
        while True:
            derivation.send(available)
    except StopIteration as completed:
        return completed.value
    finally:
        derivation.close()


def _derive_rule_steps(
    metta: Space,
    declaration: DeclaredAlgebra,
    rule: _Rule,
    budget: _EvaluationBudget,
    initial: dict[str, Atom],
) -> Generator[Atom, Sequence[TaggedAnswer], list[TaggedAnswer]]:
    """Suspend at each premise so either evaluator supplies its candidate bag."""
    states: list[
        tuple[
            dict[str, Atom],
            Atom,
            frozenset[int],
            tuple[int, ...],
            tuple[_Trace, ...],
        ]
    ] = [
        (initial, rule.tag, frozenset(), (rule.order,), ())
    ]
    linear = "linear" in declaration.requires
    for premise in rule.premises:
        budget.checkpoint()
        next_states: list[
            tuple[
                dict[str, Atom],
                Atom,
                frozenset[int],
                tuple[int, ...],
                tuple[_Trace, ...],
            ]
        ] = []
        for bindings, tag, tokens, proof, child_traces in states:
            budget.checkpoint()
            pattern = substitute(premise, bindings)
            for candidate in (yield pattern):
                budget.checkpoint()
                matched = _match(pattern, candidate.value)
                if matched is None:
                    continue
                overlap = tokens & candidate.tokens
                if linear and overlap:
                    token = min(overlap)
                    msg = (
                        f"linear_evidence_already_spent({declaration.name}, token={token})"
                    )
                    raise LinearEvidenceError(msg)
                merged = _merge_bindings(bindings, matched)
                if merged is None:
                    continue
                next_states.append(
                    (
                        merged,
                        declaration.extend_values(
                            metta,
                            tag,
                            candidate.tag,
                            budget=budget,
                        ),
                        tokens | candidate.tokens,
                        proof + candidate.proof,
                        child_traces + candidate._derivations,
                    )
                )
        states = next_states
        if not states:
            break
    answers: list[TaggedAnswer] = []
    for bindings, tag, tokens, proof, child_traces in states:
        value = substitute(rule.head, bindings)
        if any(isinstance(node, Variable) for node in _walk(value)):
            continue
        answers.append(
            TaggedAnswer(
                value,
                tag,
                tokens,
                proof,
                (_Trace(rule.order, rule.tag, child_traces, is_rule=True),),
            )
        )
    return answers


def _walk(atom: Atom) -> Iterable[Atom]:
    stack = [atom]
    while stack:
        current = stack.pop()
        yield current
        if isinstance(current, Expression):
            stack.extend(reversed(current.children))


def _signature(answer: TaggedAnswer) -> tuple[str, str, frozenset[int], tuple[int, ...]]:
    return str(answer.value), str(answer.tag), answer.tokens, answer.proof


def _fuse(
    metta: Space,
    declaration: DeclaredAlgebra,
    answers: Sequence[TaggedAnswer],
    budget: _EvaluationBudget,
) -> list[TaggedAnswer]:
    fused: list[TaggedAnswer] = []
    positions: dict[str, int] = {}
    for answer in answers:
        budget.checkpoint()
        key = str(answer.value)
        position = positions.get(key)
        if position is None:
            positions[key] = len(fused)
            fused.append(answer)
            continue
        previous = fused[position]
        fused[position] = TaggedAnswer(
            value=previous.value,
            tag=declaration.combine_values(
                metta,
                previous.tag,
                answer.tag,
                budget=budget,
            ),
            tokens=previous.tokens | answer.tokens,
            proof=previous.proof + answer.proof,
            _derivations=previous._derivations + answer._derivations,
        )
    return fused


def _headed_tag(atom: Atom, name: str) -> bool:
    return (
        isinstance(atom, Expression)
        and bool(atom.children)
        and atom.children[0] == Symbol(name)
    )


def _carrier_input(declaration: DeclaredAlgebra, trace: _Trace) -> Atom:
    """Map one universal source node into a carrier's generator value."""
    # policy-inventory-exempt: mechanism-internal; reason=the carriers whose generator value is the semiring one, named by their declared vocabulary members so a catalog rename breaks here rather than drifting; evidence=extensions/python/metta/vocabularies.py:Semiring
    if declaration.name in {
        Semiring.bool,
        Semiring.bag,
        Semiring.set,
        Semiring.counting,
    }:
        return declaration.one
    if declaration.name == "prov":
        if not trace.is_rule and _headed_tag(trace.raw, "src"):
            return trace.raw
        if trace.is_rule:
            return declaration.one
        return Expression((Symbol("src"), Grounded(trace.source)))
    if _headed_tag(trace.raw, "rate") and len(trace.raw.children) == 2:
        return trace.raw.children[1]
    return trace.raw


def _interpret_trace(
    metta: Space, declaration: DeclaredAlgebra, trace: _Trace
) -> Atom:
    value = _carrier_input(declaration, trace)
    for child in trace.children:
        value = declaration.extend_values(
            metta, value, _interpret_trace(metta, declaration, child)
        )
    return value


def _interpret_alternatives(
    metta: Space,
    declaration: DeclaredAlgebra,
    alternatives: Sequence[_Trace],
) -> Atom:
    value = declaration.zero
    for trace in alternatives:
        contribution = _interpret_trace(metta, declaration, trace)
        value = declaration.combine_values(metta, value, contribution)
    return value


def _order_answers(
    declaration: DeclaredAlgebra, answers: Sequence[TaggedAnswer]
) -> list[TaggedAnswer]:
    """Apply a declared best direction stably before Python slices the view."""
    if declaration.order is None:
        return list(answers)

    def key(answer: TaggedAnswer) -> Any:
        tag = answer.tag
        return _decode(tag) if isinstance(tag, Grounded) else tag

    return sorted(
        answers,
        key=key,
        reverse=declaration.order == SemiringOrder.descending,
    )


def _demand_evaluate(
    metta: Space,
    declaration: DeclaredAlgebra,
    facts: Sequence[TaggedAnswer],
    rules: Sequence[_Rule],
    *,
    goal: Atom,
    max_rounds: int,
    budget: _EvaluationBudget,
) -> list[TaggedAnswer] | None:
    # The demand planner consumes the algebra's rule and proof types; importing
    # it here keeps that dependency out of this module's initialization cycle.
    from ._algebra_demand import evaluate_demand  # noqa: PLC0415

    return evaluate_demand(
        metta, declaration, facts, rules,
        goal=goal, max_rounds=max_rounds, budget=budget,
    )


def evaluate(
    metta: Space,
    query: str | Atom,
    *,
    algebra: str,
    max_rounds: int = 64,
    timeout: float | None = None,
    inferences: int | None = None,
) -> AlgebraEvaluation:
    """Evaluate finite tagged derivations under one call-wide resource budget."""
    budget = _EvaluationBudget.from_call(timeout, inferences)
    declaration = require(metta, algebra)
    _require_context_capabilities(metta, declaration)
    goal = parse(query) if isinstance(query, str) else _encode(query)
    budget.checkpoint()
    available, rules = _program(metta.atoms())
    # max_rounds bounds fixpoint HEIGHT, not how long one round can run. The
    # absolute deadline therefore gets checked between rounds and inside each
    # potentially large Python scan, while every engine operation receives the
    # remaining time and inference quota. Reusing either original bound at
    # each operation would permit max_rounds times that budget instead [tested:
    # test_tagged_algebra_forwards_bounds_to_every_evaluating_door,
    # test_tagged_algebra_debits_inferences_across_operations;
    # commit=51e719767e3dd322a9cf88bd096410bbc5647493].
    demanded = _demand_evaluate(
        metta, declaration, available, rules,
        goal=goal, max_rounds=max_rounds, budget=budget,
    )
    if demanded is not None:
        available = demanded
    else:
        seen = {_signature(answer) for answer in available}
        for _ in range(max_rounds):
            budget.checkpoint()
            added: list[TaggedAnswer] = []
            for rule in rules:
                budget.checkpoint()
                for answer in _derive_rule(
                    metta, declaration, rule, available, budget
                ):
                    signature = _signature(answer)
                    if signature not in seen:
                        seen.add(signature)
                        added.append(answer)
            if not added:
                break
            available.extend(added)
        else:
            msg = (
                f"algebra_derivation_did_not_reach_fixpoint({algebra}, rounds={max_rounds})"
            )
            raise AlgebraEvaluationError(msg)
    matched: list[TaggedAnswer] = []
    for answer in available:
        budget.checkpoint()
        if _match(goal, answer.value) is not None:
            matched.append(answer)
    licence = "combine-associative"
    can_fuse = licence in declaration.laws
    plan = (
        PlanDecision(
            "fuse-equal-conclusions",
            can_fuse,
            () if can_fuse else (licence,),
        ),
        PlanDecision("demand-directed-derivation", demanded is not None),
    )
    if can_fuse:
        matched = _fuse(metta, declaration, matched, budget)
    budget.checkpoint()
    retained = []
    for answer in _order_answers(declaration, matched):
        budget.checkpoint()
        retained.append(
            replace(answer, _space=metta, _algebra=declaration.name, _plan=plan)
        )
    return AlgebraEvaluation(tuple(retained), plan)


class AlgebraEvaluationError(MettaError):
    """A tagged program exceeded its declared finite evaluation boundary."""


def _rate(tag: Atom) -> float:
    value: Any = tag
    if isinstance(tag, Expression) and _head(tag, "rate", 2):
        value = tag.children[1]
    if isinstance(value, Grounded):
        value = _decode(value)
    if isinstance(value, bool) or not isinstance(value, Real):
        msg = f"rate_not_numeric({tag})"
        raise RateDeclarationError(msg)
    numeric = float(value)
    if numeric < 0 or not math.isfinite(numeric):
        msg = f"negative_or_nonfinite_rate({tag})"
        raise RateDeclarationError(msg)
    return numeric


def _validate_rate_tag(tag: Atom) -> None:
    if _head(tag, "rate"):
        _rate(tag)


def sample(
    metta: Space,
    query: str | Atom,
    *,
    algebra: str,
    draws: int,
    seed: int,
) -> tuple[Atom, ...]:
    """Draw a stable cumulative rate selection using isolated seeded state."""
    if isinstance(draws, bool) or not isinstance(draws, int) or draws < 0:
        msg = "draws must be a nonnegative integer"
        raise ValueError(msg)
    evaluation = evaluate(metta, query, algebra=algebra)
    weighted = [(answer, _rate(answer.tag)) for answer in evaluation.answers]
    total = math.fsum(rate for _, rate in weighted)
    if not math.isfinite(total):
        msg = f"rate_total_nonfinite({algebra})"
        raise RateDeclarationError(msg)
    if total <= 0:
        return ()
    generator = random.Random(seed)  # noqa: S311 -- caller-seeded simulation is not a security boundary  # nosec B311
    selected = generator.choices(
        [answer.value for answer, _ in weighted],
        weights=[rate for _, rate in weighted],
        k=draws,
    )
    return tuple(selected)


def has_tagged_program(metta: Space, query: str | Atom) -> bool:
    """Ask whether a normative tagged fact or rule can answer this query."""
    encoded = query if isinstance(query, str) else _encode(query).to_wire()
    return metta.runtime.apply_must(
        "metta_py_has_tagged_program", metta.name, encoded
    ) == "true"


def count_tagged(
    metta: Space,
    query: str | Atom,
    *,
    max_rounds: int = 64,
    limit: int | None = None,
    timeout: float | None = None,
    inferences: int | None = None,
) -> int:
    """Count tagged derivation trees wholly inside the engine."""
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int):
        msg = "max_rounds must be a positive integer"
        raise TypeError(msg)
    if max_rounds <= 0:
        msg = "max_rounds must be positive"
        raise ValueError(msg)
    _validate_limit(limit)
    encoded = query if isinstance(query, str) else _encode(query).to_wire()
    inputs = [metta.name, encoded, max_rounds, limit or 0]
    from ._space_execution import (  # noqa: PLC0415 -- algebra stays a satellite
        _controlled_run,
        _limits,
    )

    output = _controlled_run(
        metta.runtime,
        "metta_py_tagged_count",
        inputs,
        _limits(timeout, inferences),
    )
    return int(output)


def captured_answer(
    metta: Space,
    value: Any,
    annotation: Atom,
    carrier: Any,
) -> TaggedAnswer:
    """Build an output answer around one engine-captured annotation."""
    declaration = resolve(metta, carrier)
    return TaggedAnswer(
        value,
        annotation,
        frozenset(),
        (),
        (_Trace(-1, annotation),),
        metta,
        declaration.name,
    )


_CONSTRUCTOR_MISSING: Final[object] = object()


def _algebra_name(value: Any) -> str:
    if isinstance(value, type):
        return value.__name__.replace("_", "-")
    return _carrier_name(value)


def _operation_name(
    metta: Space, algebra_name: str, role: str, operation: Any
) -> str:
    if isinstance(operation, Symbol):
        return operation.name
    if isinstance(operation, str):
        return operation
    if not callable(operation):
        msg = (
            f"{role} must be a callable, Symbol, or operation name, "
            f"not {type(operation).__name__}"
        )
        raise TypeError(msg)
    name = f"{algebra_name}-{role}"

    def binary(left: Any, right: Any) -> Any:
        return operation(left, right)

    # An algebra's combine and extend are arithmetic over two carrier values:
    # they read nothing and write nothing, which is rank 0. The declaration
    # is required at registration, and a semiring whose operator claimed a
    # higher rank would make every annotation join that used it look
    # effectful to the plan join.
    metta.op(binary, name=name, effect=EffectClass.pureStructural)
    return name


def _construct(
    subject: Any,
    *,
    plus: Any = None,
    times: Any = None,
    combine: Any = None,
    extend: Any = None,
    zero: Any = _CONSTRUCTOR_MISSING,
    one: Any = _CONSTRUCTOR_MISSING,
    laws: Iterable[str] = (),
    carrier: Iterable[Any] = (),
    requires: Iterable[str] = (),
    order: SemiringOrder | None = None,
) -> DeclaredAlgebra:
    """Implement the functional and class-decorator constructor forms."""
    from . import engine  # noqa: PLC0415 -- the callable module stays lazy

    target = engine().self
    algebra_name = _algebra_name(subject)
    if isinstance(subject, type):
        plus = getattr(subject, "plus", plus)
        times = getattr(subject, "times", times)
        combine = getattr(subject, "combine", combine)
        extend = getattr(subject, "extend", extend)
        zero = getattr(subject, "zero", zero)
        one = getattr(subject, "one", one)
        laws = getattr(subject, "laws", laws)
        carrier = getattr(subject, "carrier", carrier)
        requires = getattr(subject, "requires", requires)
        order = getattr(subject, "order", order)
    combine = plus if combine is None else combine
    extend = times if extend is None else extend
    if algebra_name in _PRESETS:
        return require(target, algebra_name)
    if combine is None or extend is None:
        msg = "algebra() needs plus=/times= (or combine=/extend=)"
        raise TypeError(msg)
    if zero is _CONSTRUCTOR_MISSING or one is _CONSTRUCTOR_MISSING:
        msg = "algebra() needs both zero= and one="
        raise TypeError(msg)
    combine_name = _operation_name(target, algebra_name, "plus", combine)
    extend_name = _operation_name(target, algebra_name, "times", extend)
    declare(
        target,
        algebra_name,
        combine=combine_name,
        extend=extend_name,
        zero=zero,
        one=one,
        laws=laws,
        carrier=carrier,
        requires=requires,
        order=order,
    )
    return require(target, algebra_name)


class _AlgebraModule(ModuleType):
    """A real namespace module that also constructs declared algebras."""

    def __call__(
        self,
        subject: Any = None,
        *,
        plus: Any = None,
        times: Any = None,
        combine: Any = None,
        extend: Any = None,
        zero: Any = _CONSTRUCTOR_MISSING,
        one: Any = _CONSTRUCTOR_MISSING,
        laws: Iterable[str] = (),
        carrier: Iterable[Any] = (),
        requires: Iterable[str] = (),
        order: SemiringOrder | None = None,
    ) -> Any:
        if subject is None:
            def decorate(cls: type) -> DeclaredAlgebra:
                return _construct(
                    cls,
                    plus=plus,
                    times=times,
                    combine=combine,
                    extend=extend,
                    zero=zero,
                    one=one,
                    laws=laws,
                    carrier=carrier,
                    requires=requires,
                    order=order,
                )

            return decorate
        return _construct(
            subject,
            plus=plus,
            times=times,
            combine=combine,
            extend=extend,
            zero=zero,
            one=one,
            laws=laws,
            carrier=carrier,
            requires=requires,
            order=order,
        )


counting = replace(_PRESETS["counting"])
tropical = replace(_PRESETS["tropical"])
prov = replace(_PRESETS["prov"])
ranked = replace(_PRESETS["ranked"])
prob = replace(_PRESETS["prob"])

# PEP 562 preserves lazy import identity at the package; changing the real
# module object's class adds construction without introducing a proxy.
sys.modules[__name__].__class__ = _AlgebraModule
