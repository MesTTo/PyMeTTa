"""examples/ch08-data/08-02-sequence-variables/05-the-fence.metta in Python: the refusal, and what it says.

A refusal arrives as an EngineError, and its message is what Python can read:
the pattern it refused, the rule it broke, and the classifier that decides.
The MeTTa side takes the same refusal apart with `index-atom`, because there it
is an ordinary error atom carrying five children; the exception exposes no
attribute for that payload, so each claim below is made against the message.

The refusing `case` arm is the one line here that cannot be Python. A pattern
binding one name twice is a SyntaxError in `match/case`, and one name in both
the gap and the ordinary role is exactly that shape, so the arm tower is built
as a term and evaluated.
"""

from metta import S, V, equation, seg, solve
from metta.errors import EngineError


def twin(m):
    """Meet the fence, read what it says, and take the remedy."""
    seven = S.Order(7, S.x, S.y)
    m += seven

    # One name may not be both a gap and an ordinary variable: that mix has no
    # finite reading outside an equation head.
    refusal = None
    try:
        list(m[(S.Order, seg(V.mm), V.mm)])
    except EngineError as error:
        refusal = error
    message = str(refusal)

    # What the message carries: the pattern, the open other side a space match
    # has not read yet, the rule, and the classifier that decides it.
    assert "outside the proved finitary fragment" in message
    assert "against any atom" in message
    assert "mixed_roles" in message
    assert "metta_seq_classify/3" in message
    assert "Theorem 62" in message
    assert "Kutsia Section 6.2" in message
    assert "Kutsia Section 6.3" in message

    # The refusal is carried, not raised while the program loads: it travels
    # with the compiled pattern and throws at the ask, so an arm nothing
    # reaches cannot stop a program from running.
    arms = (
        (S.Order(8), S.plain),
        ((S.Order, seg(V.mm), V.mm), S.never),
        (V.otherwise, S.other),
    )
    assert m.eval(S.case(S.Order(8), arms)) == [S.plain]  # rung: match/case cannot bind one name twice

    # The remedy is to ask for the run and for the term under different names,
    # and to compare them where comparison belongs.
    answered = [S.pair(row.run, row.last) for row in m[(S.Order, seg(V.run), V.last)]]
    assert answered == [S.pair(seven[1:3], S.y)]
    pair = S.Order(S.x(S.y), S.x(S.y))
    agreeing = solve((S.Order, seg(V.run), V.last), pair).one()
    assert list(agreeing.run) == [agreeing.last]

    # An equation head is the one place the mix is admitted, because a head is
    # always the pattern side of a one-sided match.
    m += equation(S.echoes((seg(V.xs), S.tag, V.xs))).to(S.yes)  # rung: *args is refused at a compiled parameter
    assert m.fn.echoes((S.a, S.b, S.tag, S.a(S.b))) == [S.yes]

    # The classifier's second refusal, `no_certificate`, needs gaps on both
    # sides and no program can write an ask that has them, so this shape is an
    # ordinary one-sided match that finds nothing.
    nested = m.fn.unify(
        S.f(S.g(seg(V.u), S.b)), S.f(S.g(S.a, seg(V.v))), S.yes, S.no
    )
    assert list(nested) == [S.no]


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 6248, 6248, 6248 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/05-the-fence.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=WORKTREE]
BUDGET = 6248
