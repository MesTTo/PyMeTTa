"""Purpose: the specification's acceptance probes for how the translator
compiles a form whose syntax has not arrived at translation time. A special
form that reads part of its argument AS SYNTAX has nothing to read when that
part is still a variable, and the answer is a runtime path rather than a
rewrite that unifies its own pattern into the source.
Assumes:
  - `Atom` on an argument's declared type makes it arrive unevaluated, which
    is what lets a body reach a wrapper unevaluated
    [source: examples/ch20-extending-the-engine/20-01-translator-rules/05-translatorrule_for.metta]
Guarantees:
  - `let*` under another name binds the body with the bindings the caller
    wrote, and refuses a value that is not bindings naming the form
    [tested: test_let_star_with_an_unarrived_bindings_list_does_not_drop_them]
  - an equation head is a pattern at every depth, so a head and the `match`
    that reads it back agree
    [tested: test_an_equation_head_is_matched_not_called]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta.errors import EngineError


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        yield space


def test_let_star_with_an_unarrived_bindings_list_does_not_drop_them(m):
    """`(= (mylet $bs $b) (let* $bs $b))` used to compile to
    `mylet([], A, A)`: the bindings argument unified with the empty list
    under the rewrite's own cut, so every binding a caller wrote was
    dropped and the body answered with nothing bound.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(: mylet (-> Atom Atom %Undefined%))")
    m.run("(= (mylet $bs $b) (let* $bs $b))")
    assert [str(a) for a in m.eval("(mylet (($x 1) ($y 2)) (+ $x $y))")] == ["3"]

    # Written out, the same bindings answer the same thing.
    assert [str(a) for a in m.eval("(let* (($x 1) ($y 2)) (+ $x $y))")] == ["3"]

    # A pair that is still a variable is the same defect one level in: the
    # rewrite used to unify [Pattern, Value] into it and change the head the
    # program wrote.
    m.run("(= (letpair $b) (let* ($b) 99))")
    assert [str(a) for a in m.eval("(letpair (noeval ($x 7)))")] == ["99"]

    # A value arriving there that is not bindings is refused naming the form.
    with pytest.raises(EngineError) as refusal:
        m.eval("(mylet (noeval ((1 2 3))) done)")
    assert "let*: a list of (pattern value) bindings expected" in str(refusal.value)


def test_an_equation_head_is_matched_not_called(m):
    """`(= (eqh (top 1 (src 5))) matched)` used to compile to
    `eqh([top, 1, A], matched) :- src(5, A)`, running `src` backwards over
    a position the program wrote as a pattern, so the head and the `match`
    that reads the same shape back disagreed.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    m.run("(= (src 5) 7)")
    m.run("(top 1 (src 5))")
    structural = [str(a) for a in m.eval("(match &self (top $k (src $n)) ($k $n))")]
    assert structural == ["(1 5)"]

    m.run("(: eqh (-> Atom Atom))")
    m.run("(= (eqh (top 1 (src 5))) matched)")
    assert [str(a) for a in m.eval("(eqh (top 1 (src 5)))")] == ["matched"]

    # The equation reads back as the shape it was written with.
    stored = [
        str(a)
        for a in m.eval("(match &self (= (eqh (top $k (src $n))) $r) ($k $n $r))")
    ]
    assert stored == ["(1 5 matched)"]

    # A nullary call in a head is a pattern too. The arbiter's own case:
    # the argument evaluates to `pa3`, so only the equation written against
    # `pa3` fires, where the call-shaped head used to fire as well.
    m.run("(= (produce-pa3) pa3)")
    m.run("(= (nested-atom pa3) evaluated)")
    m.run("(= (nested-atom (produce-pa3)) held)")
    assert [str(a) for a in m.eval("(nested-atom (produce-pa3))")] == ["evaluated"]


# The derived forms the engine's prelude ships as translator rules, each with
# the expansion its own equation builds. `arity` is what the rule's equation
# takes; `guard` names the head every argument must have for the rewrite to
# apply, which is what the set operations carried.
#
# The five set operations NAME their collapsed operand before handing it over,
# because unique-atom, alpha-unique-atom, union-atom, intersection-atom and
# subtraction-atom all declare Expression parameters and an Expression
# parameter holds its argument as written. Fused as
# `(unique-atom (collapse $s))` the collapse never runs and the operation reads
# the literal `(collapse $s)`
# [source: LeaTTa MettaHyperonFull/Minimal/Interpreter.lean:1543-1546, the
# groundedTokens rows for that family; measured 2026-08-24:
# `!(subtraction-atom ((+ 1 2) b) (b))` answers `((+ 1 2))` there].
DERIVED_FORMS = {
    ("and-then", 2): (None, "(if {0} {1} False)"),
    ("or-else", 2): (None, "(if {0} True {1})"),
    ("trace!", 2): (None, "(progn (println! {0}) {1})"),
    ("unique", 1): (
        None,
        "(let $df-in (collapse {0})"
        " (let $df-out (unique-atom $df-in) (superpose $df-out)))",
    ),
    ("alpha-unique", 1): (
        None,
        "(let $df-in (collapse {0})"
        " (let $df-out (alpha-unique-atom $df-in) (superpose $df-out)))",
    ),
    ("union", 2): (
        "superpose",
        "(let $df-left (collapse {0}) (let $df-right (collapse {1})"
        " (let $df-out (union-atom $df-left $df-right) (superpose $df-out))))",
    ),
    ("intersection", 2): (
        "superpose",
        "(let $df-left (collapse {0}) (let $df-right (collapse {1})"
        " (let $df-out (intersection-atom $df-left $df-right)"
        " (superpose $df-out))))",
    ),
    ("subtraction", 2): (
        "superpose",
        "(let $df-left (collapse {0}) (let $df-right (collapse {1})"
        " (let $df-out (subtraction-atom $df-left $df-right)"
        " (superpose $df-out))))",
    ),
}

# Every corpus file that writes one of those forms, and a file that RUNS it.
# A library is not runnable on its own, so it is exercised through one of its
# importers.
DERIVED_FORM_SITES = [
    ("examples/ch07-control-flow/07-01-if-and-booleans/10-and_then_or_else.metta", "examples/ch07-control-flow/07-01-if-and-booleans/10-and_then_or_else.metta"),
    ("examples/ch06-many-answers/09-streamops.metta", "examples/ch06-many-answers/09-streamops.metta"),
    ("lib/lib_roman.metta", "examples/ch08-data/08-01-atoms-lists-and-folds/15-roman.metta"),
    ("lib/lib_pln.metta", "examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/05-pln_direct.metta"),
    ("lib/lib_nars.metta", "examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/08-nars_direct.metta"),
]


def _tokens(text):
    """MeTTa source as a flat token list, comments dropped and strings kept
    whole. Enough to re-print a file that only has to run.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c == ";":
            while i < len(text) and text[i] != "\n":
                i += 1
        elif c == '"':
            j = i + 1
            while j < len(text) and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif c in "()":
            out.append(c)
            i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < len(text) and not text[j].isspace() and text[j] not in '();"':
                j += 1
            out.append(text[i:j])
            i = j
    return out


