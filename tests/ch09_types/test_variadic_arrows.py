"""Purpose: exercise variadic arrows through public Python atom and source doors.

Guarantees: arbitrary argument runs retain values, holding and refusal positions
[tested: test_variadic_arrows.py; commit=WORKTREE].
Owns resources: every generated example closes its declaration space.
"""

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from metta import Expression, MeTTa, S, V, arrow, equation, seg, typed


@settings(max_examples=40)
@given(st.lists(st.integers(-1000, 1000), max_size=64))
@example([0, 0])
def test_runs_match_numeric_folding_and_preserve_held_expressions(numbers):
    """The empty run and larger runs share the same declaration and equation."""
    with MeTTa().space() as space:
        space.add(typed(S.sum, arrow(S[":seg"](S.Number), S.Number)))
        space.add(equation(S.sum(seg(V.xs))).to(S.foldl_atom(V.xs, 0, S["+"])))
        assert space.eval(S.sum(*numbers)) == [sum(numbers)]
        space.add(typed(S.held, arrow(S[":seg"](S.Atom), S.Atom)))
        space.add(equation(S.held(seg(V.xs))).to(V.xs))
        expressions = [S["+"](number, 1) for number in numbers]
        assert space.eval(S.held(*expressions)) == [Expression(*expressions)]


@settings(max_examples=40)
@given(st.lists(st.integers(-1000, 1000), min_size=1, max_size=32), st.data())
def test_bad_positions_survive_a_fixed_prefix_and_dynamic_dispatch(numbers, data):
    """A runtime head reports the global argument position after a held prefix."""
    position = data.draw(st.integers(0, len(numbers) - 1))
    with MeTTa().space() as space:
        space.add(typed(S.sum, arrow(S.Atom, S[":seg"](S.Number), S.Number)))
        space.add(equation(S.sum(V.prefix, seg(V.xs))).to(S.foldl_atom(V.xs, 0, S["+"])))
        space.add(typed(S.flag, S.Bool))
        arguments = numbers.copy()
        arguments[position] = S.flag
        call = S.sum(S["+"](1, 1), *arguments)
        expected = S.Error(call, S.BadArgType(position + 2, S.Number, S.Bool))
        assert space.eval(call) == [expected]
        dynamic = S.let(V.f, S.sum, Expression(V.f, *call.children[1:]))
        assert space.eval(dynamic) == [expected]


@pytest.mark.parametrize("route", ["source", "file", "batch"])
def test_invalid_splice_admission_leaves_no_partial_write(tmp_path, route):
    """Source preflight and atomic add reject a retired marker before storage."""
    with MeTTa().space() as space:
        source = "(untouched value) (: bad (-> (%Rest% Number) Number))"
        with pytest.raises(Exception, match="retired_arrow_splice"):
            if route == "source":
                space.run(source)
            elif route == "file":
                path = tmp_path / "invalid-splice.metta"
                path.write_text(source)
                space.load(path)
            else:
                space.add(S.untouched(S.value), typed(S.bad, arrow(S["%Rest%"](S.Number), S.Number)))
        assert list(space.atoms()) == []
