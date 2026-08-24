"""examples/translation/myinterpreter.metta in Python: an interpreter in three lines.

A parameter typed `Atom` receives its argument UNREDUCED, so `myinterpreter`
gets the `(if ...)` term itself and decides when to evaluate it. That is the
whole of MeTTa's quoting story: laziness is declared by the callee, not spelled
at the call site, and the declaration is Python's own annotation. `-> Any` is
the unconstrained result type, so the pair of them is the example's
`(: myinterpreter (-> Atom %Undefined%))` said in Python.

The body compiles too. Announcing the code is `println!` reached at the
function namespace, whose bang the resolver supplies, and the original's `let`
around it is a Python assignment to a name it then ignores. The string is a
MeTTa string literal, because a compiled body's constants are what the stored
equation holds.

Which is why the two `if` terms below are DATA. They are handed to an
Atom-typed parameter and never run as control flow, so the keyword builder is
their spelling: `if_` has the arity the engine's `if` has, and `S.eq` is `==`
at the word door.
"""

from typing import Any

from metta import Atom, S, fn, if_

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
BUDGET = 1


def twin(m):
    """Define an interpreter, then hand it two branches to interpret."""

    @m.define
    def myinterpreter(code: Atom) -> Any:
        # (= (myinterpreter $code)
        #    (let $temp (println! ("Runtime-interpreting code" $code)) (eval $code)))
        _said = fn.println(("Runtime-interpreting code", code))
        return S.eval(code)

    @m.define
    def w():                                   # (= (w) 42)
        return 42

    @m.define
    def v():                                   # (= (v) 43)
        return 43

    assert myinterpreter(if_(S.eq(1, 1), S.w(), S.v())).one() == 42   # [42]
    assert myinterpreter(if_(S.eq(1, 2), S.w(), S.v())).one() == 43   # [43]
