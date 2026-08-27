"""Purpose: hold each workload family to its declared complexity CLASS.

A change that turns a linear cost quadratic fails here instead of being found
later by a program that got slow.

Nearly every pin in this tree is one number at one input size, which cannot see
a class at all: 32 of the 36 rows in `baseline.json` are single points, so a
regression in the join planner, the matcher, the write door or the parser stays
invisible until it reaches the one size that happens to be pinned. This lane
measures each family across a ladder instead, fits `y = a*x^b` in log-log space,
and gates the exponent against a class the family DECLARES.

`memory_scale` is the exception and already measures across sizes; what it
lacked was the fitted-exponent verdict on top. So the curve arithmetic is not
written twice: `benchmarks.curves` holds it and both lanes call it, which is
what generalising "memory over sizes" into "any counter over sizes" amounts to
in code.

Four things can fail a family, and they are separate on purpose:

  route      a size that did not stay on the route the family names is REFUSED
             rather than fitted, because a fallback silently changes what is
             being measured. A `&mork:` space becomes an ordinary native space
             when the backend artefact is absent, which would compare a MORK
             pin against a native measurement.
  work       the answers the workload produced are checked OUTSIDE the measured
             region. A family whose work quietly went away would otherwise
             report a beautiful flat curve.
  exponent   the fitted exponent against the family's declared maximum. This is
             the class gate.
  growth     every size against the ledger's pinned count. This is the constant
             gate, and it is deliberately looser and independent, so a 3x loss
             that leaves the class alone is still visible.

Assumes: the engine boots, and `benchmarks/scaling-policy.json` declares a class
  and a ladder for every family in `WORKLOADS`.
Guarantees:
  - the verdict is inferences, which are deterministic and load-immune, so a
    busy box cannot make a run pass or fail. Every one of the eight seeded
    families returned the IDENTICAL count at every size across three fresh
    processes, and the same counts came back from a run at loadavg 3.40, a run
    at loadavg 5.97, and a run inside `GATE_ONLY=1 sh check.sh` with the
    machine between 10 and 21
    [measured 2026-08-26; command=python -m benchmarks.scaling --json;
    fixture=the seeded ladders with engine/reader.so and libmork_ffi.so present;
    commit=906a4057ac57a340a3544ad909e829f851f35af3]
  - a family whose declared route was not taken at some size is refused rather
    than fitted [tested: test_a_family_that_left_its_route_is_refused_not_fitted;
    commit=906a4057ac57a340a3544ad909e829f851f35af3]
  - the two planted controls stay armed: a quadratic planted in a family declared
    linear fails the exponent gate, and a 3x constant-factor loss fails the growth
    gate while passing the exponent gate, and the lane fails if either control
    stops failing in its declared way
    [tested: test_the_planted_quadratic_fails_only_the_exponent_gate,
    test_the_planted_constant_factor_fails_only_the_growth_gate; commit=906a4057ac57a340a3544ad909e829f851f35af3]
  - `--record` never rewrites a control family's pinned row, because the constant
    control's plant IS its distance from that row
    [tested: test_recording_leaves_every_control_row_pinned; commit=906a4057ac57a340a3544ad909e829f851f35af3]
  - a ledger recorded under another configuration refuses the whole run before
    any family is measured, rather than reading the configuration's own cost as
    a regression. The C reader alone is worth 10.58x to 10.86x on parse-forms
    [measured 2026-08-27; command=python -m benchmarks.scaling parse-forms under
    PETTA_C_READER=off, recorded into a throwaway ledger; fixture=the parse-forms
    ladder 200/400/800/1600; commit=75d75b1ea5ed229a598925111f8bdc759a3fbb6e]
    [tested: test_a_drifted_ledger_refuses_the_run_before_it_measures_anything;
    commit=75d75b1ea5ed229a598925111f8bdc759a3fbb6e]
Fails when: a family exceeds its declared exponent, costs more than its pinned
  row by more than the allowed factor, leaves its route, or produces the wrong
  work. Also when a control stops failing, and when the ledger's configuration
  stamp does not match the live one.
Owns resources: each repetition is a fresh process that runs one family's whole
  ladder and drops every space it creates; the parent joins, terminates or kills
  it through the lifecycle callback `bench.finish_process` supplies.
Decides: inferences rather than wall time, exponent rather than absolute cost,
  and repetitions taken as separate PROCESSES rather than loops, because retired
  instruction counts move with code layout across program images and a
  cross-process minimum averages that out.

`scripts/check_program_scaling.py` in the metta-on-mork sibling is the same idea
for a native kernel and the policy schema here is modelled on its
`program-scaling-policy.json`. What did NOT port is recorded in the policy's own
note: its counter is `perf stat` retired instructions where this lane's primary
is inferences, its refusal reads one `native_answered` field where a route here
is per family, and its constant guard checks only the largest size where this
one checks every size.

[source: google/benchmark model selection, transcribed in `curves.select_model`,
https://github.com/google/benchmark/blob/eddb0241389718a23a42db6af5f0164b6e0139af/src/complexity.cc#L81-L152;
commit=906a4057ac57a340a3544ad909e829f851f35af3]
[source: trend-prof (Goldsmith, Aiken, Wilkerson, FSE 2007) is why the exponent
is compared against a DECLARED class rather than judged alone; the same linear
cost was a defect at R-squared 0.95 in one program and not a defect at 0.65 in
another; ai-benchmark-prior-art.md:467-479; commit=906a4057ac57a340a3544ad909e829f851f35af3]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from benchmarks import atomic_json, curves
from benchmarks.configuration import counter_configuration
from metta import MeTTa, S, Space, V

# The direct home rather than the `metta.testing` re-export memory_scale uses:
# `benchmarks.pure` imports this module to reach WORKLOADS and runs under perf,
# and `metta.benchmarking` is stdlib plus `.atoms` where `metta.testing` also
# pulls in the codec kit, the library loader, the space and the foreign seam.
from metta.benchmarking import measure_instructions

SCHEMA_VERSION = 1
DEFAULT_REPETITIONS = 3
_BINDING_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = Path(__file__).resolve().parent / "scaling-policy.json"
LEDGER_PATH = Path(__file__).resolve().parent / "scaling-baseline.json"

#: SWI refuses to assert a clause whose functor arity exceeds this, and a flat
#: MeTTa expression's children become exactly that arity, so any family built
#: from one wide row has to stay below it. A ladder reaching 1601 raised
#: `assertz/2: Cannot represent due to 'max_procedure_arity' (limit is 1024,
#: request = 1601)`. Read it back with
#: `swipl -g "current_prolog_flag(max_procedure_arity,X),print(X)" -t halt`
#: [source: SWI-Prolog flag max_procedure_arity; commit=906a4057ac57a340a3544ad909e829f851f35af3]
#: [tested: test_a_flat_expression_family_stays_under_the_procedure_arity_ceiling;
#: commit=906a4057ac57a340a3544ad909e829f851f35af3]
MAX_FLAT_CHILDREN = 1024


@dataclass(frozen=True)
class Workload:
    """One family at one size: what to measure, and how to check it afterwards.

    `operation` is the only part inside the measured region. `route` and `check`
    run outside it, following Renaissance's rule that validation never charges
    itself to the measurement.
    """

    space: Space
    operation: Callable[[], int]
    check: Callable[[int], str | None]
    route: Callable[[], str] | None = None


@dataclass(frozen=True)
class Failure:
    """One reason a family did not pass, tagged so a control can assert on it."""

    kind: str
    message: str


# ------------------------------------------------------------------ workloads


def _atoms(prefix: str, size: int) -> list[Any]:
    return [S[prefix](index) for index in range(size)]


def _expect(condition: bool, message: str) -> str | None:  # noqa: FBT001  -- the caller writes the comparison, this only names it
    return None if condition else message


def _reader_route(space: Space) -> Callable[[], str]:
    """Which reader answered: the C extension, or the Prolog grammar behind it.

    `parser:metta_c_reader_active/0` is asserted only when `engine/reader.so`
    loaded AND `PETTA_C_READER` is not `off` AND the foreign arity matched, so
    it is the fact rather than the intention. `metta_reader_mode/1` is NOT this
    question: its two answers are `custom` and `shipped`, and they distinguish
    custom reader TOKENS, so it says `shipped` with no C reader present at all
    [source: engine/parser.pl:131-147 metta_try_load_c_reader/0, and
    engine/parser.pl:190-191 metta_reader_mode/1; commit=906a4057ac57a340a3544ad909e829f851f35af3].
    """
    return lambda: str(
        space.runtime.once(
            "( parser:metta_c_reader_active -> Route = c ; Route = prolog )"
        )["Route"]
    )


def _storage_route(space: Space) -> Callable[[], str]:
    """Whether this space is backed by a foreign store or the engine's own.

    `seam:foreign_space/1` is the seam the engine consults before its own
    storage, and the MORK backend adds the only clause for it. Without the
    backend artefact a `&mork:` name silently becomes an ordinary native space,
    which is the fallback this refusal exists to catch.
    """
    return lambda: str(
        space.runtime.once(
            "( seam:foreign_space(Space) -> Route = foreign ; Route = native )",
            Space=space.name,
        )["Route"]
    )


def write_door(size: int, *, passes: int = 1) -> Workload:
    """`size` separate writes into one space, the shape `add-single` pins at a point."""
    space = MeTTa().space()
    atoms = _atoms("scaling-row", size)

    def operation() -> int:
        done = 0
        for _ in range(passes):
            for atom in atoms:
                space.add(atom)
                done += 1
        return done

    # A space keeps multiplicity, so writing the same atom `passes` times stores
    # it `passes` times. That is the law rather than an accident, and checking
    # for it is what makes the three-pass control's work verifiable.
    return Workload(
        space,
        operation,
        lambda done: _expect(
            done == size * passes and len(space) == size * passes,
            f"expected {size * passes} stored atoms from {size * passes} writes, "
            f"got {len(space)} from {done}",
        ),
    )


def scan_per_write(size: int) -> Workload:
    """PLANTED CONTROL. The write door with a full scan of the space per write.

    A cost paid once per step that grows with everything written so far is the
    exact shape of the two quadratics the sibling project found inside a lane
    whose own assertions were on charged steps. Declared linear in the policy,
    so the exponent gate has to catch it.
    """
    space = MeTTa().space()
    atoms = _atoms("scaling-scan", size)
    pattern = S["scaling-scan"](V.any)

    def operation() -> int:
        seen = 0
        for atom in atoms:
            space.add(atom)
            seen += len(list(space.match(pattern)))
        return seen

    return Workload(
        space,
        operation,
        lambda seen: _expect(
            seen == size * (size + 1) // 2,
            f"expected {size * (size + 1) // 2} rows scanned, got {seen}",
        ),
    )


def parse_forms(size: int) -> Workload:
    """The reader over one program text holding `size` forms.

    A CHILD space, never `MeTTa().self`. Every caller drops `Workload.space`
    when it is done, and dropping the ROOT tears down the execution module the
    engine's own compiled machinery lives in. That is invisible in this lane,
    where each measurement is a throwaway process, and destructive in pytest,
    where the file shares its process with every other file the loadfile
    scheduler put on that worker: it made 14 tests in five unrelated files fail
    after this one ran, and none of them fail without it. The `&self` check
    itself lives in `selfcheck`, which that test drives as a subprocess
    [tested: test_the_families_keep_their_engine_invariants_in_their_own_process;
    commit=cbabce0e0871a2d5bbf53b8c0e520b50aeb1a984].
    """
    space = MeTTa().space()
    text = " ".join(f"(scaling-form {index} (nested {index}))" for index in range(size))
    parsed: list[Any] = []

    def operation() -> int:
        parsed.append(space.parse(f"(scaling-wrapper {text})"))
        return size

    return Workload(
        space,
        operation,
        lambda _done: _expect(
            bool(parsed) and len(parsed[0].children) == size + 1,
            f"expected {size} parsed forms under the wrapper, "
            f"got {len(parsed[0].children) - 1 if parsed else 'nothing'}",
        ),
        _reader_route(space),
    )


def chain_join(size: int) -> Workload:
    """A conjunctive match with a shared variable over a path of `size` edges.

    The join the engine's own note calls a nested-loop join. A path graph keeps
    the ANSWER count linear, so the class is the finding rather than the output
    size: an unindexed join is quadratic here and an indexed one is linear.
    """
    space = MeTTa().space()
    space.add(*(S["scaling-edge"](index, index + 1) for index in range(size)))
    rows: list[Any] = []

    def operation() -> int:
        rows.extend(space.match(S["scaling-edge"](V.a, V.b), S["scaling-edge"](V.b, V.c)))
        return len(rows)

    return Workload(
        space,
        operation,
        lambda found: _expect(
            found == size - 1, f"expected {size - 1} chained pairs, got {found}"
        ),
    )


def selective_query(size: int) -> Workload:
    """One selective query against a space holding `size` facts.

    Declared CONSTANT. This is the family that says whether the matcher still
    reaches its index: the moment a lookup starts scanning, this becomes linear
    and the exponent gate says so, while a point pin at one size would only see
    a bigger number and call it a constant-factor regression.
    """
    space = MeTTa().space()
    space.add(*(S["scaling-fact"](index, S.payload) for index in range(size)))
    rows: list[Any] = []

    def operation() -> int:
        rows.extend(space.match(S["scaling-fact"](0, V.value)))
        return len(rows)

    return Workload(
        space,
        operation,
        lambda found: _expect(found == 1, f"expected one selective answer, got {found}"),
    )


def segment_split(size: int) -> Workload:
    """A sequence-variable pattern splitting a row of `size` children.

    Sequence variables have no performance measurement anywhere in the tree,
    and two gaps around a separator is the shape a backtracking matcher pays
    quadratically for, so this is where one would hide.
    """
    space = MeTTa().space()
    space.add(S["scaling-split"](*(S[f"e{index}"] for index in range(size)), S.SEP))
    pattern = space.parse("(scaling-split (:seg $pre) SEP (:seg $post))")
    rows: list[Any] = []

    def operation() -> int:
        rows.extend(space.match(pattern))
        return len(rows)

    return Workload(
        space,
        operation,
        lambda found: _expect(found == 1, f"expected one split, got {found}"),
    )


def mork_write(size: int) -> Workload:
    """`size` writes into a MORK-backed space, refused if the backend is absent."""
    space = MeTTa().space("&mork:scaling-write")
    atoms = _atoms("scaling-mork-row", size)

    def operation() -> int:
        for atom in atoms:
            space.add(atom)
        return size

    return Workload(
        space,
        operation,
        lambda done: _expect(
            done == size and len(space) == size,
            f"expected {size} stored atoms, got {len(space)} from {done} writes",
        ),
        _storage_route(space),
    )


WORKLOADS: dict[str, Callable[[int], Workload]] = {
    "write-door": write_door,
    "parse-forms": parse_forms,
    "chain-join": chain_join,
    "selective-query": selective_query,
    "segment-split": segment_split,
    "mork-write": mork_write,
    "planted-quadratic": scan_per_write,
    "planted-constant-factor": lambda size: write_door(size, passes=3),
}


# ----------------------------------------------------------------- measurement


def sample_worker(family: str, sizes: Sequence[int], connection: Any) -> None:
    """Run one family's whole ladder in this process and send the samples back."""
    try:
        samples = []
        for size in sizes:
            workload = WORKLOADS[family](size)
            try:
                with workload.space.stats() as stats:
                    completed = workload.operation()
                samples.append(
                    {
                        "size": size,
                        "inferences": int(stats.inferences),
                        "work": int(completed),
                        "route": None if workload.route is None else workload.route(),
                        "problem": workload.check(completed),
                    }
                )
            finally:
                workload.space.drop()
        connection.send({"ok": True, "samples": samples, "pid": os.getpid()})
    except BaseException as exc:  # noqa: BLE001  -- a worker failure crosses the process boundary as evidence
        connection.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        connection.close()


