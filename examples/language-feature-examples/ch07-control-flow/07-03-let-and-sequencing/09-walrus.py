"""Purpose: examples/ch07-control-flow/07-03-let-and-sequencing/09-walrus.metta in Python: the walrus is let.

PEP 572's `:=` binds a name in the expression it stands in and leaves it
visible after, which is exactly what `let*` does around a continuation, so
the compiler hoists a walrus into the binding the source means: bound in a
return value here, bound in an if test there, read again in both. `//` is
the engine's own floor-div, so the halved value stays the integer the
source computes.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S


def twin(m):
    """Bind with := where the value is first needed, then read it again."""

    @m.define
    def double_used(n):
        # (let* (($big (* $n 10))) (+ $big $big))
        return (big := n * 10) + big

    # !(test (double-used 3) 60)
    assert double_used(3) == [60]

    @m.define
    def guarded_half(n):
        # (let* (($half (floor-div $n 2))) (if (< $half 10) $half nope))
        if (half := n // 2) < 10:
            return half
        return S.nope

    # !(test (guarded-half 8) 4)
    assert guarded_half(8) == [4]
    # !(test (guarded-half 40) nope)
    assert guarded_half(40) == [S.nope]


#: PLACEHOLDER, never measured in this worktree: the corpus pricing pass
#: prices every budget in one run on the final tree
#: [assumed: BUDGET states no measured cost; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 1 to 4956 (+4955), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
BUDGET = 4956
