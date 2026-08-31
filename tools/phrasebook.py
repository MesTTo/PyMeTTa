"""Purpose: the MeTTa standard library, said in Python, with every saying
executed. `phrasebook_entries.py` carries one row for each of 380 stdlib
names: the MeTTa form, the Python spelling, and a note. This lane runs both
sides of every row, compares them against each other and against the frozen
answers in `phrasebook_answers.json`, and prints the coverage as a number per
bucket
rather than as a mood. `--markdown` regenerates
`website/reference/stdlib-phrasebook.md` from the same rows, so the page
cannot drift from what ran.

TWO COLUMNS, because one would prove nothing. A row's MeTTa form runs on
this engine and its Python spelling runs beside it, and the lane compares
them against each other and against what each answered last time. So a row
says whether the two surfaces agree today and whether either has moved since
it was frozen, and every disagreement is named rather than averaged away.

There was a third column once, an outside arbiter's answers, and it is gone
(user, 2026-08-31: "there should not be any leatta tests"). It finished the
migration commit 20cd107a began when it moved the conformance lane to
vendored upstream PeTTa: this engine follows upstream PeTTa, so a second
implementation's answer is not evidence about this one. The rows themselves
stay, superset and all.

Why both sides run at all: a phrasebook that only shows Python proves nothing
about the translation, and one nobody runs rots within a week. Running the
MeTTa form beside its Python spelling makes each row a DIFFERENTIAL, the same
instrument the twins lane and `example_parity` use one level up
[source: extensions/python/tools/twin_coverage.py, the count-against-count
contract; commit=f88aa8be03cb64cb59d3307515ded8701f418321].

The five buckets, and what each CLAIMS:
  - `dissolves`: Python already has the concept, so there is no metta name at
    all and the spelling is Python's own syntax, protocol or standard library
    (`e[0]`, `list()`, `assert`, `max`). Section 9e's first bucket.
  - `method`: the concept is MeTTa's, so it wears a metta name
    (`m.eval`, `space.query`, `atom.alpha_eq`). Section 9e's second bucket.
  - `instruction`: deep control that stays instruction-tier and is reached by
    building the term at the `S.` door and reducing it. Section 9e's third
    bucket. Such a row is Python with no MeTTa source text, but it is
    deliberately transliteration-shaped: the ladder keeps the rung.
  - `internal`: a mechanised interpreter, written in MeTTa. The
    `interpret-*`, `mi-*` and `u-*` families are the interpreter's own
    equations rather than operations a program calls, and MeTTa writes its
    interpreter in Prolog, so these names are on neither surface. Accounted
    for, never counted as coverage.
  - `absent`: a user-facing operation with no Python spelling today. This is
    the residue, and it derives the backlog.

Assumes:
  - a fresh space isolates equations, so 377 rows share one engine instead of
    377 processes [measured 2026-08-22: a definition made in `m._new_space()`
    is invisible to `&self` and to a sibling space, and fifty fresh spaces
    with a definition and a call cost 0.007s; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a second `MeTTa()` in one process is the SAME engine with its OWN home
    space, so stored state is isolated per context while registrations stay
    process-wide; sharing the process home is spelled `metta.engine()`
    [tested: extensions/python/tests/ch04_spaces_and_matching/test_space.py::test_metta_contexts_are_isolated;
    commit=57f21ba9edf94bcf28cde11f938bce2c241a3709]
  - `&pb` in a row's MeTTa form is that row's own space. On this engine the
    name is made unique per row before the form runs, because `bind!` here
    keeps the old contents when a bound name is re-bound, where a
    process-per-row runner would use the written name as written [measured
    2026-08-22: re-binding a bound name leaves `(f 1)` in place here, while
    a stricter reader refuses the second `bind!` with
    `(Error ... (BadArgType 1 Symbol SpaceType))`; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - both sides are frozen into `phrasebook_answers.json` and re-measured only
    under `--learn`, exactly as the upstream parity baseline freezes its numbers
    [source: tests/checks/check_upstream_parity.py, its Assumes block]
Guarantees:
  - every stdlib name has exactly one row, so the coverage denominator cannot
    quietly shrink [tested: test_the_phrasebook_carries_one_row_per_name]
  - a row whose Python spelling stops answering what it claims is a finding,
    which is what stops a phrasebook rotting [tested:
    test_a_broken_python_spelling_is_a_finding]
  - a row whose sides disagree is a finding unless it names the divergence in
    `differs`, so a translation that is merely plausible cannot pass [tested:
    test_a_silent_divergence_is_a_finding]
  - the checked-in page equals what `--markdown` produces [tested:
    test_the_phrasebook_page_is_up_to_date]
  - Python-first additions that have no stdlib declaration of their own are
    rendered in a separate exact-spelling table rather than corrupting coverage
    [tested: test_python_first_public_faces_are_in_the_phrasebook;
    commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - a row may run a MeTTa-only setup; nothing is silently sent elsewhere
    [tested:
    python extensions/python/tools/phrasebook.py --gate; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa]
  - PUBLIC/INTERNAL is row data, all live catalog names carry it, and the
    rendered reference includes PUBLIC rows only [tested:
    test_internal_rows_are_absent_from_the_public_phrasebook;
    commit=8779452fed89853c3f77c3469f7a6ec7b12e9efa]
Fails when:
  - a row's MeTTa form depends on answer ORDER: answers are compared as
    sequences, the reading `example_parity` already takes, so a genuinely
    unordered answer set would read as a difference
Decides:
  - the rendering rule, stated once so no row has to explain it: a value is
    rendered as the engine prints it, `str(atom)` for an atom and
    `str(metta.ground(x))` for an opaque value. A Python LIST is a multiset of
    answers, one string per element, because `list()` is collapse; a Python
    TUPLE is one Expression atom, because a tuple encodes to `( )`
    [source: ai-python-first-revamp-discussion.md sections 9e and 9k]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the lane's contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import argparse
import ast
import contextlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import alpha

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
PAGE = REPO / "website" / "reference" / "stdlib-phrasebook.md"
ANSWERS = TOOLS / "phrasebook_answers.json"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO / "extensions" / "python"))

from phrasebook_entries import (  # noqa: E402
    BUCKETS,
    ENTRIES,
    PUBLIC_FACES,
    SECTIONS,
    VISIBILITIES,
    Entry,
)

#: The tree state every measurement recorded in this lane was taken
#: against. A row's own note carries the date without it, because a row's
#: evidence is the row: the lane re-runs both sides on every invocation and
#: `phrasebook_answers.json` records what they answered, so a commit id there
#: would age the page's prose without making anything checkable.
EVIDENCE = "c6abaad21ab41b32b815b7481edff822b236e69a"

#: The placeholder a row writes for "a space of my own".
SPACE = "&pb"

#: How many answers a bracketed transcript line may hold before the page
#: truncates it. The largest honest row is `get-atoms` over a few facts.
SHOWN = 6


def render(value: Any) -> tuple[str, ...]:
    """Answers, as the engine prints them.

    A list is a multiset of answers, because `list()` is collapse; anything
    else is one answer. An atom prints itself and a Python value prints as
    the atom it encodes to, which is how `(1 2)` and `"text"` come out right.
    """
    if isinstance(value, list):
        return tuple(_one(item) for item in value)
    return (_one(value),)


def _one(value: Any) -> str:
    import metta  # noqa: PLC0415  -- deferred so the lane imports without an engine

    if isinstance(value, metta.Atom):
        return alpha.canonical(str(value))
    if isinstance(value, tuple):
        return alpha.canonical(str(metta.Expression(value)))
    return alpha.canonical(str(metta.ground(value)))


#: What an ordinary row may spend before the lane calls it a runaway. Strategy
#: rows override this because each fresh row compiles lib_strategy and its
#: recursive traversal equations before evaluating the small witness
#: [measured: 2026-08-26, 11079816; command=python extensions/python/tools/phrasebook.py
#: --learn --markdown --gate;
#: fixture=bottomup row after ten prior strategy imports; commit=0d37dd6b24fe916e44cdbfb4efc6a1d5ffaf74aa].
FUEL = 2_000_000
SECONDS = 10.0


def metta_answers(engine: Any, entry: Entry, index: int, space: Any = None) -> tuple[str, ...]:
    """The answers of the last `!` form of a row's MeTTa side, on this engine."""
    space = engine._new_space() if space is None else space
    source = "\n".join(part for part in (entry.metta_setup, entry.metta) if part)
    source = source.replace(SPACE, f"{SPACE}{index}")
    inferences = entry.metta_fuel or FUEL
    with engine.limits(inferences=inferences, timeout=SECONDS):
        groups = space.run(source)
    if not groups:
        message = f"{entry.name}: no runnable form in {entry.metta!r}"
        raise ValueError(message)
    return tuple(str(atom) for atom in groups[-1])


