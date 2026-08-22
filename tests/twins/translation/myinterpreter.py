"""The Python twin of examples/translation/myinterpreter.metta.

A three-line interpreter written in MeTTa: because `myinterpreter`'s parameter
is typed `Atom`, the argument arrives UNREDUCED, and the body runs it with
`eval` after printing it. Laziness is callee-declared, which is why the
declaration is the whole mechanism.

`w` and `v` are computations and are written as ones. `myinterpreter` stays at
the container door, and its declaration with it: the body names `println!`,
which is not a Python identifier and therefore not a name a compiled body can
resolve, and the residue table records that against P14.4. Its type would have
come from a `code: Atom` annotation had the body compiled.

The two runnable forms build `(== 1 1)` with `val(1).eq(1)`, the atom method,
because Python's `==` on atoms is structural equality and answers a bool.
"""

from petta import S, V, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5361 to 7183, +1822 (+33.99%), by the wave-4 idiom
#: rewrite moving `w` and `v` onto @m.define. COMPILING a definition costs
#: more than STORING one, and the difference is paid once per process plus a
#: little per definition, never per call: four trivial one-parameter
#: definitions in a fresh process measured 2221 / 2986 / 3751 / 4516
#: inferences through @m.define against 592 / 1164 / 1736 / 2308 through
#: `m += equation(...).to(...)`, so the first compiled definition costs 1,629
#: more and each one after it 193 more. Two nullary definitions here measured
#: exactly 1,822 over the same file with both stored, which is that first
#: charge plus one more definition, 1629 + 193.
BUDGET = 7183


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # (: myinterpreter (-> Atom %Undefined%))
    m += S[":"](S.myinterpreter, S["->"](S.Atom, S["%Undefined%"]))

    # (= (myinterpreter $code)
    #    (let $temp (println! ("Runtime-interpreting code" $code))
    #         (eval $code)))
    m += equation(S.myinterpreter(V.code)).to(
        S.let(
            V.temp,
            S["println!"]((val("Runtime-interpreting code"), V.code)),
            S.eval(V.code),
        )
    )

    @m.define
    def w():
        # (= (w) 42)
        return 42

    @m.define
    def v():
        # (= (v) 43)
        return 43

    # !(test (myinterpreter (if (== 1 1) (w) (v))) 42)
    yield m.eval(
        S.test(S.myinterpreter(S["if"](val(1).eq(1), S.w(), S.v())), 42)
    )
    # !(test (myinterpreter (if (== 1 2) (w) (v))) 43)
    yield m.eval(
        S.test(S.myinterpreter(S["if"](val(1).eq(2), S.w(), S.v())), 43)
    )
