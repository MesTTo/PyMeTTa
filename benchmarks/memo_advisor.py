"""Purpose: propose `(cache Name Policy)` rows and price them, never writing one.

The rows come from a workload's own call counts and each is priced by
re-running the workload in a fresh process with the row declared.

The shape is PostgreSQL's index advisors, not its planner: `pg_qualstats`
proposes from how often a predicate was actually asked, HypoPG prices the
proposal against the planner without creating anything, and Dexter closes the
loop from logs [source: https://github.com/HypoPG/hypopg;
https://github.com/ankane/dexter]. Souffle derives the same kind of policy from
the program's own searches [source: Subotic, Jordan, Chang, Fekete and Scholz,
"Automatic Index Selection for Large-Scale Datalog Computation", PVLDB 12(2),
2018, http://www.vldb.org/pvldb/vol12/p141-subotic.pdf]. PROPOSE, MEASURE THE
WHAT-IF, NEVER APPLY: a row this prints is a row a developer writes.

Assumes:
  - `metta` imports and boots an engine in every spawned process. The workload
    files are read from the repository, not from a fixture built here.
  - `multiprocessing` uses the spawn context, so a measured process shares no
    engine, memo table or catalog row with this one. Table and memo state
    SURVIVE inside a process, which is why every configuration gets its own
    [source: extensions/python/benchmarks/scaling.py, _collect].
Guarantees:
  - no `(cache ...)` row is ever applied; a run that PROPOSES a winning row
    leaves every byte of its workload untouched, and the rows it writes go into
    the report and into `--json`
    [tested: test_the_advisor_writes_no_row; commit=3287d4dd4928f09ce7c111d05a1c516808e226d5].
  - a workload that ran zero calls of any head is REFUSED by name rather than
    reported as having nothing to propose
    [tested: test_a_workload_with_no_calls_is_refused; commit=3287d4dd4928f09ce7c111d05a1c516808e226d5].
  - every proposal carries the inference count before and after, measured in
    two fresh processes over the same files
    [tested: test_a_reused_pure_head_is_proposed_with_a_measured_gain;
    commit=3287d4dd4928f09ce7c111d05a1c516808e226d5].
Fails when: the workload's files cannot be run at all. A file that RAISES is
  reported beside the proposals and its inferences still count, because the
  same failure happens identically in the baseline and in every what-if.
Owns resources: one spawned process per configuration, joined and reaped
  through bench.finish_process on every path.
Decides: a head called once is never proposed, because a memo cannot reuse a
  single call; `--candidates` bounds the rest by ranking, so the number of
  what-if runs is the operator's and the floor is not a tuning knob.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

BINDING_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BINDING_ROOT.parents[1]

#: The named workloads. `bench` is the repository's own larger MeTTa programs
#: and the memoisation chapter beside them, which is where a cache decision is
#: worth anything; `examples` is the whole executable corpus.
#: The named workloads. `bench` is the repository's own memoisation and tabling
#: chapter, which is where a cache decision is the subject rather than a detail,
#: and it is the default because every configuration runs the WHOLE workload:
#: the larger-workloads chapter beside it costs 21 s in one file alone, and
#: nine configurations of that is not a lane. `examples` is the whole
#: executable corpus, for a developer with the time.
WORKLOADS: dict[str, tuple[str, ...]] = {
    "bench": ("examples/ch18-performance/18-02-memoisation-and-tabling",),
    "examples": ("examples",),
}

#: A head called once cannot be reused, so no cache can save anything on it.
#: This is the only floor: `--candidates` bounds how many of the rest are
#: measured, by rank, and the measurement decides which of those wins.
MIN_CALLS = 2

#: The effect classes that keep a head off the force list. The engine's own
#: automatic-cache test is `\+ metta_function_volatility(Name, volatile)`
#: [source: engine/metta/interop.pl, metta_function_cacheable/1]; this is its
#: observable form over the effect row explain answers.
WRITING_EFFECTS = frozenset({"writesState", "oracleIO"})

#: How long one configuration may run before it is reaped. It is an ORPHAN
#: REAPER and not a deadline, so it scales with the work: a configuration runs
#: every file twice and one file of `examples` can be a twenty-second workload
#: on its own, which a flat 900 s reaped mid-run with nothing to show for it.
WORKER_TIMEOUT_BASE = 300.0
WORKER_SECONDS_PER_FILE = 60.0


def worker_timeout(paths: Sequence[str]) -> float:
    """The reaping bound for one configuration over these files."""
    return WORKER_TIMEOUT_BASE + WORKER_SECONDS_PER_FILE * len(paths)


@dataclass(frozen=True, slots=True)
class HeadRow:
    """One compiled head, as the baseline profile and the catalog describe it."""

    name: str
    arity: int
    entry_calls: int
    recursive_calls: int
    redos: int
    policy: str
    reason: str
    effect: str
    files: tuple[str, ...]

    @property
    def total_calls(self) -> int:
        """Every call of the head, its own recursion included."""
        return self.entry_calls + self.recursive_calls


@dataclass(frozen=True, slots=True)
class Proposal:
    """One `(cache Name Policy)` row and what running the workload under it cost."""

    row: str
    head: str
    policy: str
    files: tuple[str, ...]
    inferences_before: int
    inferences_after: int
    delta: int
    total_calls: int
    distinct_calls: int
    hit_ratio: float | None

    @property
    def wins(self) -> bool:
        """Whether the measured run under this row cost fewer inferences."""
        return self.delta > 0


# ------------------------------------------------------------------ the worker
# One configuration, in a process of its own. It runs each file TWICE: once
# under stats() for a clean inference count, and once under the profiler for
# the per-head counts. They cannot be one run, because profiling retires
# inferences of its own: the same workload measured 20,538 inferences plain and
# 145,284 profiled [measured 2026-09-07; command=PYTHONPATH=extensions/python
# python extensions/python/benchmarks/probes/profiling_inference_cost.py]. Both
# passes run in every
# configuration, in the same order, so the warm-up each pays is the same and
# the DIFFERENCE between configurations is the row's.


def measure_worker(
    paths: Sequence[str], rows: Sequence[str], connection: Any
) -> None:
    """Run one configuration and send back its inferences and head counts.

    The workload's own printing is sent to the null device at the FILE
    DESCRIPTOR, because the engine writes through SWI's streams and a Python
    redirection would not reach them; the measurement crosses the pipe instead.
    `m.capture()` would reach the same text through an engine scope that every
    print then consults, and this measures inferences. stderr is left alone, so
    a fault still reaches whoever started the run.
    """
    with open(os.devnull, "w", encoding="utf-8") as quiet:  # noqa: PTH123  -- a file descriptor is the point
        os.dup2(quiet.fileno(), 1)
    try:
        connection.send({"ok": True, **_measure(paths, rows)})
    except BaseException as exc:  # noqa: BLE001  -- a worker failure crosses the process boundary as evidence
        connection.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        connection.close()


def _measure(paths: Sequence[str], rows: Sequence[str]) -> dict[str, Any]:
    from metta import MeTTa  # noqa: PLC0415  -- the engine boots in the WORKER, never in the driver

    if rows:
        # The catalog is process-wide and outlives any one context, so the row
        # is declared once, before a single equation compiles: the memo reads
        # it while deciding, not afterwards.
        with MeTTa() as declaring:
            for row in rows:
                declaring.self.run(f"!(add-atom &metta {row})")
    inferences: dict[str, int] = {}
    errors: dict[str, str] = {}
    heads: dict[str, dict[str, Any]] = {}
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        inferences[path] = _plain_pass(MeTTa, text, path, errors)
        _profiled_pass(MeTTa, text, path, heads)
    return {"inferences": inferences, "errors": errors, "heads": heads}


def _plain_pass(
    context_type: Any, text: str, path: str, errors: dict[str, str]
) -> int:
    """The file's own inference count, with no profiler in the process.

    The file's TEXT is run rather than the file loaded, because a declared
    `(cache Fun force)` row reaches a program run as text and does NOT reach
    the same program loaded from a file: measured on the pure-head plant at
    3,644,665 inferences plain and 163,147 under the row through `run`, against
    3,643,544 and 3,647,714 through `load`. An advisor whose what-if cannot
    apply the row it is pricing measures nothing, so the door that honours the
    row is the door this uses; the cost is that a program whose `import!` names
    a sibling relatively can fail for want of its own location, which is
    reported beside the proposals rather than hidden.
    """
    with context_type() as m:
        with m.self.stats() as counters:
            try:
                m.self.run(text)
            except BaseException as exc:  # noqa: BLE001  -- a corpus file that raises is measured, not hidden
                errors[path] = f"{type(exc).__name__}: {exc}"
        return int(counters.inferences)


def _profiled_pass(
    context_type: Any, text: str, path: str, heads: dict[str, dict[str, Any]]
) -> None:
    """The file's per-head counts, and what the catalog says about each head."""
    with context_type() as m:
        try:
            _, profile = m.self.profile(text)
        except BaseException:  # noqa: BLE001  -- the plain pass already recorded this file's failure
            return
        for node in profile.nodes:
            arity = int(node.arity)
            name = str(node.name)
            if arity < 1 or not m.self.is_function_here(name):
                continue
            declared = _head_declarations(m, name, arity)
            if declared is None:
                continue
            policy, reason, effect = declared
            key = f"{name}/{arity}"
            row = heads.setdefault(
                key,
                {
                    "name": name,
                    "arity": arity,
                    "entry_calls": 0,
                    "recursive_calls": 0,
                    "redos": 0,
                    "policy": policy,
                    "reason": reason,
                    "effect": effect,
                    "files": [],
                },
            )
            row["entry_calls"] += int(node.calls)
            row["recursive_calls"] += int(node.recursive_calls)
            row["redos"] += int(node.redos)
            if path not in row["files"]:
                row["files"].append(path)


