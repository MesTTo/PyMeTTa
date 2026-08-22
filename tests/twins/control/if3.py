"""examples/control/if3.metta in Python: an unbound variable IS one.

The companion of if2: there the argument was a symbol and `is-var` answered
False, here it is `$A` and the then arm runs, which is itself an `if`.

Both `if`s are Python conditional expressions, compiled; the condition is
asked at the call for if2's reason, that `is-var` is hyphenated and a compiled
body reaches a function only by a name it can write. `lol` is capitalised for
the same reason a compiled body reads `Lol` as data and `lol` as a function to
call.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 806 to 3921, +3115 (+386.5%), by lifting this twin
#: to the definitional door now that the band pays for authoring: both `if`s
#: ENTERED the engine as compiled Python conditional expressions, with the
#: condition still crossing as a term for if2's hyphen reason. Measured min-
#: of-3 over fresh processes with the MORK backend linked in; against the
#: example's 2317 the ratio is 1.6923, and the ceiling is 4770, the example
#: plus 10% plus 2221 to author 1 definition. Prior: 806, the term-door twin
#: the old band forced.
BUDGET = 3921


def twin(m):
    """Ask whether a variable is a variable, and take the arm that answers."""
    @m.define
    def chosen(flag):
        # (if <flag> (if True 42 lol) (+ 2 2))
        return (42 if True else Lol) if flag else 2 + 2  # noqa: F821  -- a capitalised free name in a compiled body is MeTTa data, which has no Python value to bind

    # !(test (if (is-var $A) (if True 42 lol) (+ 2 2)) 42)
    assert chosen(S["is-var"](V.A)) == [42]
