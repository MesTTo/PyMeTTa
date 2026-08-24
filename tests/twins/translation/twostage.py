"""examples/translation/twostage.metta in Python: a call before its callee exists.

Three nullary equations, and the order they are written in is the subject. `f`
is stored before `g`, so its body names something the engine does not yet know;
`h` is stored after, so its body names a function. Both answer 42, which is the
two-stage claim: a call compiled against a name that is only data at the time
is re-dispatched once the name becomes a function.

Python spells that difference with the two doors the guide already has for it.
Calling the SYMBOL, `S.g()`, mentions a head and builds `(g)`, which is what
you write for a name nothing has defined; calling the Python name, `g()`, is an
application of a function that exists. The compiler says the same thing from
the other side, refusing an unknown callee and naming `S.g` as the remedy.
"""

from metta import S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
BUDGET = 1


def twin(m):
    """Install the three nullary equations in their original order."""

    @m.define
    def f():
        return S.g()        # (= (f) (g)): g is not a function yet, so it is data

    @m.define
    def g():                # (= (g) 42)
        return 42

    @m.define
    def h():
        return g()          # (= (h) (g)): now g is a name a body can call

    assert f().one() == 42  # [42]
    assert h().one() == 42  # [42]