def _head_declarations(m: Any, name: str, arity: int) -> tuple[str, str, str] | None:
    """The head's cache decision and effect, from the engine's own explanation.

    `(explain (name $a0 ... $ak))` is the one door: a head the memo has an
    opinion about answers a `(cache Choice Reason)` item, and a name that is
    not a compiled head answers none, which is how a library predicate the
    profiler happened to name is left out without a second registry to consult.
    """
    from metta import Symbol, Variable  # noqa: PLC0415  -- the engine boots in the WORKER

    call = Symbol(name)(*[Variable(f"a{index}") for index in range(arity - 1)])
    try:
        explanation = m.self.explain(call)
    except Exception:  # noqa: BLE001  -- a name explain refuses is a name this does not advise on
        return None
    cache = explanation.get("cache")
    if cache is None:
        return None
    parts = cache.children[1:]
    policy = str(parts[0]) if parts else "unknown"
    reason = " ".join(str(part) for part in parts[1:])
    effect = explanation.get("effect")
    return policy, reason, str(effect.children[1]) if effect is not None else "none"


# --------------------------------------------------------------- the collector


def _collect(
    paths: Sequence[str], rows: Sequence[str], *, label: str, context: Any, finish: Any
) -> Mapping[str, Any]:
    """Run one configuration to completion and return its payload, or raise."""
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=measure_worker, args=(list(paths), list(rows), child), name=label
    )
    process.start()
    child.close()
    failure = finish(process, worker_timeout(paths))
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


