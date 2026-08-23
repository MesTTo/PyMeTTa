"""Purpose: examples/functions/smartdispatch.metta in Python: which heads run.

Five questions about the same two symbols. `(f 21)` reduces; `(g f 2)` keeps
`f` as DATA inside `(justdata f 2)`; `(h f 2)` applies it; `((notjustdata 42)
21)` computes the head first and then applies it; and
`(datawithnondatacomponent)` answers data with a call nested inside it, which
reduces where it sits. The original asks all five in one expression; here they
are five claims, which is the same reading with the answers named.

All five definitions are ordinary Python functions, including the three that
make the point. `h` applies its parameter, so `f(x)` compiles to `($f $x)`;
`notjustdata` ANSWERS a symbol rather than calling it, and `S.f` is the
mention door for exactly that; and `justdata` and `lol` name nothing the
engine defines, being data constructors spelled in lowercase, which `S.justdata`
and `S.lol` say inside a body without the compiler having to guess from
capitalisation.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Ask five heads what they do with a function as an argument."""

    @m.define
    def f(x):
        # (= (f $x) (* $x 2))
        return x * 2

    @m.define
    def g(f, x):
        # (= (g $f $x) (justdata $f $x)): `justdata` defines nothing, so it is
        # data, and the mention door says so.
        return S.justdata(f, x)

    @m.define
    def h(f, x):
        # (= (h $f $x) ($f $x))
        return f(x)

    @m.define
    def notjustdata(_x):
        # (= (notjustdata $x) f)
        return S.f

    @m.define
    def datawithnondatacomponent():
        # (= (datawithnondatacomponent) ((lol (f 42))))
        return (S.lol(S.f(42)),)

    assert f(21) == [42]
    assert m.eval(S.g(S.f, 2)) == [S.justdata(S.f, 2)]
    assert h(S.f, 2) == [4]
    assert m.eval((S.notjustdata(42), 21)) == [42]
    assert m.eval(S.datawithnondatacomponent()) == [Expression((S.lol(84),))]
