"""Purpose: examples/control/unify.metta in Python: the matching conditional.

`(unify a b then else)` runs the then branch once per binding set under which
a and b match, and the else branch exactly when no binding set exists. The
operands cross unevaluated, all four arguments are typed Atom, and only the
selected branch runs.

`unify` keeps MeTTa's name because Python has no expression that matches two
terms and chooses a branch: `metta.unify(pattern, atom)` answers bindings on
atoms Python already holds, which is a different act, and the four-argument
form the ledger designs is not built yet. What does move into Python is
everything around it: a stored marker is asked for with `in`, which IS match
containment, and the space operand is the handle itself, because a space is a
grounded atom and no symbol names it.

Both probes are compiled definitions that write from inside their own
equations, over `(context-space)`, which is the space the equation runs in. So
the markers stored are the example's own bare symbols. The Python write door
still refuses one, `m.add(S.then_ran)` answering "a stored atom is a non-empty
expression", where the engine's `add-atom` takes it; the two doors disagreeing
is filed as residue against P14.10.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, ground

#: The two strings the ground decisions compare, carried whole.
STRING_X, STRING_Y = ground("x"), ground("y")

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Match ground terms, terms with variables, and a space."""
    # The top rung is the expression-position function the guide rules and
    # prints twice, `unify(a, b, then, els)`. It is not built. Measured
    # 2026-08-23: the root `unify` is the two-argument matcher over two atoms
    # Python already holds and raises "unify() takes 2 positional arguments but
    # 4 were given", and a bare `unify(...)` inside a compiled body raises
    # CompileError because it is not one of the four magic names a body reads.
    # `S.unify(x, pattern, then, els)` in a body does work, so the gap is the
    # FUNCTION rather than the instruction. Residue: P14.4.
    #
    # Ground decisions, including numeric promotion: 1 matches 1.0.
    # !(test (unify 1 1 same different) same)
    assert m.eval(S.unify(1, 1, S.same, S.different)) == [S.same]
    # !(test (unify 1 2 same different) different)
    assert m.eval(S.unify(1, 2, S.same, S.different)) == [S.different]
    # !(test (unify 1 1.0 same different) same)
    assert m.eval(S.unify(1, 1.0, S.same, S.different)) == [S.same]
    # !(test (unify "x" "x" same different) same)
    assert m.eval(S.unify(STRING_X, STRING_X, S.same, S.different)) == [S.same]
    # !(test (unify "x" "y" same different) different)
    assert m.eval(S.unify(STRING_X, STRING_Y, S.same, S.different)) == [S.different]

    # Bindings flow from the match into the branch, both directions at once.
    # !(test (unify (f $x b) (f a $y) (pair $x $y) nope) (pair a b))
    both = S.unify(S.f(V.x, S.b), S.f(S.a, V.y), S.pair(V.x, V.y), S.nope)
    assert m.eval(both) == [S.pair(S.a, S.b)]

    # The occurs check rejects a cyclic binding.
    # !(test (unify $x (f $x) cyclic sound) sound)
    assert m.eval(S.unify(V.x, S.f(V.x), S.cyclic, S.sound)) == [S.sound]

    @m.define
    def then_probe():
        # (= (then-probe) (chain (add-atom &self then-ran) $_ 3))
        _marked = S["add-atom"](S["context-space"](), S.then_ran)  # rung: `space += atom` is a Python statement over a handle, and a compiled body is pure atoms
        return 3

    @m.define
    def else_probe():
        # (= (else-probe) (chain (add-atom &self else-ran) $_ 4))
        _marked = S["add-atom"](S["context-space"](), S.else_ran)  # rung: the other marker, the same way
        return 4

    probes = (S["then-probe"](), S["else-probe"]())

    # Only the selected branch evaluates: each probe leaves a marker, and
    # exactly one marker lands per query.
    # !(test (unify A A (then-probe) (else-probe)) 3)
    assert m.eval(S.unify(S.A, S.A, *probes)) == [3]
    # !(test (collapse (match &self else-ran hit)) ())
    assert S.else_ran not in m
    # !(test (unify A B (then-probe) (else-probe)) 4)
    assert m.eval(S.unify(S.A, S.B, *probes)) == [4]
    # !(test (collapse (match &self then-ran hit)) (hit))
    assert S.then_ran in m

    # A space is a grounded atom whose custom matching is query, so a space
    # operand routes through match: one then-answer per stored match, the
    # else branch when nothing matches.
    # (friend Bob Alice) (friend Sam Alice)
    m += S.friend(S.Bob, S.Alice)
    m += S.friend(S.Sam, S.Alice)

    # !(test (collapse (unify &self (friend $who Alice) $who no-friends)) (Bob Sam))
    assert m.eval(S.unify(m, S.friend(V.who, S.Alice), V.who, S["no-friends"])) == [S.Bob, S.Sam]
    # !(test (unify &self (friend Pol $who) $who no-friends) no-friends)
    assert m.eval(S.unify(m, S.friend(S.Pol, V.who), V.who, S["no-friends"])) == [S["no-friends"]]

    # A variable operand binds the space whole without querying it.
    # !(test (unify $s &self bound queried) bound)
    assert m.eval(S.unify(V.s, m, S.bound, S.queried)) == [S.bound]

    # Empty in a branch is the branch remover: the else here answers nothing
    # at all, so the collapse is the empty expression. The collapsing has to
    # happen in the ENGINE, because `Empty` is what the branch answers and it
    # is the collapse that drops it: measured 2026-08-23, `m.eval` of the
    # unify answers `[Empty]` where collapsing it first answers `()`.
    # !(test (collapse (unify a b then Empty)) ())
    removed = S.unify(S.a, S.b, S.then, S.Empty)
    assert m.eval(S.collapse(removed)) == [Expression(())]  # rung: `collapse` is what drops the Empty marker, and a Python list does not
