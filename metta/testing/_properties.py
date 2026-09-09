"""Purpose: derive property tests from head annotations and algebra laws.

Guarantees: the public testing contracts survive the package partition
[tested: test_the_boolean_semiring_passes_every_generated_law; commit=WORKTREE].
"""

from __future__ import annotations

import functools
import inspect
import typing
from collections.abc import Callable, Iterable, Iterator
from typing import Any

import annotated_types as _at

import metta.seam as _seam
from metta._atoms.designation import SpaceLike
from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    S,
    Symbol,
    Variable,
    _encode,
)
from metta._atoms.mentions import CALLABLE_MENTIONS
from metta._atoms.model import decode
from metta._binding.dispatch import REGISTRY as _OPERATIONS
from metta._catalog.annotations import for_conversion, resolved_annotations
from metta._catalog.refinements import constraints as _constraints
from metta._catalog.refinements import holds as _holds
from metta._declare.define import Defined
from metta._lazy import optional as require_module
from metta._spaces.results import error_answer
from metta.algebra import DeclaredAlgebra, _canonical_laws
from metta.algebra import require as _require_algebra
from metta.convert import build as _build
from metta.convert import project as _project
from metta.testing._kits import _renamed_apart
from metta.testing._strategies import _TYPE_STRATEGIES, _register_atom_strategies, _st, ground_atoms
from metta.vocabularies import AlgebraLaw, EffectClass

#: The engine's affirmative answer, as it crosses.
_TRUE: Atom = _encode(value=True)


def _apply_predicate(test: Callable[[Any], Any], value: Any) -> bool:
    """A Predicate's function on a value: a defined head answers through the engine."""
    if isinstance(test, Defined):
        return [_encode(answer) for answer in test(value)] == [_TRUE]
    return bool(test(value))


def _admits(constraint: Any, value: Any) -> bool:
    return _holds(constraint, value, apply=_apply_predicate) is not False


def _generation_split(annotation: Any) -> tuple[Any, list[Any]]:
    """The annotation Hypothesis draws from, and the constraints it cannot.

    Hypothesis reads Gt, Ge, Lt, Le, MinLen, MaxLen and a plain Predicate
    itself and rewrites the numeric ones into bounds, so those stay in the
    annotation. MultipleOf it ignores with a warning, and a Predicate over a
    defined head it would call as a Python function, so those come back as
    filters applied after the draw. Unit, Timezone and doc constrain no value,
    and an Atom refinement is the engine's to judge; both are dropped here.
    """
    if typing.get_origin(annotation) is not typing.Annotated:
        return annotation, []
    base, *metadata = typing.get_args(annotation)
    kept: list[Any] = []
    filters: list[Any] = []
    for constraint in _constraints(metadata):
        if isinstance(constraint, _HYPOTHESIS_READS) or (
            isinstance(constraint, _at.Predicate) and not isinstance(constraint.func, Defined)
        ):
            kept.append(constraint)
        elif isinstance(constraint, (_at.MultipleOf, _at.Predicate)):
            filters.append(constraint)
    return (typing.Annotated[(base, *kept)] if kept else base), filters


_HYPOTHESIS_READS: tuple[type, ...] = (_at.Gt, _at.Ge, _at.Lt, _at.Le, _at.MinLen, _at.MaxLen)


def _inhabitants(space: Any, type_atom: Atom, parameter: str, owner: str):
    """Values for a parameter whose annotation is a MeTTa type atom.

    A builtin type draws from the strategy this module already exports for
    it; a user type draws from the atoms the space declares to inhabit it,
    ``(: x T)``, which is the engine's own answer to what a T is. A type
    nothing inhabits refuses naming the ``strategies=`` door.
    """
    st = _st()
    if isinstance(type_atom, Symbol) and type_atom.name in _TYPE_STRATEGIES:
        return _TYPE_STRATEGIES[type_atom.name]()
    declared = list(
        space.match(Expression([S[":"], Variable("inhabitant"), type_atom])).inhabitant
    )
    if not declared:
        msg = (
            f"cases({owner}): parameter {parameter!r} is typed {type_atom} and "
            f"nothing in {space} is declared to inhabit it; pass "
            f"strategies={{{parameter!r}: ...}}"
        )
        raise TypeError(msg)
    return st.sampled_from(declared)