def _parse(tokens, at=0):
    """The token list as nested lists of strings, and where reading stopped."""
    out = []
    while at < len(tokens):
        token = tokens[at]
        if token == "(":
            inner, at = _parse(tokens, at + 1)
            out.append(inner)
        elif token == ")":
            return out, at + 1
        else:
            out.append(token)
            at += 1
    return out, at


def _print(node):
    if isinstance(node, str):
        return node
    return "(" + " ".join(_print(child) for child in node) + ")"


def _expand(node):
    """Every derived-form call replaced by its expansion, innermost first."""
    if isinstance(node, str):
        return node, 0
    children, count = [], 0
    for child in node:
        expanded, n = _expand(child)
        children.append(expanded)
        count += n
    if children and isinstance(children[0], str):
        key = (children[0], len(children) - 1)
        entry = DERIVED_FORMS.get(key)
        if entry is not None:
            guard, template = entry
            args = children[1:]
            applies = guard is None or all(
                isinstance(a, list) and a and a[0] == guard for a in args
            )
            if applies:
                text = template.format(*(_print(a) for a in args))
                return _parse(_tokens(text))[0][0], count + 1
    return children, count


def _expand_source(text):
    """The file re-printed with every derived form expanded. `!` is its own
    token and binds to the form after it, so it is re-joined here: printed on
    a line of its own it is a bare symbol and the runnable is gone.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    tree, _ = _parse(_tokens(text))
    expanded, count = _expand(tree)
    lines, bang = [], False
    for form in expanded:
        if form == "!":
            bang = True
            continue
        lines.append(("!" if bang else "") + _print(form))
        bang = False
    return "\n".join(lines) + "\n", count


def test_a_prelude_derived_form_matches_its_fused_twin_on_the_corpus(repo_root):
    """Each derived form is an equation in the prelude where it used to be a
    clause of the compiler. Running a corpus file as written and running it
    with every such call replaced by the expansion the deleted clause built
    must answer the same thing, group for group.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    import sys

    sys.path.insert(0, str(repo_root / "bindings" / "python" / "tools"))
    import example_parity

    compared = 0
    for source_name, runner_name in DERIVED_FORM_SITES:
        source = repo_root / source_name
        runner = repo_root / runner_name
        original = source.read_text()
        expanded, replaced = _expand_source(original)
        assert replaced > 0, f"{source_name} writes no derived form any more"
        assert not any(
            f"({name} " in expanded for name, _ in DERIVED_FORMS
        ), f"{source_name} still names a derived form after expansion"

        as_written = example_parity.run_engine(runner, repo_root)
        source.write_text(expanded)
        try:
            as_expanded = example_parity.run_engine(runner, repo_root)
        finally:
            source.write_text(original)
        assert as_written.error is None, f"{runner_name}: {as_written.error}"
        assert as_written.groups, f"{runner_name} answered nothing to compare"
        assert as_written.groups == as_expanded.groups, runner_name
        assert as_written.error == as_expanded.error, runner_name
        compared += 1

    assert compared == len(DERIVED_FORM_SITES)
