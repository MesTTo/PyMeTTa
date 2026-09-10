"""Purpose: declare value algebras and run their one generic tagged-rule form.

Assumes:
  - facts and rules rest in a space as ordinary ``(fact tag proposition)``
    and ``(rule tag head (premises ...))`` atoms.
Guarantees:
  - provider coefficients obey the explicit typed carrier and reentrant
    membership shares source accounting [tested:
    test_provider_conclusions_check_the_explicit_typed_carrier,
    test_provider_carrier_predicate_shares_the_source_budget; commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
  - carrier predicates and operations share the selected evaluation context,
    including demand and ordering [tested:
    tests/ch06_many_answers/test_evaluation_context_types.py; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - binding preparation preserves literal values and host identity at custom
    operation crossings [tested: sh extensions/python/test.sh
    tests/ch06_many_answers/test_evaluation_context_bindings.py -n 0;
    commit=54cb2eee69c42c1ae685643cbe2578f8d617a265]
  - algebra and demand cross internal evaluation without changing answer shape
    [tested: sh extensions/python/test.sh
    tests/ch06_many_answers/test_evaluation_context.py -n 0; commit=54cb2eee69c42c1ae685643cbe2578f8d617a265]
  - provider premises retain the direct query's carrier, limit and order while
    reading complete source bags [tested:
    test_provider_premises_retain_the_direct_match_context; commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
  - provider-backed premises and direct conclusions use engine match/4 with
    their captured annotations and call-wide budgets; each evaluation retains
    complete source bags [tested:
    test_tagged_premise_keeps_the_direct_provider_annotation,
    test_provider_duplicate_premises_keep_four_proofs_and_one_source_bag;
    commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
  - linear provider evidence is refused because Answer supplies no stable
    source occurrence identity [tested:
    test_tagged_provider_linear_evidence_requires_stable_occurrence_identity;
    commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
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
    test_demand_preserves_global_cycle_and_round_failures; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
  - the generated Semiring vocabulary, preset descriptors, and public carrier
    objects name the same ten shipped algebras [tested:
    test_every_shipped_semiring_has_one_root_object_in_catalog_order;
    commit=2e627a593413191cda3170f2eb716835f7f62543]
  - arbitrary law-bearing declarations use the engine's one checker in the
    declaring space's equation module [tested:
    test_a_law_is_checked_once_in_the_declaring_space; commit=2e627a593413191cda3170f2eb716835f7f62543]
  - custom algebra rows and their Python mirrors have the same context
    lifetime as annotations, while shipped presets remain shared [tested:
    test_custom_algebras_are_context_owned; commit=2e627a593413191cda3170f2eb716835f7f62543]
  - calling the module constructor targets the ambient space rather than the
    process-default home [tested:
    test_algebra_module_constructor_targets_the_ambient_space; commit=2e627a593413191cda3170f2eb716835f7f62543]
  - counting retains the common TaggedAnswer protocol while crossing only its
    one engine-side aggregate [tested:
    test_counting_counts_match_bag_duplicates_without_opening_a_row_cursor,
    test_counting_counts_duplicate_call_answers_inside_the_engine;
    commit=2e627a593413191cda3170f2eb716835f7f62543]
  - ``current_algebra()`` observes the per-call carrier, surrounding task
    scope, or current space declaration in that order [tested:
    test_current_algebra_follows_each_selection_layer; commit=2e627a593413191cda3170f2eb716835f7f62543]
  - accepted algebra-law names and alias expansions come from the catalog,
    and a refusal names the full accepted vocabulary [tested:
    test_algebra_law_vocabulary_drives_aliases_and_unknown_refusals,
    test_equational_law_names_read_no_catalog; commit=5e0ae6c22d604c4b980766e3cc4811ee545e5c9e]
  - typed carriers check every input and result, and only a finite enumeration
    can license a law certificate [tested:
    test_tensor_type_carrier_runs_max_product_and_reinterprets_provenance,
    test_type_carrier_cannot_certify_laws; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - a failed operation raises its original Error atom before it can become a tag
    [tested: test_bag_over_tensor_tags_reports_the_type_failure; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - carrier checks debit the tagged evaluation's remaining inference and time
    budget at initial facts, initial rules, inputs, and results [tested:
    test_carrier_predicate_inferences_are_bounded_at_every_phase,
    test_carrier_checks_debit_one_quota_across_initial_facts,
    test_carrier_predicate_respects_the_enclosing_time_limit; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - algebra mirrors restore their exact preimage when a transaction rolls back
    [tested: test_rollback_releases_an_algebra_mirror,
    test_rollback_restores_a_replaced_algebra_mirror; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - Python carrier predicates preserve symbols and expressions while decoding
    grounded payloads [tested: test_carrier_preserves_text_and_symbol_types;
    commit=074dc0a88b1605c54824de677d586b6f60998bcf]
Owns resources:
  - catalog mirrors retain declared predicates; Space.drop removes its mirrors
    and transaction rollback restores their previous state [tested:
    test_drop_retires_algebra_before_redeclaration,
    test_rollback_releases_an_algebra_mirror; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - provider source bags and proof labels live only for one evaluate
    call and retain no provider cursor [tested:
    test_provider_proofs_reinterpret_without_requery_and_refresh_on_next_ask;
    commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
Decides:
  - ``contraction`` is a capability, while the remaining public law names are
    equations checked exhaustively over the declared finite carrier.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import builtins
import math
import random
import sys
import time
from collections.abc import Callable, Generator, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from fractions import Fraction
from numbers import Real
from types import ModuleType
from typing import TYPE_CHECKING, Any, Final, cast

from metta._atoms.designation import SpaceLike
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Undefined,
    Variable,
    _atom_from_wire,
    _decode,
    _encode,
    _from_wire,
    _match,
    parse,
    substitute,
)
from metta._binding.runtime import active_runtime
from metta._errors.errors import (
    EngineError,
    InferenceLimitError,
    MettaError,
    ResourceLimitError,
    TimeLimitError,
)
from metta._faces.space import Space
from metta._lazy import lazy
from metta._spaces.cursor import _validate_limit
from metta._spaces.evaluate import _prepared_ask
from metta._spaces.execution import _controlled_run, evaluate_accounted
from metta._spaces.execution import evaluate as evaluate_operation
from metta._spaces.handle import current_space
from metta._spaces.scope import EvaluationContext, _limits
from metta._spaces.scope import selected as _selected_under
from metta.vocabularies import AlgebraLaw, EffectClass, Semiring, SemiringOrder

if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')

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
    "amplitude",
    "bag",
    "bool",
    "budget",
    "counting",
    "current_algebra",
    "declare",
    "evaluate",
    "prob",
    "prov",
    "ranked",
    "resolve",
    "sample",
    "set",
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

    context: EvaluationContext
    timeout: float | None
    inferences: int | None
    deadline: float | None
    remaining_inferences: int | None

    @classmethod
    def from_call(
        cls, timeout: float | None, inferences: int | None,
        context: EvaluationContext,
    ) -> _EvaluationBudget:
        limits = _limits(timeout, inferences)
        if limits is None:
            return cls(context, None, None, None, None)
        seconds = None if limits[0] < 0 else limits[0]
        steps = None if limits[1] < 0 else limits[1]
        deadline = None if seconds is None else time.monotonic() + seconds
        return cls(context, seconds, steps, deadline, steps)

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

    def _run_accounted(
        self, metta: Space, action: Callable[[float | None, int | None], tuple[Any, int]]
    ) -> Any:
        """Share one remaining quota across operations and carrier checks."""
        remaining_time = self.checkpoint()
        remaining_steps = self.remaining_inferences
        if remaining_steps is not None and remaining_steps <= 0:
            raise self._inference_limit_error()
        try:
            result, spent = action(remaining_time, remaining_steps)
        except TimeLimitError as error:
            raise self._time_limit_error() from error
        except InferenceLimitError as error:
            raise self._inference_limit_error() from error
        except EngineError as error:
            # A predicate can re-enter Janus before the outer guard catches its
            # signal. Recover that exact term from the preserved exception.
            term = getattr(error.__cause__, "term", None)
            kind = (
                metta.runtime.apply("metta_py_raw_limit_kind", term)
                if term is not None else None
            )
            if kind == "time_limit" and self.timeout is not None:
                raise self._time_limit_error() from error
            if kind == "inference_limit" and self.inferences is not None:
                raise self._inference_limit_error() from error
            raise
        if remaining_steps is not None:
            self.remaining_inferences = remaining_steps - spent
        self.checkpoint()
        return result

    def evaluate_operation(
        self, metta: Space, target: Atom
    ) -> list[Atom | Undefined]:
        """Prepare bindings and evaluate within the same context and quota."""
        target, using = _prepared_ask(metta, target, None)
        if using:
            target = target.subs({Symbol(name): _encode(value) for name, value in using.items()})

        def run(seconds: float | None, steps: int | None) -> tuple[list[Atom | Undefined], int]:
            if steps is None:
                return evaluate_operation(
                    metta.runtime, metta.name, target, seconds, None,
                    context=self.context,
                ), 0
            return evaluate_accounted(
                metta.runtime, metta.name, target, seconds, steps,
                context=self.context,
            )

        return cast("list[Atom | Undefined]", self._run_accounted(metta, run))

    def check_values(
        self, metta: Space, name: str, carrier: Atom, values: tuple[Atom, ...]
    ) -> None:
        """Meter carrier predicates in the same engine crossing as their guard."""
        def run(seconds: float | None, steps: int | None) -> tuple[None, int]:
            spent = _controlled_run(
                metta.runtime,
                "metta_py_check_algebra_values_accounted",
                [metta.name, name, carrier.to_wire(), [value.to_wire() for value in values]],
                _limits(seconds, steps),
                context=self.context,
            )
            return None, int(spent)

        self._run_accounted(metta, run)


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
    type: Any = None

    def _carrier_atom(self) -> Expression:
        finite = _list("carrier", self.carrier)
        if self.type is None:
            return finite
        specification = self.type
        if not isinstance(specification, Atom):
            specification = Grounded(_CarrierPredicate(specification))
        return Expression((Symbol("type"), specification, finite))

    def check_values(
        self, metta: Space, *values: Atom, resources: _EvaluationBudget | None = None
    ) -> None:
        """Check inputs and results against the catalog's exact carrier contract."""
        if self.type is None and not self.carrier:
            return
        try:
            if resources is None:
                resources = _EvaluationBudget.from_call(
                    None, None, EvaluationContext(self.name, order=self.order)
                )
            resources.check_values(metta, self.name, self._carrier_atom(), values)
        except ResourceLimitError:
            raise
        except EngineError as error:
            raise AlgebraOperationError(str(error)) from error

    def operation(
        self,
        metta: Space,
        name: str,
        left: Atom,
        right: Atom,
        *,
        resources: _EvaluationBudget | None = None,
    ) -> Atom:
        """Apply a declared binary operation and require one carrier value."""
        if resources is None:
            resources = _EvaluationBudget.from_call(
                None, None, EvaluationContext(self.name, order=self.order)
            )
        for value in (left, right):
            self._require_success(name, value)
        self.check_values(metta, left, right, resources=resources)
        result = self._operate(metta, name, left, right, resources=resources)
        self._require_success(name, result)
        self.check_values(metta, result, resources=resources)
        return result

    def _require_success(self, name: str, value: Atom) -> None:
        if _head(value, "Error"):
            msg = f"algebra_operation_error({self.name}, {name}): {value}"
            raise AlgebraOperationError(msg, atom=value, operation=name)

    def _operate(
        self, metta: Space, name: str, left: Atom, right: Atom,
        *, resources: _EvaluationBudget,
    ) -> Atom:
        """Evaluate the operation after its inputs passed the carrier check."""
        if isinstance(left, Grounded) and isinstance(right, Grounded):
            left_value, right_value = _decode(left), _decode(right)
            if (
                not isinstance(left_value, builtins.bool)
                and not isinstance(right_value, builtins.bool)
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
        # policy-inventory-exempt: mechanism-internal; reason=the two role names a declaration coins for its own combine and extend operations, which _register_operation spells as <algebra>-<role>; evidence=extensions/python/metta/algebra/__init__.py:_operation_name
        if name in {"plus", "times"}:
            return Expression((Symbol(name), left, right))
        target = Expression((Symbol(name), left, right))
        answers = resources.evaluate_operation(metta, target)
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
        resources: _EvaluationBudget | None = None,
    ) -> Atom:
        """Combine alternative derivations."""
        return self.operation(
            metta,
            self.combine,
            left,
            right,
            resources=resources,
        )

    def extend_values(
        self,
        metta: Space,
        left: Atom,
        right: Atom,
        *,
        resources: _EvaluationBudget | None = None,
    ) -> Atom:
        """Extend one derivation through a premise."""
        return self.operation(
            metta,
            self.extend,
            left,
            right,
            resources=resources,
        )