@dataclass(frozen=True)
class Measurement:
    """Every repetition of one family, reduced to the values a verdict reads."""

    sizes: tuple[int, ...]
    samples: tuple[tuple[int, ...], ...]
    representative: tuple[int, ...]
    work: tuple[int, ...]
    routes: tuple[str | None, ...]
    problems: tuple[str, ...]

    @property
    def noise(self) -> dict[str, float]:
        """The widest span any size showed across its repetitions."""
        spans = [max(row) - min(row) for row in self.samples]
        return {
            "absolute_max": max(spans),
            "relative_max": max(
                span / max(abs(min(row)), 1)
                for span, row in zip(spans, self.samples, strict=True)
            ),
        }


def _agreed_route(observed: Sequence[str | None]) -> str | None:
    """One route for a size, or a compound name no declaration can match.

    A backend that loaded in some processes and not others would otherwise make
    the verdict depend on which repetition happened to be read. Joining the
    distinct names means the disagreement refuses and names both sides.
    """
    distinct = sorted({route for route in observed if route is not None})
    if not distinct:
        return None
    return distinct[0] if len(distinct) == 1 else "|".join(distinct)


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
        work=tuple(int(sample["work"]) for sample in first),
        routes=tuple(
            _agreed_route([repetition[index]["route"] for repetition in repetitions])
            for index in range(len(sizes))
        ),
        # Deduplicated, because a check that fails at every size in every
        # repetition would otherwise print the same finding once per process
        # and bury the rest of the verdict.
        problems=tuple(
            dict.fromkeys(
                f"size {sample['size']}: {sample['problem']}"
                for repetition in repetitions
                for sample in repetition
                if sample["problem"] is not None
            )
        ),
    )


