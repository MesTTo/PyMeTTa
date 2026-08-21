"""Purpose: prove the twin coverage lane catches what it claims to catch.

A lane that cannot be shown failing is evidence of nothing, so these plant a
source-text cheat, a renamed variable, a wrong answer, a hidden definition
and an undeclared skip, and require the lane to answer correctly about each.

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


def test_a_renamed_variable_still_agrees():
    """`=alpha` is the law's own relation.

    Two sides numbering a fresh variable differently answered the same thing.
    """
    assert coverage.agree("((f $x))", "((f $y))")
    assert coverage.agree("((f $x $x))", "((f $a $a))")
    assert coverage.agree("(True)", "(true)"), "a spelling is not an answer"


def test_a_wrong_answer_is_still_refused():
    """Renaming is not licence.

    A different SHAPE is a different answer, and so is a variable used twice
    where the other side used two.
    """
    assert not coverage.agree("((f $x))", "((g $x))")
    assert not coverage.agree("((f $x $x))", "((f $a $b))")
    assert not coverage.agree("(1 2)", "(1 3)")
    assert not coverage.agree("(1 2)", "(1)")


# ------------------------------------------------------------------ comparison


def test_an_undeclared_skip_is_a_finding():
    """A twin declining a form is honest only when the residue table says so.

    Otherwise "covered" quietly means "skipped".
    """
    left, right = _run(["(True)", "(2)"]), _run(["(True)", coverage.DECLINED])
    covered, findings = coverage.compare("x.metta", left, right, set())
    assert covered == 1
    assert any("declared by no residue entry" in f for f in findings)

    covered, findings = coverage.compare("x.metta", left, right, {1})
    assert (covered, findings) == (1, [])


def test_a_hidden_definition_is_a_finding():
    """Self-reflectivity: a definition lands as a matchable atom or it is not one.

    A twin answering right while defining nothing is exactly what this
    refuses.
    """
    left = _run(["(True)"], heads=("facF/1",))
    right = _run(["(True)"], heads=())
    covered, findings = coverage.compare("x.metta", left, right, set())
    assert covered == 1
    assert any("hidden in Python" in f for f in findings)
    assert any("facF/1" in f for f in findings)


def test_a_twin_answering_a_different_number_of_forms_is_a_finding():
    """Group counts align the comparison.

    Misaligned, every later form would be compared against the wrong original.
    """
    covered, findings = coverage.compare(
        "x.metta", _run(["(1)", "(2)"]), _run(["(1)"]), set()
    )
    assert covered == 0
    assert any("answered 1 forms, the example 2" in f for f in findings)


# ---------------------------------------------------------------- the budgets


def test_every_shipped_twin_states_a_budget():
    """P14.14's start: the parity claim is frozen the moment a twin ships."""
    for example in coverage.written():
        budget = coverage.budget_of(coverage.twin_for(example))
        assert isinstance(budget, int) and budget > 0, example


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

    # An example cheap enough that the pinned twin overruns the band.
    cheaper = int(budget / (1.0 + coverage.BAND_PERCENT / 100.0)) - 1
    outside = coverage._price("x.metta", twin, _run([], cost=cheaper), twin_run)
    assert any("band" in f for f in outside), outside


# ----------------------------------------------------------------- end to end


@pytest.mark.parametrize(
    "name", ["basics/factorial.metta", "basics/relational_arithmetic.metta"]
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