@dataclass(frozen=True, slots=True)
class PlanDecision:
    """An evaluation choice, including a withheld law-gated optimization."""

    optimization: str
    applied: builtins.bool
    missing_laws: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Trace:
    """One retained algebra-neutral derivation node."""

    source: int
    raw: Atom
    children: tuple[_Trace, ...] = ()
    is_rule: builtins.bool = False


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
        resources = _EvaluationBudget.from_call(
            None, None, EvaluationContext(declaration.name, order=declaration.order)
        )
        annotation = _interpret_alternatives(
            self._space, declaration, traces, resources
        )
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


# closed-set: decides; policy=which algebra laws are equational, so a declaration that names one gets the equational check; reads=algebra-law, the engine's own vocabulary, which test_under_algebra holds this to
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
# closed-set: decides; policy=which laws a semiring must satisfy to be one; reads=algebra-law, the engine's own vocabulary, which test_under_algebra holds this to
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


# closed-set: decides; policy=the carriers this seat ships ready-declared; reads=semiring, the engine's own vocabulary, which test_catalog_kinds holds this to
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

_REGISTRY: dict[tuple[int, str, str], tuple[Atom, DeclaredAlgebra]] = {}


def _record_algebra_undo(key: tuple[int, str, str]) -> None:
    """Enlist this mirror's preimage in the existing transaction undo log."""
    from metta._declare.operations import _record_registry_undo  # noqa: PLC0415

    previous = _REGISTRY.get(key)

    def restore() -> None:
        if previous is None:
            _REGISTRY.pop(key, None)
        else:
            _REGISTRY[key] = previous

    _record_registry_undo(
        restore, description=f"algebra registry entry {key!r}", key=("algebra", key),
    )