# --------------------------------------------------------------------- verdict


@dataclass
class FamilyResult:
    """One family's measurement, its fit, and every reason it did not pass."""

    name: str
    measurement: Measurement
    fit: dict[str, Any]
    failures: list[Failure] = field(default_factory=list)

    @property
    def kinds(self) -> set[str]:
        """The distinct gate names this family failed."""
        return {failure.kind for failure in self.failures}


def _fit_report(measurement: Measurement) -> dict[str, Any]:
    power = curves.power_fit(measurement.sizes, measurement.representative)
    best, models = curves.select_model(measurement.sizes, measurement.representative)
    return {
        "exponent": power.exponent,
        "r_squared": power.r_squared,
        "coefficient": power.coefficient,
        "pair_slopes": [round(value, 4) for value in power.pair_slopes],
        "best_model": best,
        "normalised_rms": {name: round(value, 6) for name, value in models.items()},
    }


def evaluate(
    family: Mapping[str, Any],
    measurement: Measurement,
    pinned: Mapping[str, Any] | None,
) -> FamilyResult:
    """Fit one family and collect every failure, each tagged with its kind.

    Route and work are checked BEFORE the fit and stop it: a family that left
    its route is refused rather than fitted, because the points then describe a
    route nobody declared.
    """
    name = str(family["name"])
    failures: list[Failure] = []
    expected_route = family.get("route")
    if expected_route is not None:
        failures.extend(
            Failure(
                "route",
                f"{name} at size {size} took route {route!r}, "
                f"not the declared {expected_route!r}",
            )
            for size, route in zip(measurement.sizes, measurement.routes, strict=True)
            if route != expected_route
        )
    # Unconditional, and the part that answers the literal requirement: a family
    # whose points fell back to another route AT SOME SIZE is refused rather
    # than fitted, whether or not it declared which route it wanted. A ladder
    # measured half on one route and half on another describes neither.
    observed = {route for route in measurement.routes if route is not None}
    if len(observed) > 1:
        failures.append(
            Failure(
                "route",
                f"{name} did not stay on one route across its ladder: "
                f"{dict(zip(measurement.sizes, measurement.routes, strict=True))}",
            )
        )
    failures.extend(Failure("work", f"{name} {problem}") for problem in measurement.problems)
    # A family the primary counter cannot see has no class to fit, and log-log
    # space has no meaning for it. Say that rather than raising out of the fit:
    # the work check catches every family whose work went away, so reaching here
    # means the work happened somewhere the inference counter does not look.
    if sum(1 for count in measurement.representative if count > 0) < 2:
        failures.append(
            Failure(
                "work",
                f"{name} recorded {list(measurement.representative)} inferences, "
                f"which is too few positive points to fit; a family whose work "
                f"the primary counter cannot see needs a counter that can",
            )
        )
    if failures:
        return FamilyResult(name, measurement, {"refused": True}, failures)

    fit = _fit_report(measurement)
    if fit["exponent"] > family["maximum_exponent"]:
        failures.append(
            Failure(
                "exponent",
                f"{name} grows as size^{fit['exponent']:.3f}, above the "
                f"{family['expected_class']} bound of {family['maximum_exponent']}",
            )
        )
    if pinned is not None:
        failures.extend(_growth_failures(name, family, measurement, pinned, fit))
    return FamilyResult(name, measurement, fit, failures)