def split_answers(line: str) -> tuple[str, ...]:
    """`[a, (f 1)]` as its answers. Commas inside a form are not separators."""
    body = line.strip()[1:-1].strip()
    if not body:
        return ()
    out, depth, start = [], 0, 0
    for index, character in enumerate(body):
        if character in "([":
            depth += 1
        elif character in ")]":
            depth -= 1
        elif character == "," and depth == 0:
            out.append(body[start:index].strip())
            start = index + 1
    out.append(body[start:].strip())
    return tuple(out)


def python_value(engine: Any, source: str, space: Any = None) -> Any:
    """A row's Python side, run whole; its value is its last expression.

    doctest's own reading of a block: statements, and the last one's value is
    what the reader sees. `ast` decides which case it is rather than a regex.
    """
    import metta  # noqa: PLC0415  -- deferred so the lane imports without an engine

    tree = ast.parse(source)
    if not tree.body:
        message = "empty python spelling"
        raise ValueError(message)
    namespace: dict[str, Any] = {
        "metta": metta,
        "m": engine,
        "S": metta.S,
        "V": metta.V,
        "space": engine._new_space() if space is None else space,
    }
    tail = tree.body[-1]
    if isinstance(tail, ast.Expr):
        head = ast.Module(body=tree.body[:-1], type_ignores=[])
        exec(compile(head, "<phrasebook>", "exec"), namespace)  # noqa: S102
        return eval(  # noqa: S307
            compile(ast.Expression(body=tail.value), "<phrasebook>", "eval"), namespace
        )
    exec(compile(tree, "<phrasebook>", "exec"), namespace)  # noqa: S102
    return None


