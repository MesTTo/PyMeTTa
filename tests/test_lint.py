"""Purpose: lint() catches the silently-wrong class MeTTa fails open on:
declarations nothing defines, arrow arity against equation arity, calls
with the wrong argument count, body variables the head never bound,
alpha-equivalent duplicate equations, and heads no function or fact
carries. A healthy space answers no findings.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


def _kinds(findings):
    return [finding.kind for finding in findings]


def test_a_healthy_space_answers_no_findings(m):
    m.run(
        "(: well-fn (-> Number Number))"
        "(= (well-fn $x) (+ $x 1))"
        "(= (well-caller) (well-fn 41))"
        "(stored fact)"
    )
    assert m.lint() == []


def test_declared_but_undefined(m):
    m.run("(: ghost-fn (-> Number Number))")
    findings = m.lint()
    assert _kinds(findings) == ["declared-but-undefined"]
    assert findings[0].subject == "ghost-fn"


def test_arrow_arity_against_equations(m):
    m.run("(: two-face (-> Number Number Number)) (= (two-face $x) $x)")
    findings = m.lint()
    assert "arrow-arity-mismatch" in _kinds(findings)


def test_calls_with_the_wrong_argument_count(m):
    m.run("(= (one-arg $x) $x) (= (bad-caller) (one-arg 1 2))")
    findings = m.lint()
    assert "arity-mismatch" in _kinds(findings)
    assert any(finding.subject == "one-arg" for finding in findings)


def test_unbound_body_variables(m):
    m.run("(= (loose-fn) (+ 1 $nowhere))")
    findings = m.lint()
    assert "unbound-variable" in _kinds(findings)
    detail = next(
        finding.detail for finding in findings
        if finding.kind == "unbound-variable"
    )
    # The engine renames stored variables, so the author's spelling is
    # gone; the finding says so instead of inventing a name.
    assert "variable" in detail and "not in the head" in detail


def test_let_bound_variables_are_not_flagged(m):
    m.run("(= (let-fn) (let $fresh 41 (+ $fresh 1)))")
    assert "unbound-variable" not in _kinds(m.lint())


def test_duplicate_equations(m):
    m.run("(= (twice-fn $x) (+ $x 1))")
    m.run("(= (twice-fn $y) (+ $y 1))")
    findings = m.lint()
    assert "duplicate-equation" in _kinds(findings)


def test_possibly_undefined_reference_is_labeled_a_heuristic(m):
    m.run("(= (typo-caller) (no-such-fn 1))")
    findings = m.lint()
    assert _kinds(findings) == ["possibly-undefined-reference"]
    assert "heuristic" in findings[0].detail
