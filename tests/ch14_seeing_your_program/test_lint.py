"""Purpose: lint() catches the silently-wrong class MeTTa fails open on:
declarations nothing defines, arrow arity against equation arity, calls
with the wrong argument count, body variables the head never bound,
alpha-equivalent duplicate equations, and heads no function or fact
carries. A healthy space answers no findings.
Guarantees:
  - public finding records survive pickle through metta.lint [tested
    test_finding_retains_public_pickle_identity]
  - duplicate-binder covers clause-scoped names across plain ``let`` forms,
    retains all three nested and sibling ``let*`` shapes, and leaves distinct
    binders' ``Pair`` answer unchanged [tested:
    test_plain_let_duplicate_binders_are_reported_across_one_clause,
    test_plain_let_duplicates_inside_binding_values_are_reported,
    test_let_star_duplicate_binder_controls_keep_reporting,
    test_distinct_plain_let_binders_are_clean_and_keep_their_pair_answer;
    commit=43bf074ce97adb6bfe599ae20faa5f38ef524bd7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import collections
import pickle

import pytest

from metta import Expression, MettaError, S
from metta.lint import Finding, lint


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


def _kinds(findings):
    return [finding.kind for finding in findings]


def test_finding_retains_public_pickle_identity():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    finding = Finding("kind", "subject", "detail", S.evidence)
    assert pickle.loads(pickle.dumps(finding)) == finding
    assert Finding.__module__ == "metta.lint"


def test_a_healthy_space_answers_no_findings(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run(
        "(: well-fn (-> Number Number))"
        "(= (well-fn $x) (+ $x 1))"
        "(= (well-caller) (well-fn 41))"
        "(Stored fact)"
    )
    assert m.lint() == []


def test_declared_but_undefined(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(: ghost-fn (-> Number Number))")
    findings = m.lint()
    assert _kinds(findings) == ["declared-but-undefined"]
    assert findings[0].subject == "ghost-fn"


def test_definition_in_another_space_does_not_satisfy_a_local_declaration(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as defining, metta._new_space() as declaring:
        defining.run("(= (cross-space-only $x) $x)")
        declaring.run("(: cross-space-only (-> Number Number))")

        assert declaring.is_function("cross-space-only") is True
        assert declaring.is_function_here("cross-space-only") is False
        findings = declaring.lint()
        assert _kinds(findings) == ["declared-but-undefined"]
        assert findings[0].subject == "cross-space-only"


def test_arrow_arity_against_equations(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(: two-face (-> Number Number Number)) (= (two-face $x) $x)")
    findings = m.lint()
    assert "arrow-arity-mismatch" in _kinds(findings)


def test_calls_with_the_wrong_argument_count(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (one-arg $x) $x) (= (bad-caller) (one-arg 1 2))")
    findings = m.lint()
    assert "arity-mismatch" in _kinds(findings)
    assert any(finding.subject == "one-arg" for finding in findings)


def test_unbound_body_variables(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_let_bound_variables_are_not_flagged(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (let-fn) (let $fresh 41 (+ $fresh 1)))")
    assert "unbound-variable" not in _kinds(m.lint())


def test_duplicate_equations(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (twice-fn $x) (+ $x 1))")
    m.run("(= (twice-fn $y) (+ $y 1))")
    findings = m.lint()
    assert "duplicate-equation" in _kinds(findings)


def test_a_semantically_redundant_equation_is_reported_with_its_bound(m):
    """Plotkin's reduction step, bounded to pairwise instance subsumption.

    (= (redun-fn a) (wrap a)) is an instance of (= (redun-fn $x) (wrap $x)):
    every answer the instance gives, the general equation gives identically,
    so calls on the overlap answer twice. The near-twin pair differs in a
    constant on both sides, is NOT redundant, and must not be flagged.
    """
    m.run("(= (redun-fn $x) (wrap $x))")
    m.run("(= (redun-fn a) (wrap a))")
    m.run("(= (near-fn a) (wrap a))")
    m.run("(= (near-fn b) (wrap b))")
    findings = [f for f in m.lint() if f.kind == "subsumed-equation"]
    assert len(findings) == 1
    assert findings[0].subject == "(redun-fn a)"
    assert findings[0].severity == "information"
    assert "pairwise" in findings[0].detail


def test_possibly_undefined_reference_is_labeled_a_heuristic(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (typo-caller) (no-such-fn 1))")
    findings = m.lint()
    assert _kinds(findings) == ["possibly-undefined-reference"]
    assert "heuristic" in findings[0].detail


def test_variable_arguments_do_not_hide_undefined_references(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
def test_calling_a_special_form_is_not_an_undefined_reference(m, body):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run(f"(= (special-caller $x) {body})")
    assert "possibly-undefined-reference" not in _kinds(m.lint())


def test_a_special_form_is_a_known_head(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta._lint_model import EngineRegistry

    registry = EngineRegistry(m.runtime)
    assert registry.is_function("if") is False
    assert registry.is_special_form("if") is True
    # And the query does not weaken the check it guards: a genuinely unknown
    # head is still unknown.
    assert registry.is_special_form("no-such-fn") is False


def test_each_extra_duplicate_equation_is_reported(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    for variable in ("x", "y", "z"):
        m.run(f"(= (three-copies ${variable}) (+ ${variable} 1))")
    duplicates = [
        finding for finding in m.lint()
        if finding.kind == "duplicate-equation"
    ]
    assert len(duplicates) == 2


def test_registry_queries_are_native_and_cached_per_name(m, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_lint_walks_deep_expression_trees_iteratively(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    body = S.leaf
    for _ in range(2_000):
        body = Expression([S.nested, body])
    m.add(Expression([S["="], Expression([S.deep_lint]), body]))
    findings = m.lint()
    assert any(finding.subject == "nested" for finding in findings)


def test_a_declaration_that_cannot_type_its_function(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The engine refuses this in a source file, over that source's own forms.
    # What reaches the linter is the route that builds one atom at a time,
    # where refusing would refuse a program that is about to add its arrow.
    m.run("(= (bare-fn $x) (+ $x 1))")
    m.add(Expression([S[":"], S["bare-fn"], S.Number]))
    findings = m.lint()
    assert "declaration-types-the-symbol" in _kinds(findings)
    detail = next(
        finding.detail for finding in findings
        if finding.kind == "declaration-types-the-symbol"
    )
    assert "(bare-fn ...) compiles unchecked" in detail


def test_one_arrow_among_several_declarations_satisfies_the_linter(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(: paired-fn (-> Number Number)) (= (paired-fn $x) (+ $x 1))")
    m.add(Expression([S[":"], S["paired-fn"], S.Number]))
    assert "declaration-types-the-symbol" not in _kinds(m.lint())


def test_an_explicitly_undefined_type_is_not_a_finding(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(: opted-out %Undefined%) (= (opted-out $x) $x)")
    assert "declaration-types-the-symbol" not in _kinds(m.lint())


def test_a_declaration_for_a_name_with_no_equations_is_data(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # NARS writes inheritance as (--> $a $b). It is an atom in a data
    # position, not a mistyped arrow, and nothing defines the subject.
    m.run("(: nars-belief (--> Cat Animal))")
    assert "declaration-types-the-symbol" not in _kinds(m.lint())


def test_a_positional_read_of_a_tabled_functions_answers(m):
    """Tabling preserves the answer SET and not its order: lib_tabling.pl's
    header measures a (collapse (pick a)) flipping from (one two) to
    (two one) when three facts nothing calls were added to another file. A
    program that reads such a collapse by position works until something
    unrelated moves.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
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