@contextlib.contextmanager
def quiet() -> Any:
    """Both sides silenced, at the file descriptor.

    A row for `println!` or `print` writes to standard output on purpose, and
    the engine's half writes from Prolog rather than from Python, so
    `redirect_stdout` would catch only one of the two. Swapping the descriptor
    catches both, and both streams are flushed inside the swap so nothing
    buffered arrives after it [measured 2026-08-22: without the flush the
    engine's `hello` reappears under the report; commit=f88aa8be03cb64cb59d3307515ded8701f418321].
    """
    sys.stdout.flush()
    saved = os.dup(1)
    with open(os.devnull, "w", encoding="utf-8") as sink:  # noqa: PTH123
        os.dup2(sink.fileno(), 1)
        try:
            yield
        finally:
            sys.stdout.flush()
            os.dup2(saved, 1)
            os.close(saved)


def measure(engine: Any, entry: Entry, index: int) -> dict[str, list[str] | None]:
    """What the two local sides answer now. Raises nothing: an error is text."""
    seen: dict[str, list[str] | None] = {"metta": None, "python": None}
    with quiet():
        if entry.metta is not None and entry.unrun is None:
            try:
                seen["metta"] = list(metta_answers(engine, entry, index))
            except Exception as error:  # noqa: BLE001
                seen["metta"] = [f"RAISED {type(error).__name__}: {error}"]
        if entry.python is not None:
            try:
                seen["python"] = list(render(python_value(engine, entry.python)))
            except Exception as error:  # noqa: BLE001
                seen["python"] = [f"RAISED {type(error).__name__}: {error}"]
    return seen


def compare(entry: Entry, frozen: dict[str, Any], seen: dict[str, Any]) -> list[str]:
    """Everything wrong with one row, named."""
    findings = []
    for side in ("metta", "python"):
        if seen[side] is None:
            continue
        if any(item.startswith("RAISED ") for item in seen[side]):
            findings.append(f"the {side} side {seen[side][0].lower()}")
            continue
        if frozen.get(side) != seen[side]:
            findings.append(
                f"the {side} side now answers {seen[side]}, not the recorded "
                f"{frozen.get(side)}"
            )
    if entry.differs is None:
        pair = [seen[side] for side in ("metta", "python") if seen[side] is not None]
        if len(pair) == 2 and pair[0] != pair[1] and not any(
            item.startswith("RAISED ") for group in pair for item in group
        ):
            findings.append(
                f"the two sides disagree, {pair[0]} against {pair[1]}, and the row "
                f"does not say why"
            )
    return findings


