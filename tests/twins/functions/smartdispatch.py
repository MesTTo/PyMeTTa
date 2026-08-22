"""Purpose: examples/functions/smartdispatch.metta in Python: which heads run.

Five questions about the same two symbols. `(f 21)` reduces; `(g f 2)` keeps
`f` as DATA inside `(justdata f 2)`; `(h f 2)` applies it; `((notjustdata 42)
21)` computes the head first and then applies it; and
`(datawithnondatacomponent)` answers data with a call nested inside it, which
reduces where it sits. The original asks all five in one expression; here they
are five claims, which is the same reading with the answers named.

Three definitions are ordinary Python functions, including the two that make
the point: `h` applies its parameter (`f(x)` compiles to `($f $x)`) and
`notjustdata` ANSWERS one (a free name the engine knows compiles to that
symbol, so `return f` writes `f`).

The other two are equations, because their bodies are lowercase symbols used
as DATA: `justdata` and `lol` name nothing the engine defines, a compiled body
reads a lowercase free name as a call it cannot resolve, and the explicit
`S.justdata` spelling is refused there as well ("Attribute has no MeTTa
equivalent in the compiled subset"). `g` has variables in its head, so it
takes the `@rules` shape of the definitional decorator;
`datawithnondatacomponent` has none, so it is one `equation(...).to(...)` and
a generator around it would say nothing. The residue table records the gap
against P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, equation, rules

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9049 to 7964, -1085 (-12.0%), by the twin contract
#: change: the one `test` wrapper left the engine for `assert`, and the
#: original's single five-element question became five claims, each
#: evaluated on its own, which is the same reading with the answers named.
#: Against the example's 11293 the ratio is 0.7052 [measured 2026-08-22
#: min-of-3, `twin_coverage.py --measure`]. The old figure priced a
#: different program.
BUDGET = 7964


def twin(m):
    """Ask five heads what they do with a function as an argument."""

    @m.define
    def f(x):
        # (= (f $x) (* $x 2))
        return x * 2

    # rung: the body names `justdata`, a lowercase symbol used as DATA, which a
    #   compiled body reads as a call it cannot resolve (residue, P14.4)
    @rules
    def data_heads(f, x):
        # (= (g $f $x) (justdata $f $x))
        yield equation(S.g(f, x)).to(S.justdata(f, x))

    m.add(*data_heads)

    @m.define
    def h(f, x):
        # (= (h $f $x) ($f $x))
        return f(x)

    @m.define
    def notjustdata(_x):
        # (= (notjustdata $x) f)
        return f

    # (= (datawithnondatacomponent) ((lol (f 42))))
    # rung: the body names `lol`, a lowercase symbol used as DATA (residue, P14.4)
    m += equation(S.datawithnondatacomponent()).to((S.lol(S.f(42)),))

    assert f(21) == [42]
    assert m.eval(S.g(S.f, 2)) == [S.justdata(S.f, 2)]
    assert h(S.f, 2) == [4]
    assert m.eval((S.notjustdata(42), 21)) == [42]
    assert m.eval(S.datawithnondatacomponent()) == [Expression((S.lol(84),))]
