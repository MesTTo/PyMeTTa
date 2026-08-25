"""Purpose: pin outcomes that were reached and then left unpinned, so each
one regresses loudly instead of silently. An outcome nothing tests is an
outcome that comes back: the performance oracles were deleted rather than
gated, `test.sh` computed a verdict summary it did not print, MeTTa's
generated Prolog contains no cut, Ruff's added families remain enabled with
reviewed line-level suppressions, and the compiler still threads its state by
hand because measuring the DCG alternative said to.
Assumes:
    - the repository root is two directories above this file, the same way
      test_example_parity.py derives it
    - `m.disassemble/1` answers the Prolog text a MeTTa equation compiled
      to [source: bindings/python/metta/space.py:MeTTa.disassemble;
      commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Guarantees:
    - each test fails if its outcome is reverted, which is what makes it
      evidence rather than decoration
      [tested: test_the_ruff_configuration_enables_every_family_or_records_why_not;
      commit=f88aa8be03cb64cb59d3307515ded8701f418321]
    - the compiler-state test scans the translator and reader umbrellas plus
      every source unit in their matching fragment directories
      [tested: test_no_dcg_semicontext_threads_the_compilers_state;
      commit=9a116762fb4372d55675e2ef64b7657092bc136d]
    - the naming burn-down prices the two exact Stratego public atoms whose
      language names shadow Python builtins [tested:
      test_the_ruff_configuration_enables_every_family_or_records_why_not;
      commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import json
import re
import subprocess
import sys
import tokenize
import tomllib
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PYTHON_ROOT = REPO / "bindings" / "python"
RUFF_CONFIGS = (REPO / "pyproject.toml", PYTHON_ROOT / "pyproject.toml")
RUFF_SCOPE = ("metta", "tests", "bench.py")
REQUIRED_RUFF_FAMILIES = frozenset({"FBT", "N", "A", "D", "ARG", "PERF", "C90", "TRY", "EM"})
RUFF_SUPPRESSION_GUARDS = frozenset({"RUF100", "RUF103"})
RUFF_FAMILY_BURN_DOWN = {
    # 67, from 55 before the idiomatic twin corpus. The twelve new sites are
    # boolean LITERALS crossing as atom or wire data, not behaviour switches:
    # `m.fn("match-type-or")(True, S.Number, S.Number)` asks the engine about
    # the atom True. Each carries a suppression saying so, and the corpus's own
    # named-constant convention (`TRUE, FALSE = ground(value=True), ...`) is used
    # where the value is reused rather than asked about once.
    "FBT": 67,
    "N": 35,
    # 8 -> 10 for metta.strategies: `id` and `all` must be the exact public
    # strategy atoms, while each line carries the narrow A001 explanation.
    "A": 10,
    # 2112 -> 2114 at the p12-space-model merge: its two new test modules
    # carry the repository's obligation-header docstring convention, whose
    # Purpose/Guarantees block is a deliberate per-line D205 suppression.
    # 2114 -> 2119, and ARG 134 -> 139, C90 16 -> 24, TRY 21 -> 23, at the
    # p5-surface-cluster merge: its twenty-five rows add new modules whose
    # obligation headers carry the D205 convention, signature-reflection
    # test doubles whose parameters must stay visible (ARG), registration
    # and annotation walkers kept whole by design (C901), and two internal
    # invariant raises that deliberately keep their exception class
    # (TRY004). Every one is a per-line suppression with its own reason.
    # 2119 -> 2120 at the CLI-demo repair: its regression test's scenario
    # docstring carries the same one-invariant D205 convention.
    # 2120 -> 2118 removing the legacy python.petta path: its two pinned
    # tests went with it, each carrying a D103 suppression.
    # 2118 -> 2125 at the p3-typing-cluster merge: its three new test
    # modules received the repository's docstring-suppression conventions
    # (the obligation-header D205 and the named-contract D103 forms).
    # 2125 -> 2131 with the translator rule system: one new test module
    # carrying the obligation-header D205 form and the five named-contract
    # D103 forms, one per acceptance criterion it proves.
    # 2131 -> 2135 with the grounded-equality split: four continuous-invariant
    # D205 docstrings, on _ground_identical (the unification-identity
    # relation), on the atom-equality property law, on the pinned
    # integer-vs-float counterexample test, and on the MatchIndex unification
    # law that replaced the one-line numeric-equality claim.
    # 2135 -> 2141 with P14.8's engine-stdlib prerequisites: eight new test
    # modules, one per shipped package, each carrying the obligation-header
    # D205 form, less two the same wave paid back by writing real docstrings
    # where the older convention would have suppressed D103. The one that is
    # NOT a header form is a D417 on test_doc_emission.py's fixture, where a
    # parameter is undocumented ON PURPOSE: that is the case the positional
    # (@param ...) list has to survive, so documenting it would delete the
    # fixture.
    # 2141 -> 2146 with the twins lane's idiom check: five scenario
    # docstrings across two commits carry the one-invariant D205 form. This
    # ceiling was raised TWICE badly before it was raised right, which is the
    # lesson: ddaa528 added two suppressions and did not move it at all, and
    # then 598ffea moved it to 2145 while the same commit's three new tests
    # took the count to 2146, so it was computed against the tree as it stood
    # a moment earlier. A suppression and its ceiling belong in one commit AND
    # the count belongs measured after the last edit, not before it.
    # 2146 -> 2148 as four twin folders land in the library's own idiom: the
    # two are doc_lib's D415 suppressions, where the @doc emitter keeps a
    # docstring summary VERBATIM so a summary MeTTa accepts is one pydocstyle
    # rejects. That conflict is filed against P14.8 with its decision (the
    # emitter strips one trailing period, because a docstring is Python's
    # concept and Python's convention wins), and these two suppressions go
    # when it lands. Measured on the merged tree, after the last merge.
    # 2151 after the startup-perf merge, which added `metta/__main__.py` and
    # its test. Measured on the merged tree, after the last merge.
    # 2172 as the library import door (`metta/_library.py`, its test file),
    # the flat-door typed-dispatch tests, the Handle-species test, and the
    # conformance kit's Space-handle dispatch test land: every new site is
    # the repository's own D205 one-invariant form or a D103 test-function
    # suppression, the two idioms the ceiling already prices. Measured
    # after the last edit of the landing set.
    # 2173 as the grown integration/python twin's scenario docstring takes
    # the corpus's D205 one-invariant form. Measured after the last edit.
    # 2179 as the benchmark harness gains its two-sided-band and
    # configuration-stamp tests plus the shared benchmarks/configuration
    # module: every new site is the D103 test-function suppression or the
    # D205 one-invariant module form, the two priced idioms. Measured
    # after the last edit.
    "D": 2179,
    # 145, from 139 before the idiomatic twin corpus. Every one of the six new
    # sites is a `twin(m)` whose example needs no engine, because the form it
    # demonstrates is native Python (destructuring, `len`, `max`), or a
    # callback parameter a protocol fixes. Each carries a suppression naming
    # its reason, and --ignore-noqa counts the site whatever the suppression
    # says, which is the point of a burn-down.
    # 147 after the startup-perf merge; its two new files carry two sites.
    "ARG": 147,
    "PERF": 0,
    # 24 -> 25 at the twins-wave merge: functions/specialize.py mirrors an
    # example that defines thirteen functions in a source order its
    # interleaved claims depend on, so the twin is one function by fidelity
    # rather than by accretion, and says so at its own noqa.
    # 25 -> 26 at the library-fixes merge: evaluate_answers hosts the count
    # and stream closures over one decoded target and policy context, the
    # shape fix 17's engine-side len and fix 8's suspended producer share.
    "C90": 26,
    "TRY": 23,
    "EM": 0,
}

FILE_OR_RANGE_SUPPRESSION = re.compile(r"(?i)^#\s*(?:ruff|flake8)\s*:\s*(?:noqa|disable|enable)\b")
LINE_NOQA = re.compile(r"(?i)^#\s*noqa\b")
CANONICAL_NOQA = re.compile(
    r"^#\s*(?i:noqa):\s*"
    r"(?P<codes>[A-Z]+[0-9]{3,4}(?:,\s+[A-Z]+[0-9]{3,4})*)"
    r"\s+--\s+(?P<reason>\S(?:.*\S)?)\s*$"
)
GENERIC_REASON = re.compile(r"(?i)\b(?:legacy|debt|temporary|later|todo|fixme|burn[- ]?down)\b")


def _selector_hits_family(selector: str, family: str) -> bool:
    selector = selector.upper()
    return selector == "ALL" or re.fullmatch(rf"{re.escape(family)}[0-9]*", selector) is not None


def _selector_covers_rule(selector: str, rule: str) -> bool:
    selector = selector.upper()
    return selector == "ALL" or rule.startswith(selector)


def _required_family(code: str) -> str | None:
    for family in sorted(REQUIRED_RUFF_FAMILIES, key=len, reverse=True):
        if re.fullmatch(rf"{re.escape(family)}[0-9]+", code):
            return family
    return None


def _ignore_entries(ruff: dict):
    lint = ruff["lint"]
    for section_name, section in (("[tool.ruff]", ruff), ("[tool.ruff.lint]", lint)):
        for key in ("ignore", "extend-ignore"):
            for selector in section.get(key, ()):
                yield f"{section_name}.{key}", selector
        for key in ("per-file-ignores", "extend-per-file-ignores"):
            for pattern, selectors in section.get(key, {}).items():
                for selector in selectors:
                    yield f"{section_name}.{key}[{pattern!r}]", selector


def _ruff_findings(*extra: str) -> list[dict]:
    command = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        "--output-format=json",
        *extra,
        *RUFF_SCOPE,
    ]
    completed = subprocess.run(
        command,
        cwd=PYTHON_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode in {0, 1}, (
        f"{command!r} exited {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        msg = (
            f"{command!r} did not emit Ruff JSON\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
        raise AssertionError(msg) from exc


def _assert_ruff_configuration(path: Path, ruff: dict) -> None:
    lint = ruff["lint"]
    selected = set(lint.get("select", ())) | set(lint.get("extend-select", ()))
    assert REQUIRED_RUFF_FAMILIES <= selected, (
        f"{path}: missing exact family selectors {sorted(REQUIRED_RUFF_FAMILIES - selected)}"
    )
    assert lint["pydocstyle"]["convention"] == "google"
    for guard in RUFF_SUPPRESSION_GUARDS:
        assert any(_selector_covers_rule(selector, guard) for selector in selected), (
            f"{path}: {guard} is not selected"
        )

    hidden = []
    for location, selector in _ignore_entries(ruff):
        required = sorted(
            family for family in REQUIRED_RUFF_FAMILIES if _selector_hits_family(selector, family)
        )
        guards = sorted(
            guard for guard in RUFF_SUPPRESSION_GUARDS if _selector_covers_rule(selector, guard)
        )
        if required or guards:
            hidden.append((location, selector, required, guards))
    assert not hidden, f"{path}: required Ruff rules are ignored: {hidden}"


def _audit_policy_suppressions() -> list[tuple[str, list[str], str]]:
    suppressions = []
    sources = [
        *sorted((PYTHON_ROOT / "metta").rglob("*.py")),
        *sorted((PYTHON_ROOT / "tests").rglob("*.py")),
        PYTHON_ROOT / "bench.py",
    ]
    for path in sources:
        with path.open("rb") as stream:
            comments = (
                token
                for token in tokenize.tokenize(stream.readline)
                if token.type == tokenize.COMMENT
            )
            for token in comments:
                comment = token.string
                location = f"{path.relative_to(REPO)}:{token.start[0]}"
                assert not FILE_OR_RANGE_SUPPRESSION.search(comment), (
                    f"{location}: file-level and range Ruff suppressions are forbidden: {comment}"
                )
                if not LINE_NOQA.search(comment):
                    continue
                assert ":" in comment, f"{location}: blanket noqa is forbidden: {comment}"
                code_text = comment.split(":", 1)[1].split(" -- ", 1)[0]
                candidates = re.findall(r"[A-Za-z]+[0-9]*", code_text)
                touches_policy = any(
                    _required_family(candidate.upper()) is not None
                    or candidate.upper() in RUFF_SUPPRESSION_GUARDS
                    for candidate in candidates
                )
                if not touches_policy:
                    continue
                match = CANONICAL_NOQA.fullmatch(comment)
                assert match is not None, f"{location}: use full codes and ` -- reason`: {comment}"
                codes = [code.strip() for code in match.group("codes").split(",")]
                assert len(codes) == len(set(codes)), (
                    f"{location}: duplicate suppression code: {comment}"
                )
                forbidden_guards = RUFF_SUPPRESSION_GUARDS.intersection(codes)
                assert not forbidden_guards, (
                    f"{location}: cannot suppress {sorted(forbidden_guards)}"
                )
                reason = match.group("reason")
                assert len(reason) >= 20 and GENERIC_REASON.search(reason) is None, (
                    f"{location}: replace the generic suppression reason: {reason!r}"
                )
                suppressions.append((location, codes, reason))
    return suppressions


def test_the_ruff_configuration_enables_every_family_or_records_why_not():
    """Keep every P0.13 family enabled and every suppression narrow and reviewed."""
    configurations = [
        tomllib.loads(path.read_text(encoding="utf-8"))["tool"]["ruff"] for path in RUFF_CONFIGS
    ]
    assert configurations[0] == configurations[1]
    for path, ruff in zip(RUFF_CONFIGS, configurations, strict=True):
        _assert_ruff_configuration(path, ruff)

    suppressions = _audit_policy_suppressions()
    assert suppressions, "the suppression audit saw no P0.13 line-level decisions"

    clean = _ruff_findings()
    assert not clean, f"configured Ruff gate is not clean: {clean[:20]}"

    ignored = _ruff_findings("--ignore-noqa")
    counts = Counter(
        family for finding in ignored if (family := _required_family(finding["code"])) is not None
    )
    regressions = {
        family: (counts[family], limit)
        for family, limit in RUFF_FAMILY_BURN_DOWN.items()
        if counts[family] > limit
    }
    assert not regressions, (
        f"P0.13 suppression burn-down increased (observed, maximum): {regressions}"
    )


def test_no_ungated_prolog_performance_oracle_returns():
    """P0.8 asked that the eight Prolog performance oracles be gated
    against a committed baseline OR deleted, and the delete branch is what
    happened. Nothing stopped them coming back, and an oracle that runs
    against no baseline is a file that passes by existing.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    oracles = sorted(p.relative_to(REPO) for p in (REPO / "tests" / "performance").rglob("*.pl"))
    assert not oracles, (
        f"{len(oracles)} Prolog performance oracle(s) are back and nothing "
        f"compares them to a baseline: {[str(p) for p in oracles]}"
    )


