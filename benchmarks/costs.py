"""Purpose: hold every head that DECLARES a cost class to that class.

`(cost (car-atom $n) linear)` in the engine's own source is a claim, and this
lane is what can fail it. Nothing else in the tree reads those rows as anything
but data: `explain` prints one, a docstring shows one, and neither asks whether
it is TRUE. A claim nobody checks is worse than no claim, because a reader
believes it.

The shape is Ciao's. Its assertion language states asymptotic cost as
`:- check comp nrev(A,B) + steps_o(length(A))` and CiaoPP discharges it against
statically inferred bounds, reporting the assertion `checked` when the inferred
upper bound sits under the stated one; the size measures it offers are
list-length, term-size, term-depth and integer-value
[source: https://ciao-lang.org/ciao/build/doc/ciaopp_tutorials.html/tut_advanced.html].
What is different here is the checker: this one MEASURES a ladder of sizes and
fits it, where CiaoPP proves. Static inference of the class is the research half
and is not claimed. Comparing the fit against a DECLARED class rather than
judging it alone is trend-prof's rule, which `benchmarks.scaling` already cites:
the same linear cost was a defect in one program at R-squared 0.95 and not a
defect in another at 0.65.

`benchmarks.scaling` is the sibling and the difference is who declares. There a
FAMILY is declared in a policy file this repository writes, and the workload is
Python. Here the declaration is a catalog row in the engine's own source, any
program can add one, and the workload is whatever call the row's witness names.
The curve arithmetic is `benchmarks.curves` for both, which is what keeps one
fit shared by three lanes.

Three gates, separate so a control can name which one it arms:

  refusal   a row this lane cannot measure is named and fails, rather than
            being skipped: a head that is not loaded, a measure with no ladder,
            a class the ladder's own floor makes unreachable, or a row whose
            worker did not finish inside the timeout.
  work      the answers the call produced, checked OUTSIDE the measured region
            and against the ledger's pinned counts. A head whose work quietly
            went away would otherwise report a beautiful flat curve.
  class     the fitted class against the declared one, in BOTH directions. An
            upper bound alone would let `quadratic` stand over a linear head,
            and a row that overstates its cost is as wrong as one that
            understates it.

The class gate is a band per class rather than a single bound, and the bands
below record the measurement that set them. They deliberately OVERLAP at their
edges: a reading in the overlap fits either neighbour and fails neither, so the
gate fires on a class jump and never on a boundary.

Assumes: the engine boots, and `&metta` carries the `(cost ...)` rows the
  engine's own source shipped.
Guarantees:
  - the verdict is inferences, which are deterministic and load-immune, so a
    busy box cannot make a run pass or fail. Every one of the ten shipped rows
    returned the IDENTICAL count at every size across two fresh processes at
    loadavg 47
    [measured 2026-09-07; command=python -m benchmarks.costs --json a.json,
    twice; fixture=the shipped rows on the provisioned MORK and C-reader
    configuration; commit=WORKTREE]
  - the two class controls the design asks for stay armed: a quadratic witness
    DECLARED linear fails the class gate, and the same witness declared
    quadratic passes it
    [tested: test_the_understated_control_fails_only_the_class_gate,
    test_the_quadratic_control_passes_every_gate; commit=WORKTREE]
  - the other direction is armed too: a linear witness declared quadratic fails
    the same gate, which is what makes the band a band rather than a ceiling
    [tested: test_the_overstated_control_fails_only_the_class_gate; commit=WORKTREE]
  - the exponential class is checked by the semi-log slope and not by the
    log-log exponent, because that exponent moves with the ladder: the fib
    control reads 6.887 over 14 to 20 and 8.466 over 16 to 22 while its slope
    reads 0.650 either way
    [measured 2026-09-07; command=python -m benchmarks.costs cost-control-exponential;
    fixture=the fib control under (cache ... refuse); commit=WORKTREE]
  - the work gate is armed by a control whose pinned answer counts come from
    ANOTHER row, so a head that stopped answering cannot pass
    [tested: test_the_work_control_fails_only_the_work_gate; commit=WORKTREE]
  - a ledger recorded under another configuration refuses the whole run before
    any row is measured, through the same stamp and the same comparison
    `benchmarks.scaling` uses [tested: test_a_drifted_ledger_refuses_the_cost_run;
    commit=WORKTREE]
Fails when: a declared class disagrees with the measurement in either
  direction, a row cannot be measured, a call's answers left their pinned
  counts, a control stops failing in its declared way, or the ledger's
  configuration stamp does not match the live one.
Owns resources: each row is a fresh process that runs its whole ladder and
  drops every space it creates; the parent joins, terminates or kills it
  through the lifecycle callback `bench.finish_process` supplies. A fresh SPACE
  per size is what keeps a memoised head honest: compiled clauses and their
  memo live in the space's module, so measuring size 22 after size 16 in one
  space would read a warm memo instead of the recursion.
Decides: inferences rather than wall time; a class band rather than a single
  bound; one ladder per measure rather than per row, with a control free to
  name its own because a quadratic body on the linear ladder would cost 2.7e8
  answers; and NO constant-factor guard, because `benchmarks.baseline.json` and
  `benchmarks.scaling` already pin absolute counts and a second tripwire here
  would turn every unrelated constant change into a red without new
  information.

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from benchmarks import atomic_json, collect_worker, curves
from benchmarks.scaling import configuration_drift, stamp_worker
from metta import engine
from metta.atoms import Expression, Symbol, V, Variable

SCHEMA_VERSION = 1
DEFAULT_REPETITIONS = 1
DEFAULT_TIMEOUT = 200.0
_BINDING_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = Path(__file__).resolve().parent / "cost-baseline.json"

#: The ladder a `length` measure fills its hole from. It has to be tall enough
#: that linear and linearithmic separate: the same builtins read 0.92 and 1.08
#: over 512 to 4096, where the gap is 0.15 and the fit is still climbing, and
#: 0.970 and 1.090 over these four, where the pair slopes have settled
#: [measured 2026-09-07; command=python -m benchmarks.costs size-atom
#: intersection-atom; fixture=the shipped rows; commit=WORKTREE].
#:
#: The design's `MAX_FLAT_CHILDREN` ceiling of 1024 does NOT apply and the
#: ladder deliberately passes it: that ceiling is SWI's `max_procedure_arity`,
#: which a flat expression meets only when it is STORED as a space fact, and a
#: fixture here is an argument the reader never asserts. Measured directly, a
#: 16,384-child argument crosses and evaluates with no arity error at all.
LENGTH_LADDER = (2048, 4096, 8192, 16384)

#: The ladder an `int` measure fills its hole from: the VALUE of $n, where the
#: term stays one atom however large it counts to.
INT_LADDER = (8, 16, 32, 64, 128)

#: The `int` ladder an `exponential` row takes instead, because the ladder above
#: would need fib(128). The design's `4 6 8 10 12` was measured first and does
#: not work here: the per-call floor of about 7,500 inferences dominates it and
#: the semi-log slope reads 0.088 against the 0.650 these four read
#: [measured 2026-09-07; command=python -m benchmarks.costs cost-control-exponential
#: with each ladder; fixture=the fib control under (cache ... refuse);
#: commit=WORKTREE].
EXPONENTIAL_LADDER = (16, 18, 20, 22)


@dataclass(frozen=True)
class Band:
    """The fitted exponents one class admits, as a closed interval."""

    lower: float
    upper: float

    def holds(self, exponent: float) -> bool:
        """Whether a fitted exponent sits inside this class."""
        return self.lower <= exponent <= self.upper


#: What each polynomial class admits, set from this tree's own measurements and
#: not from the sibling project's, for the reason `scaling-policy.json` records
#: about its own bounds. Every number below was read on the ladders above
#: [measured 2026-09-07; command=python -m benchmarks.costs --json;
#: fixture=the ten shipped rows and the five controls; commit=WORKTREE]:
#:
#:   constant       `(+ $n 1)` reads -0.005 flat at 409 inferences
#:   linear         the six linear rows read 0.962 to 0.990
#:   linearithmic   the four sorted rows read 1.056 to 1.090
#:   quadratic      the planted control reads 1.922
#:
#: `log` has no shipped row and its band is placed between constant's ceiling
#: and linear's floor; it is reachable only through an `int` measure, since a
#: call that receives an expression cannot cost less than reading it.
#:
#: Every pair below quadratic OVERLAPS at its boundary on purpose. A reading in
#: [1.02, 1.05] fits either linear or linearithmic and the gate stays quiet; the
#: gap it has to see is the one between 0.99 and 1.06, and it does.
#:
#: linearithmic and quadratic do NOT meet, and that gap is deliberate too. A
#: curve at n^1.45 is neither n log n nor n squared, this vocabulary has no word
#: for it, and stretching the two bands together would let such a head declare
#: the cheaper of the two. Ciao has no gap here because its `steps_o` takes an
#: arbitrary cost function where this takes one of six names
#: [tested: test_the_gap_below_quadratic_is_deliberate; commit=WORKTREE].
CLASS_BANDS: Mapping[str, Band] = {
    "constant": Band(-math.inf, 0.25),
    "log": Band(0.02, 0.60),
    "linear": Band(0.60, 1.05),
    "linearithmic": Band(1.02, 1.30),
    "quadratic": Band(1.60, 2.35),
}

#: An `exponential` row is judged on its semi-log slope, in doublings per unit
#: of size, rather than on a log-log exponent that has no fixed value for a
#: curve no power law describes. Measured on the same four sizes: the fib
#: control reads 0.650 and a synthetic cubic reads 0.230, so the floor sits
#: between them with room on both sides.
EXPONENTIAL_MINIMUM_SLOPE = 0.30

#: And on the log-log exponent as a second condition, above every polynomial
#: class this vocabulary can spell. A cubic reads exactly 3.000 and the fib
#: control reads 8.466.
EXPONENTIAL_MINIMUM_EXPONENT = 3.5

#: A `length` hole is filled with an expression of n children, and the call
#: evaluates the expression it is handed, so its cost cannot be below linear
#: whatever the head then does with it. Measured: a call that never even LOOKS
#: at its argument, `(if-equal a a 1 $n)`, still reads exponent 0.781 over 512
#: to 4096 and 4,412 to 22,314 inferences, all of it the argument arriving
#: [measured 2026-09-07; fixture=the same length fixture; commit=WORKTREE].
#: Declaring a cheaper class on a length measure is therefore unmeasurable
#: rather than merely wrong, and it is refused with the remedy: a head whose
#: cost really is constant in a size takes that size as a NUMBER.
LENGTH_FLOOR_CLASSES = frozenset({"constant", "log"})

#: The measures this lane can build a ladder for. Ciao's `size` (term-size) and
#: `depth` (term-depth) are in its vocabulary and not here, because no shipped
#: row needs them and a builder nothing exercises is a builder nothing checks.
#: A row naming one is refused BY NAME rather than measured as something else.
MEASURE_LADDERS: Mapping[str, tuple[int, ...]] = {
    "int": INT_LADDER,
    "length": LENGTH_LADDER,
}

# The multiplier, increment and modulus of the "ANSI C" linear congruential
# generator, transcribed so the fixture's order is pinned by THIS file rather
# than by a standard-library algorithm whose documentation reserves the right
# to change [source: Press, Teukolsky, Vetterling and Flannery, Numerical
# Recipes in C, second edition, table 7.1.1, the `rand()` line]. A ledger that
# pins exact inference counts cannot afford a fixture that moves with the
# interpreter.
_LCG_MULTIPLIER, _LCG_INCREMENT, _LCG_MODULUS = 1103515245, 12345, 2**31
_LCG_SEED = 7


def shuffled(size: int) -> list[int]:
    """`size` distinct integers in a fixed pseudorandom order.

    Distinct, so a dedup or a set operation does real work; UNSORTED, because
    `0..n-1` in order is the best case of every comparison sort and a row
    measured on it would claim a class the head only has for sorted input.
    """
    values = list(range(size))
    state = _LCG_SEED
    for index in range(size - 1, 0, -1):
        state = (_LCG_MULTIPLIER * state + _LCG_INCREMENT) % _LCG_MODULUS
        swap = state % (index + 1)
        values[index], values[swap] = values[swap], values[index]
    return values


def filler(measure: str, size: int) -> Any:
    """What one size puts in the row's hole, by the row's measure."""
    return size if measure == "int" else Expression(shuffled(size))


# ------------------------------------------------------------------- controls


@dataclass(frozen=True)
class Control:
    """A planted row whose verdict is known, riding in the lane permanently.

    `expect` is the gate it must fail, or `pass` when what it proves is that
    the gate admits a true claim. Both directions are needed: a gate that only
    ever fails is as useless as one that only ever passes.

    The two setup phases are not interchangeable. `setup` runs ONCE on the root
    space and carries what the process owns: the `&metta` rows, which a second
    add refuses as a duplicate, and the arrow declaration, which is where the
    engine resolves the row's measure from and which a child space cannot hold
    for it. `program` runs in EVERY fresh space and carries the equations,
    because a compiled clause and its memo live in that space's own module and
    reusing them would measure the previous size's memo.
    """

    head: str
    cost_class: str
    measure: str
    expect: str
    why: str
    setup: tuple[str, ...]
    program: tuple[str, ...]
    sizes: tuple[int, ...] | None = None
    pinned_from: str | None = None


#: A body that is genuinely quadratic in its argument's length: for every child
#: it enumerates every child again. This is the shape the sibling project found
#: twice inside a lane whose own assertions were on charged steps.
_QUADRATIC_BODY = (
    "(= ({head} $xs)"
    "   (collapse (let $x (superpose $xs) (let $y (superpose $xs) $y))))"
)
#: A body that is linear and answers ONE atom, so its class and its answer
#: count are independent plants.
_LINEAR_BODY = "(= ({head} $xs) (collapse (superpose $xs)))"

#: The quadratic controls run here rather than on LENGTH_LADDER, and the reason
#: is arithmetic: 16,384 squared is 2.7e8 answers. The plant is the CLASS, and
#: the class transfers -- the same body reads 1.922 here and would read closer
#: to 2 higher up, both far above linear's 1.05 ceiling. The sibling lane makes
#: the same choice for the same reason, its planted quadratic running 50 to 400
#: while its siblings run 200 to 1600.
_CONTROL_LADDER = (64, 128, 256, 512)

CONTROLS: tuple[Control, ...] = (
    Control(
        head="cost-control-quadratic",
        cost_class="quadratic",
        measure="length",
        expect="pass",
        why="a quadratic body declared quadratic, which is what proves the "
        "band admits a true claim rather than only rejecting false ones",
        setup=("!(add-atom &metta (cost (cost-control-quadratic $n) quadratic))",),
        program=(_QUADRATIC_BODY.format(head="cost-control-quadratic"),),
        sizes=_CONTROL_LADDER,
    ),
    Control(
        head="cost-control-understated",
        cost_class="linear",
        measure="length",
        expect="class",
        why="the same quadratic body DECLARED linear: the exponent gate's own "
        "reason for existing",
        setup=("!(add-atom &metta (cost (cost-control-understated $n) linear))",),
        program=(_QUADRATIC_BODY.format(head="cost-control-understated"),),
        sizes=_CONTROL_LADDER,
    ),
    Control(
        head="cost-control-overstated",
        cost_class="quadratic",
        measure="length",
        expect="class",
        why="a linear body declared quadratic, which an upper-bound check would "
        "let stand and which is just as wrong as understating",
        setup=("!(add-atom &metta (cost (cost-control-overstated $n) quadratic))",),
        program=(_LINEAR_BODY.format(head="cost-control-overstated"),),
        sizes=_CONTROL_LADDER,
    ),
    Control(
        head="cost-control-exponential",
        cost_class="exponential",
        measure="int",
        expect="pass",
        why="naive Fibonacci with the automatic memo refused, which is the only "
        "shape the semi-log test is for; without it that test never runs",
        setup=(
            "!(add-atom &metta (cache cost-control-exponential refuse))",
            "!(add-atom &metta (cost (cost-control-exponential $n) exponential))",
            # The arrow lives HERE and not in the per-space program: the engine
            # resolves a row's measure from &self's declarations, so an arrow
            # declared only in a child space leaves this row reading `length`
            # and the ladder filling an integer hole with an expression.
            "(: cost-control-exponential (-> Number Number))",
        ),
        program=(
            "(= (cost-control-exponential $n)"
            "   (if (< $n 2) $n (+ (cost-control-exponential (- $n 1))"
            "                      (cost-control-exponential (- $n 2)))))",
        ),
    ),
    Control(
        head="cost-control-work",
        cost_class="linear",
        measure="length",
        expect="work",
        why="a linear body whose answer counts are pinned from another row, so "
        "the work gate fires while the class gate stays quiet",
        setup=("!(add-atom &metta (cost (cost-control-work $n) linear))",),
        program=("(= (cost-control-work $xs) (superpose $xs))",),
        pinned_from="size-atom",
    ),
)

CONTROLS_BY_HEAD: Mapping[str, Control] = {control.head: control for control in CONTROLS}


# ------------------------------------------------------------------ the rows


@dataclass(frozen=True)
class Row:
    """One declared row, resolved enough to be measured."""

    head: str
    witness: str
    cost_class: str
    measure: str
    sizes: tuple[int, ...]
    control: Control | None = None

    @property
    def shipped(self) -> bool:
        """Whether this row came from the engine's source rather than a plant."""
        return self.control is None


