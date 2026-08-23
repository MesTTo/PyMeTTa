"""Purpose: examples/types/dont_eval_type.metta in Python: a user-declared lazy type.

`DontEvalType` is a kind of type, and a parameter declared with a type of that
kind receives its argument BEFORE evaluation. So `inspect-opaque` sees the term
`(+ 1 2)` rather than 3, and reports its metatype, Expression.

The declaration is an ordinary annotated signature: `OpaquePayload` is a Python
class so the parameter can name it, `Symbol` is the metatype class the answer
has, and `@m.define` publishes `(: inspect-opaque (-> OpaquePayload Symbol))`
from the two. Only the KIND declaration stays an atom, because `DontEvalType`
says something about the type rather than about a function.

The body names `get-metatype` through the function namespace. Python's own
`type()` is the metatype accessor out here, where the atom is already in hand,
and the last line says so by asking both sides about the same term; inside a
compiled body `type()` has no lowering, which is the friction P14.4 records.
"""

from metta import Expression, S, Symbol, fn, typed

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


class OpaquePayload:
    """The MeTTa type `OpaquePayload`, so a signature can name it."""


def twin(m):
    """Declare the lazy type, then read what the body was handed."""
    # (: OpaquePayload DontEvalType)
    m += typed(S.OpaquePayload, S.DontEvalType)

    @m.define
    def inspect_opaque(written: OpaquePayload) -> Symbol:
        """(= (inspect-opaque $written) (get-metatype $written))."""
        return fn.get_metatype(written)

    sum_term = S.add(1, 2)

    # !(test (inspect-opaque (+ 1 2)) Expression)
    assert inspect_opaque(sum_term) == [S.Expression]

    # The same question on the Python side of the seam: the metatype IS the
    # class, so nothing crosses to ask it.
    assert type(sum_term) is Expression
