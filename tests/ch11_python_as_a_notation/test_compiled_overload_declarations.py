"""Purpose: exercise stored control builders and overloaded compiled declarations."""

from typing import overload

import pytest

from metta import Expression, S, V, arrow, fn, typed
from metta._errors.errors import CompileError


def test_stored_control_builders_include_nested_arguments(scratch_space):
    """The existing function namespace constructs all three stored forms."""
    m = scratch_space
    m.add(S.edge(1, 2))
    terms = (
        (fn.let(V.x, 4, V.x + 1), 5),
        (fn["let*"](((V.x, 4), (V.y, V.x + 1)), V.y), 5),
        (fn.match(m, S.edge(V.x, V.y), V.y), 2),
        (fn.add(fn.let(V.x, 4, V.x), 3), 7),
    )
    for term, expected in terms:
        assert isinstance(term, Expression)
        assert m.eval(term) == [expected]
    stored = S.program(terms[-1][0])
    m.add(stored)
    assert stored in m


def test_define_emits_each_overload_from_one_source(scratch_space):
    """Unannotated implementation bodies retain correlated overload arrows."""
    m = scratch_space

    @overload
    def identity(value: int) -> int: ...

    @overload
    def identity(value: str) -> str: ...

    def identity(value):
        return value

    compiled = m.define(identity)
    assert set(m.eval(fn.get_type(S.identity))) == {arrow(int, int), arrow(str, str)}
    assert compiled(7) == [7]
    assert compiled("word") == ["word"]
    assert compiled.py(7) == 7
    assert m.define(identity)(7) == [7]
    assert len(m.eval(fn.match(m, typed(S.identity, V.t), V.t))) == 2


def test_define_deduplicates_coincident_overload_arrows(scratch_space):
    """Python int and float both declare the engine's Number signature."""
    m = scratch_space

    @overload
    def identity(value: int) -> int: ...

    @overload
    def identity(value: float) -> float: ...

    @m.define
    def identity(value):
        return value

    assert m.eval(fn.match(m, typed(S.identity, V.t), V.t)) == [arrow(int, int)]
    assert identity(3) == [3]


def test_define_refuses_overloads_without_a_matching_body_arity(scratch_space):
    """A declaration must not advertise arguments the equation cannot accept."""
    m = scratch_space

    @overload
    def identity(value: int) -> int: ...

    @overload
    def identity(value: int, other: int) -> int: ...

    def identity(value):
        return value

    with pytest.raises(CompileError, match="fixed positional arity"):
        m.define(identity)
    assert not m.is_function_here("identity")
    assert m.eval(fn.match(m, typed(S.identity, V.t), V.t)) == []


@pytest.mark.parametrize("fail_at", ["second declaration", "equation"])
def test_failed_overload_publication_rolls_back_all_arrows(
    scratch_space, monkeypatch, fail_at
):
    """Publication failures leave no declaration and a retry installs both."""
    m = scratch_space

    @overload
    def identity(value: int) -> int: ...

    @overload
    def identity(value: str) -> str: ...

    def identity(value):
        return value

    real_add = type(m).add
    declarations_seen = 0
    failure_message = "forced overload publication failure"

    def failing_add(space, *atoms, **kwargs):
        nonlocal declarations_seen
        if space is m:
            for atom in atoms:
                if isinstance(atom, Expression) and atom.children[0] == S[":"]:
                    declarations_seen += 1
                    if fail_at == "second declaration" and declarations_seen == 2:
                        raise RuntimeError(failure_message)
                if (
                    fail_at == "equation"
                    and isinstance(atom, Expression)
                    and atom.children[0] == S["="]
                ):
                    raise RuntimeError(failure_message)
        return real_add(space, *atoms, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(type(m), "add", failing_add)
        with pytest.raises(RuntimeError, match="forced overload publication failure"):
            m.define(identity)
    assert not m.is_function_here("identity")
    assert m.eval(fn.match(m, typed(S.identity, V.t), V.t)) == []
    assert m.define(identity)(7) == [7]
    assert set(m.eval(fn.get_type(S.identity))) == {arrow(int, int), arrow(str, str)}


def test_a_second_clause_publishes_the_arrow_its_own_signature_states(scratch_space):
    """A MeTTa name may carry several declarations, so a later clause adds its own.

    One boolean per name recorded only WHETHER it had declared anything, which
    is a different question, so every clause after the first published none of
    its own signature.
    """
    m = scratch_space

    @m.define
    def sized(x: int = 0) -> int:  # noqa: ARG001 -- the default is the clause head pattern
        """The literal-head clause."""
        return 1

    @m.define
    def sized(x: str) -> int:  # noqa: F811, ARG001 -- the other argument type
        """The other clause."""
        return 2

    assert set(m.eval(fn.get_type(S.sized))) == {arrow(int, int), arrow(str, int)}


def test_a_clause_repeating_a_signature_declares_it_once(scratch_space):
    """The ledger holds what was published, so an equal arrow is not stored twice."""
    m = scratch_space

    @m.define
    def paired(x: int = 0) -> int:  # noqa: ARG001 -- the default is the clause head pattern
        """The literal-head clause."""
        return 1

    @m.define
    def paired(x: int) -> int:  # noqa: F811, ARG001 -- the same signature again
        """The same signature on the general clause."""
        return 2

    declared = list(m.eval(fn.match(m, typed(S.paired, V.t), V.t)))
    assert declared == [arrow(int, int)]
