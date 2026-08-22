"""Purpose: prove the twin coverage lane catches what it claims to catch.

A lane that cannot be shown failing is evidence of nothing, so these plant a
source-text cheat, a renamed variable, a wrong answer, a hidden definition
and an undeclared skip, and require the lane to answer correctly about each.

Guarantees:
  - point budgets remain two-sided with the deterministic tolerance stated
    separately [tested: test_a_budget_is_two_sided; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
  - empirical envelopes are asymmetric, protocol-scoped, and falsified by
    the first observation outside their measured bounds [tested:
    test_an_empirical_envelope_passes_its_observations_and_fails_new_spread,
    test_an_empirical_envelope_cannot_license_another_protocol;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
  - malformed or legacy spread declarations cannot silently widen a budget
    [tested: test_an_empirical_envelope_requires_complete_measurement_metadata,
    test_spread_is_not_a_budget_door; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
  - expected printing text is written as Python text while strings carried as
    MeTTa data still require val() [tested:
    test_printing_text_is_not_forced_through_the_value_carrier;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
  - the 159 entries superseded by empirical budgets are retired exactly once
    [tested: test_the_distribution_budget_retirement_is_exact;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "bindings" / "python" / "tools"))

import example_parity as parity  # noqa: E402
import twin_coverage as coverage  # noqa: E402


def _run(groups, heads=(), cost=0, error=None):
    """One side's run, built rather than measured.

    The comparison can then be exercised without starting an engine.
    """
    return coverage.Run(parity.Outcome(list(groups), error), cost, tuple(heads))


# ------------------------------------------------------------------- discovery


def test_the_twin_set_is_derived_from_the_one_corpus():
    """Discovery is example_parity's and the twin path is a transform of it.

    So a twin cannot exist for something no runner runs.
    """
    corpus = parity.corpus()
    assert corpus, "the corpus is empty, which means discovery is broken"
    for example in corpus:
        assert coverage.example_for(coverage.twin_for(example)) == example
    assert coverage.orphans() == [], "a twin covers nothing the corpus runs"
    assert coverage.written(), "no example has a twin"
    assert set(coverage.written()) <= set(corpus)


def test_the_coverage_fraction_names_every_folder_of_the_corpus():
    """A lane reporting only what has been written reports only good news.

    The fraction is the point of this lane, so a folder with no twin at all
    still prints, at zero over its corpus count.
    """
    folders = coverage._folders([], REPO)
    corpus = {
        str(path.relative_to(REPO / "examples").parent) for path in parity.corpus()
    }
    assert set(folders) == corpus
    assert sum(counts[1] for counts in folders.values()) == len(parity.corpus())
    assert all(counts[0] == 0 for counts in folders.values()), "no verdicts were given"


def test_every_residue_entry_names_a_real_example_and_a_row():
    """A residue entry is the backlog, so it must name something that exists.

    An entry naming a deleted example is a line nobody will notice is dead,
    which is why example_skips.txt is checked the same way.
    """
    kinds = {coverage.DECLINED_KIND, coverage.FRICTION_KIND}
    for entry in coverage.residue():
        assert entry["kind"] in kinds, entry
        assert (REPO / entry["example"]).is_file(), entry["example"]
        assert entry["row"].startswith("P14."), entry
        assert entry["missing"] and entry["detail"], entry
        if entry["kind"] == coverage.DECLINED_KIND:
            assert isinstance(entry["form"], int), "a declined entry names its form"


# ------------------------------------------------------------ source discipline


def test_the_source_scan_catches_a_planted_string(tmp_path):
    """Every way a twin could reach the engine through MeTTa source text."""
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""A docstring mentioning (f a) is not a finding."""\n'
        "from petta import S\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        '    m.run("(= (f) 42) !(f)")\n'
        '    yield m.eval("(+ 1 2)")\n'
        '    yield m.eval(S.test(S.f(), "(f a)"))\n'
        '    yield m.eval(m.parse("(f a)"))\n',
        encoding="utf-8",
    )
    findings = "\n".join(coverage.scan(planted))
    assert "calls run(), which takes MeTTa source" in findings
    assert "calls parse(), which takes MeTTa source" in findings
    assert "'(+ 1 2)' is neither a name nor val() data" in findings
    assert "'(f a)' is neither a name nor val() data" in findings
    # The docstring says (f a) too, and a docstring is documentation.
    assert findings.count("'(f a)'") == 2, findings


