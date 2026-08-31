"""Purpose: the matching-core cluster's acceptance criteria, run not read.

One compiler means a quoted term in a pattern position holds what a quoted term
in a body position holds, and a rule's guard decides whether the rule applies
without rewriting the call it was asked about.

Assumes:
  - a MeTTa program can be evaluated in-process through ``metta.MeTTa``, and
    one query group's atoms come back in their stable textual form.
Guarantees:
  - `quote` scopes a pattern exactly as it scopes a body, so a head written to
    match what a body writes does match it.
  [tested: test_quote_is_a_scope_in_head_position_too; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - a translator rule's guard, written as a head shape or as a goal in the
    rule's body, cannot instantiate the call it is matched against, so the
    equation holding that call keeps its own head pattern.
  [tested: test_a_guard_that_binds_a_pattern_variable_cannot_create_a_match;
   commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the compiler says which head pattern position it decided something about,
    which label, and why, for both decisions it can take there, and says
    nothing where the parameter's evaluation mask makes the decision the one
    the programmer asked for.
  [tested: test_the_compiler_names_a_pattern_position_it_turned_into_a_goal;
   commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import re

import pytest

from metta import MeTTa

# Terms whose meaning changes if a pattern's quote is walked instead of held.
# `cons` is rewritten into an improper list by the pattern walk, `:` into a
# type premise goal, and a defined label used to be run backwards; a body's
# quote does none of those to any of them.
QUOTED_PAYLOADS = [
    "(cons 1 2)",
    "(: $x Number)",
    "(g $x)",
    "(h (g 1))",
    "(foo bar)",
    "$x",
]


#: A payload's variables print under the engine's allocation names, `$_18268`,
#: which differ between runs and from the source spelling. Only the shape is
#: the claim in the rows below, so every variable becomes `$v` first.
#:
#: This COLLAPSES distinct variables onto one name, which would weaken the
#: comparison for a payload holding two of them; every payload above holds at
#: most one, and the rows assert that before relying on it. Use
#: Atom.alpha_eq or tools/alpha.canonical for a payload that needs a real
#: bijection.
_ANY_VARIABLE = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*|\$_\d+")


def _normalise(text: str) -> str:
    """One term with every variable name replaced by `$v`."""
    return _ANY_VARIABLE.sub("$v", text)


def _normalised(answers: list[str]) -> list[str]:
    """Answers with every variable name replaced by `$v`."""
    return [_normalise(answer) for answer in answers]


def _answers(metta: MeTTa, source: str) -> list[str]:
    """Return one query group's atoms in their stable textual form."""
    groups = metta.run(source)
    assert len(groups) == 1
    return [str(atom) for atom in groups[0]]


@pytest.mark.parametrize(
    "index, payload", list(enumerate(QUOTED_PAYLOADS)), ids=QUOTED_PAYLOADS
)
def test_quote_is_a_scope_in_head_position_too(index, payload):
    """A quoted pattern holds its payload INTACT, and a quoted body answers it.

    The two positions do different things and that is the law: a body's quote
    is an evaluation barrier, so it answers the payload with no wrapper left,
    while a head's quote is literal structure, because a pattern is matched
    rather than evaluated [source: PeTTa@ae66fa8 src/translator.pl:320 for the
    body, and its constrain_args/3 head walk, which gives quote no special
    meaning]. They meet when the parameter is declared ``Atom`` and the
    argument is WRITTEN as a quote, which is the shape the shipped ``unquote``
    uses and the only one upstream gets right.

    What both halves share is that the payload is not mangled on the way in.
    Measured on the tip before the pattern walk stopped descending into a
    quote: with the payload ``(cons 1 2)`` the head compiled the pattern
    ``[quote, [1|2]]``, an improper list, so the call had no answer at all.
    Upstream still compiles exactly that ``qh([quote, [1|2]], matched).``
    [measured 2026-08-30, ai-tmp/qs3.metta], which is why this row is a
    superset rather than a parity claim.
    """
    metta = MeTTa(verbose=False).self
    #The normaliser below maps every variable to one name, so it only stands
    #in for alpha-equivalence while a payload holds at most one.
    assert len(set(_ANY_VARIABLE.findall(payload))) <= 1
    body, head = f"qs-body-{index}", f"qs-head-{index}"

    # The BODY: the barrier answers the payload itself, with no wrapper. A
    # variable in the payload comes back under the engine's own allocation
    # name, so only the SHAPE is the claim and every name is normalised away.
    metta.run(f"(= ({body}) (quote {payload}))")
    assert _normalised(_answers(metta, f"!({body})")) == [_normalise(payload)]

    # The HEAD: an Atom parameter holds the written argument, so the quoted
    # pattern is reached and the payload inside it survived the walk.
    metta.run(f"(: {head} (-> Atom %Undefined%))")
    metta.run(f"(= ({head} (quote {payload})) matched)")
    assert _answers(metta, f"!({head} (quote {payload}))") == ["matched"]