@dataclass(frozen=True, slots=True)
class _CarrierPredicate:
    """Retain Python carrier membership across the engine boundary."""

    specification: Any

    def __call__(self, value: Any) -> builtins.bool:
        if isinstance(self.specification, builtins.type):
            return isinstance(value, self.specification)
        result = self.specification(value)
        if not isinstance(result, builtins.bool):
            msg = "an algebra type predicate must return one bool; use bool(...) or an explicit all(...) reduction"
            raise TypeError(msg)
        return result


def _carrier_type_accepts(type_wire: Any, value_wire: Any) -> builtins.bool:
    """Apply a host carrier predicate without erasing native atom kinds."""
    predicate = _decode(_from_wire(type_wire))
    if not isinstance(predicate, _CarrierPredicate):
        predicate = _CarrierPredicate(predicate)
    return predicate(_decode(_from_wire(value_wire)))


def _forget_space(metta: Space) -> None:
    """Release catalog mirrors when their owning Python space closes."""
    prefix = id(metta._rt), _context_name(metta)
    for key in tuple(_REGISTRY):
        if key[:2] == prefix:
            _record_algebra_undo(key)
            del _REGISTRY[key]


def _context_name(metta: Space) -> str:
    return str(metta.name)


def _key(metta: Space, context: str, name: str) -> tuple[int, str, str]:
    return id(metta._rt), context, name


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