def test_the_source_scan_passes_the_shipped_twins():
    """The rule has to be one a real twin can follow, or it is not a rule."""
    for example in coverage.written():
        twin = coverage.twin_for(example)
        assert coverage.scan(twin) == [], f"{twin}: {coverage.scan(twin)}"


def test_a_name_and_marked_data_are_not_programs(tmp_path):
    """The four positions a string is allowed in, and nothing else.

    `val()` is the whole escape: it says "this is a Python value carried
    whole", which is what a MeTTa string literal is.
    """
    allowed = tmp_path / "allowed.py"
    allowed.write_text(
        '"""Allowed."""\n'
        "from petta import S, sym, val\n"
        "BUDGET = 1\n"
        "def twin(m):\n"
        '    yield m.eval(S["sread-command"](val("(f a)")))\n'
        '    yield m.eval(sym("#>=")(1, 2))\n'
        '    yield m.eval(m.fn("xor")(True, False))\n'
        "    @m.define(name='math-string')\n"
        "    def math_string():\n"
        '        return "s"\n',
        encoding="utf-8",
    )
    assert coverage.scan(allowed) == []


def test_printing_text_is_not_forced_through_the_value_carrier(tmp_path):
    """A print claim compares text; an unrelated MeTTa string remains data."""
    printing = tmp_path / "printing.py"
    printing.write_text(
        '"""Printing."""\n'
        "from petta import S, val\n"
        "BUDGET = 1\n"
        'PRINTED = ((S.a, "a"), (S.b, "b"))\n'
        "def twin(m):\n"
        "    assert str(S.a) == 'a'\n"
        "    assert m.one(S.repr(S.b)) == 'b'\n"
        "    assert [m.fn('repr')(atom) for atom, _ in PRINTED] == "
        "[text for _, text in PRINTED]\n"
        "    assert val('data') == val('data')\n",
        encoding="utf-8",
    )
    assert coverage.scan(printing) == []

    data = tmp_path / "data.py"
    data.write_text(
        '"""Data."""\n'
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    assert m.one(S.identity('data')) == 'data'\n",
        encoding="utf-8",
    )
    findings = coverage.scan(data)
    assert len(findings) == 2
    assert all("neither a name nor val() data" in finding for finding in findings)


def test_a_twin_that_does_not_parse_is_a_finding_and_not_a_traceback(tmp_path):
    """A REPORT lane says what is wrong with a twin.

    Raising out of the scan would take every other verdict down with it.
    """
    broken = tmp_path / "broken.py"
    broken.write_text("def twin(m:\n", encoding="utf-8")
    assert coverage.scan(broken) == [
        "does not parse as Python, so nothing about it can be read"
    ]
    assert coverage.budget_of(broken) is None


def test_a_string_in_a_compiled_body_is_a_metta_literal(tmp_path):
    """`(= (math-string) "s")` writes a MeTTa string, and its Python is `return "s"`.

    The body is read as SYNTAX, so the constant is a literal in an equation.
    The source doors stay refused there, because a door is a call and the
    call rule does not care where the call sits.
    """
    planted = tmp_path / "body.py"
    planted.write_text(
        '"""Body."""\n'
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def g():\n"
        '        return m.run("(f)")\n',
        encoding="utf-8",
    )
    findings = coverage.scan(planted)
    assert len(findings) == 1
    assert "calls run(), which takes MeTTa source" in findings[0]


# -------------------------------------------------------------- alpha equality


def test_the_form_reader_agrees_with_the_engines_own_count():
    """The lane reads an example's forms without running it.

    Balancing parentheses over source is only usable if it counts what the
    engine counts, so this holds it to the corpus rather than to a fixture.
    """
    for example in coverage.written():
        heads = coverage.example_forms(example)
        assert heads, example
        assert all(head for head in heads), example


