"""Purpose: the specification's acceptance probes for how the translator
compiles a form whose syntax has not arrived at translation time. A special
form that reads part of its argument AS SYNTAX has nothing to read when that
part is still a variable, and the answer is a runtime path rather than a
rewrite that unifies its own pattern into the source.
Assumes:
  - `Atom` on an argument's declared type makes it arrive unevaluated, which
    is what lets a body reach a wrapper unevaluated
    [source: examples/translation/translatorrule_for.metta]
Guarantees:
  - `let*` under another name binds the body with the bindings the caller
    wrote, and refuses a value that is not bindings naming the form
    [tested: test_let_star_with_an_unarrived_bindings_list_does_not_drop_them]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import pytest

from petta import EngineError


@pytest.fixture()
def m(metta):
    with metta.new_space() as space:
        yield space


def test_let_star_with_an_unarrived_bindings_list_does_not_drop_them(m):
    """`(= (mylet $bs $b) (let* $bs $b))` used to compile to
    `mylet([], A, A)`: the bindings argument unified with the empty list
    under the rewrite's own cut, so every binding a caller wrote was
    dropped and the body answered with nothing bound."""
    m.run("(: mylet (-> Atom Atom %Undefined%))")
    m.run("(= (mylet $bs $b) (let* $bs $b))")
    assert [str(a) for a in m.eval("(mylet (($x 1) ($y 2)) (+ $x $y))")] == ["3"]

    # Written out, the same bindings answer the same thing.
    assert [str(a) for a in m.eval("(let* (($x 1) ($y 2)) (+ $x $y))")] == ["3"]

    # A pair that is still a variable is the same defect one level in: the
    # rewrite used to unify [Pattern, Value] into it and change the head the
    # program wrote.
    m.run("(= (letpair $b) (let* ($b) 99))")
    assert [str(a) for a in m.eval("(letpair (quote ($x 7)))")] == ["99"]

    # A value arriving there that is not bindings is refused naming the form.
    with pytest.raises(EngineError) as refusal:
        m.eval("(mylet (quote ((1 2 3))) done)")
    assert "let*: a list of (pattern value) bindings expected" in str(refusal.value)