def _strategy_for(space: Any, parameter: str, annotation: Any, owner: str):
    st = _st()
    if annotation is Any or annotation is inspect.Parameter.empty:
        return ground_atoms()
    if isinstance(annotation, Atom):
        return _inhabitants(space, annotation, parameter, owner)
    generated, filters = _generation_split(annotation)
    strategy = st.from_type(generated)
    for constraint in filters:
        strategy = strategy.filter(functools.partial(_admits, constraint))
    return strategy


def _return_constraints(head: Defined) -> list[Any]:
    returned = resolved_annotations(head.py).get("return")
    if typing.get_origin(returned) is not typing.Annotated:
        return []
    return _constraints(typing.get_args(returned)[1:])


def _snapshot(space: Any) -> list[str]:
    """The space's atoms as a multiset, renamed apart, for an unchanged claim."""
    return sorted(_renamed_apart(atom) for atom in space.atoms())


def _hypothesis_test(
    run: Callable[..., None],
    name: str,
    strategies: dict[str, Any],
    *,
    examples: int,
    seed: int | None,
) -> Callable[[], None]:
    """One Hypothesis test over ``run``, drawing each keyword from ``strategies``.

    The signature Hypothesis reads is supplied rather than compiled, so a
    failing example prints as ``cases_double(x=0)`` with the parameter names
    the caller chose. An engine call is a crossing and the box the suite runs
    on is loaded, so no wall deadline is set per example: it would fail the
    contract for the scheduler's reasons rather than the head's.
    """
    hypothesis = require_module(
        "hypothesis",
        "metta.testing generates examples with hypothesis, which is not "
        "installed; install pymetta[test]",
    )
    # Python lets a function object carry attributes and no static type says
    # so, so the three writes go through one local rather than three
    # classifiers: Hypothesis reads __signature__ to name the parameters it
    # draws, and pytest prints __name__.
    generated: Any = run
    generated.__signature__ = inspect.Signature(
        [inspect.Parameter(parameter, inspect.Parameter.KEYWORD_ONLY) for parameter in strategies]
    )
    generated.__name__ = name
    generated.__qualname__ = name
    wrapped = hypothesis.given(**strategies)(run)
    wrapped = hypothesis.settings(
        max_examples=examples,
        deadline=None,
        suppress_health_check=(
            hypothesis.HealthCheck.filter_too_much,
            hypothesis.HealthCheck.too_slow,
        ),
    )(wrapped)
    if seed is not None:
        wrapped = hypothesis.seed(seed)(wrapped)
    return wrapped


