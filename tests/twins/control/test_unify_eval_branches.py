"""Purpose: examples/control/test_unify_eval_branches.metta in Python: branches evaluate.

Space-based `unify` evaluates the branch it selects, both of them. Without
that, the then branch of a matched case would answer `(+ 1 2)` instead of 3,
and a nested `unify` in an else branch would come back unrun. The shape is
pverify's: an `Error` atom when a declaration already exists, and a nested
check in the else branch when it does not.

`unify` keeps MeTTa's name, for the reason unify.metta gives: Python has no
expression that matches two terms and chooses a branch. What is ordinary
Python here is the knowledge: two facts go in through the write door, and the
strings the errors carry are named once and carried whole.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, val

#: The strings the knowledge and the errors carry, carried whole rather than
#: parsed: `$c` and `$v` are metamath's constant and variable markers, and the
#: two sentences are the messages the errors are made of.
CONSTANT, VARIABLE = val("$c"), val("$v")
DECLARED = val("already declared")
CONFLICT = val("active variable conflict")

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 12097 to 10851, -1246 (-10.3%), by the twin contract
#: change: five `test` wrappers LEFT the engine for `assert`s and the two
#: facts entered through `+=`; the five `unify` calls and the library import
#: still run there. Measured min-of-3 over fresh processes with the MORK
#: backend linked in, which the artefact-free worktree omits and which moves
#: a compiled twin by about 10 inferences per definition; against the
#: example's 21134 the ratio is 0.5134. Prior: 12097, the transliterated twin
#: this replaces.
BUDGET = 10851


def twin(m):
    """Take a then branch, an else branch, and a nested else branch."""
    # !(import! &self (library lib_he))
    m.eval(S["import!"](S[m.space_name], (S.library, S.lib_he)))

    # (Constant wff (Type "$c"))
    m += S.Constant(S.wff, S.Type(CONSTANT))
    # (Var x 0 (Type "$v"))
    m += S.Var(S.x, 0, S.Type(VARIABLE))

    here = S[m.space_name]
    nothing = Expression(())

    # Test 1: then-branch needs eval (expression in matched case)
    # !(test (unify &self (Constant wff (Type "$c"))
    #          (Error (Constant wff) "already declared") ())
    #        (Error (Constant wff) "already declared"))
    already = S.Error(S.Constant(S.wff), DECLARED)
    assert m.eval(S.unify(here, S.Constant(S.wff, S.Type(CONSTANT)), already, nothing)) == [already]

    # Test 2: else-branch needs eval (fallthrough to nested unify)
    # !(test (unify &self (Constant y (Type "$c")) (Error (Constant y) "already declared")
    #          (unify &self (Var y 0 (Type "$v")) (Error (Var y) "active variable conflict") ()))
    #        ())
    y_conflict = S.unify(here, S.Var(S.y, 0, S.Type(VARIABLE)), S.Error(S.Var(S.y), CONFLICT), nothing)
    y_declared = S.Error(S.Constant(S.y), DECLARED)
    assert m.eval(S.unify(here, S.Constant(S.y, S.Type(CONSTANT)), y_declared, y_conflict)) == [nothing]

    # Test 3: else-branch nested unify hits (real conflict chain)
    # !(test (unify &self (Constant x (Type "$c")) (Error (Constant x) "already declared")
    #          (unify &self (Var x 0 (Type "$v")) (Error (Var x) "active variable conflict") ()))
    #        (Error (Var x) "active variable conflict"))
    x_conflicted = S.Error(S.Var(S.x), CONFLICT)
    x_conflict = S.unify(here, S.Var(S.x, 0, S.Type(VARIABLE)), x_conflicted, nothing)
    x_declared = S.Error(S.Constant(S.x), DECLARED)
    assert m.eval(S.unify(here, S.Constant(S.x, S.Type(CONSTANT)), x_declared, x_conflict)) == [x_conflicted]

    # Test 4: arithmetic in branches (minimal reproducer)
    # !(test (unify &self (Constant wff (Type "$c")) (+ 1 2) 0) 3)
    assert m.eval(S.unify(here, S.Constant(S.wff, S.Type(CONSTANT)), S["+"](1, 2), 0)) == [3]

    # Test 5: arithmetic in else-branch
    # !(test (unify &self (Constant NOSUCH (Type "$c")) 0 (+ 10 20)) 30)
    assert m.eval(S.unify(here, S.Constant(S.NOSUCH, S.Type(CONSTANT)), 0, S["+"](10, 20))) == [30]