def _growth_failures(
    name: str,
    family: Mapping[str, Any],
    measurement: Measurement,
    pinned: Mapping[str, Any],
    fit: dict[str, Any],
) -> list[Failure]:
    """Compare every size against its pinned count, not only the largest.

    A curve that bends in the middle of its ladder passes a last-size check,
    which is the weakness the coverage survey records against the memory-scale
    gate and the one place this lane deliberately goes beyond the sibling
    project's, whose guard reads `counts[-1]` alone.
    """
    if list(pinned["sizes"]) != list(measurement.sizes):
        return [
            Failure(
                "growth",
                f"{name} sizes changed from {pinned['sizes']} to "
                f"{list(measurement.sizes)}; the pinned row no longer applies",
            )
        ]
    recorded = [int(value) for value in pinned["representative"]]
    ratios = [
        current / max(previous, 1)
        for current, previous in zip(measurement.representative, recorded, strict=True)
    ]
    fit["growth"] = [round(value, 4) for value in ratios]
    worst = max(ratios)
    if worst <= family["maximum_growth"]:
        return []
    index = ratios.index(worst)
    return [
        Failure(
            "growth",
            f"{name} costs {worst:.3f}x its pinned row at size "
            f"{measurement.sizes[index]} "
            f"({recorded[index]} -> {measurement.representative[index]}), "
            f"above its bound of {family['maximum_growth']}",
        )
    ]