class Case:
    """One generated call of a defined head, with its contract checks.

    ``call`` is the MeTTa form, ``(double 3)``; calling the case runs the head
    over the arguments and checks every declared contract, answering the
    encoded answers or raising AssertionError naming the call and what it
    violated.
    """

    __slots__ = ("arguments", "head")

    def __init__(self, head: Defined, arguments: tuple[Any, ...]) -> None:
        """One case over ``head`` and the argument tuple to call it with."""
        self.head = head
        self.arguments = arguments

    @property
    def call(self) -> Expression:
        """The MeTTa form this case evaluates."""
        return Expression([Symbol(self.head.name), *(_encode(item) for item in self.arguments)])

    def __call__(self) -> list[Any]:
        """Run the head and check the return refinement and the effect class."""
        head = self.head
        call = self.call
        effect = head.effect
        watched = effect is not None and effect <= EffectClass.nondeterministicReadOnly
        before = _snapshot(head.space) if watched else None
        answers = [_encode(answer) for answer in head(*self.arguments)]
        for answer in answers:
            if error_answer(answer) is not None:
                msg = (
                    f"{call} answered {answer}: the head's declarations refuse a "
                    f"call its own signature generated"
                )
                raise AssertionError(msg)
        for constraint in _return_constraints(head):
            for answer in answers:
                if _holds(constraint, decode(answer), apply=_apply_predicate) is False:
                    msg = (
                        f"{call} answered {answer}, which violates "
                        f"{_encode(constraint)} declared on the return"
                    )
                    raise AssertionError(msg)
        if watched:
            if _snapshot(head.space) != before:
                msg = (
                    f"{call} wrote into {head.space}, and {head.name} declares "
                    f"the effect class {effect}, which promises no write"
                )
                raise AssertionError(msg)
            again = [_encode(answer) for answer in head(*self.arguments)]
            if again != answers:
                msg = (
                    f"{call} answered {answers} and then {again}: {head.name} "
                    f"declares the effect class {effect}, which promises the "
                    f"same answers for the same call"
                )
                raise AssertionError(msg)
        return answers

    def __repr__(self) -> str:
        """The case as its MeTTa call form."""
        return f"Case({self.call})"


class Cases:
    """The property test a defined head's declarations write.

    Built by ``cases``; see it for the three ways this object is used.
    """

    def __init__(
        self,
        head: Defined,
        *,
        examples: int,
        strategies: dict[str, Any] | None,
        seed: int | None,
    ) -> None:
        """Hold the head and the draw settings; refuse anything that is not a defined head."""
        if not isinstance(head, Defined):
            msg = (
                "cases takes a head defined with @m.define, whose annotations "
                f"say what to generate; got {head!r}"
            )
            raise TypeError(msg)
        unknown = sorted(set(strategies or ()) - set(head.params))
        if unknown:
            msg = f"cases({head.name}): strategies names no parameter of {head.name}: {unknown}"
            raise TypeError(msg)
        self.head = head
        self.examples = examples
        self.strategies = dict(strategies or {})
        self.seed = seed

    @functools.cached_property
    def strategy(self) -> dict[str, Any]:
        """One Hypothesis strategy per parameter, in the head's own order."""
        _register_atom_strategies()
        annotations = for_conversion(resolved_annotations(self.head.py))
        return {
            name: (
                self.strategies[name]
                if name in self.strategies
                else _strategy_for(
                    self.head.space, name, annotations.get(name, Any), self.head.name
                )
            )
            for name in self.head.params
        }

    def __call__(self, target: Callable[[Case], Any] | None = None) -> Any:
        """Run every case, or wrap a test function that receives each case."""
        if target is None:
            self._run()
            return None
        return self._wrap(target)

    @property
    def __func__(self) -> Callable[[], None]:
        """The Hypothesis test itself, which is what pytest collects."""
        return self._run

    @functools.cached_property
    def _run(self) -> Callable[[], None]:
        return self._wrap(lambda case: case())

    def _wrap(self, test: Callable[..., Any]) -> Callable[[], None]:
        head = self.head
        parameters = tuple(head.params)

        def run(**arguments: Any) -> None:
            test(Case(head, tuple(arguments[name] for name in parameters)))

        return _hypothesis_test(
            run, f"cases_{head.name}", self.strategy, examples=self.examples, seed=self.seed
        )

    def __iter__(self) -> Iterator[Case]:
        """The generated cases themselves, none of them run yet."""
        collected: list[Case] = []
        self._wrap(collected.append)()
        return iter(collected)

    def __repr__(self) -> str:
        """The call that built this object."""
        return f"cases({self.head.name}, examples={self.examples})"