def test_the_runner_prints_every_assertion_it_collects():
    """P0.10. `test.sh` collected the `is ... should ...` lines into a
    variable and, at the time of the audit, never printed it. A verdict
    computed and dropped is worse than one never computed, because the run
    looks like it reported.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    text = (REPO / "test.sh").read_text(encoding="utf-8")
    assigned = [n for n, line in enumerate(text.splitlines(), 1) if "assertions=" in line]
    assert assigned, "test.sh no longer collects assertions; this test guards the wrong thing now"
    used = [
        n
        for n, line in enumerate(text.splitlines(), 1)
        if '"$assertions"' in line and "assertions=" not in line
    ]
    assert used, (
        f"test.sh assigns assertions at line(s) {assigned} and never reads it back; "
        "the summary it computes is dropped"
    )


def test_a_generated_clause_carries_no_cut(metta):
    """P0.12. Generated code is worse than hand-written code for a stray
    cut, because nobody reads it: a cut in a compiled equation would make
    the second clause unreachable and the program would simply answer less.

    Two clauses for one name is the shape that shows it. `(f 0)` answers
    both `zero` and `other` only if neither clause cut, so this asserts the
    behaviour AND the text, and the behaviour is the part that matters.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    metta.run("(= (petta-cut-probe 0) zero)")
    metta.run("(= (petta-cut-probe $x) other)")
    compiled = metta._disassemble("petta-cut-probe")
    assert "!" not in compiled, f"a generated clause contains a cut:\n{compiled}"
    answers = [str(a) for group in metta.run("!(petta-cut-probe 0)") for a in group]
    assert answers == ["zero", "other"], (
        f"both clauses should answer; got {answers}, which is what a cut looks like"
    )


