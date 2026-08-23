"""Purpose: examples/control/and_then_or_else.metta in Python: short-circuiting.

`and-then` and `or-else` are the short-circuiting boolean connectives. They
are special forms rather than functions, which is the whole point: a
function's arguments are evaluated before the call, so a function could not
skip its second one.

Python's own `and` and `or` are those two forms exactly. Inside a compiled
body they lower to a binding plus a test that answers the DECIDING OPERAND,
so `a and b` is `(and-then $a $b)` down to which value comes back, and the
argument that is not chosen is never evaluated, because a compiled body's
arguments are syntax rather than calls.

They are not a second spelling of `and` and `or`. Those are RELATIONAL: they
evaluate both sides and can solve for an unbound argument. Python has no
relational `and`, so that one keeps MeTTa's name, and so does the `if` in the
last claim, which is there only to expose the bindings a solved answer would
carry.

The original opens a second space to keep its two experiments apart. Python
keeps them apart with a slice of the first, so `note2` records into the same
space `note` does and the two equations really are the same equation twice,
which is what the original's two are once the space is factored out.

The write itself goes through a grounded operation. A compiled body reaches a
space that is a PARAMETER or the context space, and `&ran` is neither: it is a
host value the body would have to close over, which would pin the equation to
this process. Filed as residue against P14.4.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import FALSE, TRUE, Atom, S, V

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Skip a branch, take a branch, and prove which one ran."""
    ran = metta.space("&ran")

    # The top rung writes from inside the equation, with no operation at all:
    #
    #     @m.define
    #     def note(tag):
    #         ran += S.ran(tag)      # a body statement that lowers to add-atom
    #         return True
    #
    # A compiled body is pure atoms and reaches a space that is a PARAMETER or
    # `(context-space)`; `&ran` is neither, so closing over it would pin the
    # equation to this process. control/unify and control/eval write over
    # `(context-space)` and need no operation; this file cannot, because its
    # two experiments must not share `&self`. Residue: P14.4.
    @m.op
    def record(tag: Atom) -> bool:
        """Write the tag and answer True: `space += atom` is add-atom's door."""
        ran.add(S.ran(tag))
        return True

    @m.define
    def note(tag):
        # (= (note $tag) (let $_ (add-atom &ran (ran $tag)) True))
        return record(tag)

    @m.define
    def note2(tag):
        # (= (note2 $tag) (let $_ (add-atom &ran2 (ran $tag)) True))
        return record(tag)

    @m.define
    def both(a, b):
        # (and-then $a $b)
        return a and b

    @m.define
    def either(a, b):
        # (or-else $a $b)
        return a or b

    # !(test (and-then True yes) yes)
    assert both(TRUE, S.yes) == [S.yes]
    # !(test (and-then False yes) False)
    assert both(FALSE, S.yes) == [False]
    # !(test (or-else True no) True)
    assert either(TRUE, S.no) == [True]
    # !(test (or-else False fallback) fallback)
    assert either(FALSE, S.fallback) == [S.fallback]

    # They take expressions, not just literals. An argument that is a term
    # reduces on the way in, which is what the original's do too.
    # !(test (and-then (> 2 1) (> 3 2)) True)
    assert both(S[">"](2, 1), S[">"](3, 2)) == [True]
    # !(test (or-else (> 1 2) (> 3 2)) True)
    assert either(S[">"](1, 2), S[">"](3, 2)) == [True]

    @m.define
    def gated(flag, tag):
        # (and-then $flag (note $tag)): the note is a call the body COMPILES,
        # so whether it runs is the engine's decision, not Python's
        return flag and note(tag)

    @m.define(name="fallback")
    def fell_back(flag, tag):
        # (or-else $flag (note $tag))
        return flag or note(tag)

    # Each form is run by READING its answer: creating the answer view does no
    # engine work, so a call whose result is dropped never reaches the engine
    # and the skipping this file is about would be unobservable.
    # !(and-then False (note skipped-by-and-then))
    assert gated(FALSE, S["skipped-by-and-then"]) == [False]
    # !(or-else True (note skipped-by-or-else))
    assert fell_back(TRUE, S["skipped-by-or-else"]) == [True]
    # !(and-then True (note taken-by-and-then))
    assert gated(TRUE, S["taken-by-and-then"]) == [True]
    # !(or-else False (note taken-by-or-else))
    assert fell_back(FALSE, S["taken-by-or-else"]) == [True]

    # !(test (collapse (get-atoms &ran))
    #        ((ran taken-by-and-then) (ran taken-by-or-else)))
    assert list(ran) == [S.ran(S["taken-by-and-then"]), S.ran(S["taken-by-or-else"])]

    # The contrast, in one place: `and` does NOT skip, so its second argument
    # runs even though the first is False. Both forms are written the same way
    # so the pair stays comparable.
    # The original opens `&ran2` to keep this experiment apart. The top rung
    # would open a second space here too, `metta.space("&ran2")`, and `note2`
    # would write into it; a compiled body cannot name either, so both
    # equations route through the one operation and the experiments are kept
    # apart by a slice of the same space instead. Residue: P14.4, the same
    # entry as the write above.
    already = len(ran)
    # !(and False (note2 and-runs-it))
    m.eval(S["and"](FALSE, S.note2(S["and-runs-it"])))
    # !(and-then False (note2 and-then-skips-it))
    m.eval(S["and-then"](FALSE, S.note2(S["and-then-skips-it"])))

    # !(test (collapse (get-atoms &ran2)) ((ran and-runs-it)))
    assert list(ran)[already:] == [S.ran(S["and-runs-it"])]

    # And the other side of the trade: and-then cannot be solved backwards,
    # where `and` can.
    # !(test (collapse (if (and-then (or-else $p True) $q) ($p $q))) ())
    unsolved = S["and-then"](S["or-else"](V.p, TRUE), V.q)
    assert m.eval(S["if"](unsolved, (V.p, V.q))) == []  # rung: the `if` is what exposes the bindings, and a two-argument `if` has no Python conditional to be