def cases(
    head: Defined,
    *,
    examples: int = 100,
    strategies: dict[str, Any] | None = None,
    seed: int | None = None,
) -> Cases:
    """The property test a defined head's declarations already write.

    Every parameter's annotation becomes a Hypothesis strategy through
    ``from_type``, so ``Annotated[int, Gt(0)]`` draws positive integers, an
    atom class draws atoms, and a MeTTa type atom draws the values the space
    declares to inhabit it. Each generated call is run, and three contracts
    are checked: the head answers no ``(Error ...)``, every answer satisfies
    the return annotation's refinements, and a declared effect class at or
    below ``nondeterministicReadOnly`` neither writes into the space nor
    answers differently when the call is repeated. The failing example is
    Hypothesis's own shrunk one, printed with the MeTTa call form.

    Three shapes, deal.cases's:

        from metta import testing

        test_double = testing.cases(double)          # pytest collects it

        @testing.cases(double)
        def test_double_keeps_its_contract(case):
            case()                                   # run it; inspect case.call

        for case in testing.cases(double, examples=10):
            print(case.call)

    ``strategies`` overrides the draw for named parameters, which is the door
    for a MeTTa type nothing inhabits or an Atom refinement only the engine
    can judge; ``examples`` is Hypothesis's max_examples; ``seed`` derandomises
    one run.
    """
    return Cases(head, examples=examples, strategies=strategies, seed=seed)


# ------------------------------------------------------------ algebra laws
#
# The ghostwriter's vocabulary over a carrier: `binary_operation(associative=,
# commutative=, identity=, distributes_over=)`, `idempotent`, `roundtrip` and
# `equivalent` are the catalog's own algebra-law rows, so a declared row IS
# the property test, drawn over the carrier's values.


class _Carrier:
    """A declared algebra's operations, applied through the engine."""

    def __init__(self, space: Any, declaration: Any) -> None:
        self.space = space
        self.declaration = declaration

    def apply(self, operation: str, left: Any, right: Any) -> Atom:
        """One evaluated application, required to answer exactly one value."""
        call = Expression([Symbol(operation), _encode(left), _encode(right)])
        answers = self.space.eval(call)
        if len(answers) != 1:
            msg = f"{call} answered {len(answers)} values rather than one: {answers}"
            raise AssertionError(msg)
        (answer,) = answers
        if error_answer(answer) is not None:
            msg = f"{call} answered {answer}"
            raise AssertionError(msg)
        return answer

    def combine(self, left: Any, right: Any) -> Atom:
        """The declared combine operation on two carrier values."""
        return self.apply(self.declaration.combine, left, right)

    def extend(self, left: Any, right: Any) -> Atom:
        """The declared extend operation on two carrier values."""
        return self.apply(self.declaration.extend, left, right)

    @property
    def zero(self) -> Atom:
        """The declared combine identity."""
        return self.declaration.zero

    @property
    def one(self) -> Atom:
        """The declared extend identity."""
        return self.declaration.one

    def roundtrip(self, value: Any) -> tuple[Any, Any]:
        """The carrier value's projection, evaluated by the engine and rebuilt, beside the value.

        The carrier row carries values, so a value is decoded first and its
        TRANSLATED image, ``convert.project``, is what crosses: a registered
        class rebuilds through its own ``from_atom`` and a scalar through its
        grounding, and either must come back equal to what went in.
        """
        original = decode(_encode(value))
        answers = self.space.eval(_project(original).atom)
        if len(answers) != 1:
            msg = f"{_project(original).atom} evaluated to {answers} rather than to one value"
            raise AssertionError(msg)
        return _build(answers[0], type(original)), original

    def twin(self, operation: str) -> Callable[[Any, Any], Any] | None:
        """The host reference of an operation, or None when it has none.

        An operation registered from a Python callable has that callable; a
        builtin the callable-mention table names has the standard callable
        that mentions it, ``*`` and ``operator.mul``. A MeTTa-defined operation
        with neither has no host twin, and ``equivalent`` says so.
        """
        registered = _OPERATIONS.get(operation)
        if registered is not None:
            return registered.fn
        for standard, mention in CALLABLE_MENTIONS.items():
            if mention == operation:
                return standard
        return None


def _same(left: Any, right: Any) -> bool:
    """Equality as the engine reads it: by atom, identity for an opaque object."""
    return _encode(left) == _encode(right)