def structural(entries: list[Entry]) -> list[str]:
    """What is wrong with the phrasebook itself, before anything runs."""
    findings = []
    names = [entry.name for entry in entries]
    duplicated = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicated:
        findings.append(f"{len(duplicated)} name(s) carry more than one row: {duplicated}")
    for entry in entries:
        if entry.bucket not in BUCKETS:
            findings.append(f"{entry.name}: unknown bucket {entry.bucket!r}")
        if entry.section not in SECTIONS:
            findings.append(f"{entry.name}: unknown section {entry.section!r}")
        if entry.visibility not in VISIBILITIES:
            findings.append(
                f"{entry.name}: unknown visibility {entry.visibility!r}"
            )
        if entry.bucket == "internal" and entry.visibility != "INTERNAL":
            findings.append(
                f"{entry.name}: an internal row claims {entry.visibility} visibility"
            )
        if entry.bucket in {"dissolves", "method"} and entry.python is None:
            findings.append(f"{entry.name}: claims bucket {entry.bucket} with no spelling")
        if entry.bucket == "absent" and entry.python is not None:
            findings.append(f"{entry.name}: claims to be absent yet carries a spelling")
        if not entry.note:
            findings.append(f"{entry.name}: no note, so the row says nothing to a reader")
        if entry.unrun is not None and entry.metta is None:
            findings.append(f"{entry.name}: says why its form does not run, but shows no form")
        if entry.ruled is not None and entry.bucket != "absent":
            findings.append(
                f"{entry.name}: names a ruling, which only a residue row needs"
            )
        if entry.metta_setup is not None and entry.metta is None:
            findings.append(f"{entry.name}: has setup but no MeTTa form")
        if entry.unary_metta is not None and entry.metta is None:
            findings.append(f"{entry.name}: has a unary form but no MeTTa form")
        if entry.metta_fuel is not None and entry.metta_fuel < 1:
            findings.append(f"{entry.name}: has a non-positive MeTTa inference limit")
    return findings


def visibility_drift(engine: Any, entries: list[Entry]) -> list[str]:
    """Compare phrasebook row visibility with the live callable catalog."""
    import metta  # noqa: PLC0415  -- deferred so importing the lane stays inert

    rows = engine._at("&metta").match(metta.S.visibility(metta.V.name, metta.V.level))
    pairs = [(str(row.name), str(row.level)) for row in rows]
    observed = dict(pairs)
    names = set(engine.builtins())
    findings = []
    if len(observed) != len(pairs):
        findings.append("more than one visibility row exists for a callable name")
    missing = sorted(names - observed.keys())
    extra = sorted(observed.keys() - names)
    if missing:
        findings.append(f"callable names have no visibility row: {missing}")
    if extra:
        findings.append(f"visibility rows name no callable: {extra}")
    findings.extend(
        f"{entry.name}: catalog says {observed[entry.name]}, "
        f"phrasebook says {entry.visibility}"
        for entry in entries
        if entry.name in observed and observed[entry.name] != entry.visibility
    )
    return findings


def report(
    entries: list[Entry],
    findings: dict[str, list[str]],
    answers: dict[str, Any],
    *,
    show: int,
) -> None:
    """The whole verdict on one screen: coverage, residue, findings."""
    _report_coverage(entries)
    _report_cost(answers)
    _report_residue(entries)
    _report_findings(findings, show)


def _report_coverage(entries: list[Entry]) -> None:
    counts = Counter(entry.bucket for entry in entries)
    total = len(entries)
    spoken = counts["dissolves"] + counts["method"] + counts["instruction"]
    surface = total - counts["internal"]
    print(
        f"stdlib phrasebook: {spoken} of {surface} surface operations have a Python "
        f"spelling ({total} distinct names, {counts['internal']} of them the "
        f"mechanised interpreter's own)"
    )
    for bucket, description in BUCKETS.items():
        print(f"  {bucket:<12} {counts[bucket]:>4}   {description}")


