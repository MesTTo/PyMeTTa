"""Purpose: verify operator frame cardinality, retained values and effects.

Owns resources: monkeypatch restores the temporary operator.call selector;
the fixture owns its native equations and grounded values.
"""

import operator

from metta import Expression, Grounded, S, V
from metta._declare import prelude


def test_operator_frames_accept_many_operands_and_retain_values(metta, monkeypatch):
    """One service port carries arbitrary argument counts without evaluating data."""
    @metta.define
    def frame_add(left, right):
        return left + right

    assert frame_add(2, 3) == [5]
    assert metta.eval(S["py-operator"](S["max"], S.noeval(Expression([3, 1, 4, 2])))) == [4]

    monkeypatch.setitem(prelude._PYTHON_OPERATORS, "call", operator.call)
    received = []

    def observe(*values):
        received.append(values)
        return len(values)

    held = S.FrameOperand
    carried = S.FrameBody(held)
    metta.add(S["="](held, S.UnwantedReduction))
    frame = Expression([
        Grounded(observe), *(Grounded(value) for value in (None, False, 0, "")),
        held, Grounded(carried),
    ])
    call = S.let(V.frame, S.noeval(frame), S["py-operator"](S["call"], V.frame))
    assert metta.eval(call) == [6]
    assert received == [(None, False, 0, "", held, carried)]
    assert received[0][-1] is carried

    received.clear()
    assert metta.eval(S["py-operator"](S["call"], S.noeval(Expression([Grounded(observe)])))) == [0]
    assert received == [()]


def test_compiled_operator_frames_evaluate_sources_once_in_order(metta):
    """Computed operands finish left-to-right before the selected operation runs."""
    events = []

    class Left:
        def __add__(self, right):
            events.append(("add", right))
            return 7

    left = Left()
    held = S.FrameSymbol
    metta.add(S["="](held, S.UnwantedReduction))

    def read(label, value):
        events.append(label)
        return value

    @metta.define
    def computed_operands():
        return read("left", left) + read("right", held)

    assert computed_operands() == [7]
    assert events == ["left", "right", ("add", held)]


def test_compiled_operator_frames_remain_native_rewrite_patterns(metta):
    """Native matching and replacement change a compiled operator's behavior."""
    @metta.define
    def frame_rewrite(left, right):
        return left + right

    assert frame_rewrite(3, 4) == [7]
    head = S["frame-rewrite"](V.left, V.right)
    frame = S.noeval(Expression([V.first, V.second]))
    original = S["="](head, S["py-operator"](V.selector, frame))
    replacement = S["="](head, S["py-operator"](S["mul"], frame))
    rows = metta.eval(S.match(S["&self"], original, S.noeval(replacement)))
    assert len(rows) == 1
    metta.remove(original)
    metta.add(rows[0])
    assert frame_rewrite(3, 4) == [12]