def _shown(value: Any) -> str:
    """A value in a counterexample: its atom, or an opaque object's own repr."""
    atom = _encode(value)
    inner = decode(atom)
    if isinstance(atom, Grounded) and not isinstance(inner, (bool, int, float, str)):
        return repr(inner)
    return str(atom)


def _equal_values(left: Any, right: Any) -> bool:
    """Equality as the host reads it, for a value rebuilt from its projection.

    A rebuilt object is a new object, so atom identity would refuse every
    correct codec; the class's own ``__eq__`` is the claim a round trip makes.
    An array-valued comparison reduces with ``all``.
    """
    outcome = left == right
    reduce = getattr(outcome, "all", None)
    return bool(reduce()) if callable(reduce) else bool(outcome)


def _law_spelling(law: Any) -> str:
    """A law by its catalog spelling, from a member or Python's own spelling of it.

    `AlgebraLaw.distributes_over` and the member name `"distributes_over"`
    both read as `distributes-over`: the enum is the underscore-to-hyphen map
    this surface keeps. A catalog spelling passes through, and an unknown name
    reaches the catalog's own refusal.
    """
    if isinstance(law, AlgebraLaw):
        return law.value
    return AlgebraLaw[law].value if law in AlgebraLaw.__members__ else str(law)


def _two_sided(
    operation: Callable[[Any, Any], Atom], unit: Any, value: Any, expected: Any
) -> tuple[Any, Any]:
    """Both orders of an identity or annihilation law: the failing pair, else the last."""
    on_the_left = (operation(unit, value), expected)
    if not _same(*on_the_left):
        return on_the_left
    return operation(value, unit), expected


class _Law(typing.NamedTuple):
    """One law as the two sides it compares over the values it draws."""

    arity: int
    sides: Callable[..., tuple[Any, Any] | None]
    same: Callable[[Any, Any], bool] = _same


#: The laws this seat ships, registered on the seam's `law` point so a PROVIDER
#: whose carrier obeys one nobody wrote down adds it the same way. The arity is
#: how many carrier values the property needs; a pair of sides the law's own
#: equality refuses is the counterexample. The names are the engine's
#: `algebra-law` vocabulary, which test_every_ghostwriter_law_name_is_a_catalog_row
#: holds them to.
# closed-set: seam; point=law; reason=a provider whose carrier obeys a law nobody wrote down registers it with metta.seam.law.register and metta.testing.laws runs it beside these
_SHIPPED_LAWS: dict[str, _Law] = {
    "combine-associative": _Law(
        3, lambda c, a, b, x: (c.combine(c.combine(a, b), x), c.combine(a, c.combine(b, x)))
    ),
    "combine-commutative": _Law(2, lambda c, a, b: (c.combine(a, b), c.combine(b, a))),
    "extend-associative": _Law(
        3, lambda c, a, b, x: (c.extend(c.extend(a, b), x), c.extend(a, c.extend(b, x)))
    ),
    "extend-commutative": _Law(2, lambda c, a, b: (c.extend(a, b), c.extend(b, a))),
    "left-distributive": _Law(
        3,
        lambda c, a, b, x: (c.extend(a, c.combine(b, x)), c.combine(c.extend(a, b), c.extend(a, x))),
    ),
    "right-distributive": _Law(
        3,
        lambda c, a, b, x: (c.extend(c.combine(a, b), x), c.combine(c.extend(a, x), c.extend(b, x))),
    ),
    "combine-idempotent": _Law(1, lambda c, a: (c.combine(a, a), a)),
    "combine-zero-identity": _Law(1, lambda c, a: _two_sided(c.combine, c.zero, a, a)),
    "extend-one-identity": _Law(1, lambda c, a: _two_sided(c.extend, c.one, a, a)),
    "extend-zero-annihilates": _Law(1, lambda c, a: _two_sided(c.extend, c.zero, a, c.zero)),
    "roundtrip": _Law(1, lambda c, a: c.roundtrip(a), _equal_values),
    "contraction": _Law(0, lambda _carrier: None),
}