def _report_cost(answers: dict[str, Any]) -> None:
    priced = [
        record for record in answers.values()
        if isinstance(record, dict) and "python_inferences" in record
    ]
    if priced:
        print(
            f"  cost over {len(priced)} rows that run both sides: "
            f"{sum(r['metta_inferences'] for r in priced):,} engine inferences through "
            f"MeTTa against {sum(r['python_inferences'] for r in priced):,} through "
            f"Python, {sum(1 for r in priced if r['python_inferences'] == 0)} of them "
            "costing the engine nothing"
        )


def _report_residue(entries: list[Entry]) -> None:
    residue = sorted(entry.name for entry in entries if entry.bucket == "absent")
    ruled = sorted(entry.name for entry in entries if entry.ruled is not None)
    if residue:
        print(f"  residue ({len(residue)}): {', '.join(residue)}")
    if ruled:
        print(
            f"  of which {len(ruled)} are a RULED decline rather than a gap: "
            f"{', '.join(ruled)}"
        )


def _report_findings(findings: dict[str, list[str]], show: int) -> None:
    total_findings = sum(len(items) for items in findings.values())
    if not total_findings:
        print("  0 findings")
        return
    print(f"  {total_findings} finding(s)")
    shown = 0
    for name, items in findings.items():
        for item in items:
            if shown >= show:
                print(f"  ... {total_findings - shown} more")
                return
            print(f"    {name}: {item}")
            shown += 1


def page(entries: list[Entry], answers: dict[str, Any]) -> str:
    """The phrasebook, as the page a reader opens."""
    counts = Counter(entry.bucket for entry in entries)
    surface = len(entries) - counts["internal"]
    spoken = counts["dissolves"] + counts["method"] + counts["instruction"]
    out = [
        "# The MeTTa standard library, in Python",
        "",
        "Every operation MeTTa's standard library declares, and what you write in Python",
        f"instead. {spoken} of the {surface} operations a program can call have a Python",
        "spelling, and every runnable row below was measured on this engine and",
        "through the Python spelling here. A row names the equivalent unary form",
        "when this engine's reified strategy application has another arity.",
        "",
        f"The rows carry this engine's own names and types, {len(entries)} distinct names,",
        "and `extensions/python/tools/phrasebook.py` runs them and fails when a",
        "spelling stops answering what it says it answers. A third column",
        "measured against a second engine until 2026-08-31; upstream PeTTa is the",
        "arbiter and `tests/conformance/petta.py` is the lane that gates on it.",
        "",
        "## How to read a row",
        "",
        "The MeTTa column is a form that runs. The Python column is what you write instead.",
        "The answer column is what both produced. In a Python cell `m` is the engine, `space`",
        "is a fresh space, and `S` and `V` build symbols and variables; in a MeTTa cell `&pb`",
        "is that row's own space.",
        "",
        "Rows fall in five buckets, and the bucket is the honest part:",
        "",
    ]
    for bucket, description in BUCKETS.items():
        out.append(f"- **{bucket}** ({counts[bucket]}) &mdash; {description}")
    out += [
        "",
        "## Python-first additions",
        "",
        "These faces implement the Python-first execution model and therefore have no",
        "standard-library declaration to occupy one of the rows above.",
        "They stay separate so the coverage denominator remains exact.",
        "",
        "| public spelling | meaning | example |",
        "|---|---|---|",
    ]
    out += [
        f"| {_cell(face.spelling)} | {face.meaning} | {_cell(face.example)} |"
        for face in PUBLIC_FACES
    ]
    priced = [
        (entry.name, answers[entry.name])
        for entry in entries
        if entry.name in answers and "python_inferences" in answers[entry.name]
    ]
    engine_total = sum(record["metta_inferences"] for _, record in priced)
    python_total = sum(record["python_inferences"] for _, record in priced)
    free = sum(1 for _, record in priced if record["python_inferences"] == 0)
    out += [
        "",
        f"Provenance: {len(entries)} distinct stdlib names, each with one row.",
        "",
        "## What the Python spelling costs",
        "",
        "Section 9e claims that a structure operation on an atom already held in Python",
        "costs no engine crossing at all. Measured over the rows that run both sides:",
        f"the MeTTa forms cost {engine_total:,} engine inferences and the Python spellings",
        f"cost {python_total:,}, and {free} of the {len(priced)} rows cost the engine EXACTLY",
        "NOTHING. `e[0]`, `e[1:]`, `len(e)`, `max([...])` and `S.f(1)` each read the same",
        "count as an empty measurement block, so the claim holds: the work never reaches",
        "the engine at all.",
        "",
        f"`(car-atom (a b c))` costs {_priced(answers, 'car-atom')} inferences on this",
        "engine against 0 for `e[0]`, and `(map-atom (1 2 3) $x (+ $x 1))` costs",
        f"{_priced(answers, 'map-atom')} against 0 for the comprehension.",
        "",
        "The other side of the same coin, so the comparison is not oversold. Most of a",
        "MeTTa row's cost is running one form at all: on a fresh engine an unreduced",
        "three-argument call costs 713 inferences and `(car-atom (a b c))` costs 848, so",
        "about 135 of it is the operation. And inside an `@m.define` body the Python",
        "spelling COMPILES to the same instruction, where the cost is the handwritten cost",
        "by construction. The saving is real where a program already holds the atom in",
        "Python, which is what the bucket says.",
        "",
        "Absolute counts move with what the engine has already done, which is why the two",
        "paragraphs above disagree by tens of inferences on the same form; the zero on the",
        "Python side does not move. Within one run the counts are exact: three fresh",
        "`--learn` processes wrote byte-identical files, cost numbers included",
        f"[measured 2026-08-22; commit={EVIDENCE}].",
        "",
    ]
    for section, heading in SECTIONS.items():
        rows = [
            entry
            for entry in entries
            if entry.section == section and entry.visibility == "PUBLIC"
        ]
        if not rows:
            continue
        out += [f"## {heading}", ""]
        out += ["| MeTTa | Python | answers | bucket |", "|---|---|---|---|"]
        out += [_row(entry, answers.get(entry.name, {})) for entry in rows]
        out.append("")
        if section == "strategies":
            out += _strategy_basis_section()
        for entry in rows:
            line = f"- `{entry.name}` `{' | '.join(entry.types)}` &mdash; {entry.note}"
            if entry.differs:
                line += f" Where they differ: {entry.differs}."
            if entry.unrun:
                line += f" The form is shown but not run here: {entry.unrun}."
            if entry.ruled:
                line += f" Ruled rather than missing: {entry.ruled}."
            if entry.unary_metta:
                unary = entry.unary_metta.replace("\n", " ⏎ ")
                line += f" Unary form: `{unary}`."
            out.append(line)
        out.append("")
    return "\n".join(out) + "\n"


