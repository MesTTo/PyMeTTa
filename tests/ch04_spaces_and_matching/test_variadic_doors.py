"""Purpose: pin the variadic door family — transfer, batched remove and
eval, simultaneous unify — and the write/remove symmetry behind them.
Guarantees:
  - transfer moves one occurrence per named atom into another space in one
    transactional crossing, counting the found [tested:
    test_transfer_moves_a_batch_atomically; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - remove's variadic face counts the found in one crossing while the
    one-atom call keeps its truth-value reading, and every shape add
    accepts removes symmetrically [tested:
    test_remove_batches_and_takes_every_added_shape; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - `-=` drains every unifying occurrence, upstream's law, where remove()
    stays the one-occurrence door [tested:
    test_isub_drains_every_occurrence; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - eval's variadic face answers one group per term, run()'s grouping,
    with one bind scope over the whole batch [tested:
    test_eval_batches_with_one_bind_scope; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - unify is simultaneous when variadic: every operand agrees under one
    substitution or the answer is None [tested:
    test_unify_is_simultaneous_when_variadic; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - an abandoned FutureSpace warns and a settled one stays silent [tested:
    test_an_abandoned_future_warns; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import gc
import warnings

import pytest

from metta import G, MeTTa, S, V


@pytest.fixture
def context():
    """One closed-on-exit context per test."""
    m = MeTTa()
    yield m
    m.close()


def test_transfer_moves_a_batch_atomically(context):
    """Transfer moves a batch atomically."""
    source = context.space("&transfer-src")
    target = context.space("&transfer-dst")
    source.add(S.p(1), S.p(1), S.q(2), S.r(3))

    moved = source.transfer(S.p(1), S.q(2), S.absent(9), to=target)
    assert moved == 2
    assert sorted(str(atom) for atom in source) == ["(p 1)", "(r 3)"]
    assert sorted(str(atom) for atom in target) == ["(p 1)", "(q 2)"]

    # The one-atom call reads as the truth value remove reads as.
    assert source.transfer(S.r(3), to=target) == 1
    assert source.transfer(S.r(3), to=target) == 0


def test_remove_batches_and_takes_every_added_shape(context):
    """Remove batches and takes every added shape."""
    space = context.space("&remove-batch")
    space.add(S.a(1), S.a(1), S.b(2))
    assert space.remove(S.a(1), S.b(2), S.missing(0)) == 2
    assert sorted(str(atom) for atom in space) == ["(a 1)"]

    # Symmetry: what add accepts, remove takes back.
    space.add(S.alone, G(7))
    assert space.remove(S.alone) is True
    assert space.remove(G(7)) is True


def test_isub_drains_every_occurrence(context):
    """Isub drains every occurrence."""
    space = context.space("&drain-law")
    space.add(S.d(1), S.d(1), S.d(1), S.e(9))
    space -= S.d(1)
    assert sorted(str(atom) for atom in space) == ["(e 9)"]


def test_eval_batches_with_one_bind_scope(context):
    """Eval batches with one bind scope."""
    space = context.self
    space.run("(= (dbl $x) (+ $x $x))")
    assert space.eval(S.dbl(3)) == [6]
    grouped = space.eval(S.dbl(3), S.dbl(5), S.dbl(7))
    assert grouped == [[6], [10], [14]]
    with space.bind({"seed": 7}):
        assert space.eval("(dbl seed)", "(+ seed 1)") == [[14], [8]]


def test_unify_is_simultaneous_when_variadic():
    """Unify is simultaneous when variadic."""
    agreed = S.f(V.x, S.b).unify(S.f(S.a, V.y), S.f(V.p, V.q))
    assert agreed is not None
    assert agreed[V.x] == S.a
    assert agreed[V.y] == S.b
    assert agreed[V.p] == S.a
    assert agreed[V.q] == S.b
    assert S.f(V.x).unify(S.f(S.a), S.f(S.b)) is None


def test_an_abandoned_future_warns(context):
    """An abandoned future warns."""
    from metta.parallel import spawn

    space = context.self
    space.run("(= (idle) 1)")
    with space:
        settled = spawn(S.idle())
        settled.wait()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            del settled
            gc.collect()
        assert not any("abandoned" in str(row.message) for row in caught)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            dangling = spawn(S.idle())
            del dangling
            gc.collect()
        assert any("abandoned" in str(row.message) for row in caught)
