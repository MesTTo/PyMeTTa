"""Purpose: lint() catches the silently-wrong class MeTTa fails open on:
declarations nothing defines, arrow arity against equation arity, calls
with the wrong argument count, body variables the head never bound,
alpha-equivalent duplicate equations, and heads no function or fact
carries. A healthy space answers no findings.
Guarantees:
  - public finding records survive pickle through petta.lint [tested
    test_finding_retains_public_pickle_identity]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pickle

import pytest

from petta import Expr, S
from petta.lint import Finding


@pytest.fixture()
def m(metta):
    with metta.fresh_space() as space:
        yield space


def _kinds(findings):
    return [finding.kind for finding in findings]


def test_finding_retains_public_pickle_identity():
    finding = Finding("kind", "subject", "detail", S.evidence)
    assert pickle.loads(pickle.dumps(finding)) == finding
    assert Finding.__module__ == "petta.lint"


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


def test_definition_in_another_space_does_not_satisfy_a_local_declaration(metta):
    with metta.fresh_space() as defining, metta.fresh_space() as declaring:
        defining.run("(= (cross-space-only $x) $x)")
        declaring.run("(: cross-space-only (-> Number Number))")

        assert declaring.is_function("cross-space-only") is True
        assert declaring.is_function_here("cross-space-only") is False
        findings = declaring.lint()
        assert _kinds(findings) == ["declared-but-undefined"]
        assert findings[0].subject == "cross-space-only"


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


def test_variable_arguments_do_not_hide_undefined_references(m):
    m.run("(= (variable-caller $x) (no-variable-fn $x))")
    findings = m.lint()
    assert _kinds(findings) == ["possibly-undefined-reference"]
    assert findings[0].subject == "no-variable-fn"


def test_each_extra_duplicate_equation_is_reported(m):
    for variable in ("x", "y", "z"):
        m.run(f"(= (three-copies ${variable}) (+ ${variable} 1))")
    duplicates = [
        finding for finding in m.lint()
        if finding.kind == "duplicate-equation"
    ]
    assert len(duplicates) == 2


def test_registry_queries_are_native_and_cached_per_name(m, monkeypatch):
    m.run(
        "(= (cached-target $x) $x)"
        "(= (cached-caller $x) (and (cached-target $x) (cached-target $x)))"
    )
    runtime_type = type(m.runtime)
    original = runtime_type.once
    queries = []

    def counted(runtime, goal, **bindings):
        if bindings.get("F") == "cached-target":
            queries.append(goal)
        return original(runtime, goal, **bindings)

    monkeypatch.setattr(runtime_type, "once", counted)
    assert m.lint() == []
    assert len([goal for goal in queries if "fun(F)" in goal]) == 1
    arity_queries = [goal for goal in queries if "findall" in goal]
    assert arity_queries == ["findall(_A, arity(F, _A), L)"]


def test_lint_walks_deep_expression_trees_iteratively(m):
    body = S.leaf
    for _ in range(2_000):
        body = Expr([S.nested, body])
    m.add(Expr([S["="], Expr([S.deep_lint]), body]))
    findings = m.lint()
    assert any(finding.subject == "nested" for finding in findings)
