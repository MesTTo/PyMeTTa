"""Purpose: examples/control/letstarcomputed.metta in Python: bindings as a value.

The bindings of a `let*` are usually written out, and then they are syntax:
the form rewrites them into nested `let`s once. They do not have to be written
out. A bindings argument that arrives as a VALUE is rewritten when it arrives,
so a program can decide its own bindings while it runs, which is what lets
`let*` be given another name as an ordinary definition.

That is the shape Python has no word for. An assignment binds a name the
author wrote, so a definition whose bindings ARRIVE has no compiled spelling,
and neither has a binding whose left side is a pattern. Written-out bindings
sit beside handed-over ones here on purpose, so writing half of them as Python
assignments would break the pairing the file exists to show. Filed as residue
against P14.4.

Three things do move into Python: an answer set that is empty is an empty
list, a refusal crosses the seam as a Python exception so `catch` is `except`,
and `repr` of an atom is Python's own `str`.
Guarantees:
  - expected printed output in this twin remains Python str text
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, V, equation
from petta.errors import MettaOperationError

#: What the unapplied form prints as: expected printing is Python text.
UNAPPLIED = "(partial let* (foo ok))"

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `let*` whose bindings arrive as a VALUE has no assignment spelling"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8844 to 8934, +90 (+1.0%), by the twin contract
#: change: eight `test` wrappers, one collapse and one `repr` LEFT the engine
#: for `assert`s, an empty list and Python's `str`, while `car-atom`/`catch`
#: became `except`; the total barely moves because the eight `mylet` and
#: `let*` calls are the whole cost and they all still run there. Measured
#: min-of-3 over fresh processes with the MORK backend linked in, which the
#: artefact-free worktree omits and which moves a compiled twin by about 10
#: inferences per definition; against the example's 18590 the ratio is
#: 0.4806. Prior: 8844, the transliterated twin this replaces.
BUDGET = 8934


def twin(m):
    """Hand bindings over, write them out, and refuse a list that is not one."""
    # (: mylet (-> Atom Atom %Undefined%))
    # The body has to reach the definition unevaluated for the bindings to
    # bind anything in it, and `Atom` is the metatype that says so.
    m += S[":"](S.mylet, S["->"](S.Atom, S.Atom, S["%Undefined%"]))
    # (= (mylet $bindings $body) (let* $bindings $body))
    m += equation(S.mylet(V.bindings, V.body)).to(S["let*"](V.bindings, V.body))

    written = ((V.x, 1), (V.y, 2))

    # !(test (mylet (($x 1) ($y 2)) (+ $x $y)) 3)
    assert m.eval(S.mylet(written, V.x + V.y)) == [3]

    # Handed over or written out, the same bindings answer the same thing.
    # !(test (let* (($x 1) ($y 2)) (+ $x $y)) 3)
    assert m.eval(S["let*"](written, V.x + V.y)) == [3]

    # A binding is a (pattern value) pair, not only (variable value), and a
    # pattern that does not match gives the whole form no answer.
    # !(test (mylet ((($a $b) (1 2))) $b) 2)
    assert m.eval(S.mylet((((V.a, V.b), (1, 2)),), V.b)) == [2]
    # !(test (mylet ((5 5)) matched) matched)
    assert m.eval(S.mylet(((5, 5),), S.matched)) == [S.matched]
    # !(test (collapse (mylet ((5 6)) matched)) ())
    assert m.eval(S.mylet(((5, 6),), S.matched)) == []

    # Without the `Atom` metatype the arguments evaluate on the way in, so
    # this is the other way to hand bindings over: `noeval` carries them as
    # data, and the body is a variable the same call site wrote.
    # (= (mylet-evaluating $bindings $body) (let* $bindings $body))
    m += equation(S["mylet-evaluating"](V.bindings, V.body)).to(S["let*"](V.bindings, V.body))

    # !(test (mylet-evaluating (noeval (($x 1))) $x) 1)
    assert m.eval(S["mylet-evaluating"](S.noeval(((V.x, 1),)), V.x)) == [1]

    # Bindings are checked when they arrive, because nothing after that point
    # can check them.
    # !(test (car-atom (catch (mylet-evaluating (noeval ((1 2 3))) done))) Error)
    try:
        m.eval(S["mylet-evaluating"](S.noeval(((1, 2, 3),)), S.done))
        refused = None
    except MettaOperationError as error:
        refused = error
    assert refused is not None

    # A bindings argument that is no list at all is not bindings, it is a
    # program using the name as data, and it stays the unapplied form it
    # always was.
    # !(test (repr (let* foo ok)) "(partial let* (foo ok))")
    assert str(m.eval(S["let*"](S.foo, S.ok))[0]) == UNAPPLIED