def ladder_for(measure: str, cost_class: str, override: Sequence[int] | None) -> tuple[int, ...]:
    """The sizes a row is measured over, from its measure and its class."""
    if override is not None:
        return tuple(override)
    if measure == "int" and cost_class == "exponential":
        return EXPONENTIAL_LADDER
    return MEASURE_LADDERS.get(measure, ())


def refusal(head: str, cost_class: str, measure: str, *, loaded: bool) -> str | None:
    """Why this row cannot be measured, or None when it can."""
    if not loaded:
        return (
            f"{head} declares a cost row and is not a function this engine can "
            f"call, so the row's ladder would measure nothing; import the "
            f"library that defines it, or remove the row"
        )
    if measure not in MEASURE_LADDERS:
        return (
            f"{head} names the measure {measure!r}, which this lane builds no "
            f"ladder for; the measures it builds are "
            f"{', '.join(sorted(MEASURE_LADDERS))}"
        )
    if measure == "length" and cost_class in LENGTH_FLOOR_CLASSES:
        return (
            f"{head} declares {cost_class} over a length measure, and a call "
            f"that receives an expression of n children cannot cost less than "
            f"reading it; take the size as a Number and declare the measure "
            f"int, or declare linear"
        )
    if cost_class != "exponential" and cost_class not in CLASS_BANDS:
        return f"{head} declares the class {cost_class!r}, which has no band here"
    return None