def _strategy_basis_section() -> list[str]:
    """Every public lib_strategy constructor and application/type door."""
    rows = (
        ("id", "`id`", "`strategies.id`", "`id(t) = t`"),
        ("fail", "`fail`", "`strategies.fail`", "answers no result"),
        ("seq", "`(seq s1 s2)`", "`strategies.seq(s1, s2)`", "`s2(s1(t))`"),
        (
            "choice",
            "`(choice left right)`",
            "`strategies.choice(left, right)`",
            "complete left result bag, or `right(t)` only when that bag is empty",
        ),
        ("try", "`(try s)`", "`strategies.try_(s)`", "`choice(s, id)`"),
        ("repeat", "`(repeat s)`", "`strategies.repeat(s)`", "`try(seq(s, repeat(s)))`"),
        ("all", "`(all s)`", "`strategies.all(s)`", "apply `s` to every immediate child"),
        ("one", "`(one s)`", "`strategies.one(s)`", "enumerate each successful one-child rewrite"),
        (
            "topdown",
            "`(topdown s)`",
            "`strategies.topdown(s)`",
            "`seq(s, all(topdown(s)))`",
        ),
        (
            "bottomup",
            "`(bottomup s)`",
            "`strategies.bottomup(s)`",
            "`seq(all(bottomup(s)), s)`",
        ),
        (
            "innermost",
            "`(innermost s)`",
            "`strategies.innermost(s)`",
            "`bottomup(try(seq(s, innermost(s))))`",
        ),
        (
            "stratego-all",
            "`(stratego-all s)`",
            "`strategies.stratego_all(s)`",
            "public alias of `all(s)`",
        ),
        (
            "stratego-one",
            "`(stratego-one s)`",
            "`strategies.stratego_one(s)`",
            "public alias of `one(s)`",
        ),
        ("gtry", "direct call only", "`S.gtry`", "`gtry(s, t) = try(s)(t)`"),
        (
            "strategy-apply",
            "`(strategy-apply s t)`",
            "`S['strategy-apply'](s, t)`",
            "translator-lowers to the atom `(strategy-eval s t)`",
        ),
        ("TP", "`TP`", "`strategies.TP`", "type-preserving strategy scheme"),
        ("TU", "`(TU result-type)`", "`strategies.TU(result_type)`", "type-unifying strategy scheme"),
        (
            "◁",
            "`(◁ s TP t)` or `(◁ s (TU r) t)`",
            "`S['◁'](s, scheme, t)`",
            "apply only when the declared strategy arrow fits the scheme",
        ),
    )
    out = [
        "MeTTa's complete shipped basis is reified below. Every plan cell is ordinary",
        "queryable atom data, and every row is exercised by",
        "`examples/ch20-extending-the-engine/20-02-metta-written-in-metta/11-strategy.metta` through the normal library runner.",
        "",
        "| public name | reified plan or MeTTa door | Python atom | law |",
        "|---|---|---|---|",
    ]
    out += [f"| `{name}` | {plan} | {python} | {law} |" for name, plan, python, law in rows]
    out.append("")
    return out