def current_algebra() -> str | None:
    """Return the selected algebra name, or ``None`` when none is declared.

    An explicit carrier on the evaluating call wins over ``with under(...)``;
    that task-local scope wins over the current space's annotations row.
    """
    scoped = _selected_under()
    runtime = active_runtime()
    if runtime is None:
        return None if scoped is None else _carrier_name(scoped)
    target = Space(current_space(), _runtime=runtime)
    scope = [] if scoped is None else [_carrier_name(scoped)]
    row = target.runtime.once(
        "metta_current_algebra(Ctx, Scope, Algebra)",
        Ctx=str(target.name),
        Scope=scope,
    )
    return None if not row else str(row["Algebra"])


def resolve(metta: SpaceLike, carrier: Any) -> DeclaredAlgebra:
    """Resolve any public carrier spelling against one runtime catalog.

    metta may be a context or a space.
    """
    home = metta.self
    if isinstance(carrier, DeclaredAlgebra):
        return carrier
    return require(home, _carrier_name(carrier))


def _catalog_law_aliases(metta: Space) -> dict[str, tuple[str, ...]]:
    """Read algebra-law alias expansions from the live catalog."""
    aliases: dict[str, tuple[str, ...]] = {}
    prefix = (Symbol("claim"), Symbol("algebra-law"))
    for atom in Space("&metta", _runtime=metta.runtime).atoms():
        if (
            not isinstance(atom, Expression)
            or len(atom.children) < 5
            or atom.children[:2] != prefix
            or atom.children[3] != Symbol("expands-to")
            or not all(isinstance(value, Symbol) for value in atom.children[2:])
        ):
            continue
        alias = cast(Symbol, atom.children[2])
        aliases[alias.name] = tuple(
            cast(Symbol, value).name for value in atom.children[4:]
        )
    return aliases


def _canonical_laws(metta: Space, laws: Iterable[str]) -> frozenset[str]:
    accepted = tuple(member.value for member in AlgebraLaw)
    accepted_set = frozenset(accepted)
    requested = tuple(laws)
    unknown = sorted({law for law in requested if law not in accepted_set})
    if unknown:
        msg = (
            f"algebra_law_unknown({unknown!r}); accepted laws are "
            f"{', '.join(accepted)}"
        )
        raise AlgebraDeclarationError(msg)
    # Reading the alias claims walks every &metta row, so ask only when a
    # requested name is not already an equation that stands for itself. No
    # alias claim is named after an equation, so both paths answer the same set
    # [tested: catalog_self_description:algebra_law_vocabulary_and_alias_claims_are_exact,
    # test_algebra_law_vocabulary_drives_aliases_and_unknown_refusals;
    # commit=5e0ae6c22d604c4b980766e3cc4811ee545e5c9e].  declare() canonicalizes before it writes, so a stored
    # row reaches this with equations and pays nothing; a row written as MeTTa
    # source with an alias still asks the catalog
    # [tested: test_equational_law_names_read_no_catalog; commit=5e0ae6c22d604c4b980766e3cc4811ee545e5c9e].
    if all(law in _EQUATIONAL_LAWS for law in requested):
        return frozenset(requested)
    aliases = _catalog_law_aliases(metta)
    out: builtins.set[str] = builtins.set()
    for law in requested:
        out.update(aliases.get(law, (law,)))
    return frozenset(out)