def control_verdict(family: Mapping[str, Any], result: FamilyResult) -> list[str]:
    """Check a planted control still fails, and still fails in its declared way.

    A negative control that quietly starts passing is worse than no control, so
    this is the only place where NOT failing is itself a failure. Renaissance
    ships `dummy-validation-failing` for the same reason; asserting the KIND as
    well is what proves the exponent gate and the constant guard are
    independent rather than one gate wearing two names.
    """
    control = family.get("control")
    if control is None:
        return []
    declared = str(control["fails"])
    observed = result.kinds
    if observed == {declared}:
        return []
    if not observed:
        return [
            f"control {result.name} passed every gate; it is planted to fail the "
            f"{declared} gate and is no longer proving that gate can fail"
        ]
    return [
        f"control {result.name} failed {sorted(observed)}, but it is planted to "
        f"fail exactly the {declared} gate"
    ]


# --------------------------------------------------------- configuration stamp


def stamp_worker(connection: Any) -> None:
    """Report the configuration this run measured, so no number is unstamped.

    It starts from `benchmarks.configuration.counter_configuration`, the same
    fingerprint `baseline.json` and the extension-cost gate stamp, so the shared
    facts are spelled once. It adds `mork_backend`, which that fingerprint does
    not carry: the coverage survey records that the MORK backend's presence is
    in no configuration stamp, and that with it absent a `&mork:` name silently
    becomes a native space, so two gated curves can compare MORK pins against
    native measurements. That one is observed LIVE rather than from the
    filesystem, because the hazard is the fallback, not the missing file.
    """
    try:
        engine = MeTTa()
        probe = engine.space("&mork:scaling-stamp")
        try:
            connection.send(
                {
                    "ok": True,
                    "stamp": dict(counter_configuration())
                    | {
                        "mork_backend": str(_storage_route(probe)()),
                        "swipl_version": str(
                            engine.self.runtime.once(
                                "current_prolog_flag(version_data, swi(Major,Minor,Patch,_)),"
                                " format(atom(Version), '~w.~w.~w', [Major,Minor,Patch])"
                            )["Version"]
                        ),
                        "python_version": sys.version.split()[0],
                    },
                }
            )
        finally:
            probe.drop()
    except BaseException as exc:  # noqa: BLE001  -- a stamp failure crosses the process boundary as evidence
        connection.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        connection.close()


def configuration_drift(
    live: Mapping[str, Any], previous: Mapping[str, Any]
) -> list[str]:
    """Name every configuration fact that moved since the ledger was recorded.

    Deterministic counters only compare within one configuration. Measured on
    this lane's own parse-forms ladder, the C reader's presence alone is worth
    10.58 to 10.86 times: [55248, 111250, 223254, 452062] on the Prolog reader
    against [5222, 10422, 20822, 41624] on the C one. Both fit the same class,
    so the exponent gate is unharmed either way, but the growth guard would fire
    at 10x against a 1.1 bound and name a parser regression where only the box
    differed. The tree already refuses a drifted comparison in
    `BenchmarkBaseline.observe_configuration` and this is the same rule for this
    ledger, with the same two remedies.
    """
    pinned = previous.get("configuration")
    if pinned is None:
        return []
    return [
        f"{key}: pinned under {pinned.get(key)!r}, measuring under {live.get(key)!r}"
        for key in sorted(set(pinned) | set(live))
        if pinned.get(key) != live.get(key)
    ]