def _priced(answers: dict[str, Any], name: str) -> str:
    """One row's recorded engine cost, for the prose that quotes it."""
    return f"{answers.get(name, {}).get('metta_inferences', 0):,}"


def _cell(text: str | None) -> str:
    if not text:
        return "&mdash;"
    return "`" + text.replace("\n", " ⏎ ").replace("|", "\\|") + "`"


def _answer(frozen: dict[str, Any]) -> str:
    """What the row answered, one value where the three sides agree.

    A phrasebook row is only interesting when they disagree, so the column
    labels the sides exactly then and stays quiet otherwise.
    """
    sides = [(name, frozen.get(name)) for name in ("metta", "python")]
    present = [(name, value) for name, value in sides if value is not None]
    if not present:
        return ""
    groups: dict[tuple[str, ...], list[str]] = {}
    for name, value in present:
        groups.setdefault(tuple(_capped(value)), []).append(name)
    if len(groups) == 1:
        return ", ".join(next(iter(groups))) or "(no answer)"
    return "; ".join(
        f"{', '.join(answers) or '(no answer)'} on {' and '.join(names)}"
        for answers, names in groups.items()
    )


def _capped(value: list[str]) -> list[str]:
    return [*value[:SHOWN], "..."] if len(value) > SHOWN else list(value)


def _row(entry: Entry, frozen: dict[str, Any]) -> str:
    answer = _answer(frozen)
    return (
        f"| {_cell(entry.metta)} | {_cell(entry.python)} | "
        f"{_cell(answer) if answer else '&mdash;'} | {entry.bucket} |"
    )


def cost(engine: Any, entries: list[Entry]) -> list[tuple[str, int, int]]:
    """Each row's two sides, priced in inferences.

    Section 9e claims that a structure operation on an atom already held in
    Python costs NO engine crossing at all, which beats evaluating the MeTTa
    form. This is that claim as a number, per row: engine inferences for the
    MeTTa side, engine inferences for the Python side. Inferences are
    deterministic on this box, which is why one process decides and three
    only confirm it.
    """
    # Reading the counter costs a few inferences of its own, and each side
    # needs a space it did not pay for, so both are made outside the block and
    # the floor is subtracted [measured 2026-08-22: an empty `with
    # m.stats()` block reads 5 inferences and `m._new_space()` costs 35;
    # commit=f88aa8be03cb64cb59d3307515ded8701f418321].
    with engine.stats() as empty:
        pass
    floor = empty.inferences
    out = []
    for index, entry in enumerate(entries):
        if entry.metta is None or entry.python is None or entry.unrun is not None:
            continue
        metta_space, python_space = engine._new_space(), engine._new_space()
        # A row that raises still prices its other side; the answer lane is
        # what reports the raise.
        with quiet():
            with engine.stats() as engine_side, contextlib.suppress(Exception):
                metta_answers(engine, entry, index, metta_space)
            with engine.stats() as python_side, contextlib.suppress(Exception):
                python_value(engine, entry.python, python_space)
        out.append(
            (
                entry.name,
                max(engine_side.inferences - floor, 0),
                max(python_side.inferences - floor, 0),
            )
        )
    return out