def _catalog_declaration(
    metta: Space, context: str, name: str
) -> tuple[DeclaredAlgebra, Atom] | None:
    """Reify a direct ``&metta`` algebra row through the Python interface."""
    # The context's own row, else the shipped global one: the same two-clause
    # preference metta_algebra_descriptor_fresh/9 applies engine-side. At most
    # one of each exists, because the catalog refuses a second row for one
    # context and name.
    owned: Expression | None = None
    shared: Expression | None = None
    for atom in Space("&metta", _runtime=metta.runtime).atoms():
        if not isinstance(atom, Expression) or len(atom.children) != 10:
            continue
        head, declared_name = atom.children[:2]
        if head != Symbol("algebra") or declared_name != Symbol(name):
            continue
        owner = atom.children[9]
        if owner == Symbol(context):
            owned = atom
        elif owner == Symbol("global"):
            shared = atom
    row = owned if owned is not None else shared
    if row is None:
        return None
    _, _, combine, extend, zero, one, laws, carrier, requires, _ = row.children
    specification = None
    if _head(carrier, "type", 3):
        specification = carrier.children[1]
        if isinstance(specification, Grounded):
            specification = _decode(specification)
            if isinstance(specification, _CarrierPredicate):
                specification = specification.specification
        carrier = carrier.children[2]
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
        laws=_canonical_laws(metta, law_names),
        carrier=tuple(carrier.children[1:]),
        requires=frozenset(requirement_names),
        order=_catalog_order(metta, name),
        type=specification,
    ), row


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
    context = _context_name(metta)
    catalog = _catalog_declaration(metta, context, name)
    key = _key(metta, context, name)
    if catalog is None:
        if key in _REGISTRY:
            _record_algebra_undo(key)
            del _REGISTRY[key]
        return None
    declaration, row = catalog
    cached = _REGISTRY.get(key)
    return cached[1] if cached is not None and cached[0] == row else declaration


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
        # policy-inventory-exempt: mechanism-internal; reason=three and four are the only lengths the annotations catalog row is written with, the fourth child being the optional (capabilities ...) field; evidence=extensions/python/metta/_spaces/handle.py:annotations
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


def _same(left: Atom, right: Atom) -> builtins.bool:
    try:
        result = left == right
        return (
            result
            if isinstance(result, builtins.bool)
            else builtins.bool(result)
        )
    except (RuntimeError, TypeError, ValueError):
        return left is right


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
    type: Any = None,  # noqa: A002 -- the public carrier concept is a type
    requires: Iterable[str] = (),
    order: SemiringOrder | None = None,
) -> Atom:
    """Check and add one algebra catalog atom, without replacing an old one.

    metta may be a context or a space.
    """
    home = metta.self
    if not name or not isinstance(name, str):
        msg = "algebra_name_must_be_a_nonempty_symbol"
        raise AlgebraDeclarationError(msg)
    if name in _PRESETS or get(home, name) is not None:
        msg = f"algebra_already_declared({name})"
        raise AlgebraDeclarationError(msg)
    if not combine or not isinstance(combine, str):
        msg = f"algebra_operation_invalid({name}, combine)"
        raise AlgebraDeclarationError(msg)
    if not extend or not isinstance(extend, str):
        msg = f"algebra_operation_invalid({name}, extend)"
        raise AlgebraDeclarationError(msg)
    if order is not None and order not in builtins.set(SemiringOrder):
        msg = f"algebra_order_invalid({name}, {order!r})"
        raise AlgebraDeclarationError(msg)
    if type is not None and not isinstance(type, (Symbol, Expression, builtins.type)) and not callable(type):
        msg = "algebra type= needs a Python type, a MeTTa type atom, or a callable predicate; use carrier= for a finite enumeration"
        raise AlgebraDeclarationError(msg)
    if isinstance(type, Atom) and type.vars:
        msg = "algebra type= must be ground; bind its type variables before declaring it"
        raise AlgebraDeclarationError(msg)
    # Atom classes spell their engine metatypes; Python strings remain text.
    carrier_type = type
    if type is str:
        carrier_type = Symbol("String")
    elif isinstance(type, builtins.type) and issubclass(type, Atom):
        from metta._catalog.annotations import type_atom_for  # noqa: PLC0415
        carrier_type = type_atom_for(type)
    declaration = DeclaredAlgebra(
        name=name,
        combine=combine,
        extend=extend,
        zero=_encode(zero),
        one=_encode(one),
        laws=_canonical_laws(home, laws),
        carrier=tuple(_encode(value) for value in carrier),
        requires=frozenset(requires),
        order=order,
        type=carrier_type,
    )
    context = _context_name(home)
    atom = Expression(
        (
            Symbol("algebra"),
            Symbol(name),
            Symbol(combine),
            Symbol(extend),
            declaration.zero,
            declaration.one,
            _symbol_list("laws", sorted(declaration.laws)),
            declaration._carrier_atom(),
            _symbol_list("requires", sorted(declaration.requires)),
            Symbol(context),
        )
    )
    try:
        home.runtime.do_must(
            "metta_py_declare_algebra", home.name, atom.to_wire()
        )
    except EngineError as error:
        if str(error).startswith(
            (
                "algebra_carrier_not_closed",
                "algebra_law_uncheckable",
                "algebra_law_violation",
            )
        ):
            raise AlgebraLawError(str(error)) from error
        if str(error).startswith(("algebra_value_outside_carrier", "algebra_type_predicate")) or "algebra type predicate" in str(error):
            raise AlgebraDeclarationError(str(error)) from error
        raise
    key = _key(home, context, name)
    _record_algebra_undo(key)
    _REGISTRY[key] = (atom, declaration)
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