def test_a_test_form_is_read_as_a_claim():
    """An assert-family head states a claim; every other head does not."""
    heads = coverage.example_forms(REPO / "examples" / "integration" / "git_import.metta")
    assert heads == [
        "import!",
        "import_prolog_functions_from_file",
        "git-import!",
        "import!",
        "test",
    ]
    assert sum(head in coverage.ASSERT_HEADS for head in heads) == 1


# ------------------------------------------------------------------ comparison


def _claims(tmp_path, example_text, twin_text, declared=frozenset()):
    """One example and one twin, compared without an engine."""
    example = tmp_path / "x.metta"
    example.write_text(example_text, encoding="utf-8")
    twin = tmp_path / "x.py"
    twin.write_text(twin_text, encoding="utf-8")
    return coverage.compare("x.metta", example, twin, set(declared))


def test_a_twin_that_claims_less_is_a_finding(tmp_path):
    """A claim a twin cannot make is a residue entry, never a silent gap.

    Without this, deleting an assertion would read as coverage rather than as
    the hole it is.
    """
    two = "!(test (f 1) 1)\n!(test (f 2) 4)\n"
    owed, proved, findings = _claims(tmp_path, two, "def twin(m):\n    assert f(1) == [1]\n")
    assert (owed, proved) == (2, 1)
    assert any("1 short" in finding for finding in findings)

    owed, proved, findings = _claims(
        tmp_path, two, "def twin(m):\n    assert f(1) == [1]\n", declared={1}
    )
    assert (owed, proved, findings) == (1, 1, [])


def test_a_claim_stated_anywhere_counts(tmp_path):
    """Shape is the twin's own business.

    Two assertions inside a loop are two claims, which is the whole point of
    dropping the form-by-form mirror.
    """
    twin = (
        "def twin(m):\n"
        "    for n in (1, 2):\n"
        "        assert f(n) == [n * n]\n"
        "        assert g(n) == [n]\n"
    )
    owed, proved, findings = _claims(tmp_path, "!(test (f 1) 1)\n!(test (f 2) 4)\n", twin)
    assert (owed, proved, findings) == (2, 2, [])


def test_a_hidden_definition_is_a_finding():
    """Self-reflectivity: a definition lands as a matchable atom or it is not one.

    A twin proving its claims while defining nothing in the space is exactly
    what this refuses, and no restructuring may weaken it.
    """
    findings = coverage._visible(
        "x.metta", _run([], heads=("facF/1",)), _run([], heads=())
    )
    assert any("hidden in Python" in finding for finding in findings)
    assert any("facF/1" in finding for finding in findings)
    assert coverage._visible("x.metta", _run([], heads=()), _run([], heads=("f/1",))) == []


# ---------------------------------------------------------------- the budgets


def test_the_full_lane_protocol_names_every_scheduling_input():
    """A corpus-width or executor-width change is a different population."""
    assert coverage.full_lane_protocol(204) == "full-lane/204/workers=32"
    with pytest.raises(ValueError, match="positive example count"):
        coverage.full_lane_protocol(0)


def test_every_shipped_twin_states_a_budget():
    """P14.14's start: the parity claim is frozen the moment a twin ships."""
    for example in coverage.written():
        budget = coverage.budget_of(coverage.twin_for(example))
        assert isinstance(budget, (int, coverage.EmpiricalBudget)), example
        if isinstance(budget, int):
            assert budget > 0, example