# ---------------------------------------------------------------- the workload


def workload_files(name: str) -> list[str]:
    """Every `.metta` file one workload names, in a stable order."""
    roots = WORKLOADS.get(name)
    if roots is None:
        target = Path(name)
        if not target.is_absolute():
            target = REPOSITORY_ROOT / target
        if target.is_file():
            return [str(target)]
        if target.is_dir():
            return sorted(str(path) for path in target.rglob("*.metta"))
        msg = (
            f"unknown workload {name!r}: name one of {sorted(WORKLOADS)} or give "
            f"a .metta file or a directory of them"
        )
        raise SystemExit(msg)
    files: list[str] = []
    for root in roots:
        files.extend(sorted(str(path) for path in (REPOSITORY_ROOT / root).rglob("*.metta")))
    return files


# --------------------------------------------------------------- the candidates


def head_rows(payload: Mapping[str, Any]) -> list[HeadRow]:
    """The baseline's heads, most-called first."""
    rows = [
        HeadRow(
            name=str(row["name"]),
            arity=int(row["arity"]),
            entry_calls=int(row["entry_calls"]),
            recursive_calls=int(row["recursive_calls"]),
            redos=int(row["redos"]),
            policy=str(row["policy"]),
            reason=str(row["reason"]),
            effect=str(row["effect"]),
            files=tuple(row["files"]),
        )
        for row in payload["heads"].values()
    ]
    rows.sort(key=lambda row: (-row.total_calls, row.name))
    return rows


