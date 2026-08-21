"""Purpose: the matching-core cluster's acceptance criteria, run not read.

One compiler means a quoted term in a pattern position holds what a quoted term
in a body position holds, and a rule's guard decides whether the rule applies
without rewriting the call it was asked about.

Assumes:
  - a MeTTa program can be evaluated in-process through ``petta.MeTTa``, and
    one query group's atoms come back in their stable textual form.
Guarantees:
  - `quote` scopes a pattern exactly as it scopes a body, so a head written to
    match what a body writes does match it.
  [tested: test_quote_is_a_scope_in_head_position_too; commit=4465fc492071932eab0b2818a4ccd46f01f0d6aa]
  - a translator rule's guard, written as a head shape or as a goal in the
    rule's body, cannot instantiate the call it is matched against, so the
    equation holding that call keeps its own head pattern.
  [tested: test_a_guard_that_binds_a_pattern_variable_cannot_create_a_match;
   commit=4465fc492071932eab0b2818a4ccd46f01f0d6aa]
  - the compiler says which head pattern position it decided something about,
    which label, and why, for both decisions it can take there, and says
    nothing where the parameter's evaluation mask makes the decision the one
    the programmer asked for.
  [tested: test_the_compiler_names_a_pattern_position_it_turned_into_a_goal;
   commit=4465fc492071932eab0b2818a4ccd46f01f0d6aa]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import pytest

from petta import MeTTa

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


def _answers(metta: MeTTa, source: str) -> list[str]:
    """Return one query group's atoms in their stable textual form."""
    groups = metta.run(source)
    assert len(groups) == 1
    return [str(atom) for atom in groups[0]]


@pytest.mark.parametrize(
    "index, payload", list(enumerate(QUOTED_PAYLOADS)), ids=QUOTED_PAYLOADS
)
def test_quote_is_a_scope_in_head_position_too(index, payload):
    """A quoted pattern matches the value a quoted body produces.

    The body's own output is fed straight into the head's own pattern, so the
    two positions are compared against each other rather than against a
    transcription of what either was expected to compile to. Measured on the
    tip before the pattern walk stopped descending into a quote: with the
    payload ``(cons 1 2)`` the body compiled the value ``[quote, [cons, 1, 2]]``
    and the head compiled the pattern ``[quote, [1|2]]``, so this call had no
    answer at all.
    """
    metta = MeTTa(verbose=False)
    body, head = f"qs-body-{index}", f"qs-head-{index}"
    metta.run(f"(= ({body}) (quote {payload}))")
    metta.run(f"(= ({head} (quote {payload})) matched)")
    assert _answers(metta, f"!({head} ({body}))") == ["matched"]


def test_a_quoted_annotation_pattern_matches_the_annotation_and_not_its_subject():
    """The sharpest observable half of the same change, in both directions.

    While the walk descended, ``(= (h3 (quote (: $x Number))) matched)``
    compiled to ``h3([quote, A], matched) :- has_type(A, 'Number')``: the
    pattern had lost the annotation and kept only its variable, so it matched
    ``(quote 5)``, which nobody wrote it for, and refused
    ``(quote (: foo Number))``, which is exactly what it says.
    """
    metta = MeTTa(verbose=False)
    metta.run("(= (h3 (quote (: $x Number))) matched)")
    assert _answers(metta, "!(h3 (quote (: foo Number)))") == ["matched"]
    assert _answers(metta, "!(h3 (quote (: 7 Number)))") == ["matched"]
    assert _answers(metta, "!(h3 (quote 5))") == ["(h3 (quote 5))"]


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
    metta = MeTTa(verbose=False)

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

    assert _answers(metta, "!(p216-uses-gp 5)") == ["(p216-gp 5)"]
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
    metta = MeTTa(verbose=False)
    metta.run("(= (p22-g $x) (inner $x))")
    capfd.readouterr()

    metta.run("(= (p22-goal (: $x Number)) $x)")
    annotation = capfd.readouterr().err
    assert "(= (p22-goal ...) ...)" in annotation
    assert "head argument 1" in annotation
    assert "annotation on :" in annotation
    assert "GOAL" in annotation

    metta.run("(= (p22-label (deeper (p22-g $x))) $x)")
    label = capfd.readouterr().err
    assert "(= (p22-label ...) ...)" in label
    assert "head argument 1, subterm 1" in label
    assert "against (p22-g ...)" in label
    assert "p22-g has equations here" in label
    assert "matched STRUCTURALLY" in label

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

    # The decision the note describes is real, not a style opinion.
    assert _answers(metta, "!(p22-label (deeper (p22-g 3)))") == [
        "(p22-label (deeper (inner 3)))"
    ]