def _head(atom: Atom, name: str, arity: int | None = None) -> builtins.bool:
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


@dataclass(slots=True)
class _ProviderSources:
    """One evaluation's complete match bags and local proof labels."""

    metta: Space
    declaration: DeclaredAlgebra
    resources: _EvaluationBudget
    bags: dict[str, list[TaggedAnswer]] = field(default_factory=dict)
    occurrences: dict[tuple[str, str, int], int] = field(default_factory=dict)

    def match(self, pattern: Atom) -> list[TaggedAnswer]:
        """Read through match/4 once per bound pattern, retaining every row."""
        key = str(pattern)
        if key in self.bags:
            return self.bags[key]
        def run(seconds: float | None, steps: int | None) -> tuple[Any, int]:
            rows, spent = _controlled_run(
                self.metta.runtime,
                "metta_py_tagged_sources",
                [self.metta.name, pattern.to_wire(), self.declaration.name],
                _limits(seconds, steps),
                context=self.resources.context,
            )
            return rows, int(spent)

        rows = self.resources._run_accounted(self.metta, run)
        if rows and "linear" in self.declaration.requires:
            msg = (
                f"linear_provider_occurrence_identity_missing({self.metta.name}, "
                f"{self.declaration.name}); provider answers carry values and k, "
                "not stable occurrence identities; use stored tagged facts for "
                "linear evidence"
            )
            raise LinearEvidenceError(msg)
        answers = []
        counts: dict[tuple[str, str], int] = {}
        for value_wire, tag_wire in rows:
            self.resources.checkpoint()
            value, tag = _atom_from_wire(value_wire), _atom_from_wire(tag_wire)
            self.declaration.check_values(self.metta, tag, resources=self.resources)
            row_key = str(value), str(tag)
            ordinal = counts.get(row_key, 0)
            counts[row_key] = ordinal + 1
            # Equal rows retain bag multiplicity and repeated demands keep
            # stable local proof labels, disjoint from stored declaration
            # positions. These are not physical provider occurrence identities;
            # the linear guard above refuses to infer those from values and k.
            source = self.occurrences.setdefault(
                (*row_key, ordinal), -1 - len(self.occurrences)
            )
            answers.append(TaggedAnswer(
                value, tag, frozenset({source}), (source,), (_Trace(source, tag),)
            ))
        self.bags[key] = answers
        return answers


def _derive_rule(
    metta: Space,
    declaration: DeclaredAlgebra,
    rule: _Rule,
    available: Sequence[TaggedAnswer],
    resources: _EvaluationBudget,
    *,
    sources: _ProviderSources | None = None,
) -> list[TaggedAnswer]:
    derivation = _derive_rule_steps(metta, declaration, rule, resources, {})
    # A generator's return value arrives through StopIteration, whose `value` is
    # untyped, so the declaration is what says what crosses that boundary. The
    # loop leaves only by that exception, which is why the name is bound there
    # and returned once after the close.
    answers: list[TaggedAnswer]
    try:
        pattern = next(derivation)
        while True:
            candidates = available if sources is None else [
                *available, *sources.match(pattern)
            ]
            pattern = derivation.send(candidates)
    except StopIteration as completed:
        answers = completed.value
    finally:
        derivation.close()
    return answers


def _derive_rule_steps(
    metta: Space,
    declaration: DeclaredAlgebra,
    rule: _Rule,
    resources: _EvaluationBudget,
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
        resources.checkpoint()
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
            resources.checkpoint()
            pattern = substitute(premise, bindings)
            # The suspension point, written as its own statement: a `yield`
            # inside a `for` header is the same generator and astroid reads the
            # function as an ordinary one that returns a list, which made every
            # caller's `.send`, `.close` and iteration a finding.
            candidates = yield pattern
            for candidate in candidates:
                resources.checkpoint()
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
                            resources=resources,
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
    resources: _EvaluationBudget,
) -> list[TaggedAnswer]:
    fused: list[TaggedAnswer] = []
    positions: dict[str, int] = {}
    for answer in answers:
        resources.checkpoint()
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
                resources=resources,
            ),
            tokens=previous.tokens | answer.tokens,
            proof=previous.proof + answer.proof,
            _derivations=previous._derivations + answer._derivations,
        )
    return fused