# ------------------------------------------------------------------ workers


def _witness_atom(context: Any, head: str) -> tuple[Any, str, str] | None:
    """The row's witness, class and measure as this process's engine holds them.

    Read through the ordinary catalog match and the engine's own resolution of
    the measure, so the lane measures what `explain` and every docstring report
    rather than a second reading of the same rows.
    """
    catalog = context.space("&metta")
    for row in catalog.match(Expression([Symbol("cost"), V.witness, V.cost_class])):
        witness = row.witness
        if isinstance(witness, Expression) and str(witness.children[0]) == head:
            claim = context._rt.apply_must("metta_py_cost_declaration", head)
            return witness, str(claim[0]), str(claim[1])
    return None


def _hole(witness: Any) -> str | None:
    """The one variable name in the witness, or None when there is not exactly one."""
    names: set[str] = set()
    stack = [witness]
    while stack:
        atom = stack.pop()
        if isinstance(atom, Variable):
            names.add(atom.name)
        elif isinstance(atom, Expression):
            stack.extend(atom.children)
    return names.pop() if len(names) == 1 else None


def _is_error(atom: Any) -> bool:
    return isinstance(atom, Expression) and bool(atom.children) and str(atom.children[0]) == "Error"


def cost_row_case(head: str, size: int) -> tuple[Any, Callable[[], int]]:
    """One shipped row's call at one size, as the space-and-operation pair
    `benchmarks.pure` drives inside perf's controlled window.

    Only the evaluation is the operation. Resolving the row and building the
    fixture happen here, outside it, which is Renaissance's rule that
    validation and setup never charge themselves to the measurement, and the
    reason this pairing says anything about the head at all: the fixture is the
    larger half of the inference count.
    """  # noqa: D205  -- the contract is one continuous invariant
    context = engine()
    found = _witness_atom(context, head)
    if found is None:
        message = f"{head} declares no (cost ...) row this engine can read"
        raise LookupError(message)
    witness, _cost_class, measure = found
    hole = _hole(witness)
    if hole is None:
        message = f"{head}'s witness {witness} does not name exactly one hole"
        raise LookupError(message)
    call = witness.subs({Variable(hole): filler(measure, size)})
    space = context.space()

    def operation() -> int:
        space.eval(call)
        return size

    return space, operation


