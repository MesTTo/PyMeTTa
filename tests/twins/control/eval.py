"""The Python twin of examples/control/eval.metta: running a retrieved body.

`match` does not interpret what it retrieves, so matching an equation's head
answers its BODY as data; `eval` then runs that data. The second half emulates
the same thing with `add-atom` and `remove-atom`, which the original marks as
not recommended and keeps because it shows what `eval` saves.

`f` is a computation and is written as one: `result = a + b` is exactly the
`let` the original writes, and `(result,)` is the one-element expression
`($result)`. The stored body comes out as `let*` with one pair rather than
`let`, which is the same binding, and the retrieval above still finds it
because a match reads the equation's HEAD.

`evalCustom` is written at the container door: its body names `add-atom`,
`remove-atom` and `reduce`, and a compiled body resolves a free name EXACTLY,
so a hyphenated engine function cannot be reached from one (wave one recorded
that against P14.4 for `fibsmart`).
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5658 to 5975, +317, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 5658 by 47554fc's control/types twin baseline.
BUDGET = 5975


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    append = m.fn("append")

    @m.define
    def f(li, a, b):
        # (= (f $L $a $b) (let $result (+ $a $b) (append ($result) $L)))
        result = a + b
        return append((result,), li)

    # Match does not automatically interpret the returned pattern as code,
    # but we can eval after it if we desire.
    # !(test (let $fbody_specialized (match &self (= (f (42) 40.7 2) $x) $x)
    #          (eval $fbody_specialized))
    #        (42.7 42))
    retrieved = S["match"](
        S["&self"],
        S["="](S.f(expr(42), 40.7, 2), V.x),
        V.x,
    )
    yield m.eval(
        S.test(
            S["let"](V.body, retrieved, S["eval"](V.body)),
            expr(42.7, 42),
        )
    )

    # (= (evalCustom $body)
    #    (let* (($a   (add-atom &self (= (myfunc) $body)))
    #           ($res (reduce (myfunc)))
    #           ($r   (remove-atom &self (= (myfunc) $body))))
    #          $res))
    equation = S["="](S.myfunc(), V.body)
    m += S["="](
        S.evalCustom(V.body),
        S["let*"](
            expr(
                expr(V.a, S["add-atom"](S["&self"], equation)),
                expr(V.res, S["reduce"](S.myfunc())),
                expr(V.r, S["remove-atom"](S["&self"], equation)),
            ),
            V.res,
        ),
    )

    # !(test (evalCustom (match &self (= (f (42) 40.7 2) $x) $x)) (42.7 42))
    # DECLINED: the form ANSWERS correctly, and it cannot be PRICED. Running
    # it stores an equation whose body carries a variable the match minted,
    # and the cost of compiling that equation moves with the variable's
    # identity: measured over six fresh processes, the original costs
    # 14,781-14,805 inferences and a twin that runs the form costs
    # 12,870-12,914, against the lane's allowance of 4. The residue table
    # routes that to P14.14, which owns the budget law.
    yield None
