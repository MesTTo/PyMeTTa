"""The Python twin of examples/types/outputtype.metta: the output type decides.

One body, `(+ $x 42)`, three declarations, three answers. `%Undefined%` lets
the sum run and answers 44; `Atom` on the OUTPUT stops the result being
evaluated, so `g` answers the term `(+ 2 42)`; and `Atom` on the input as well
stops the argument evaluating too, so `h` answers `(+ (+ 1 1) 42)`.

The declarations are written as atoms rather than as Python annotations, and
the reason is a defect this file is the reproducer for. `@m.define` reads a
signature and writes `(: name (-> ...))`, which is the door P14.9 names, but it
writes it AFTER storing the equation, and an OUTPUT type decides how the
equation's own body treats its result. Measured on this tree: `def g(x: int)
-> Atom: return x + 42` stores `(: g (-> Number Atom))` in the space and still
answers `44`, where the identical declaration added before the identical
compiled equation answers `(+ 2 42)`. An INPUT type is read at the call site
and does work through the annotation door, which is why
`types/functiontypes.py` uses it. The residue table routes the ordering to
P14.9.

So the declaration is an atom and the equation is a compiled function with no
annotations, which is the pair that behaves.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
BUDGET = 6895


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (: f (-> Number %Undefined%))
    m += S[":"](S.f, S["->"](S.Number, S["%Undefined%"]))

    @m.define
    def f(x):
        # (= (f $x) (+ $x 42))
        return x + 42

    # (: g (-> Number Atom))
    m += S[":"](S.g, S["->"](S.Number, S.Atom))

    @m.define
    def g(x):
        # (= (g $x) (+ $x 42))
        return x + 42

    # (: h (-> Atom Atom))
    m += S[":"](S.h, S["->"](S.Atom, S.Atom))

    @m.define
    def h(x):
        # (= (h $x) (+ $x 42))
        return x + 42

    # !(test (f (+ 1 1)) 44)
    yield m.eval(S.test(f(S["+"](1, 1)), 44))
    # quote retains its wrapper in LeaTTa; noeval is the payload-preserving
    # form these expected expressions require.
    # !(test (g (+ 1 1)) (noeval (+ 2 42)))
    yield m.eval(
        S.test(g(S["+"](1, 1)), S.noeval(S["+"](2, 42)))
    )
    # !(test (h (+ 1 1)) (noeval (+ (+ 1 1) 42)))
    yield m.eval(
        S.test(
            h(S["+"](1, 1)),
            S.noeval(S["+"](S["+"](1, 1), 42)),
        )
    )