def sample_worker(spec: Mapping[str, Any], connection: Any) -> None:
    """Measure one row's whole ladder in this process and send the samples back.

    The setup runs ONCE on the root space; the program runs per SIZE in a fresh
    child. `Control` says why that split is not a detail.
    """
    try:
        context = engine()
        for text in spec["setup"]:
            context.self.run(text)
        head = str(spec["head"])
        found = _witness_atom(context, head)
        if found is None:
            message = f"{head} has no (cost ...) row in this process"
            raise LookupError(message)
        witness, cost_class, measure = found
        hole = _hole(witness)
        if hole is None:
            message = f"{head}'s witness {witness} does not name exactly one hole"
            raise LookupError(message)
        samples = []
        for size in spec["sizes"]:
            space = context.space()
            try:
                for text in spec["program"]:
                    space.run(text)
                call = witness.subs({Variable(hole): filler(measure, size)})
                with space.stats() as stats:
                    answers = space.eval(call)
                errors = sum(1 for atom in answers if _is_error(atom))
                samples.append(
                    {
                        "size": size,
                        "inferences": int(stats.inferences),
                        "answers": len(answers),
                        "problem": (
                            f"answered {errors} Error atoms at size {size}"
                            if errors
                            else None
                        ),
                    }
                )
            finally:
                space.drop()
        connection.send(
            {
                "ok": True,
                "samples": samples,
                "resolved": [str(witness), cost_class, measure],
                "pid": os.getpid(),
            }
        )
    except BaseException as exc:  # noqa: BLE001  -- a worker failure crosses the process boundary as evidence
        connection.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        connection.close()


