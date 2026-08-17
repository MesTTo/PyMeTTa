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

import collections
import pickle

import pytest

from petta import Expr, S
from petta.lint import Finding


@pytest.fixture()
def m(metta):
    with metta.new_space() as space:
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
    with metta.new_space() as defining, metta.new_space() as declaring:
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


# The heads the translator compiles instead of equations defining them. Most
# answer false to fun/1, so asking fun/1 alone reported every one of them as
# an undefined reference; `if` is the one that made the check unusable, since
# an equation branching on it is the commonest shape in the language.
SPECIAL_FORM_BODIES = [
    "(if (> $x 0) yes no)",
    "(case $x ((1 one) ($other other)))",
    "(collapse (superpose ($x $x)))",
    "(unify $x 1 yes no)",
    "(chain $x $y $y)",
    "(once (superpose ($x)))",
    "(quote $x)",
    "(catch $x error handled)",
    # The stream rewrites are the translator's other compilation route, and
    # they answer False to fun/1 too.
    "(trace! $x $x)",
    "(unique (superpose ($x $x)))",
    "(union (superpose ($x)) (superpose ($x)))",
]


@pytest.mark.parametrize("body", SPECIAL_FORM_BODIES)
def test_calling_a_special_form_is_not_an_undefined_reference(m, body):
    m.run(f"(= (special-caller $x) {body})")
    assert "possibly-undefined-reference" not in _kinds(m.lint())


def test_a_special_form_is_a_known_head(m):
    from petta._lint_model import EngineRegistry

    registry = EngineRegistry(m.runtime)
    assert registry.is_function("if") is False
    assert registry.is_special_form("if") is True
    # And the query does not weaken the check it guards: a genuinely unknown
    # head is still unknown.
    assert registry.is_special_form("no-such-fn") is False


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
        "(= (cached-brancher $x) (if (if $x a b) (cached-target $x) $x))"
    )
    runtime_type = type(m.runtime)
    original = runtime_type.once
    queries = collections.defaultdict(list)

    def counted(runtime, goal, **bindings):
        name = bindings.get("F")
        if name in ("cached-target", "if"):
            queries[name].append(goal)
        return original(runtime, goal, **bindings)

    monkeypatch.setattr(runtime_type, "once", counted)
    assert m.lint() == []
    target = queries["cached-target"]
    assert len([goal for goal in target if "fun(F)" in goal]) == 1
    assert [goal for goal in target if "findall" in goal] == [
        "findall(_A, arity(F, _A), L)"
    ]
    # `if` appears three times across two equations and is asked once for
    # each of the two questions the registry answers about a head.
    branch = queries["if"]
    assert len([goal for goal in branch if "fun(F)" in goal]) == 1
    assert len([goal for goal in branch if "metta_translated_head(F)" in goal]) == 1


def test_lint_walks_deep_expression_trees_iteratively(m):
    body = S.leaf
    for _ in range(2_000):
        body = Expr([S.nested, body])
    m.add(Expr([S["="], Expr([S.deep_lint]), body]))
    findings = m.lint()
    assert any(finding.subject == "nested" for finding in findings)


def test_a_declaration_that_cannot_type_its_function(m):
    # The engine refuses this in a source file, over that source's own forms.
    # What reaches the linter is the route that builds one atom at a time,
    # where refusing would refuse a program that is about to add its arrow.
    m.run("(= (bare-fn $x) (+ $x 1))")
    m.add(Expr([S[":"], S["bare-fn"], S.Number]))
    findings = m.lint()
    assert "declaration-types-the-symbol" in _kinds(findings)
    detail = next(
        finding.detail for finding in findings
        if finding.kind == "declaration-types-the-symbol"
    )
    assert "(bare-fn ...) compiles unchecked" in detail


def test_one_arrow_among_several_declarations_satisfies_the_linter(m):
    m.run("(: paired-fn (-> Number Number)) (= (paired-fn $x) (+ $x 1))")
    m.add(Expr([S[":"], S["paired-fn"], S.Number]))
    assert "declaration-types-the-symbol" not in _kinds(m.lint())


def test_an_explicitly_undefined_type_is_not_a_finding(m):
    m.run("(: opted-out %Undefined%) (= (opted-out $x) $x)")
    assert "declaration-types-the-symbol" not in _kinds(m.lint())


def test_a_declaration_for_a_name_with_no_equations_is_data(m):
    # NARS writes inheritance as (--> $a $b). It is an atom in a data
    # position, not a mistyped arrow, and nothing defines the subject.
    m.run("(: nars-belief (--> Cat Animal))")
    assert "declaration-types-the-symbol" not in _kinds(m.lint())


def test_a_positional_read_of_a_tabled_functions_answers(m):
    """Tabling preserves the answer SET and not its order: lib_tabling.pl's
    header measures a (collapse (pick a)) flipping from (one two) to
    (two one) when three facts nothing calls were added to another file. A
    program that reads such a collapse by position works until something
    unrelated moves."""
    m.run("!(import! &self (library lib_tabling))")
    m.run("(= (tbl-pick a) one)\n(= (tbl-pick a) two)")
    m.run("(= (tbl-first) (car-atom (collapse (tbl-pick a))))")
    m.run("!(tabled (tbl-pick $x))")
    findings = m.lint()
    assert "tabled-answer-order-read" in _kinds(findings)
    finding = next(
        f for f in findings if f.kind == "tabled-answer-order-read"
    )
    assert finding.subject == "tbl-pick"
    assert "sort-atom" in finding.detail


def test_a_canonicalised_read_of_a_tabled_function_is_not_a_finding(m):
    m.run("!(import! &self (library lib_tabling))")
    m.run("(= (tbl-safe a) one)\n(= (tbl-safe a) two)")
    m.run("(= (tbl-safe-first) (car-atom (sort-atom (collapse (tbl-safe a)))))")
    m.run("!(tabled (tbl-safe $x))")
    assert "tabled-answer-order-read" not in _kinds(m.lint())


def test_a_positional_read_of_an_untabled_function_is_not_a_finding(m):
    m.run("(= (untbl-pick a) one)\n(= (untbl-pick a) two)")
    m.run("(= (untbl-first) (car-atom (collapse (untbl-pick a))))")
    assert "tabled-answer-order-read" not in _kinds(m.lint())