def test_a_quoted_annotation_pattern_matches_the_annotation_and_not_its_subject():
    """The sharpest observable half of the same change, in both directions.

    While the walk descended, ``(= (h3 (quote (: $x Number))) matched)``
    compiled to ``h3([quote, A], matched) :- has_type(A, 'Number')``: the
    pattern had lost the annotation and kept only its variable, so it matched
    ``(quote 5)``, which nobody wrote it for, and refused
    ``(quote (: foo Number))``, which is exactly what it says.
    """
    metta = MeTTa(verbose=False).self
    # An Atom parameter holds the written argument, so the quoted pattern is
    # what the call meets; without it the argument's own quote is a barrier
    # and strips before the head sees it.
    metta.run("(: h3 (-> Atom %Undefined%))")
    metta.run("(= (h3 (quote (: $x Number))) matched)")
    assert _answers(metta, "!(h3 (quote (: foo Number)))") == ["matched"]
    assert _answers(metta, "!(h3 (quote (: 7 Number)))") == ["matched"]
    # No clause matches, and the default no-match policy is NoMatchFail, so
    # the call answers NOTHING -- upstream's own answer for a guarded head
    # with no matching clause [measured 2026-08-30 against PeTTa@ae66fa8].
    assert _answers(metta, "!(h3 (quote 5))") == []


def test_a_guard_that_binds_a_pattern_variable_cannot_create_a_match():
    """Two guards are planted, and neither narrows the equation holding the call.

    A translator rule can guard itself two ways: by naming a shape in its head,
    or by running a goal in its body that binds one of its head variables. Both
    reach the call through Prolog's ``call/1``, which unifies, so before the
    match was re-checked both rewrote the ENCLOSING equation's head while they
    were there. Measured 2026-08-21 on the tip before the change:
    ``(= (p216-uses-bg $z) (p216-bg $z))`` compiled to ``uses-bg(planted, ...)`` and
    ``(= (p216-uses-gp $z) (p216-gp $z))`` to ``uses-gp([pair, A, B], ...)``, so a
    head the programmer wrote to match anything matched one symbol and one
    shape, and the other calls had no answer and no message.
    """
    metta = MeTTa(verbose=False).self

    # The body-guard rule, with the fall-through its decline reaches.
    metta.run("(: p216-bg (-> Atom %Undefined%))")
    metta.run("(= (p216-bg $a) (let $a p216-planted (noeval (saw $a))))")
    metta.run("(= (p216-bg $a) (noeval (fell-through $a)))")
    assert _answers(metta, "!(add-translator-rule! p216-bg)") == ["True"]
    metta.run("(= (p216-uses-bg $z) (p216-bg $z))")

    assert _answers(metta, "!(p216-uses-bg 5)") == ["(fell-through 5)"]
    assert _answers(metta, "!(p216-uses-bg p216-planted)") == [
        "(fell-through p216-planted)"
    ]
    # Still a rule, and still fires where the call really is what it names.
    assert _answers(metta, "!(p216-bg p216-planted)") == ["(saw p216-planted)"]

    # The head-shape guard, which is how the shipped set operations are written.
    metta.run("(: p216-gp (-> Atom %Undefined%))")
    metta.run("(= (p216-gp (pair $a $b)) (noeval (got $a $b)))")
    assert _answers(metta, "!(add-translator-rule! p216-gp)") == ["True"]
    metta.run("(= (p216-uses-gp $z) (p216-gp $z))")

    assert _answers(metta, "!(p216-uses-gp 5)") == []
    assert _answers(metta, "!(p216-uses-gp (pair 1 2))") == ["(got 1 2)"]
    assert _answers(metta, "!(p216-gp (pair 3 4))") == ["(got 3 4)"]


def test_the_compiler_names_a_pattern_position_it_turned_into_a_goal(capfd):
    """Both invisible decisions about a head pattern position are now said out loud.

    A position that compiles to a type premise GOAL and a position whose label
    already means something are both correct and both unreadable in the source:
    ``!(p22-label (p22-g 3))`` arrives as ``(p22-label (inner 3))`` and matches
    nothing, with no answer and, before this, no message. The engine speaks
    through SWI's message machinery, so ``-q`` batch runs stay quiet while the
    library door, which is where somebody is reading, prints it.
    """
    metta = MeTTa(verbose=False).self
    metta.run("(= (p22-g $x) (inner $x))")
    capfd.readouterr()

    # A colon head is ordinary structure since 2026-08-30, so there is no
    # decision to report and this says NOTHING. It named an in-place type
    # annotation until then.
    metta.run("(= (p22-goal (: $x Number)) $x)")
    assert capfd.readouterr().err == ""

    metta.run("(= (p22-label (deeper (p22-g $x))) $x)")
    label = capfd.readouterr().err
    assert "(= (p22-label ...) ...)" in label
    assert "head argument 1, subterm 1" in label
    # A nested position holding a call to something runnable compiles to a
    # GOAL, so the message names the call and says what the caller's argument
    # is matched against.
    assert "holds the call (p22-g ...)" in label
    assert "compiled to a GOAL" in label

    # The other route to a head meaning, which asking fun/1 alone would miss.
    metta.run("(= (p22-special (if True 1 2)) hit)")
    special = capfd.readouterr().err
    assert "head argument 1" in special
    assert "special form or a registered translator rule" in special

    # And it stays quiet where the decision is the one the programmer asked
    # for: an evaluation-masked parameter receives its argument as written.
    metta.run("(: p22-lazy (-> Atom %Undefined%))")
    metta.run("(= (p22-lazy (p22-g $x)) $x)")
    assert capfd.readouterr().err == ""

    # The decision the note describes is real, not a style opinion: the head
    # position RUNS (p22-g $x) and matches the caller's argument against what
    # it answers, so the call whose argument evaluated to (deeper (inner 3))
    # is exactly the one that matches.
    assert _answers(metta, "!(p22-label (deeper (p22-g 3)))") == ["3"]