def _headed_tag(atom: Atom, name: str) -> builtins.bool:
    return (
        isinstance(atom, Expression)
        and builtins.bool(atom.children)
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
    metta: Space, declaration: DeclaredAlgebra, trace: _Trace,
    resources: _EvaluationBudget,
) -> Atom:
    value = _carrier_input(declaration, trace)
    declaration.check_values(metta, value, resources=resources)
    for child in trace.children:
        value = declaration.extend_values(
            metta, value, _interpret_trace(metta, declaration, child, resources),
            resources=resources,
        )
    return value


def _interpret_alternatives(
    metta: Space,
    declaration: DeclaredAlgebra,
    alternatives: Sequence[_Trace],
    resources: _EvaluationBudget,
) -> Atom:
    value = declaration.zero
    for trace in alternatives:
        contribution = _interpret_trace(metta, declaration, trace, resources)
        value = declaration.combine_values(
            metta, value, contribution, resources=resources
        )
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
    resources: _EvaluationBudget,
) -> list[TaggedAnswer] | None:
    # The demand planner consumes the algebra's rule and proof types; importing
    # it here keeps that dependency out of this module's initialization cycle.
    from metta.algebra._demand import evaluate_demand  # noqa: PLC0415

    return evaluate_demand(
        metta, declaration, facts, rules,
        goal=goal, max_rounds=max_rounds, budget=resources,
    )


_MAX_ROUNDS = 64


def evaluate(
    metta: Space,
    query: str | Atom,
    *,
    algebra: str | DeclaredAlgebra,
    max_rounds: int = _MAX_ROUNDS,
    context: EvaluationContext | None = None,
    timeout: float | None = None,
    inferences: int | None = None,
) -> AlgebraEvaluation:
    """Evaluate finite tagged derivations under one call-wide resource budget.

    metta may be a context or a space.
    """
    home = metta.self
    declaration = resolve(home, algebra)
    if context is None:
        context = EvaluationContext(declaration.name, order=declaration.order)
    resources = _EvaluationBudget.from_call(timeout, inferences, context)
    return _evaluate_with_budget(home, query, declaration, resources, max_rounds=max_rounds)


def _evaluate_with_budget(
    home: Space,
    query: str | Atom,
    declaration: DeclaredAlgebra,
    resources: _EvaluationBudget,
    *,
    max_rounds: int = _MAX_ROUNDS,
) -> AlgebraEvaluation:
    """Run tagged derivation inside the budget owned by its enclosing query."""
    _require_context_capabilities(home, declaration)
    goal = parse(query) if isinstance(query, str) else _encode(query)
    resources.checkpoint()
    available, rules = _program(home.atoms())
    for answer in available:
        declaration.check_values(home, answer.tag, resources=resources)
    for rule in rules:
        declaration.check_values(home, rule.tag, resources=resources)
    sources = (
        _ProviderSources(home, declaration, resources)
        if home.runtime.once("seam:foreign_space(Space)", Space=home.name)
        else None
    )
    # max_rounds bounds fixpoint HEIGHT, not how long one round can run. The
    # absolute deadline therefore gets checked between rounds and inside each
    # potentially large Python scan, while every engine operation receives the
    # remaining time and inference quota. Reusing either original bound at
    # each operation would permit max_rounds times that budget instead [tested:
    # test_tagged_algebra_forwards_bounds_to_every_evaluating_door,
    # test_tagged_algebra_debits_inferences_across_operations;
    # commit=51e719767e3dd322a9cf88bd096410bbc5647493].
    # Unread provider values and effects cannot satisfy the static integer
    # certificate. The full evaluator shares their ordinary match door and
    # caches complete bags for this evaluation's fixed point.
    demanded = None if sources is not None else _demand_evaluate(
        home, declaration, available, rules,
        goal=goal, max_rounds=max_rounds, resources=resources,
    )
    if demanded is not None:
        available = demanded
    else:
        seen = {_signature(answer) for answer in available}
        for _ in range(max_rounds):
            resources.checkpoint()
            added: list[TaggedAnswer] = []
            for rule in rules:
                resources.checkpoint()
                for answer in _derive_rule(
                    home, declaration, rule, available, resources, sources=sources
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
                f"algebra_derivation_did_not_reach_fixpoint({declaration.name}, rounds={max_rounds})"
            )
            raise AlgebraEvaluationError(msg)
    matched: list[TaggedAnswer] = [] if sources is None else list(sources.match(goal))
    for answer in available:
        resources.checkpoint()
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
        matched = _fuse(home, declaration, matched, resources)
    resources.checkpoint()
    retained = []
    for answer in _order_answers(declaration, matched):
        resources.checkpoint()
        retained.append(
            replace(answer, _space=home, _algebra=declaration.name, _plan=plan)
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
    if isinstance(value, builtins.bool) or not isinstance(value, Real):
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
    """Draw a stable cumulative rate selection using isolated seeded state.

    metta may be a context or a space.
    """
    home = metta.self
    if isinstance(draws, builtins.bool) or not isinstance(draws, int) or draws < 0:
        msg = "draws must be a nonnegative integer"
        raise ValueError(msg)
    evaluation = evaluate(home, query, algebra=algebra)
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


def has_tagged_program(metta: Space, query: str | Atom) -> builtins.bool:
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
) -> TaggedAnswer:
    """Count tagged derivation trees into one protocol-shaped answer."""
    if isinstance(max_rounds, builtins.bool) or not isinstance(max_rounds, int):
        msg = "max_rounds must be a positive integer"
        raise TypeError(msg)
    if max_rounds <= 0:
        msg = "max_rounds must be positive"
        raise ValueError(msg)
    _validate_limit(limit)
    encoded = query if isinstance(query, str) else _encode(query).to_wire()
    inputs = [metta.name, encoded, max_rounds, limit or 0]
    output = _controlled_run(
        metta.runtime,
        "metta_py_tagged_count",
        inputs,
        _limits(timeout, inferences),
    )
    return counting_answer(metta, int(output))