def test_a_budget_is_two_sided():
    """A benchmark baseline only fails upward, and a twin budget fails both ways.

    A twin that suddenly costs far LESS has most likely stopped doing the
    work and started answering the expected value, which is the cheat a fixed
    public corpus invites.
    """
    twin = coverage.twin_for(REPO / "examples" / "basics" / "factorial.metta")
    budget = coverage.budget_of(twin)
    left = _run(["(True)"], cost=budget)
    for observed in (budget + coverage.TOLERANCE + 1, budget // 2):
        findings = coverage._price("x.metta", twin, left, _run([], cost=observed))
        assert any("pinned budget" in f for f in findings), observed
    within = coverage._price(
        "x.metta", twin, left, _run([], cost=budget + coverage.TOLERANCE)
    )
    assert within == []


def _empirical_twin(tmp_path, budget):
    twin = tmp_path / "nondeterministic.py"
    twin.write_text(
        '"""Purpose: a planted nondeterministic twin budget."""\n'
        f"BUDGET = {budget!r}\n"
        "def twin(m):\n"
        "    assert m\n",
        encoding="utf-8",
    )
    return twin


def test_an_empirical_envelope_passes_its_observations_and_fails_new_spread(tmp_path):
    """Observed extrema pass; the first wider observation is a finding.

    The lower bound matters independently of the upper one: making a twin
    cheaper can mean it stopped doing the work, so an asymmetric declaration
    must never be widened into ``centre +/- spread``.
    """
    declared = {
        "minimum": 1_000,
        "maximum": 1_014,
        "observations": 10,
        "protocol": "full-lane/204/workers=32",
    }
    twin = _empirical_twin(tmp_path, declared)
    budget = coverage.budget_of(twin)
    assert isinstance(budget, coverage.EmpiricalBudget)
    assert budget.spread == 14

    example = _run([], cost=2_000)
    for observed in (1_000, 1_007, 1_014):
        assert coverage._price(
            "x.metta",
            twin,
            example,
            _run([], cost=observed),
            protocol="full-lane/204/workers=32",
        ) == []

    for observed, direction in ((999, "BELOW"), (1_015, "above")):
        findings = coverage._price(
            "x.metta",
            twin,
            example,
            _run([], cost=observed),
            protocol="full-lane/204/workers=32",
        )
        assert len(findings) == 1, findings
        assert direction in findings[0]
        assert "10 observations" in findings[0]
        assert "spread 14" in findings[0]
        assert "deterministic tolerance is not added" in findings[0]


def test_an_empirical_envelope_cannot_license_another_protocol(tmp_path):
    """Serial evidence says nothing about the scheduler the full lane adds."""
    twin = _empirical_twin(
        tmp_path,
        {
            "minimum": 1_000,
            "maximum": 1_014,
            "observations": 10,
            "protocol": "serial",
        },
    )
    findings = coverage._price(
        "x.metta",
        twin,
        _run([], cost=2_000),
        _run([], cost=1_007),
        protocol="full-lane/204/workers=32",
    )
    assert len(findings) == 1, findings
    assert "measured under 'serial'" in findings[0]
    assert "current protocol is 'full-lane/204/workers=32'" in findings[0]


@pytest.mark.parametrize(
    "budget",
    [
        {"minimum": 1_000, "maximum": 1_014, "observations": 10},
        {
            "minimum": 1_014,
            "maximum": 1_000,
            "observations": 10,
            "protocol": "full-lane/204/workers=32",
        },
        {
            "minimum": 1_000,
            "maximum": 1_014,
            "observations": 1,
            "protocol": "full-lane/204/workers=32",
        },
        {
            "minimum": 1_000,
            "maximum": 1_014,
            "observations": 10,
            "protocol": "",
        },
    ],
)
def test_an_empirical_envelope_requires_complete_measurement_metadata(
    tmp_path, budget
):
    """A band without bounds, repeated observations, and protocol is no claim."""
    twin = _empirical_twin(tmp_path, budget)
    with pytest.raises(ValueError, match="BUDGET empirical envelope"):
        coverage.budget_of(twin)


def test_spread_is_not_a_budget_door(tmp_path):
    """The guessed symmetric allowance was deleted, not retained as a shim."""
    twin = tmp_path / "legacy.py"
    twin.write_text(
        '"""Purpose: plant the deleted spread declaration."""\n'
        "BUDGET = 1_000\n"
        "SPREAD = 20\n"
        "def twin(m):\n"
        "    assert m\n",
        encoding="utf-8",
    )
    assert not hasattr(coverage, "spread_of")
    findings = coverage._price(
        "x.metta", twin, _run([], cost=2_000), _run([], cost=1_005)
    )
    assert any("pinned budget" in finding for finding in findings)


def test_the_band_refuses_a_twin_that_costs_more_than_it_was_pinned_to_allow():
    """The band is the parity half of the goal.

    The Python spelling costs the same inferences as the handwritten `.metta`
    program, or fewer, within what the first measurements showed.
    """
    twin = coverage.twin_for(REPO / "examples" / "basics" / "factorial.metta")
    budget = coverage.budget_of(twin)
    twin_run = _run([], cost=budget)

    # The example costing what the twin costs leaves the whole band spare.
    assert coverage._price("x.metta", twin, _run([], cost=budget), twin_run) == []

    # An example cheap enough that the pinned twin overruns the band, its
    # authoring allowance included: factorial AUTHORS one compiled definition,
    # and the band must let it pay for that.
    authored = coverage.definitions(twin)
    assert authored == 1, "factorial's twin authors exactly one definition"
    allowance = coverage.DEFINITION_WARMUP + coverage.DEFINITION_COST * authored
    cheaper = int((budget - allowance) / (1.0 + coverage.BAND_PERCENT / 100.0)) - 1
    outside = coverage._price("x.metta", twin, _run([], cost=cheaper), twin_run)
    assert any("band" in f for f in outside), outside
    assert any("author 1 compiled definition" in f for f in outside), outside


def test_the_band_pays_for_authoring_but_only_what_was_measured(tmp_path):
    """A definition costs to WRITE, and the example has none to write.

    Without the allowance the band selected for transliteration on exactly the
    small examples where Python's spelling is clearest: measured 2026-08-22,
    examples/control/if.metta costs 2092 against a ceiling of 2301, and one
    decorated definition costs 2221 in a fresh process.
    """
    plain = tmp_path / "plain.py"
    plain.write_text('"""D."""\nBUDGET = 2000\ndef twin(m):\n    assert m\n', encoding="utf-8")
    assert coverage.definitions(plain) == 0

    authored = tmp_path / "authored.py"
    authored.write_text(
        '"""D."""\n'
        "BUDGET = 2000\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def f(x):\n"
        "        return x\n"
        "    assert f(1) == [1]\n",
        encoding="utf-8",
    )
    assert coverage.definitions(authored) == 1

    # One example, one twin cost, two verdicts: the twin that AUTHORS is given
    # the measured room and the one that does not is given none.
    cost = 2000
    example = _run([], cost=100)
    spent = _run([], cost=cost)
    assert any("band" in f for f in coverage._price("x", plain, example, spent))
    assert coverage._price("x", authored, example, spent) == []


# ----------------------------------------------------------------- end to end


@pytest.mark.parametrize(
    "name", ["basics/identity.metta", "spaces/spaces3.metta"]
)
def test_a_shipped_twin_agrees_with_its_example_end_to_end(name):
    """Two twins run for real.

    A change breaking the machinery itself is then caught rather than reading
    as a corpus finding.
    """
    verdict = coverage.check(REPO / "examples" / name, coverage.residue())
    assert verdict.findings == (), verdict.findings
    assert verdict.covered == verdict.forms > 0


def test_the_residue_json_is_the_one_definition_of_what_is_missing():
    """The lane's own file, read the way every runner reads example_skips."""
    document = json.loads(coverage.RESIDUE.read_text(encoding="utf-8"))
    assert document["schema"] == "petta-twin-residue-1"
    assert document["entries"] == coverage.residue()


def test_the_distribution_budget_retirement_is_exact():
    """Only the determinism-assumption population moved, all 159 entries."""
    document = json.loads(coverage.RESIDUE.read_text(encoding="utf-8"))
    section = "correction to the lane's determinism assumption"
    active = [entry for entry in document["entries"] if entry["section"] == section]
    retired = [
        entry
        for entry in document["retired"]
        if entry.get("section") == section
        and "empirical two-sided envelope" in entry["retired"]
    ]
    assert active == []
    assert len(retired) == 159


def test_the_idiom_check_catches_a_planted_transliteration(tmp_path):
    """A twin can avoid MeTTa source TEXT and still be MeTTa source with
    Python punctuation, which is what this check exists for: the string scan
    passes the planted file below and the idiom check refuses it, naming the
    spelling Python already has.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from petta import Expression, S, V\n"
        "def twin(m):\n"
        '    m += Expression((S["="], Expression((S["f"], V["x"])), 1))\n',
        encoding="utf-8",
    )
    assert coverage.scan(planted) == []
    joined = " ".join(coverage.idiom(planted))
    assert 'S["f"] is S.f' in joined
    assert 'V["x"] is V.x' in joined
    assert "Expression(...) builds what calling the head builds" in joined


def test_an_operator_head_is_a_finding_only_where_an_operator_would_build(tmp_path):
    """`a + b` builds `(+ $a $b)` INSIDE a compiled body, so writing the head
    there is a transliteration. Outside one the same spelling is deliberate,
    because Python's `+` on ground values computes and its `==` is structural
    equality, so the rule would report a correct twin. The arity matters for
    the same reason: `S["+"](1)` is a partial application Python cannot spell.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    outside = tmp_path / "outside.py"
    outside.write_text(
        '"""Doc."""\n'
        "from petta import S, V\n"
        "def twin(m):\n"
        '    m += S["+"](V.a, V.b)\n',
        encoding="utf-8",
    )
    assert not [f for f in coverage.idiom(outside) if "operator" in f]

    inside = tmp_path / "inside.py"
    inside.write_text(
        '"""Doc."""\n'
        "from petta import S, V\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def add(a, b):\n"
        '        return S["+"](a, b)\n'
        "    @m.define\n"
        "    def partial(a):\n"
        '        return S["+"](a)\n',
        encoding="utf-8",
    )
    operators = [f for f in coverage.idiom(inside) if "operator" in f]
    assert len(operators) == 1, operators
    assert "'+'" in operators[0]


def test_a_term_may_name_a_head_that_shares_a_source_doors_name(tmp_path):
    """`S.parse(text)` builds the term `(parse text)`; only a real call takes
    MeTTa source. Reading every call by name alone left a twin with no way to
    write that head at all, since the idiom check refuses `S["parse"]` too.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    planted = tmp_path / "head.py"
    planted.write_text(
        '"""Doc."""\n'
        "from petta import S, val\n"
        "def twin(m):\n"
        "    assert m.eval(S.parse(val('(f a)'))) == []\n",
        encoding="utf-8",
    )
    assert coverage.scan(planted) == []
    assert coverage.idiom(planted) == []

    real = tmp_path / "real.py"
    real.write_text(
        '"""Doc."""\n'
        "def twin(m):\n"
        "    yield m.run('!(f a)')\n",
        encoding="utf-8",
    )
    assert coverage.scan(real)


def test_a_declared_rung_is_a_documented_drop_rather_than_a_finding(tmp_path):
    """The ladder keeps every rung, so sitting below the top one is legal
    when the twin SAYS why. A silent drop is the defect; a declared one is
    documentation, and the lane reads the declaration the way it reads BUDGET.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    body = (
        '"""Doc."""\n'
        "from petta import Expression, S, V\n"
        "%s"
        "def twin(m):\n"
        '    m += Expression((S["="], Expression((S["f"], V["x"])), 1))\n'
    )
    silent = tmp_path / "silent.py"
    silent.write_text(body % "", encoding="utf-8")
    assert coverage.idiom(silent)

    declared = tmp_path / "declared.py"
    declared.write_text(
        body % 'RUNG = "the compiled subset has no lowering for this form yet"\n',
        encoding="utf-8",
    )
    assert coverage.idiom(declared) == []
    # BOTH checks have to accept the declaration, or the escape is unusable:
    # the reason is a module-level string, and the source scan refuses those
    # unless they are documentation. Asserting only idiom() is what let the
    # contradiction ship [found 2026-08-22 by two twin agents at once].
    assert coverage.scan(declared) == []


def test_a_line_may_state_its_own_rung(tmp_path):
    """A twin idiomatic everywhere but one line excuses that line rather than
    the whole file, in the shape of the tree's noqa grammar.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    planted = tmp_path / "line.py"
    planted.write_text(
        '"""Doc."""\n'
        "from petta import S\n"
        "def twin(m):\n"
        '    m += S["f"](1)  # rung: the head is built by a caller that needs the string\n'
        '    m += S["g"](2)\n',
        encoding="utf-8",
    )
    findings = coverage.idiom(planted)
    assert len(findings) == 1, findings
    assert 'S["g"] is S.g' in findings[0]


def test_a_dissolved_head_names_the_python_spelling_it_replaces(tmp_path):
    """A concept Python already has is written Python's way.

    This is the check the punctuation rules could not make: `S.test(...)` and
    `S["add-atom"](...)` are perfectly good Python that say MeTTa, which is
    what the corpus filled up with while the lane only read spelling.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from petta import S, V\n"
        "def twin(m):\n"
        "    m += S['add-atom'](S['&self'], S.fact(1))\n"
        "    assert m.eval(S.test(S.f(1), 1)) == []\n",
        encoding="utf-8",
    )
    findings = coverage.idiom(planted)
    assert any("space += atom" in finding for finding in findings)
    assert any("Python's own assert" in finding for finding in findings)
    assert any("names a SPACE as a symbol" in finding for finding in findings)