def learn(engine: Any, entries: list[Entry], answers: dict[str, Any]) -> dict[str, Any]:
    """Re-measure every side and freeze it. LeaTTa only when it is present."""
    return _learn(engine, entries, answers)


def _learn(
    engine: Any, entries: list[Entry], answers: dict[str, Any]
) -> dict[str, Any]:
    fresh: dict[str, Any] = {
        "//": {
            "what": "measured answers, one record per stdlib name; --learn rewrites it",
        }
    }
    for index, entry in enumerate(entries):
        if entry.metta is None and entry.python is None:
            continue
        record = dict(answers.get(entry.name, {}))
        record.pop("leatta", None)
        record.update(measure(engine, entry, index))
        fresh[entry.name] = record
    for name, engine_side, python_side in cost(engine, entries):
        fresh[name]["metta_inferences"] = engine_side
        fresh[name]["python_inferences"] = python_side
    return fresh


def _print_cost(rows: list[tuple[str, int, int]]) -> None:
    """The per-row prices as CSV, with the totals on a comment line."""
    print("name,metta_inferences,python_inferences")
    for name, engine_side, python_side in rows:
        print(f"{name},{engine_side},{python_side}")
    print(
        f"# {len(rows)} rows: {sum(row[1] for row in rows)} inferences through the "
        f"engine, {sum(row[2] for row in rows)} through the Python spelling, "
        f"{sum(1 for row in rows if row[2] == 0)} of them costing the engine nothing"
    )


def _page_state(wanted: str, *, write: bool) -> str:
    """Rewrite the page, or say how it differs from what the rows produce."""
    if write:
        PAGE.parent.mkdir(parents=True, exist_ok=True)
        PAGE.write_text(wanted, encoding="utf-8")
        print(f"wrote {PAGE.relative_to(REPO)}")
        return ""
    if not PAGE.is_file():
        return "is missing; run with --markdown"
    if PAGE.read_text(encoding="utf-8") != wanted:
        return (
            "no longer matches the rows; run "
            "`python extensions/python/tools/phrasebook.py --markdown`"
        )
    return ""


def main(argv: list[str]) -> int:
    """Run the lane, or rewrite what it reads and writes."""
    parser = argparse.ArgumentParser(description="the MeTTa standard library, in Python")
    parser.add_argument("--markdown", action="store_true", help="rewrite the page")
    parser.add_argument("--learn", action="store_true", help="re-measure and freeze answers")
    parser.add_argument("--show", type=int, default=25, help="how many findings to print")
    parser.add_argument("--gate", action="store_true", help="exit nonzero on any finding")
    parser.add_argument("--cost", action="store_true", help="price both sides in inferences")
    arguments = parser.parse_args(argv)

    entries = list(ENTRIES)
    findings: dict[str, list[str]] = {}
    structure = structural(entries)
    if structure:
        findings["the phrasebook itself"] = structure
    import metta  # noqa: PLC0415  -- deferred so the lane imports without an engine

    engine = metta.MeTTa(metta_path=str(REPO)).self
    answers = json.loads(ANSWERS.read_text(encoding="utf-8")) if ANSWERS.is_file() else {}
    visibility = visibility_drift(engine, entries)
    if visibility:
        findings["catalog visibility"] = visibility

    if arguments.cost:
        _print_cost(cost(engine, entries))
        return 0

    if arguments.learn:
        answers = learn(engine, entries, answers)
        ANSWERS.write_text(json.dumps(answers, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {ANSWERS.relative_to(REPO)}")
    else:
        for index, entry in enumerate(entries):
            if entry.metta is None and entry.python is None:
                continue
            problems = compare(entry, answers.get(entry.name, {}), measure(engine, entry, index))
            if problems:
                findings[entry.name] = problems

    stale = _page_state(page(entries, answers), write=arguments.markdown)
    if stale:
        findings["the page"] = [stale]

    report(
        entries,
        findings,
        answers,
        show=arguments.show,
    )
    return 1 if (arguments.gate and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
