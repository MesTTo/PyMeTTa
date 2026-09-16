"""Purpose: a write and a drop that raced each other are decided at the outer commit, never by the order luck dealt.

The engine validates both at commit in the refreshed view (engine/spaces/lifecycle.pl,
metta_validate_retirements/1): a writer whose space another transaction retired is
refused, and a retirement over rows another transaction committed since its
withdrawal is refused; the loser's handle and rows are what they were.

Guarantees: a drop that committed first leaves the racing write refused with the
retry remedy and every handle of the name dead; a write that committed first
leaves the racing drop refused, its handle live and usable, and both rows kept;
ordinary disjoint and multivalued writes commit in either order
[tested: test_a_write_loses_to_a_drop_that_committed_first,
test_a_drop_loses_to_a_write_that_committed_first,
test_disjoint_and_multivalued_writes_commit_in_either_order; commit=23dee6dc5b745a57ade43bd5fd2d317116634f6f].
"""

from metta import MeTTa, S, Space, V
from metta._errors.errors import EngineError

ROW = S.commit_value


def _rows(space):
    return sorted(int(value) for value in space.eval(S.match(space, ROW(V.x), V.x)))


def test_a_write_loses_to_a_drop_that_committed_first(overlap):
    """The drop commits; the write that observed the live space is refused, and every handle is dead."""
    with MeTTa() as context:
        space = context.space()
        space.add(ROW(1))
        alias = Space(space)
        first, second = overlap(context.self, [alias.drop, lambda: space.add(ROW(2))])
        assert first is None
        assert isinstance(second, EngineError)
        assert "retired by another transaction" in str(second)
        assert "retry the outer transaction" in str(second)
        assert alias.dropped and space.dropped


def test_a_drop_loses_to_a_write_that_committed_first(overlap):
    """The write commits; the drop is refused, restores its handle, and the rows are all there."""
    with MeTTa() as context:
        space = context.space()
        space.add(ROW(1))
        alias = Space(space)
        first, second = overlap(context.self, [lambda: space.add(ROW(2)), alias.drop])
        assert first is None
        assert isinstance(second, EngineError)
        assert "conflicts with state committed since its withdrawal" in str(second)
        assert "retry the outer transaction" in str(second)
        assert not alias.dropped and not space.dropped
        assert _rows(space) == [1, 2]
        alias.add(ROW(3))
        assert _rows(space) == [1, 2, 3]


def test_disjoint_and_multivalued_writes_commit_in_either_order(overlap):
    """Ordinary writes are the positive control: no retirement, no refusal."""
    with MeTTa() as context:
        left, right = context.space(), context.space()
        assert overlap(context.self, [lambda: left.add(ROW(1)), lambda: right.add(ROW(2))]) == (None, None)
        assert overlap(context.self, [lambda: left.add(ROW(3)), lambda: left.add(ROW(4))]) == (None, None)
        assert _rows(left) == [1, 3, 4]
        assert _rows(right) == [2]