def _dcg_scan(*sources):
    """Every DCG rule and threaded clause head of the named engine files."""
    finished = subprocess.run(
        ["swipl", "-q", "dcg_semicontext.pl", "--", *sources],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=str(REPO / "tests" / "prolog"),
    )
    scanned, dcgs, clauses = {}, set(), set()
    for line in finished.stdout.splitlines():
        head, *rest = line.split()
        assert head in {"file", "dcg", "clause"}, f"unexpected scanner line: {line!r}"
        if head == "file":
            scanned[rest[0]] = int(rest[1])
        elif head == "dcg":
            dcgs.add((rest[0], rest[1], rest[2], int(rest[3])))
        else:
            clauses.add((rest[0], rest[1]))
    return scanned, dcgs, clauses


def _engine_source_units(owner: str) -> tuple[str, ...]:
    """The owner umbrella and each source unit in its matching directory."""
    umbrella = f"../../engine/{owner}.pl"
    fragments = tuple(
        f"../../engine/{owner}/{path.name}"
        for path in sorted((REPO / "engine" / owner).glob("*.pl"))
    )
    return (umbrella, *fragments)


def test_no_dcg_semicontext_threads_the_compilers_state():
    """P2.20, closed as REJECTED by measurement, and this is what it owes.

    The question was whether the translator's hand-threaded difference lists
    should become DCGs with semicontext, which threads the state implicitly the
    way Triska's `lisprolog.pl` does. `listing/1` answered it: the DCG expands
    to `num_leaves(nil, [A|B], C) :- D is A+1, E=B, C=[D|E].` where the hand
    version is `hand(nil, N0, N1) :- N1 is N0+1.`, so the expansion adds head
    destructuring and two unification goals the hand version does not have
    [measured 2026-08-18]. The item closed on that, and nothing stopped it
    being reversed by the next reader who finds a ten-argument predicate ugly.

    The scan reads the translator source tree's TERMS, so the two `-->` inside
    tracer format strings are not mistaken for rules. Its only DCGs are message
    rules, which thread nothing: three `prolog:error_message//1` clauses and
    the two `prolog:message//1` head-pattern notes.

    The ban is the COMPILER's, not the engine's, and engine/filereader.pl is
    scanned beside it to say so: its `exec_marker_boundary//0` pushes a token
    back into the reader's stream, which is what the notation is for. That one
    head is also what proves this detector can see a semicontext rule at all,
    so a green result here is not an empty scan.
    """
    translator_sources = _engine_source_units("translator")
    reader_sources = _engine_source_units("filereader")
    scanned, dcgs, clauses = _dcg_scan(*translator_sources, *reader_sources)
    assert sum(scanned[path] for path in translator_sources) > 300, scanned
    assert sum(scanned[path] for path in reader_sources) > 100, scanned

    # The detector is live: the reader's one pushback rule is found.
    assert any(
        path in reader_sources
        and shape == "semicontext"
        and name == "exec_marker_boundary"
        and arity == 0
        for path, shape, name, arity in dcgs
    ), sorted(dcgs)

    # And the compiler has no DCG that threads anything. Its message rules are
    # the whole of its DCG use, so this covers the semicontext question and the
    # wider one: no translator predicate became a DCG at all.
    compiling = {
        (shape, name, arity)
        for path, shape, name, arity in dcgs
        if path in translator_sources
    }
    assert compiling == {
        ("plain", "error_message", 1),
        ("plain", "message", 1),
    }, sorted(compiling)

    # The other half of the same claim, from the positive side: the predicates
    # the item named still have ordinary clauses, which a converted one would
    # not.
    assert {name for path, name in clauses if path in translator_sources} == {
        "translate_expr_dl",
        "translate_special_dl",
        "translate_args_dl",
        "translate_let_dl",
        "mbr_goal",
    }, sorted(clauses)
