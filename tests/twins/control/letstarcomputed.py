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
    [tested: test_printing_text_is_not_forced_through_the_value_carrier; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, equation
from metta.errors import MettaOperationError

#: What the unapplied form prints as: expected printing is Python text.
UNAPPLIED = "(partial let* (foo ok))"

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `let*` whose bindings arrive as a VALUE has no assignment spelling"

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Hand bindings over, write them out, and refuse a list that is not one."""
    # The top rung is a compiled definition whose bindings are assignments:
    #
    #     @m.define
    #     def mylet(bindings, body): ...
    #
    # An assignment binds a name the AUTHOR wrote, so a definition whose
    # bindings arrive as a value has no compiled spelling, and neither has a
    # binding whose left side is a pattern. Residue: P14.4.
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