def candidates(rows: Sequence[HeadRow], limit: int) -> list[tuple[HeadRow, str]]:
    """Which rows are worth MEASURING, and which policy each would carry.

    `force` for a head the memo declined as not recursive whose effect row does
    not say it writes: the memo never considered it and the workload called it
    more than once. `refuse` for a head the memo took on its own initiative:
    the table is a cost the program never asked for, and the what-if is what
    says whether it earns it.
    """
    chosen: list[tuple[HeadRow, str]] = []
    if limit <= 0:
        return chosen
    for row in rows:
        if row.total_calls < MIN_CALLS:
            continue
        if row.policy == "declined" and row.reason == "not-recursive":
            if row.effect in WRITING_EFFECTS:
                continue
            chosen.append((row, "force"))
        elif row.policy == "automatic":
            chosen.append((row, "refuse"))
        if len(chosen) >= limit:
            break
    return chosen


def proposal(
    row: HeadRow,
    policy: str,
    baseline: Mapping[str, Any],
    measured: Mapping[str, Any],
) -> Proposal:
    """One candidate priced against the baseline over the files it appears in.

    `total_calls` is read from the configuration where the head is NOT cached
    and `distinct_calls` from the one where it is, because a memoised head's
    profile counts its MISSES: the raw predicate is entered once per distinct
    argument and a hit never reaches it. So the hit ratio is a property of the
    PAIR of runs, and neither run alone carries it.
    """
    key = f"{row.name}/{row.arity}"
    after_row = measured["heads"].get(key)
    after_entry = int(after_row["entry_calls"]) if after_row else 0
    after_total = after_entry + (int(after_row["recursive_calls"]) if after_row else 0)
    if policy == "force":
        total, distinct = row.total_calls, after_entry
    else:
        total, distinct = after_total, row.entry_calls
    before = sum(int(baseline["inferences"][path]) for path in row.files)
    after = sum(int(measured["inferences"][path]) for path in row.files)
    return Proposal(
        row=f"(cache {row.name} {policy})",
        head=key,
        policy=policy,
        files=row.files,
        inferences_before=before,
        inferences_after=after,
        delta=before - after,
        total_calls=total,
        distinct_calls=distinct,
        hit_ratio=None if total <= 0 else round(1.0 - (distinct / total), 4),
    )


# ------------------------------------------------------------------- the report