def _equivalent(carrier: _Carrier, left: Any, right: Any) -> tuple[Any, Any] | None:
    """Each operation with a host twin agrees with it; the first disagreement is the counterexample."""
    for operation in (carrier.declaration.combine, carrier.declaration.extend):
        twin = carrier.twin(operation)
        if twin is None:
            continue
        engine = carrier.apply(operation, left, right)
        host = twin(decode(_encode(left)), decode(_encode(right)))
        if not _same(engine, host):
            return engine, host
    return None


_SHIPPED_LAWS["equivalent"] = _Law(2, _equivalent)


def _register_laws() -> None:
    """Put the shipped laws on the seam, once per process.

    Registering the same name twice REPLACES the row in place, so this is a
    no-op after the first call and a provider's own law is untouched by it.
    """
    for name, shipped in _SHIPPED_LAWS.items():
        _seam.law.register(
            name, arity=shipped.arity, sides=shipped.sides, same=shipped.same
        )


def _law_row(name: str) -> _Law:
    """One law by name: the seat's own, or one a provider registered.

    The point is the roster, so a law a provider added is here beside the
    shipped ones and the runner cannot tell them apart. A name with no row
    refuses with the roster.
    """
    _register_laws()
    row = _seam.law.table().get(name)
    if row is None:
        known = ", ".join(sorted(_seam.law.table())) or "nothing"
        msg = (
            f"no algebra law named {name!r}; registered: {known}. A provider "
            f"registers one with metta.seam.law.register(<name>, arity=..., "
            f"sides=...)"
        )
        raise KeyError(msg)
    return _Law(row.arity, row.sides, row.fields.get("same", _same))


class Laws:
    """The property tests a declared algebra's law rows write.

    Built by ``laws``; see it for the shapes. Iterating answers ``(law,
    test)`` pairs, one Hypothesis test per canonical law; calling runs them
    all; ``notes`` records the laws that had nothing to compare.
    """

    # `laws` is the keyword laws() takes and hands on, so the constructor
    # spells it the same way the factory does.
    def __init__(  # pylint: disable=redefined-outer-name
        self,
        algebra: Any,
        space: SpaceLike,
        *,
        laws: Iterable[str] | None,
        values: Any,
        examples: int,
        seed: int | None,
    ) -> None:
        """Resolve the declaration and canonicalise the requested laws through the catalog."""
        self.space = space.self
        self.declaration = (
            algebra
            if isinstance(algebra, DeclaredAlgebra)
            else _require_algebra(self.space, str(algebra))
        )
        requested = (
            tuple(_law_spelling(law) for law in laws)
            if laws is not None
            else tuple(sorted(self.declaration.laws))
        )
        self.laws = tuple(sorted(_canonical_laws(self.space, requested)))
        self.values = values
        self.examples = examples
        self.seed = seed
        self.notes: list[str] = []
        self._carrier = _Carrier(self.space, self.declaration)

    @functools.cached_property
    def strategy(self) -> Any:
        """The carrier's values: the declared finite carrier, the declared type, or ``values``."""
        st = _st()
        if self.values is not None:
            return self.values
        declaration = self.declaration
        if declaration.carrier:
            return st.sampled_from(list(declaration.carrier))
        kind = declaration.type
        if isinstance(kind, Symbol) and kind.name == "Number":
            # Integers, deliberately: floating-point addition is not
            # associative, and a law over Number is a claim about the
            # algebra rather than about rounding.
            return st.integers(min_value=-(2**62), max_value=2**62)
        if isinstance(kind, Symbol) and kind.name in _TYPE_STRATEGIES:
            return _TYPE_STRATEGIES[kind.name]()
        if isinstance(kind, type):
            return st.from_type(kind)
        if kind is None:
            # A preset with no carrier row is tested over its two identities,
            # which is the finite fragment its own laws are stated on.
            return st.sampled_from([declaration.zero, declaration.one])
        msg = (
            f"laws({declaration.name}): the carrier is {kind}, which names no "
            "strategy; pass values="
        )
        raise TypeError(msg)

    def _test(self, law: str) -> Callable[[], None]:
        arity, sides, same = _law_row(law)
        carrier = self._carrier
        name = self.declaration.name
        parameters = ("a", "b", "c")[:arity]

        def run(**drawn: Any) -> None:
            compared = sides(carrier, *(drawn[parameter] for parameter in parameters))
            if compared is None:
                return
            left, right = compared
            if not same(left, right):
                where = ", ".join(_shown(drawn[parameter]) for parameter in parameters)
                msg = (
                    f"algebra_law_violation: {name} law {law} fails at ({where}): "
                    f"{_shown(left)} differs from {_shown(right)}"
                )
                raise AssertionError(msg)

        if arity == 0:
            self.notes.append(f"{law}: a declared capability, not a property")
            run.__name__ = f"law_{law.replace('-', '_')}"
            return run
        return _hypothesis_test(
            run,
            f"law_{law.replace('-', '_')}",
            dict.fromkeys(parameters, self.strategy),
            examples=self.examples,
            seed=self.seed,
        )

    def __iter__(self) -> Iterator[tuple[str, Callable[[], None]]]:
        """One ``(law, test)`` pair per canonical law, in name order."""
        return iter([(law, self._test(law)) for law in self.laws])

    def __call__(self) -> None:
        """Run every law's property test."""
        self._run()

    @property
    def __func__(self) -> Callable[[], None]:
        """The test pytest collects: every law in turn."""
        return self._run

    @functools.cached_property
    def _run(self) -> Callable[[], None]:
        tests = list(self)

        def run_laws() -> None:
            for _law, test in tests:
                test()

        run_laws.__name__ = f"laws_{self.declaration.name.replace('-', '_')}"
        run_laws.__qualname__ = run_laws.__name__
        return run_laws

    def __repr__(self) -> str:
        """The algebra and the canonical laws this object tests."""
        return f"laws({self.declaration.name}, {', '.join(self.laws)})"


