"""examples/control/unify.metta in Python: the matching conditional.

`(unify a b then else)` runs the then branch once per binding set under which
a and b match, and the else branch exactly when no binding set exists. The
operands cross unevaluated, all four arguments are typed Atom, and only the
selected branch runs.

`unify` keeps MeTTa's name because Python has no expression that matches two
terms and chooses a branch: `petta.unify(pattern, atom)` answers bindings on
atoms Python already holds, which is a different act, and the four-argument
form the ledger designs is not built yet. What does move into Python is
everything around it: a stored marker is asked for with `in`, which IS match
containment, and the two probes are ordinary definitions whose effect goes
through the one door an effect goes through, a grounded operation.

The two markers are capitalised and wrapped. A compiled body reads a
lowercase free name as a function and a capitalised one as data, the gap case2
records against P14.4; and `m.add` refuses a bare symbol, "a stored atom is a
non-empty expression", where MeTTa's own `add-atom` stores one, so the marker
is `(Ran ThenRan)` rather than `then-ran`. Both are filed as residue.
"""

from petta import Atom, S, V, expr, val

#: The two strings the ground decisions compare, carried whole.
STRING_X, STRING_Y = val("x"), val("y")

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9314 to 10397, +1083 (+11.6%), by the twin contract
#: change: the two probe definitions ENTERED the engine as compiled bodies
#: calling a grounded operation, which pays `@m.define`'s fixed registration
#: twice plus one crossing per probe; fifteen `test` wrappers and two
#: collapses LEFT for `assert`s and Python's `in`, which IS match
#: containment. Measured min-of-3 over fresh processes with the MORK backend
#: linked in, which the artefact-free worktree omits and which moves a
#: compiled twin by about 10 inferences per definition; against the example's
#: 20259 the ratio is 0.5132. Prior: 9314, the transliterated twin this
#: replaces.
BUDGET = 10397


def twin(m):
    """Match ground terms, terms with variables, and a space."""
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

    @m.op
    def mark(tag: Atom) -> bool:
        """Store the marker, through the write door spelled as a method.

        `space += atom` is the door; `+=` would rebind the name inside this
        closure, so the same write is spelled as the method it already is.
        """
        m.add(tag)
        return True

    @m.define(name="then-probe")
    def then_probe():
        # (= (then-probe) (chain (add-atom &self then-ran) $_ 3))
        _ = mark(Ran(ThenRan))  # noqa: F821  -- capitalised free names in a compiled body are MeTTa data, which has no Python value to bind
        return 3

    @m.define(name="else-probe")
    def else_probe():
        # (= (else-probe) (chain (add-atom &self else-ran) $_ 4))
        _ = mark(Ran(ElseRan))  # noqa: F821  -- the other marker, the same way
        return 4

    probes = (S["then-probe"](), S["else-probe"]())

    # Only the selected branch evaluates: each probe leaves a marker, and
    # exactly one marker lands per query.
    # !(test (unify A A (then-probe) (else-probe)) 3)
    assert m.eval(S.unify(S.A, S.A, *probes)) == [3]
    # !(test (collapse (match &self else-ran hit)) ())
    assert S.Ran(S.ElseRan) not in m
    # !(test (unify A B (then-probe) (else-probe)) 4)
    assert m.eval(S.unify(S.A, S.B, *probes)) == [4]
    # !(test (collapse (match &self then-ran hit)) (hit))
    assert S.Ran(S.ThenRan) in m

    # A space is a grounded atom whose custom matching is query, so a space
    # operand routes through match: one then-answer per stored match, the
    # else branch when nothing matches.
    # (friend Bob Alice) (friend Sam Alice)
    m += S.friend(S.Bob, S.Alice)
    m += S.friend(S.Sam, S.Alice)

    # !(test (collapse (unify &self (friend $who Alice) $who no-friends)) (Bob Sam))
    here = S[m.space_name]
    assert m.eval(S.unify(here, S.friend(V.who, S.Alice), V.who, S["no-friends"])) == [S.Bob, S.Sam]
    # !(test (unify &self (friend Pol $who) $who no-friends) no-friends)
    assert m.eval(S.unify(here, S.friend(S.Pol, V.who), V.who, S["no-friends"])) == [S["no-friends"]]

    # A variable operand binds the space whole without querying it.
    # !(test (unify $s &self bound queried) bound)
    assert m.eval(S.unify(V.s, here, S.bound, S.queried)) == [S.bound]

    # Empty in a branch is the branch remover: the else here answers nothing
    # at all, so the collapse is the empty expression. The collapsing has to
    # happen in the ENGINE, because `Empty` is what the branch answers and it
    # is the collapse that drops it: measured 2026-08-22, `m.eval` of the
    # unify answers `[Sym('Empty')]` where collapsing it first answers `()`.
    # !(test (collapse (unify a b then Empty)) ())
    removed = S.unify(S.a, S.b, S.then, S.Empty)
    assert m.eval(S.collapse(removed)) == [expr()]  # rung: `collapse` is what drops the Empty marker, and a Python list does not