def catalog_worker(connection: Any) -> None:
    """Every shipped `(cost ...)` row, with whether its head can be called."""
    try:
        context = engine()
        catalog = context.space("&metta")
        callable_here = set(context.self.builtins())
        rows = []
        for row in catalog.match(Expression([Symbol("cost"), V.witness, V.cost_class])):
            witness = row.witness
            if not isinstance(witness, Expression) or not witness.children:
                continue
            head = str(witness.children[0])
            claim = context._rt.apply_must("metta_py_cost_declaration", head)
            rows.append(
                {
                    "head": head,
                    "witness": str(witness),
                    "class": str(claim[0]),
                    "measure": str(claim[1]),
                    "loaded": head in callable_here
                    or bool(context.self.is_function_here(head)),
                }
            )
        connection.send({"ok": True, "rows": sorted(rows, key=lambda row: row["head"])})
    except BaseException as exc:  # noqa: BLE001  -- a worker failure crosses the process boundary as evidence
        connection.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        connection.close()


# ------------------------------------------------------------------- verdict


@dataclass(frozen=True)
class Measurement:
    """Every repetition of one row, reduced to the values a verdict reads."""

    sizes: tuple[int, ...]
    samples: tuple[tuple[int, ...], ...]
    representative: tuple[int, ...]
    answers: tuple[int, ...]
    problems: tuple[str, ...]

    @property
    def spread(self) -> dict[str, float]:
        """The widest gap any size showed across its repetitions."""
        gaps = [max(row) - min(row) for row in self.samples]
        return {
            "absolute_max": max(gaps),
            "relative_max": max(
                gap / max(abs(min(row)), 1)
                for gap, row in zip(gaps, self.samples, strict=True)
            ),
        }


def reduce_repetitions(
    sizes: Sequence[int], repetitions: Sequence[Sequence[Mapping[str, Any]]]
) -> Measurement:
    """Take the minimum across repetitions and collect every check they ran."""
    columns = tuple(
        tuple(int(repetition[index]["inferences"]) for repetition in repetitions)
        for index in range(len(sizes))
    )
    first = repetitions[0]
    return Measurement(
        sizes=tuple(sizes),
        samples=columns,
        representative=tuple(min(column) for column in columns),
        answers=tuple(int(sample["answers"]) for sample in first),
        problems=tuple(
            dict.fromkeys(
                str(sample["problem"])
                for repetition in repetitions
                for sample in repetition
                if sample["problem"] is not None
            )
        ),
    )


@dataclass(frozen=True)
class Failure:
    """One reason a row did not pass, tagged so a control can assert on it."""

    kind: str
    message: str


@dataclass
class RowResult:
    """One row's measurement, its fit, and every reason it did not pass."""

    row: Row
    measurement: Measurement | None
    fit: dict[str, Any]
    failures: list[Failure] = field(default_factory=list)

    @property
    def kinds(self) -> set[str]:
        """The distinct gate names this row failed."""
        return {failure.kind for failure in self.failures}


def fit_report(measurement: Measurement) -> dict[str, Any]:
    """Both fits and google/benchmark's shape name, for one row's ladder."""
    power = curves.power_fit(measurement.sizes, measurement.representative)
    growth = curves.exponential_fit(measurement.sizes, measurement.representative)
    best, models = curves.select_model(measurement.sizes, measurement.representative)
    return {
        "exponent": power.exponent,
        "r_squared": power.r_squared,
        "coefficient": power.coefficient,
        "pair_slopes": [round(value, 4) for value in power.pair_slopes],
        "doubling_slope": growth.slope,
        "doubling_r_squared": growth.r_squared,
        "best_model": best,
        "normalised_rms": {name: round(value, 6) for name, value in models.items()},
    }


def class_failure(row: Row, fit: Mapping[str, Any]) -> str | None:
    """Why the measurement disagrees with the declared class, in either direction."""
    if row.cost_class == "exponential":
        slope = float(fit["doubling_slope"])
        exponent = float(fit["exponent"])
        if slope < EXPONENTIAL_MINIMUM_SLOPE:
            return (
                f"{row.head} doubles {slope:.4f} times per unit of $n, below the "
                f"{EXPONENTIAL_MINIMUM_SLOPE} an exponential claim needs; a "
                f"polynomial's slope falls toward zero and a cubic reads 0.230"
            )
        if exponent < EXPONENTIAL_MINIMUM_EXPONENT:
            return (
                f"{row.head} grows as size^{exponent:.3f}, which every "
                f"polynomial class in this vocabulary already covers, so an "
                f"exponential claim overstates it"
            )
        return None
    band = CLASS_BANDS[row.cost_class]
    exponent = float(fit["exponent"])
    if exponent > band.upper:
        return (
            f"{row.head} grows as size^{exponent:.3f}, above the "
            f"{row.cost_class} band's ceiling of {band.upper}"
        )
    if exponent < band.lower:
        return (
            f"{row.head} grows as size^{exponent:.3f}, below the "
            f"{row.cost_class} band's floor of {band.lower}; the row claims a "
            f"cost the head does not have"
        )
    return None