def test_a_canonicalised_read_of_a_tabled_function_is_not_a_finding(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("!(import! &self (library lib_tabling))")
    m.run("(= (tbl-safe a) one)\n(= (tbl-safe a) two)")
    m.run("(= (tbl-safe-first) (car-atom (sort-atom (collapse (tbl-safe a)))))")
    m.run("!(tabled (tbl-safe $x))")
    assert "tabled-answer-order-read" not in _kinds(m.lint())


def test_a_positional_read_of_an_untabled_function_is_not_a_finding(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (untbl-pick a) one)\n(= (untbl-pick a) two)")
    m.run("(= (untbl-first) (car-atom (collapse (untbl-pick a))))")
    assert "tabled-answer-order-read" not in _kinds(m.lint())


def test_findings_carry_the_lsp_diagnostic_fields(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (q1-f $x) (if True $x 0))\n(= (q1-g) (car-atomm 1))")
    findings = {f.kind: f for f in lint(m)}
    simplification = findings["constant-if-true"]
    assert simplification.severity == "information"
    assert str(simplification.autofix) == "(= (q1-f $_640) $_640)".replace(
        "$_640", str(simplification.autofix[1][1])
    )
    assert simplification.payload["replacement"] is not None
    # Which page, and that it names every kind, is checked by
    # test_every_lint_kind_is_named_on_the_page_its_findings_link_to.
    assert simplification.docs_link.startswith("https://")
    # applying the fix is remove-then-add, no positions needed
    assert m.remove(simplification.atom)
    m.add(simplification.autofix)
    assert m._one("(q1-f 7)") == 7
    typo = findings["possibly-undefined-reference"]
    assert typo.severity == "hint"
    assert typo.suggestion == "car-atom"
    assert "did you mean car-atom?" in str(typo)


def test_the_seven_simplification_rules_fire(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run(
        "(= (q3-a $x) (if True $x 0))\n"
        "(= (q3-b $x) (if False $x 0))\n"
        "(= (q3-c $x) (if (> $x 0) $x $x))\n"
        "(= (q3-d $x) (if (> $x 0) True False))\n"
        "(= (q3-e) (superpose ()))\n"
        "(= (q3-f) (superpose (7)))\n"
        "(= (q3-g $a) (let* (($y 1) ($y 2)) $y))\n"
    )
    kinds = {f.kind for f in lint(m)}
    assert {
        "constant-if-true",
        "constant-if-false",
        "if-same-branches",
        "if-true-false",
        "superposed-empty",
        "superposed-single",
        "duplicate-binder",
    } <= kinds


def test_plain_let_duplicate_binders_are_reported_across_one_clause(m):
    """Two single-binding lets still share one compiled clause variable."""
    m.run(
        "(= (plain-let-duplicate) "
        "(Pair (let $a 1 $a) (let $a 2 $a)))"
    )
    duplicates = [finding for finding in lint(m) if finding.kind == "duplicate-binder"]
    assert len(duplicates) == 1
    assert duplicates[0].atom[1][0] == S["plain-let-duplicate"]
    assert "clause-scoped" in duplicates[0].detail
    assert m.run("!(plain-let-duplicate)") == [[]]


def test_plain_let_duplicates_inside_binding_values_are_reported(m):
    """The reporter's nested-value shape is clause-scoped too."""
    m.run(
        "(= (plain-let-duplicate-values) "
        "(let* (($x (let $a 1 $a)) ($y (let $a 2 $a))) (Pair $x $y)))"
    )
    duplicates = [finding for finding in lint(m) if finding.kind == "duplicate-binder"]
    assert len(duplicates) == 1
    assert duplicates[0].atom[1][0] == S["plain-let-duplicate-values"]
    assert m.run("!(plain-let-duplicate-values)") == [[]]


@pytest.mark.parametrize(
    "body",
    [
        "(let* (($a 1) ($a 2)) (Pair $a $a))",
        "(let* (($x (let* (($a 1) ($a 2)) $a))) $x)",
        "(let* (($x 1)) (let* (($a 1) ($a 2)) (Pair $x $a)))",
    ],
)
def test_let_star_duplicate_binder_controls_keep_reporting(m, body):
    """Sibling, binding-value, and body nesting keep their existing finding."""
    m.run(f"(= (let-star-duplicate-control) {body})")
    duplicates = [finding for finding in lint(m) if finding.kind == "duplicate-binder"]
    assert len(duplicates) == 1
    assert duplicates[0].atom[1][0] == S["let-star-duplicate-control"]


def test_distinct_plain_let_binders_are_clean_and_keep_their_pair_answer(m):
    """Distinct clause variables neither warn nor change evaluation."""
    m.run(
        "(= (plain-let-distinct) "
        "(Pair (let $a 1 $a) (let $b 2 $b)))"
    )
    assert m.run("!(plain-let-distinct)") == [[Expression(S.Pair, 1, 2)]]
    assert "duplicate-binder" not in _kinds(lint(m))


def test_inconsistent_arity_reports_and_an_arrow_silences(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run("(= (q3-multi $x) $x)\n(= (q3-multi $x $y) $x)")
    assert any(f.kind == "inconsistent-arity" for f in lint(m))
    m.run("(: q3-multi (-> Number Number))")
    kinds = [f.kind for f in lint(m)]
    assert "inconsistent-arity" not in kinds
    # and no arrow-arity-mismatch either: the arrow matches ONE compiled
    # arity, which the existing check reads as declared dispatch
    assert "arrow-arity-mismatch" not in kinds


def test_type_mismatch_uses_the_engines_total_get_type(m):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    m.run(
        '(: q3-typed (-> Number Number))\n'
        "(= (q3-typed $x) $x)\n"
        '(= (q3-bad) (q3-typed "oops"))\n'
        "(= (q3-good) (q3-typed 4))\n"
    )
    mismatches = [f for f in lint(m) if f.kind == "type-mismatch"]
    assert len(mismatches) == 1
    assert mismatches[0].severity == "error"
    assert "String where the declared arrow wants Number" in mismatches[0].detail


def test_positioned_forms_recover_exact_lines():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta._source_forms import positioned_forms

    source = "; a comment quoting (f 1)\n(f 1)\n\n!(+ 1 2)\n(= (g $x)\n   $x)\n"
    forms = positioned_forms(source)
    assert [(f.kind, f.line, f.column) for f in forms] == [
        ("expression", 2, 1),
        ("runnable", 4, 2),
        ("function", 5, 1),
    ]
    # the comment quoting (f 1) could not mislead the walk: the form
    # anchors at line 2, not inside the line-1 comment


def test_a_locator_mismatch_refuses(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from metta import _source_forms

    real = _source_forms.runtime

    class Lying:
        def must(self, goal, **inputs):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
            return {"Forms": [["expression", "(never-there)"]]}

    monkeypatch.setattr(_source_forms, "runtime", lambda: Lying())
    with pytest.raises(MettaError, match="the reader and the locator disagree"):
        _source_forms.positioned_forms("(real form)")
    monkeypatch.setattr(_source_forms, "runtime", real)


def test_lint_file_anchors_findings_to_lines(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    target = tmp_path / "anchored.metta"
    target.write_text(
        "; prose first\n"
        "(: q2-ghost (-> Number Number))\n"
        "\n"
        "(= (q2-fine $x) $x)\n"
        "(= (q2-loose $x) (if True $x 0))\n"
    )
    from metta.lint import lint_file

    findings = {f.kind: f for f in lint_file(target, m=metta)}
    ghost = findings["declared-but-undefined"]
    assert ghost.payload["line"] == 2
    assert ghost.payload["file"] == str(target)
    simplifiable = findings["constant-if-true"]
    assert simplifiable.payload["line"] == 5