# ------------------------------------------------------- the paired instruction
# lane. LAW 2: a family whose work crosses into C or Rust cannot be judged on
# inferences alone, because foreign code retires none of them. This measures the
# same ladder under `perf stat -e instructions:u` and reports its exponent
# beside the inference one. It never gates: the workstation this runs on is
# shared, and a retired-instruction count taken beside other load is advisory by
# construction.


def paired_instructions(
    family: str, sizes: Sequence[int], *, rounds: int, timeout: float
) -> dict[str, Any]:
    """Retired instructions across the same ladder, reported and never gated."""
    representative = []
    for size in sizes:
        samples = measure_instructions(
            [
                "/usr/bin/env",
                "-C",
                str(_BINDING_ROOT),
                sys.executable,
                "-m",
                "benchmarks.pure",
                f"scaling-{family}",
                "--size",
                str(size),
                "--controlled",
            ],
            rounds=rounds,
            controlled=True,
            timeout=timeout,
        )
        representative.append(min(samples))
    power = curves.power_fit(sizes, representative)
    return {
        "counter": "instructions:u",
        "advisory": True,
        "representative": representative,
        "exponent": power.exponent,
        "r_squared": power.r_squared,
        "pair_slopes": [round(value, 4) for value in power.pair_slopes],
    }


# -------------------------------------------------------------- the self-check
# The engine-level invariants of the families themselves, which a Python test
# cannot check in its own process without paying for an engine there. That price
# is not theoretical: booting one inside pytest to run these three checks made a
# combination of four test files segfault 3 times in 20 against 0 in 20 both
# without this file and with an inert file of the same wall time, always inside
# janus's finalizer on another test's worker thread. Running them HERE, in a
# process that is measuring the engine anyway, keeps the test file engine-free
# and the invariants checked.


def selfcheck() -> list[str]:
    """Every engine-level invariant of the seeded families, as a findings list."""
    findings: list[str] = []
    for name, build in WORKLOADS.items():
        workload = build(4)
        try:
            if str(workload.space.name) == "&self":
                findings.append(
                    f"{name} hands back the engine root, which its caller drops"
                )
            if workload.route is not None:
                observed = workload.route()
                if observed not in {"c", "prolog", "foreign", "native"}:
                    findings.append(f"{name} reported an unknown route {observed!r}")
        finally:
            workload.space.drop()

    reader = "c" if (_BINDING_ROOT.parents[1] / "engine" / "reader.so").exists() else "prolog"
    for name, expected in (("parse-forms", reader), ("mork-write", "foreign")):
        workload = WORKLOADS[name](4)
        try:
            assert workload.route is not None
            observed = workload.route()
            if observed != expected:
                findings.append(
                    f"{name} took route {observed!r} where this tree's "
                    f"configuration means {expected!r}"
                )
        finally:
            workload.space.drop()

    # The plants are in the WORKLOADS, not only in the recorded numbers, so a
    # control cannot rot into a passing family while its pinned row keeps the
    # verdict tests green.
    for family, expected in (("planted-quadratic", "quadratic"), ("write-door", "linear")):
        sizes, counts = (40, 80, 160), []
        for size in sizes:
            workload = WORKLOADS[family](size)
            try:
                with workload.space.stats() as stats:
                    completed = workload.operation()
                problem = workload.check(completed)
                if problem is not None:
                    findings.append(f"{family} at size {size}: {problem}")
                counts.append(int(stats.inferences))
            finally:
                workload.space.drop()
        best, _ = curves.select_model(sizes, counts)
        if best != expected:
            findings.append(
                f"{family} measures {best} over {list(sizes)}, expected {expected}"
            )
    return findings


# ------------------------------------------------------------------- the suite


def _collect(
    target: Callable[..., None],
    arguments: tuple[Any, ...],
    *,
    label: str,
    timeout: float,
    context: Any,
    finish_process: Callable[[Any, float], str | None],
) -> Mapping[str, Any]:
    """Run one worker to completion and return its payload, or raise its failure."""
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=target, args=(*arguments, child), name=label)
    process.start()
    child.close()
    failure = finish_process(process, timeout)
    payload: Mapping[str, Any] | None = None
    if failure is None and parent.poll():
        payload = parent.recv()
    parent.close()
    if failure is None and payload is None:
        failure = "worker exited without a measurement"
    if failure is None and payload is not None and not payload["ok"]:
        failure = str(payload["error"])
    if failure is not None:
        message = f"{label}: {failure}"
        raise RuntimeError(message)
    assert payload is not None
    return payload