def evaluate(
    row: Row, measurement: Measurement, pinned: Mapping[str, Any] | None
) -> RowResult:
    """Fit one row and collect every failure, each tagged with its gate.

    Work is checked BEFORE the fit and stops it, the way the sibling lane
    refuses a family that left its route: a call whose answers went away
    describes no class, and fitting it would report a shape for nothing.
    """
    failures = [Failure("work", f"{row.head} {problem}") for problem in measurement.problems]
    if pinned is not None and list(pinned.get("answers", [])) != list(measurement.answers):
        failures.append(
            Failure(
                "work",
                f"{row.head} answered {list(measurement.answers)} where its "
                f"pinned row records {list(pinned.get('answers', []))}; the call "
                f"is not doing the work the class was measured on",
            )
        )
    if sum(1 for count in measurement.representative if count > 0) < 2:
        failures.append(
            Failure(
                "work",
                f"{row.head} recorded {list(measurement.representative)} "
                f"inferences, too few positive points to fit",
            )
        )
    if failures:
        return RowResult(row, measurement, {"refused": True}, failures)
    fit = fit_report(measurement)
    problem = class_failure(row, fit)
    if problem is not None:
        failures.append(Failure("class", problem))
    return RowResult(row, measurement, fit, failures)


def control_verdict(control: Control, result: RowResult) -> list[str]:
    """Check a planted control still lands where it is planted to land.

    This is the only place where NOT failing is itself a failure, and where
    failing the WRONG gate is too: asserting the gate as well as the outcome is
    what proves the three gates are independent rather than one gate wearing
    three names.
    """
    observed = result.kinds
    if control.expect == "pass":
        if not observed:
            return []
        return [
            f"control {control.head} failed {sorted(observed)}; it is planted to "
            f"pass every gate, and what it proves is that {control.why}"
        ]
    if observed == {control.expect}:
        return []
    if not observed:
        return [
            f"control {control.head} passed every gate; it is planted to fail "
            f"the {control.expect} gate, and that gate is no longer proven able "
            f"to fail ({control.why})"
        ]
    return [
        f"control {control.head} failed {sorted(observed)}, but it is planted to "
        f"fail exactly the {control.expect} gate"
    ]


# -------------------------------------------------------------------- the ledger


def _planted_row(
    control: Control, recorded: Mapping[str, Any], rows: Mapping[str, Any], cause_commit: str
) -> dict[str, Any]:
    """Take the work control's ANSWER counts from another row, never its own.

    The plant IS the distance between what this control answers and what its
    row records, so recording its own answers here would replace the plant with
    itself and the lane would go green having proved nothing. Everything else in
    the row stays the control's own measurement, so the file still says what was
    run; only the one planted field comes from elsewhere, and the chain below
    says which field and from where.
    """
    source = rows.get(str(control.pinned_from))
    if source is None:
        msg = (
            f"control {control.head} is pinned from {control.pinned_from}, which "
            f"has no row yet; record it in the same run or before this one"
        )
        raise KeyError(msg)
    return dict(recorded) | {
        "answers": list(source["answers"]),
        "cause": {
            "commit": cause_commit,
            "chain": [
                f"THE PLANT. Only `answers` is copied, from {control.pinned_from}, "
                f"whose call answers one atom where this control answers one per "
                f"child.",
                "The distance between the two is the planted work failure, so this "
                "field is never re-recorded from the control's own run.",
                "Its class is untouched and true, so the control passes the class "
                "gate and fails only the work gate.",
            ],
        },
    }


def ledger_document(
    results: Mapping[str, RowResult],
    previous: Mapping[str, Any],
    *,
    stamp: Mapping[str, Any],
    repetitions: int,
    measured_on: str,
    cause_commit: str,
) -> dict[str, Any]:
    """Pin every measured row, keeping each control's row exactly as planted."""
    rows = dict(previous.get("rows", {}))
    recorded: dict[str, dict[str, Any]] = {}
    for head, result in results.items():
        if result.measurement is None:
            continue
        recorded[head] = {
            "witness": result.row.witness,
            "class": result.row.cost_class,
            "measure": result.row.measure,
            "counter": "inferences",
            "sizes": list(result.measurement.sizes),
            "inferences": list(result.measurement.representative),
            "answers": list(result.measurement.answers),
            "spread": result.measurement.spread,
            "fit": result.fit,
            "measured": measured_on,
            "cause": {
                "commit": cause_commit,
                "chain": [
                    f"python -m benchmarks.costs --record measured {head}",
                    f"minimum of {repetitions} fresh process(es), one fresh space per size",
                    f"the declared class is {result.row.cost_class} "
                    f"in $n by {result.row.measure}",
                ],
            },
        }
    rows |= {
        head: row
        for head, row in recorded.items()
        if CONTROLS_BY_HEAD.get(head) is None
        or CONTROLS_BY_HEAD[head].pinned_from is None
    }
    for control in CONTROLS:
        if control.pinned_from is not None and control.head in recorded:
            rows[control.head] = _planted_row(
                control, recorded[control.head], rows, cause_commit
            )
    return {
        "schema": SCHEMA_VERSION,
        "repetitions": repetitions,
        "configuration": dict(stamp),
        "rows": rows,
        "repin_rule": (
            "A changed pin must name the first causal code change, carry the old "
            "and new counts, and say why the head still holds its declared class. "
            "The class itself lives in the engine's source as a (cost ...) row; "
            "this file is only what the lane measured and when. A control row "
            "pinned from another row is never re-recorded: the planted work "
            "failure IS the distance between them."
        ),
    }