# The keyword names what it selects, which is what the function is called;
# renaming either to please the shadow check would rename public API.
def laws(  # pylint: disable=redefined-outer-name
    algebra: Any,
    space: Any = None,
    *,
    laws: Iterable[str] | None = None,
    values: Any = None,
    examples: int = 100,
    seed: int | None = None,
) -> Laws:
    """The property tests a declared algebra's law rows write.

    ``algebra`` is a ``DeclaredAlgebra`` (``metta.algebra.bool``, or what
    ``require`` answers) or its name in ``space``, which must be given
    because the operations are evaluated in it. Every law row the
    declaration names, or every law in ``laws``, becomes one Hypothesis test
    named by the ghostwriter vocabulary the ``AlgebraLaw`` rows spell:
    ``associative`` and ``commutative`` over each operation, ``identity`` for
    the two identities, ``distributes_over`` for extend over combine,
    ``idempotent`` for combine, ``roundtrip`` for every carrier value
    surviving projection through the engine and back, and ``equivalent`` for
    each operation agreeing with its host twin. A failure is the engine's own
    ``algebra_law_violation`` sentence with the shrunk counterexample.

        from metta import algebra, testing

        test_bool_laws = testing.laws(algebra.bool, m)   # pytest collects it
        for law, test in testing.laws("mine", m, laws=("commutative",)):
            test()

    Values come from the declared finite carrier, from the declared type
    (``Number`` draws integers, because floating-point addition is not
    associative), or from ``values``; a preset with no carrier row is tested
    over its two identities. A symbolic identity such as ``tropical``'s
    ``infinity`` is outside its operation's domain, which the engine's algebra
    scope short-circuits and this sweep does not; pass ``values`` and ``laws``
    that exclude it.
    """
    return Laws(algebra, space, laws=laws, values=values, examples=examples, seed=seed)
