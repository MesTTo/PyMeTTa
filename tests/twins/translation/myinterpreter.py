"""examples/translation/myinterpreter.metta in Python: an interpreter in three lines.

A parameter typed `Atom` receives its argument UNREDUCED, so `myinterpreter`
gets the `(if ...)` term itself and decides when to evaluate it. That is the
whole of MeTTa's quoting story: laziness is declared by the callee, not spelled
at the call site.

Which is why the two `if` terms below are DATA. They are built at the `S.` door
and handed over as arguments, never run as control flow, so Python's own `if`
is not the spelling for them even though it is the spelling everywhere else.

The interpreter itself is at the container door: its body calls `println!`,
which a compiled body has no way to spell, and binds the result of that call
with a `let` whose only purpose is sequencing (residue, P14.4). `w` and `v` are
ordinary compiled definitions, which is what makes the point that the code
being interpreted is the same code anything else would call.
"""

from petta import S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 7183 to 6900, -283 (-3.9%), by the twin contract
#: change: two `(test (myinterpreter ...) ...)` terms became two Python
#: `assert`s, so the `test` wrapper left the engine twice while both
#: interpretations, both printed lines and all three definitions stayed in it.
#: Against the example's 9344 the ratio is 0.7384.
#: Prior: 7183, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 6900


def twin(m):
    """Define an interpreter, then hand it two branches to interpret."""
    # (: myinterpreter (-> Atom %Undefined%)): the Atom parameter is what makes
    # the argument arrive unreduced.
    m += S[":"](S.myinterpreter, S["->"](S.Atom, S["%Undefined%"]))

    # (= (myinterpreter $code)
    #    (let $temp (println! ("Runtime-interpreting code" $code)) (eval $code)))
    announce = S["println!"]((val("Runtime-interpreting code"), V.code))  # rung: a compiled body has no spelling for println!
    m += equation(S.myinterpreter(V.code)).to(S.let(V.said, announce, S.eval(V.code)))  # rung: a let whose only job is sequencing a call it then ignores

    @m.define
    def w():
        return 42

    @m.define
    def v():
        return 43

    assert m.one(S.myinterpreter(S["if"](S["=="](1, 1), S.w(), S.v()))) == 42  # rung: this `if` is DATA, the unreduced argument of an Atom-typed parameter
    assert m.one(S.myinterpreter(S["if"](S["=="](1, 2), S.w(), S.v()))) == 43  # rung: as above