# --------------------------------------------------------------------- the suite


def _print_row(result: RowResult) -> None:
    row = result.row
    if result.measurement is None:
        print(f"{row.head:26s} REFUSED, not measured")
        return
    fit = result.fit
    if fit.get("refused"):
        print(f"{row.head:26s} {list(result.measurement.representative)} REFUSED, not fitted")
        return
    quality = "n/a" if fit["r_squared"] is None else f"{fit['r_squared']:.4f}"
    print(
        f"{row.head:26s} {list(result.measurement.representative)}\n"
        f"{'':26s} {row.witness} declared {row.cost_class} in $n ({row.measure})\n"
        f"{'':26s} exponent={fit['exponent']:.3f} r2={quality} "
        f"doubling={fit['doubling_slope']:.4f} best_model={fit['best_model']}\n"
        f"{'':26s} pairs={fit['pair_slopes']} answers={list(result.measurement.answers)}"
    )


def declared_rows(shipped: Sequence[Mapping[str, Any]]) -> list[Row]:
    """Every row this run will consider, the engine's own and the plants."""
    rows = [
        Row(
            head=str(row["head"]),
            witness=str(row["witness"]),
            cost_class=str(row["class"]),
            measure=str(row["measure"]),
            sizes=ladder_for(str(row["measure"]), str(row["class"]), None),
        )
        for row in shipped
        if str(row["head"]) not in CONTROLS_BY_HEAD
    ]
    rows.extend(
        Row(
            head=control.head,
            witness=f"({control.head} $n)",
            cost_class=control.cost_class,
            measure=control.measure,
            sizes=ladder_for(control.measure, control.cost_class, control.sizes),
            control=control,
        )
        for control in CONTROLS
    )
    return sorted(rows, key=lambda row: row.head)


def run_suite(
    *,
    names: Sequence[str],
    repetitions: int,
    timeout: float,
    output: Path | None,
    record: bool,
    paired: bool,
    measured_on: str,
    cause_commit: str,
    ledger_path: Path,
    context: Any,
    finish_process: Callable[[Any, float], str | None],
) -> int:
    """Measure every selected row, fit it, and report the verdict."""
    previous = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {}
    pinned = previous.get("rows", {})
    stamp = collect_worker(
        stamp_worker,
        (),
        label="metta-costs-stamp",
        timeout=timeout,
        context=context,
        finish_process=finish_process,
    )["stamp"]
    print("configuration: " + ", ".join(f"{key}={value}" for key, value in sorted(stamp.items())))
    drift = [] if record else configuration_drift(stamp, previous)
    if drift:
        for moved in drift:
            print(f"CONFIGURATION DRIFT {moved}")
        print(
            "the pinned rows were measured under a different configuration, so "
            "no comparison here would mean anything; restore the pinned "
            "configuration or re-pin with --record"
        )
        return 1

    shipped = collect_worker(
        catalog_worker,
        (),
        label="metta-costs-catalog",
        timeout=timeout,
        context=context,
        finish_process=finish_process,
    )["rows"]
    loaded = {str(row["head"]): bool(row["loaded"]) for row in shipped}
    selected = [row for row in declared_rows(shipped) if not names or row.head in names]
    if not selected:
        print("no (cost ...) row matched; use --list to see the declared heads")
        return 1

    results: dict[str, RowResult] = {}
    failures: list[str] = []
    for row in selected:
        refused = refusal(
            row.head, row.cost_class, row.measure, loaded=loaded.get(row.head, True)
        )
        if refused is None and not row.sizes:
            refused = f"{row.head} has no ladder for measure {row.measure!r}"
        if refused is not None:
            result = RowResult(row, None, {"refused": True}, [Failure("refusal", refused)])
        else:
            control = row.control
            spec = {
                "head": row.head,
                "sizes": list(row.sizes),
                "setup": list(control.setup) if control else [],
                "program": list(control.program) if control else [],
            }
            try:
                repeated = [
                    collect_worker(
                        sample_worker,
                        (spec,),
                        label=f"metta-costs-{row.head}-{index}",
                        timeout=timeout,
                        context=context,
                        finish_process=finish_process,
                    )["samples"]
                    for index in range(repetitions)
                ]
            except RuntimeError as error:
                result = RowResult(
                    row,
                    None,
                    {"refused": True},
                    [
                        Failure(
                            "refusal",
                            f"{row.head} did not finish its ladder "
                            f"{list(row.sizes)}: {error}",
                        )
                    ],
                )
            else:
                measurement = reduce_repetitions(row.sizes, repeated)
                result = evaluate(row, measurement, pinned.get(row.head))
        results[row.head] = result
        _print_row(result)

        if row.control is not None:
            problems = control_verdict(row.control, result)
            for problem in problems:
                print(f"CONTROL BROKEN {problem}")
            failures.extend(problems)
            for failure in result.failures:
                print(f"{'':26s} control fired as planted: {failure.message}")
        else:
            for failure in result.failures:
                print(f"REFUTED [{failure.kind}] {failure.message}")
                failures.append(failure.message)

    document = {
        "schema": SCHEMA_VERSION,
        "repetitions": repetitions,
        "configuration": stamp,
        "loadavg": Path("/proc/loadavg").read_text(encoding="ascii").strip(),
        "rows": {
            head: {
                "witness": result.row.witness,
                "class": result.row.cost_class,
                "measure": result.row.measure,
                "sizes": list(result.row.sizes),
                "inferences": (
                    [] if result.measurement is None else list(result.measurement.representative)
                ),
                "answers": (
                    [] if result.measurement is None else list(result.measurement.answers)
                ),
                "fit": result.fit,
                "control": None if result.row.control is None else result.row.control.expect,
                "failures": [
                    {"kind": item.kind, "message": item.message} for item in result.failures
                ],
            }
            for head, result in results.items()
        },
        "failures": failures,
    }
    if paired:
        _report_paired(results, document, repetitions=repetitions, timeout=timeout)
    if output is not None:
        atomic_json(output, document)
        print(f"wrote cost data to {output}")
    if record:
        atomic_json(
            ledger_path,
            ledger_document(
                results,
                previous,
                stamp=stamp,
                repetitions=repetitions,
                measured_on=measured_on,
                cause_commit=cause_commit,
            ),
        )
        print(f"recorded {ledger_path}")
    if failures:
        return 1
    print(f"every one of {len(results)} declared cost rows measured its declared class")
    return 0