def render(
    workload: str,
    rows: Sequence[HeadRow],
    proposals: Sequence[Proposal],
    errors: Mapping[str, str],
) -> str:
    """The advisor's table: what the workload called, and what to declare."""
    lines = [f"memo advisor over {workload}: {len(rows)} compiled heads called"]
    lines.append(
        f"{'head':28s} {'calls':>9s} {'recursive':>10s} {'redos':>8s} "
        f"{'policy':>10s}  effect"
    )
    for row in rows[:20]:
        policy = row.policy if not row.reason else f"{row.policy} {row.reason}"
        lines.append(
            f"{row.name + '/' + str(row.arity):28s} {row.entry_calls:9d} "
            f"{row.recursive_calls:10d} {row.redos:8d} {policy:>10s}  {row.effect}"
        )
    if len(rows) > 20:
        lines.append(f"... {len(rows) - 20} more heads")
    lines.append("")
    if not proposals:
        lines.append("no row proposed: no head the memo has not already settled")
    else:
        lines.append(
            f"{'proposed row':34s} {'before':>12s} {'after':>12s} {'delta':>12s} "
            f"{'hit':>7s}  verdict"
        )
        for item in proposals:
            ratio = "-" if item.hit_ratio is None else f"{item.hit_ratio:.1%}"
            verdict = "WRITE IT" if item.wins else "no gain"
            lines.append(
                f"{item.row:34s} {item.inferences_before:12d} "
                f"{item.inferences_after:12d} {item.delta:12d} {ratio:>7s}  {verdict}"
            )
        lines.append("")
        lines.append(
            "Nothing above was applied. A row is declared by writing "
            "!(add-atom &metta (cache <head> <policy>)) in the program."
        )
    if errors:
        lines.append("")
        lines.append(f"{len(errors)} workload file(s) raised while running:")
        lines.extend(f"  {path}: {detail}" for path, detail in sorted(errors.items()))
    return "\n".join(lines)


def advise(
    workload: str, *, limit: int, context: Any, finish: Any
) -> tuple[list[HeadRow], list[Proposal], Mapping[str, str]]:
    """Profile the workload, propose rows, and measure each proposal's what-if."""
    paths = workload_files(workload)
    if not paths:
        msg = f"workload {workload!r} names no .metta file"
        raise SystemExit(msg)
    baseline = _collect(paths, (), label="baseline", context=context, finish=finish)
    rows = head_rows(baseline)
    if not any(row.total_calls for row in rows):
        msg = (
            f"workload {workload!r} ran zero calls of any compiled head over "
            f"{len(paths)} file(s), so there is nothing to advise on; name a "
            f"workload that runs the functions you want cached"
        )
        raise SystemExit(msg)
    proposals = []
    for row, policy in candidates(rows, limit):
        # The WHOLE workload, in the baseline's order, even though only the
        # head's own files are summed: a corpus run in one process carries
        # state between files (12-tabling_statistics.metta reads the table
        # counters the files before it left), so running a subset would change
        # what those files cost for a reason that is not the row's.
        measured = _collect(
            paths,
            (f"(cache {row.name} {policy})",),
            label=f"what-if:{row.name}:{policy}",
            context=context,
            finish=finish,
        )
        proposals.append(proposal(row, policy, baseline, measured))
    return rows, proposals, baseline["errors"]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the advisor over one workload and report; never write a row."""
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks.memo_advisor",
        description=(
            "Propose (cache Name Policy) rows from a workload's own call counts "
            "and measure each proposal in a fresh process. Nothing is applied."
        ),
    )
    parser.add_argument(
        "--workload",
        default="bench",
        help="examples, bench, or a path to a .metta file or a directory of them",
    )
    parser.add_argument(
        "--candidates",
        type=int,
        default=8,
        help="how many proposals to measure, most-called first (default 8)",
    )
    parser.add_argument("--json", action="store_true", help="report as JSON")
    arguments = parser.parse_args(argv)
    if arguments.candidates < 0:
        parser.error("--candidates cannot be negative")
    # Deferred: bench.py pulls pytest in, and the measured workers must not
    # carry it. scaling.py defers the same import for the same reason.
    from bench import finish_process  # noqa: PLC0415

    rows, proposals, errors = advise(
        arguments.workload,
        limit=arguments.candidates,
        context=multiprocessing.get_context("spawn"),
        finish=finish_process,
    )
    if arguments.json:
        json.dump(
            {
                "workload": arguments.workload,
                "heads": [asdict(row) for row in rows],
                "proposals": [asdict(item) for item in proposals],
                "errors": dict(errors),
            },
            sys.stdout,
            indent=2,
            sort_keys=True,
        )
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render(arguments.workload, rows, proposals, errors) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