def _planted_row(
    name: str,
    control: Mapping[str, Any],
    families: Mapping[str, Any],
    cause_commit: str,
) -> dict[str, Any]:
    """Pin a constant-factor control against ANOTHER family's row, never its own.

    The plant IS the distance between the control's measurement and this row, so
    recording the control's own cost here would replace the plant with itself and
    the lane would go green having proved nothing. Deriving the row from the
    named source instead keeps the plant reproducible: `--record` rebuilds it and
    nobody has to remember to hand-edit the ledger.
    """
    source_name = str(control["pinned_from"])
    source = families.get(source_name)
    if source is None:
        msg = (
            f"control {name} is pinned from {source_name}, which has no row yet; "
            f"record {source_name} in the same run or before this one"
        )
        raise KeyError(msg)
    return dict(source) | {
        "cause": {
            "commit": cause_commit,
            "chain": [
                f"THE PLANT. This row is {source_name}'s own measurement, for the "
                f"UNMULTIPLIED workload that {name} runs a fixed number of times.",
                "The distance between this row and the control's measurement is "
                "the planted constant-factor loss, so it is copied rather than "
                "measured and never reflects the control's own cost.",
                "The class is untouched, so the control passes the exponent gate "
                "and fails only the growth gate.",
            ],
        }
    }


def ledger_document(
    results: Mapping[str, FamilyResult],
    policy: Mapping[str, Any],
    previous: Mapping[str, Any],
    *,
    stamp: Mapping[str, Any],
    repetitions: int,
    cause_commit: str,
) -> dict[str, Any]:
    """Pin every measured family, keeping each control's row exactly as it was.

    A control row is never rewritten. The constant-factor control is planted by
    running three passes of a workload pinned at one pass, so re-recording it
    would quietly replace the plant with its own inflated cost and the lane
    would go green having proved nothing.
    """
    declared = {str(family["name"]): family for family in policy["families"]}
    families = dict(previous.get("families", {}))
    for name, result in results.items():
        control = declared[name].get("control")
        if control is None:
            families[name] = {
                "expected_class": declared[name]["expected_class"],
                "counter": "inferences",
                "sizes": list(result.measurement.sizes),
                "representative": list(result.measurement.representative),
                "work": list(result.measurement.work),
                "noise": result.measurement.noise,
                "fit": result.fit,
                "cause": {
                    "commit": cause_commit,
                    "chain": [
                        f"python -m benchmarks.scaling --record measured {name}",
                        f"minimum of {repetitions} fresh processes per size",
                        f"the declared class is {declared[name]['expected_class']}",
                    ],
                },
            }
        elif "pinned_from" in control:
            families[name] = _planted_row(name, control, families, cause_commit)
    return {
        "schema": SCHEMA_VERSION,
        "repetitions": repetitions,
        "configuration": dict(stamp),
        "families": families,
        "repin_rule": (
            "A changed pin must name the first causal code or dependency change, "
            "carry the old and new counts, and explain why the family still holds "
            "its declared class. A control row is never re-pinned: the planted "
            "constant-factor loss IS the distance between its measurement and the "
            "row below it."
        ),
    }


#: A curve whose largest value is within half again of its smallest has almost
#: no variation for a fit to explain, so its R-squared reports rounding rather
#: than shape and must not be read as a bad fit. selective-query spans 100 to 97
#: and reads 0.6000; every other seeded family spans about eightfold and reads
#: above 0.999.
_FLAT_RANGE_RATIO = 1.5


def _print_family(family: Mapping[str, Any], result: FamilyResult) -> None:
    fit = result.fit
    if fit.get("refused"):
        print(f"{result.name:26s} REFUSED, not fitted")
        return
    r_squared = fit["r_squared"]
    counts = result.measurement.representative
    if r_squared is None:
        quality = "n/a (no variation)"
    elif max(counts) / max(min(counts), 1) < _FLAT_RANGE_RATIO:
        quality = f"{r_squared:.4f} (flat curve, uninformative)"
    else:
        quality = f"{r_squared:.4f}"
    print(
        f"{result.name:26s} {list(result.measurement.representative)}\n"
        f"{'':26s} exponent={fit['exponent']:.3f} r2={quality} "
        f"bound={family['maximum_exponent']} ({family['expected_class']})\n"
        f"{'':26s} pairs={fit['pair_slopes']} best_model={fit['best_model']}"
    )
    if "growth" in fit:
        print(f"{'':26s} growth vs pinned={fit['growth']} bound={family['maximum_growth']}")