def captured_answer(
    metta: Space,
    value: Any,
    annotation: Atom,
    carrier: Any,
    *,
    context: EvaluationContext | None = None,
) -> TaggedAnswer:
    """Build an output answer around one engine-captured annotation."""
    declaration = resolve(metta, carrier)
    if context is None:
        context = EvaluationContext(declaration.name, order=declaration.order)
    resources = _EvaluationBudget.from_call(None, None, context)
    declaration.check_values(metta, annotation, resources=resources)
    return TaggedAnswer(
        value,
        annotation,
        frozenset(),
        (),
        (_Trace(-1, annotation),),
        metta,
        declaration.name,
    )


def counting_answer(
    metta: Space,
    count: int,
    carrier: Any = "counting",
) -> TaggedAnswer:
    """Wrap one engine aggregate without manufacturing a proposition row.

    Public beside `captured_answer` and `count_tagged` because `Space` is the
    caller: the count doors under it stay scalar so that the core never
    imports this satellite, and the layering contract stays kept.
    """
    annotation = _encode(count)
    return TaggedAnswer(
        (),
        annotation,
        frozenset(),
        (),
        (_Trace(-1, annotation),),
        metta,
        _carrier_name(carrier),
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
    type: Any = None,  # noqa: A002 -- the public carrier concept is a type
    requires: Iterable[str] = (),
    order: SemiringOrder | None = None,
) -> DeclaredAlgebra:
    """Implement the functional and class-decorator constructor forms."""
    # The module-level `current_space`, the one `current_algebra` reads too,
    # rather than the root door of the same name: the root's own spelling adds
    # only the implementation-module rehide, and importing it here would shadow
    # this module's.
    target = _root.engine().space(current_space())
    algebra_name = _algebra_name(subject)
    carrier_type = type
    if isinstance(subject, builtins.type):
        plus = getattr(subject, "plus", plus)
        times = getattr(subject, "times", times)
        combine = getattr(subject, "combine", combine)
        extend = getattr(subject, "extend", extend)
        zero = getattr(subject, "zero", zero)
        one = getattr(subject, "one", one)
        laws = getattr(subject, "laws", laws)
        carrier = getattr(subject, "carrier", carrier)
        carrier_type = getattr(subject, "type", type)
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
    def install() -> DeclaredAlgebra:
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
            type=carrier_type,
            requires=requires,
            order=order,
        )
        return require(target, algebra_name)

    return target.transaction(install)


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
        type: Any = None,  # noqa: A002 -- the public carrier concept is a type
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
                    type=type,
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
            type=type,
            requires=requires,
            order=order,
        )


bool = replace(_PRESETS["bool"])  # noqa: A001 -- the catalog spelling is public
bag = replace(_PRESETS["bag"])
counting = replace(_PRESETS["counting"])
set = replace(_PRESETS["set"])  # noqa: A001 -- the catalog spelling is public
ranked = replace(_PRESETS["ranked"])
tropical = replace(_PRESETS["tropical"])
prob = replace(_PRESETS["prob"])
prov = replace(_PRESETS["prov"])
budget = replace(_PRESETS["budget"])
amplitude = replace(_PRESETS["amplitude"])

# PEP 562 preserves lazy import identity at the package; changing the real
# module object's class adds construction without introducing a proxy.
sys.modules[__name__].__class__ = _AlgebraModule
