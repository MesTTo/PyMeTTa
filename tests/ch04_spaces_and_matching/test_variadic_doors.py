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
  - `-=` subtracts ONE occurrence per operand element, Counter's grain,
    so it inverts `+=`; `del space[pattern]` is the drain and remove()
    the door that reports absence [tested:
    test_isub_subtracts_one_occurrence_and_inverts_iadd; commit=c6a40460b1db341198a6150e3600f502831a6e83]
  - eval's variadic face answers one group per term, run()'s grouping,
    with one bind scope over the whole batch [tested:
    test_eval_batches_with_one_bind_scope; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - unify is simultaneous when variadic: every operand agrees under one
    substitution or the answer is None [tested:
    test_unify_is_simultaneous_when_variadic; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - an abandoned FutureSpace warns and a settled one stays silent [tested:
    test_an_abandoned_future_warns; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - `-=` classifies its operand exactly as `+=` does, so the fact stream
    one door stores the other subtracts, one occurrence each, in one
    crossing [tested: test_isub_reads_the_same_stream_shapes_iadd_writes;
    commit=9ee2057351b951fe99cbfb6cbd43d8b137b05002]
  - the MeTTa context mirrors its space's container and write protocols
    through the generated dunder tier, the in-place trio answers the
    context itself, and repr names the home space with the closed state
    [tested: test_the_context_speaks_its_spaces_protocols;
    commit=9ee2057351b951fe99cbfb6cbd43d8b137b05002]
  - alpha stays binary because the engine declares =alpha's input arity;
    the wider spelling is connective composition [tested:
    test_alpha_stays_binary_on_the_engines_own_ground; commit=9ee2057351b951fe99cbfb6cbd43d8b137b05002]
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


def test_isub_subtracts_one_occurrence_and_inverts_iadd(context):
    """Isub subtracts one occurrence and inverts iadd.

    Python's own multiset is Counter, whose `-=` subtracts the multiplicity
    given rather than clearing the key, and that is the only reading under
    which `+=` and `-=` are inverses. The drain door is `del`.
    """
    space = context.space("&subtract-law")
    space.add(S.d(1), S.d(1), S.d(1), S.e(9))
    space -= S.d(1)
    assert sorted(str(atom) for atom in space) == ["(d 1)", "(d 1)", "(e 9)"]

    before = sorted(str(atom) for atom in space)
    space += S.d(1)
    space -= S.d(1)
    assert sorted(str(atom) for atom in space) == before

    # Subtracting what is not there changes nothing and does not raise.
    space -= S.absent(0)
    assert sorted(str(atom) for atom in space) == before

    # The drain door still drains, and still raises on nothing matched.
    del space[S.d(V.n)]
    assert sorted(str(atom) for atom in space) == ["(e 9)"]
    with pytest.raises(KeyError):
        del space[S.gone(V.n)]


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


def test_isub_reads_the_same_stream_shapes_iadd_writes(context):
    """Isub reads the same stream shapes iadd writes.

    Before the symmetric classification, a tuple of rows quietly became one
    never-matching pattern and -= "succeeded" over an unchanged space.
    """
    space = context.space("&stream-symmetry")
    rows = ((S.edge, 1, 2), (S.edge, 2, 3))
    space += rows
    space += rows
    assert len(space) == 4
    space -= rows
    assert sorted(str(atom) for atom in space) == ["(edge 1 2)", "(edge 2 3)"]
    space -= rows
    assert sorted(str(atom) for atom in space) == []

    space += [S.d(1), S.d(1), S.e(2)]
    space -= [S.d(1)]
    assert sorted(str(atom) for atom in space) == ["(d 1)", "(e 2)"]


def test_the_context_speaks_its_spaces_protocols(context):
    """The context speaks its space's protocols.

    The generated dunder tier delegates the container and write faces to
    the process home, and the in-place trio answers the CONTEXT so the
    operator protocol cannot rebind a MeTTa to its Space.
    """
    m = context
    assert len(m) == 0
    assert bool(m) is True
    m += S.top(1)
    m += [(S.edge, 1, 2), (S.edge, 2, 3)]
    assert len(m) == 3
    assert S.top(1) in m
    assert [str(row.x) for row in m[S.edge(1, V.x)]] == ["2"]
    m -= (S.edge(1, 2), S.edge(2, 3))
    assert sorted(str(atom) for atom in m) == ["(top 1)"]
    m |= [S.k(9)]
    del m[S.k(V.n)]
    assert sorted(str(atom) for atom in m) == ["(top 1)"]
    before = m
    m += S.more(2)
    assert m is before
    assert repr(m) == f"MeTTa(self={str(m.self)!r})"


def test_alpha_stays_binary_on_the_engines_own_ground(context):
    """Alpha stays binary on the engine's own ground.

    An n-ary alpha was reviewed and declined: the door builds THE =alpha
    term and the engine declares its input arity, so the wider spelling is
    the connective composition, fn.and_ over the pairs.
    """
    with pytest.raises(Exception, match="function_input_arities"):
        context.self.eval("(=alpha 1 1 1)")


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