def _paired_disagreement(row: Row, exponent: float) -> str | None:
    """Whether the retired-instruction curve lands outside the declared class.

    Advisory and never a failure, because instructions are not load-immune. It
    is here because a row whose two counters disagree states the cheaper of the
    two, and that is how `unique-atom` came to have no row at all: SWI's
    `list_to_set/2` sorts in C, so the engine retires one inference for a call
    whose real work is n log n, and its inference curve is the ARGUMENT
    arriving [measured 2026-09-07: 0.978 against 1.057]. Whatever the shipped
    rows do today, this is what says when one of them starts doing that.
    """
    if row.cost_class == "exponential":
        return None
    band = CLASS_BANDS[row.cost_class]
    if band.holds(exponent):
        return None
    return (
        f"instructions read size^{exponent:.3f}, outside the "
        f"{row.cost_class} band [{band.lower}, {band.upper}] the inference "
        f"curve sits in; the row states one counter's answer and the other "
        f"counter disagrees"
    )


def _report_paired(
    results: Mapping[str, RowResult],
    document: dict[str, Any],
    *,
    repetitions: int,
    timeout: float,
) -> None:
    """The same ladders under `perf stat -e instructions:u`, advisory and never gating.

    LAW 2: a head whose work crosses into C retires no inferences there, and
    four of the ten shipped rows do exactly that. `size-atom` is SWI's own
    `length/2`, so its inference curve is the ARGUMENT arriving and says
    nothing about the C the head then runs. This is the second reading, and it
    is advisory because this workstation is shared and a retired-instruction
    count taken beside other load is advisory by construction.
    """
    from benchmarks.scaling import paired_instructions  # noqa: PLC0415 -- perf only

    for head, result in results.items():
        if result.measurement is None or not result.row.shipped:
            continue
        try:
            document["rows"][head]["paired"] = paired_instructions(
                ["cost-row", "--head", head],
                result.measurement.sizes,
                rounds=max(repetitions, 3),
                timeout=timeout,
            )
            exponent = document["rows"][head]["paired"]["exponent"]
            note = _paired_disagreement(result.row, exponent)
            print(f"{head:26s} paired instructions:u exponent={exponent:.3f} (advisory)")
            if note is not None:
                print(f"{'':26s} PAIRED DISAGREES {note}")
        except (FileNotFoundError, RuntimeError, TimeoutError, ValueError) as error:
            document["rows"][head]["paired"] = {"error": str(error)}
            print(f"{head:26s} paired instructions unavailable: {error}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the cost-rows gate over the selected rows."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*")
    parser.add_argument("--list", action="store_true", dest="list_rows")
    parser.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--record", action="store_true", help="rewrite the ledger")
    parser.add_argument(
        "--paired",
        action="store_true",
        help="also measure retired instructions for every shipped row",
    )
    parser.add_argument(
        "--measured-on",
        default=os.environ.get("METTA_COSTS_MEASURED_ON", ""),
        help="the date --record writes into each row; today when unset",
    )
    parser.add_argument(
        "--cause-commit", default=os.environ.get("METTA_COSTS_CAUSE_COMMIT", "WORKTREE")
    )
    arguments = parser.parse_args(argv)
    if arguments.repetitions < 1:
        parser.error("--repetitions must be positive")
    if arguments.timeout <= 0:
        parser.error("--timeout must be positive")
    # Deferred for the reason the sibling lane defers it: benchmarks.pure
    # imports this module for the paired ladder, and a top-level import here
    # would pull bench.py and pytest into the image perf measures.
    from bench import finish_process  # noqa: PLC0415

    context = multiprocessing.get_context("spawn")
    if arguments.list_rows:
        shipped = collect_worker(
            catalog_worker,
            (),
            label="metta-costs-catalog",
            timeout=arguments.timeout,
            context=context,
            finish_process=finish_process,
        )["rows"]
        for row in declared_rows(shipped):
            plant = "" if row.control is None else f"  [control, expects {row.control.expect}]"
            print(f"{row.head:26s} {row.witness} {row.cost_class} ({row.measure}){plant}")
        return 0
    return run_suite(
        names=list(arguments.names),
        repetitions=arguments.repetitions,
        timeout=arguments.timeout,
        output=arguments.json,
        record=arguments.record,
        paired=arguments.paired,
        measured_on=arguments.measured_on or date.today().isoformat(),
        cause_commit=arguments.cause_commit,
        ledger_path=LEDGER_PATH,
        context=context,
        finish_process=finish_process,
    )


if __name__ == "__main__":
    raise SystemExit(main())
