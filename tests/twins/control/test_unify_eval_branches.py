"""Purpose: examples/control/test_unify_eval_branches.metta in Python: branches evaluate.

Space-based `unify` evaluates the branch it selects, both of them. Without
that, the then branch of a matched case would answer `(+ 1 2)` instead of 3,
and a nested `unify` in an else branch would come back unrun. The shape is
pverify's: an `Error` atom when a declaration already exists, and a nested
check in the else branch when it does not.

`unify` keeps MeTTa's name, for the reason unify.metta gives: Python has no
expression that matches two terms and chooses a branch. What is ordinary
Python here is the knowledge: two facts go in through the write door, the
space operand is the handle itself, and the strings the errors carry are named
once and carried whole.

`lib_he` takes the bracket. The factory's attribute map is total, so
`S.lib_he` is the atom `lib-he` and the import would look for a library of
that name; the library on disk is `lib/lib_he.metta`.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, ground

# THIS FILE'S NAME IS A DEFECT. It begins with `test_`, so pytest treats it as a
# test module and imports it during collection, and the twins wave owed it a
# rename. The rename is blocked: `twin_coverage.twin_for` is a pure path
# transform from the example's path, and `orphans()` reports any .py under
# `twins/` that no example derives, which `test_the_twin_set_is_derived_from_
# the_one_corpus` asserts is empty. So renaming this file alone makes the lane
# exit 2 on `examples/control/test_unify_eval_branches.metta` and turns that
# gate test red, and a `conftest.py` beside it would itself be an orphan. The
# fix is one of two things the integrator owns: rename the EXAMPLE and this
# file together, updating `tests/check_upstream_parity.py` and
# `tests/upstream-parity-baseline.json` with them; or set `python_files` in
# `bindings/python/pyproject.toml` so `tests/twins/**` is never collected.
# Until then the module imports cleanly and defines no `test_*` name, so
# `pytest --collect-only` over this directory reports no tests and no errors.

#: The strings the knowledge and the errors carry, carried whole rather than
#: parsed: `$c` and `$v` are metamath's constant and variable markers, and the
#: two sentences are the messages the errors are made of.
CONSTANT, VARIABLE = ground("$c"), ground("$v")
DECLARED = ground("already declared")
CONFLICT = ground("active variable conflict")

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Take a then branch, an else branch, and a nested else branch."""
    # !(import! &self (library lib_he))
    m.eval(S["import!"](m, (S.library, S["lib_he"])))

    # (Constant wff (Type "$c"))
    m += S.Constant(S.wff, S.Type(CONSTANT))
    # (Var x 0 (Type "$v"))
    m += S.Var(S.x, 0, S.Type(VARIABLE))

    nothing = Expression(())

    # Test 1: then-branch needs eval (expression in matched case)
    # !(test (unify &self (Constant wff (Type "$c"))
    #          (Error (Constant wff) "already declared") ())
    #        (Error (Constant wff) "already declared"))
    already = S.Error(S.Constant(S.wff), DECLARED)
    assert m.eval(S.unify(m, S.Constant(S.wff, S.Type(CONSTANT)), already, nothing)) == [already]

    # Test 2: else-branch needs eval (fallthrough to nested unify)
    # !(test (unify &self (Constant y (Type "$c")) (Error (Constant y) "already declared")
    #          (unify &self (Var y 0 (Type "$v")) (Error (Var y) "active variable conflict") ()))
    #        ())
    y_conflict = S.unify(m, S.Var(S.y, 0, S.Type(VARIABLE)), S.Error(S.Var(S.y), CONFLICT), nothing)
    y_declared = S.Error(S.Constant(S.y), DECLARED)
    assert m.eval(S.unify(m, S.Constant(S.y, S.Type(CONSTANT)), y_declared, y_conflict)) == [nothing]

    # Test 3: else-branch nested unify hits (real conflict chain)
    # !(test (unify &self (Constant x (Type "$c")) (Error (Constant x) "already declared")
    #          (unify &self (Var x 0 (Type "$v")) (Error (Var x) "active variable conflict") ()))
    #        (Error (Var x) "active variable conflict"))
    x_conflicted = S.Error(S.Var(S.x), CONFLICT)
    x_conflict = S.unify(m, S.Var(S.x, 0, S.Type(VARIABLE)), x_conflicted, nothing)
    x_declared = S.Error(S.Constant(S.x), DECLARED)
    assert m.eval(S.unify(m, S.Constant(S.x, S.Type(CONSTANT)), x_declared, x_conflict)) == [x_conflicted]

    # Test 4: arithmetic in branches (minimal reproducer)
    # !(test (unify &self (Constant wff (Type "$c")) (+ 1 2) 0) 3)
    assert m.eval(S.unify(m, S.Constant(S.wff, S.Type(CONSTANT)), S["+"](1, 2), 0)) == [3]

    # Test 5: arithmetic in else-branch
    # !(test (unify &self (Constant NOSUCH (Type "$c")) 0 (+ 10 20)) 30)
    assert m.eval(S.unify(m, S.Constant(S.NOSUCH, S.Type(CONSTANT)), 0, S["+"](10, 20))) == [30]