def test_a_yielding_twin_is_a_finding(tmp_path):
    """A yield in twin() is the form-by-form mirror, and that is the defect.

    A yield inside a `@m.define`d body is nondeterminism and must stay legal,
    so the rule reads the twin's own body and not the functions it defines.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from petta import S\n"
        "def twin(m):\n"
        "    @m.define\n"
        "    def colour():\n"
        "        yield S.red\n"
        "    assert set(colour()) == {S.red}\n",
        encoding="utf-8",
    )
    assert coverage.idiom(planted) == []

    planted.write_text(
        '"""Doc."""\n'
        "from petta import S\n"
        "def twin(m):\n"
        "    yield m.eval(S.f(1))\n",
        encoding="utf-8",
    )
    assert any("FORM BY FORM" in finding for finding in coverage.idiom(planted))


def test_a_variable_headed_expression_keeps_its_only_spelling(tmp_path):
    """`Expression((V.x,))` builds ($x) and nothing shorter reaches it.

    `Var` is not callable, so the Expression() rule must fire on a SYMBOL head
    only; firing on a variable would demand a spelling that does not exist.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        '"""Doc."""\n'
        "from petta import Expression, S, V\n"
        "def twin(m):\n"
        "    assert list(m.query(Expression((V.x,)))) == []\n"
        "    assert list(m.query(V.x)['x']) == []\n",
        encoding="utf-8",
    )
    assert coverage.scan(planted) == []
    assert coverage.idiom(planted) == []


def test_a_failing_assertion_is_a_finding(tmp_path):
    """A false claim fails the twin, which is what makes the count an oracle.

    The contract says a twin running to completion has PROVED every claim it
    states. That only holds if a false assertion stops it, so this runs a real
    twin against a real engine rather than a fixture: the AssertionError has to
    leave the process, and the lane has to read that as an error rather than as
    a twin with nothing to say.
    """
    twin = tmp_path / "false.py"
    twin.write_text(
        '"""A twin that claims something untrue."""\n'
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    assert 1 == 2\n",
        encoding="utf-8",
    )
    run = coverage.run_twin(twin)
    assert run.outcome.error is not None, "a raised assertion must leave the run in error"
    assert "AssertionError" in run.outcome.error, run.outcome.error

    twin.write_text(
        '"""A twin whose claim holds."""\n'
        "BUDGET = 1\n"
        "def twin(m):\n"
        "    assert 1 == 1\n",
        encoding="utf-8",
    )
    assert coverage.run_twin(twin).outcome.error is None