def run_suite(
    *,
    names: Sequence[str],
    repetitions: int,
    timeout: float,
    output: Path | None,
    record: bool,
    paired: bool,
    cause_commit: str,
    policy_path: Path,
    ledger_path: Path,
    context: Any,
    finish_process: Callable[[Any, float], str | None],
) -> int:
    """Measure every selected family, fit it, and report the verdict."""
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    previous = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {}
    pinned = previous.get("families", {})
    selected = [
        family for family in policy["families"] if not names or family["name"] in names
    ]
    stamp = _collect(
        stamp_worker,
        (),
        label="petta-scaling-stamp",
        timeout=timeout,
        context=context,
        finish_process=finish_process,
    )["stamp"]
    print(
        "configuration: "
        + ", ".join(f"{key}={value}" for key, value in sorted(stamp.items()))
    )
    # Recording is the stated remedy, so it must not be blocked by the thing it
    # remedies: a --record run measures under the live configuration and stamps
    # it, which is exactly what a drifted ledger needs.
    drift = [] if record else configuration_drift(stamp, previous)
    if drift:
        for moved in drift:
            print(f"CONFIGURATION DRIFT {moved}")
        print(
            "the pinned rows were measured under a different configuration, so no "
            "growth comparison here would mean anything; restore the pinned "
            "configuration (build the artifact or unset the mode override) or "
            "re-pin with --record"
        )
        return 1

    results: dict[str, FamilyResult] = {}
    document_families: dict[str, Any] = {}
    failures: list[str] = []
    for family in selected:
        name = str(family["name"])
        sizes = [int(size) for size in family["sizes"]]
        repeated = [
            _collect(
                sample_worker,
                (name, sizes),
                label=f"petta-scaling-{name}-{index}",
                timeout=timeout,
                context=context,
                finish_process=finish_process,
            )["samples"]
            for index in range(repetitions)
        ]
        measurement = reduce_repetitions(sizes, repeated)
        result = evaluate(family, measurement, pinned.get(name))
        results[name] = result
        _print_family(family, result)

        control_problems = control_verdict(family, result)
        for problem in control_problems:
            print(f"CONTROL BROKEN {problem}")
        failures.extend(control_problems)
        if family.get("control") is None:
            for failure in result.failures:
                print(f"REGRESSED {failure.message}")
                failures.append(failure.message)
        else:
            for failure in result.failures:
                print(f"{'':26s} control fired as planted: {failure.message}")

        entry: dict[str, Any] = {
            "sizes": list(measurement.sizes),
            "samples": [list(column) for column in measurement.samples],
            "representative": list(measurement.representative),
            "work": list(measurement.work),
            "routes": list(measurement.routes),
            "noise": measurement.noise,
            "fit": result.fit,
            "expected_class": family["expected_class"],
            "control": family.get("control"),
            "failures": [
                {"kind": item.kind, "message": item.message} for item in result.failures
            ],
        }
        if paired and family.get("paired_counter"):
            try:
                entry["paired"] = paired_instructions(
                    name, sizes, rounds=max(repetitions, 3), timeout=timeout
                )
                print(
                    f"{'':26s} paired instructions:u exponent="
                    f"{entry['paired']['exponent']:.3f} (advisory, shared box)"
                )
            except (FileNotFoundError, RuntimeError, TimeoutError, ValueError) as error:
                entry["paired"] = {"error": str(error)}
                print(f"{'':26s} paired instructions unavailable: {error}")
        document_families[name] = entry

    document = {
        "schema": SCHEMA_VERSION,
        "repetitions": repetitions,
        "configuration": stamp,
        "loadavg": Path("/proc/loadavg").read_text(encoding="ascii").strip(),
        "families": document_families,
        "failures": failures,
    }
    if output is not None:
        atomic_json(output, document)
        print(f"wrote scaling data to {output}")
    if record:
        atomic_json(
            ledger_path,
            ledger_document(
                results,
                policy,
                previous,
                stamp=stamp,
                repetitions=repetitions,
                cause_commit=cause_commit,
            ),
        )
        print(f"recorded {ledger_path}")
    if failures:
        return 1
    print("every family stayed inside its declared complexity class")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scaling gate over the selected families."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*")
    parser.add_argument("--list", action="store_true", dest="list_families")
    parser.add_argument(
        "--selfcheck",
        action="store_true",
        help="check the families' own engine-level invariants and exit",
    )
    parser.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS)
    parser.add_argument("--timeout", type=float, default=200.0)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--record", action="store_true", help="rewrite the ledger")
    parser.add_argument(
        "--paired",
        action="store_true",
        help="also measure retired instructions for families that declare it",
    )
    parser.add_argument(
        "--cause-commit", default=os.environ.get("PETTA_SCALING_CAUSE_COMMIT", "WORKTREE")
    )
    arguments = parser.parse_args(argv)
    if arguments.list_families:
        print("\n".join(sorted(WORKLOADS)))
        return 0
    if arguments.selfcheck:
        findings = selfcheck()
        for finding in findings:
            print(f"SELFCHECK {finding}")
        if findings:
            return 1
        print("every family keeps its engine-level invariants")
        return 0
    if arguments.repetitions < 1:
        parser.error("--repetitions must be positive")
    if arguments.timeout <= 0:
        parser.error("--timeout must be positive")
    unknown = sorted(set(arguments.names) - WORKLOADS.keys())
    if unknown:
        parser.error(f"unknown family {', '.join(unknown)}; use --list for valid names")
    # Deferred: benchmarks.pure imports this module to reach WORKLOADS, and a
    # top-level import here would pull bench.py and pytest into the import graph
    # of the process perf measures.
    from bench import finish_process  # noqa: PLC0415

    return run_suite(
        names=list(arguments.names),
        repetitions=arguments.repetitions,
        timeout=arguments.timeout,
        output=arguments.json,
        record=arguments.record,
        paired=arguments.paired,
        cause_commit=arguments.cause_commit,
        policy_path=POLICY_PATH,
        ledger_path=LEDGER_PATH,
        context=multiprocessing.get_context("spawn"),
        finish_process=finish_process,
    )


if __name__ == "__main__":
    raise SystemExit(main())
