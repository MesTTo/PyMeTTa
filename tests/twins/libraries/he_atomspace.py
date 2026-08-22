"""The Python twin of examples/libraries/he_atomspace.metta.

Storing a definition unreduced against storing its reduct, and the space-relative
readings of get-type and unify.

`(+ 1 3)` is a term over two GROUND numbers, and Python's own `+` on two ground
numbers is Python arithmetic: it answers 4 before any term exists. So the head is
named instead.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.

`equation(...).to(...)` builds the `(= ...)` term in both positions it is needed:
as the datum `add-atom` stores, and as the PATTERN `match` looks for. That is the
same builder doing the same job, which is what makes an equation ordinary data
here rather than a special form.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11625 to 11625, +0 (+0.00%), by the P14 twin-style
#: rewrite: the twin's atoms are unchanged: equation(...).to(...) builds what
#: S["="](...) built, in both the datum and the pattern position. Prior:
#: ADDED 2026-08-22 at 11625 by the wave-3 libraries baseline, which recorded
#: no cause.
BUDGET = 11625

#: `(+ 1 3)` is a term over two GROUND numbers, and Python's own `+` on two
#: ground numbers is Python arithmetic: it answers 4 before any term exists. So
#: the head is named, which is the door the design authority gives for exactly
#: this ("operators build terms on symbolic operands and compute on ground
#: ones", §9b). Nothing else in this file drops a rung; the residue table
#: records the check refinement against P14.1.
def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(import! &self (library lib_he))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    # !(add-atom &self (= (addnormal) (+ 1 3)))
    yield m.eval(
        S["add-atom"](S["&self"], equation(S.addnormal()).to(S["+"](1, 3)))
    )
    # !(add-reduct &self (= (addreduct) (+ 1 3)))
    yield m.eval(
        S["add-reduct"](S["&self"], equation(S.addreduct()).to(S["+"](1, 3)))
    )

    # quote retains its wrapper in LeaTTa types-meta/30_evaluation_control.metta;
    # noeval holds the stored body without adding that wrapper.
    # !(test (match &self (= (addnormal) $X) $X) (noeval (+ 1 3)))
    yield m.eval(
        S.test(
            S.match(S["&self"], equation(S.addnormal()).to(V.X), V.X),
            S.noeval(S["+"](1, 3)),
        )
    )
    # 4, not (4). add-reduct is an engine builtin now and reduces the
    # definition's body to a VALUE.
    # !(test (match &self (= (addreduct) $X) (noeval $X)) 4)
    yield m.eval(
        S.test(
            S.match(S["&self"], equation(S.addreduct()).to(V.X), S.noeval(V.X)),
            4,
        )
    )

    # !(get-type 1)
    yield m.eval(S["get-type"](1))

    # (: a A)
    m += S[":"](S.a, S.A)
    # !(test (get-type-space &self a) A)
    yield m.eval(S.test(S["get-type-space"](S["&self"], S.a), S.A))

    # (hello world)
    m += S.hello(S.world)
    # !(test (unify &self (hello world) Yes No) Yes)
    yield m.eval(S.test(S.unify(S["&self"], S.hello(S.world), S.Yes, S.No), S.Yes))
    # !(test (unify &self (hello dream) Yes No) No)
    yield m.eval(S.test(S.unify(S["&self"], S.hello(S.dream), S.Yes, S.No), S.No))
