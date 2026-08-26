"""Purpose: pin the cache decorator as notation over the engine's memo store.
Assumes: lib_memo is importable from the space, which the decorator does
  itself; nothing here declares a table by hand.
Guarantees:
  - a cached definition answers from the engine memo, so an exponential
    recursion becomes linear, and its counters and clear are reachable under
    functools.lru_cache's own names; the uncached control declares the
    automatic memo policy's explicit refusal.
  [tested: test_a_cached_definition_memoizes_its_complete_answer_bag;
   commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - cached answer replay preserves duplicate occurrences because multiplicity
    is part of the result law, even after the owning space shadows the replay
    loop's host spelling.
  [tested: test_a_cached_definition_preserves_duplicate_answers,
   test_exact_cache_replay_ignores_a_space_local_between_shadow; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - cached and uncached answer bags agree for ground recursion, open calls and
    a dependency whose definition changes between calls, including when an
    already-live pool engine populated the old private answer table.
  [tested: test_exact_cache_matches_uncached_answer_bags,
   test_exact_cache_invalidation_crosses_a_live_pool_engine; commit=39092863ae34184a9f955f185ff57c1ff177ec40]
  - stacking cache over op refuses before definition registration and sends
    host-only memoization to functools.
  [tested: test_cache_over_an_operation_refuses_before_definition_registration;
   commit=39092863ae34184a9f955f185ff57c1ff177ec40]
Fails when: read as a fixed-size cache. The memo holds the answers for the calls
  that were made and has no maxsize; `unchecked=True` is the staleness the
  engine's own `(cache <name> unchecked)` accepts, not a size.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

import functools
from collections import Counter

import pytest

from metta import MeTTa, S, V
from metta.parallel import EnginePool

#: Big enough that the uncached twin cannot finish inside the default
#: evaluation fuel, which is the point being made, and small enough that the
#: memoized one is instant.
_N = 25


def _assert_ground_bags_equal(memoized, plain, values) -> None:
    for value in values:
        assert Counter(map(str, memoized(value))) == Counter(map(str, plain(value)))


def _assert_alpha_bags_equal(memoized, plain) -> None:
    remaining = list(plain)
    for answer in memoized:
        match = next(
            (
                index
                for index, candidate in enumerate(remaining)
                if answer.alpha_eq(candidate)
            ),
            None,
        )
        assert match is not None
        remaining.pop(match)
    assert remaining == []


def _install_recursive_bag_pair(memo, plain):
    @memo.cache(name="p14-diff-recursive")
    def memo_recursive(n):
        yield n
        yield n
        if n > 0:
            yield from memo_recursive(n - 1)

    @plain.define(name="p14-diff-recursive-plain")
    def plain_recursive(n):
        yield n
        yield n
        if n > 0:
            yield from plain_recursive(n - 1)

    return memo_recursive, plain_recursive


def test_a_cached_definition_memoizes_its_complete_answer_bag() -> None:
    """The decorator is notation; the answers come from the engine memo."""
    metta = MeTTa().space("&cachedecorator")

    @metta.cache
    def cachedec_fib(n):
        return n if n < 2 else cachedec_fib(n - 1) + cachedec_fib(n - 2)

    with metta.stats() as cached:
        assert cachedec_fib(_N) == [75025]

    # Counts describe this definition's call-key entries and answer bag.
    info = cachedec_fib.cache_info()
    assert info["entries"] == _N + 1
    assert info["answers"] == _N + 1
    cachedec_fib.cache_clear()
    assert cachedec_fib.cache_info() == {"entries": 0, "answers": 0}

    # The same definition without the memo is exponential, and on this input
    # it does not finish inside the default evaluation fuel at all. Automatic
    # bag-preserving memoization would deliberately accelerate this shape, so
    # the control uses its public refuse declaration.
    plain = MeTTa().space("&cachedecorator-plain")
    refusal = "(cache cachedec-plain refuse)"
    plain.run(f"!(add-atom &petta {refusal})")
    try:

        @plain.define
        def cachedec_plain(n):
            return n if n < 2 else cachedec_plain(n - 1) + cachedec_plain(n - 2)

        with plain.stats() as untabled:
            overrun = list(cachedec_plain(_N))

        assert [str(atom) for atom in overrun] == ["(Error 1 StackOverflow)"]
        # Measured 2026-08-26: 830,770 inferences uncached against 2,548
        # cached, a ratio of 326.0. The bag-counting trie costs 1.57x the old
        # 1,622-inference set table and recovers 4.49x from the 11,433-
        # inference Prolog-list memo. The floor stays just below the measured
        # ratio so another move away from direct answer-trie dispatch is red.
        assert untabled.inferences > 320 * cached.inferences
    finally:
        plain.run(f"!(remove-atom &petta {refusal})")

    # The Python twin is untouched: a cached definition is still a definition.
    assert cachedec_fib.py(10) == 55

    # unchecked=True is the engine's own staleness-accepting declaration, and
    # name= is define's own.
    @metta.cache(name="cachedec-named", unchecked=True)
    def cachedec_named(n):
        return n if n < 2 else cachedec_named(n - 1) + cachedec_named(n - 2)

    assert cachedec_named(20) == [6765]
    assert cachedec_named.cache_info() == {"entries": 21, "answers": 21}


def test_a_cached_definition_preserves_duplicate_answers() -> None:
    """Caching preserves the language law that answer multiplicity is visible.

    "Result order within one directive's list is unspecified; result
    multiplicity is specified" [source: LeaTTa wiki/Specification.md:22]. A
    cache may change when an answer is computed, but cannot turn the bag
    ``a, a, b`` into the set ``a, b``. This test used to assert that defect;
    it now pins the law on the public decorator itself.
    """
    metta = MeTTa().space("&cachedup")

    @metta.cache
    def cachedup():
        yield "a"
        yield "a"
        yield "b"

    metta.run("!(config-memoize (answer-limit 2) (aggregate count) (float 0))")
    try:
        metta.run("!(clear-memoize-stats)")
        assert sorted(str(atom) for atom in cachedup()) == ['"a"', '"a"', '"b"']
        assert sorted(str(atom) for atom in cachedup()) == [
            '"a"',
            '"a"',
            '"b"',
        ]
        assert cachedup.cache_info() == {"entries": 1, "answers": 3}
        stats = {
            str(pair[0]): int(pair[1])
            for pair in metta.run("!(get-memoize-stats)")[0][0]
        }
        assert stats == {"cache_hit": 1, "cache_miss": 1}
    finally:
        metta.run(
            "!(config-memoize (answer-limit 2048) (aggregate none) (float 12))"
        )


def test_exact_cache_matches_uncached_answer_bags() -> None:
    """Match an uncached oracle across duplicate, open, recursive, and changed calls."""
    memo = MeTTa().space("&p14-differential-memo")
    plain = MeTTa().space("&p14-differential-plain")
    refusal = "(cache p14-diff-recursive-plain refuse)"
    plain.run(f"!(add-atom &petta {refusal})")

    memo_recursive, plain_recursive = _install_recursive_bag_pair(memo, plain)

    @memo.cache(name="p14-diff-open")
    def memo_open(value):
        yield value
        yield value
        yield S.Pair(value, value)

    @plain.define(name="p14-diff-open-plain")
    def plain_open(value):
        yield value
        yield value
        yield S.Pair(value, value)

    def install_memo_source_before():
        @memo.define(name="p14-diff-state-source")
        def memo_source(value):
            yield S.Before(value)
            yield S.Before(value)

        return memo_source

    def install_plain_source_before():
        @plain.define(name="p14-diff-state-source-plain")
        def plain_source(value):
            yield S.Before(value)
            yield S.Before(value)

        return plain_source

    memo_source = install_memo_source_before()
    plain_source = install_plain_source_before()

    @memo.cache(name="p14-diff-state")
    def memo_state(value):
        yield memo_source(value)

    @plain.define(name="p14-diff-state-plain")
    def plain_state(value):
        yield plain_source(value)

    try:
        _assert_ground_bags_equal(memo_recursive, plain_recursive, (0, 1, 3))
        _assert_alpha_bags_equal(memo_open(V.x), plain_open(V.x))

        assert Counter(map(str, memo_state(S.seed))) == Counter(
            map(str, plain_state(S.seed))
        )
        assert memo_state.cache_info() == {"entries": 1, "answers": 2}

        def install_memo_source_after():
            @memo.define(name="p14-diff-state-source")
            def memo_source(value):
                yield S.After(value)
                yield S.After(value)
                yield S.Extra(value)

            return memo_source

        def install_plain_source_after():
            @plain.define(name="p14-diff-state-source-plain")
            def plain_source(value):
                yield S.After(value)
                yield S.After(value)
                yield S.Extra(value)

            return plain_source

        install_memo_source_after()
        install_plain_source_after()

        assert memo_state.cache_info() == {"entries": 0, "answers": 0}
        assert Counter(map(str, memo_state(S.seed))) == Counter(
            map(str, plain_state(S.seed))
        )
        assert memo_state.cache_info() == {"entries": 1, "answers": 3}
    finally:
        plain.run(f"!(remove-atom &petta {refusal})")


def test_exact_memo_wrappers_keep_named_space_owners_separate() -> None:
    """Each cached wrapper enters the dispatch of the space that owns it."""
    left = MeTTa().space("&cache-owner-left")
    right = MeTTa().space("&cache-owner-right")

    @left.cache(name="cache-owner-shared")
    def left_shared():
        yield "left"
        yield "left"

    @right.cache(name="cache-owner-shared")
    def right_shared():
        yield "right"
        yield "right"
        yield "right"

    assert [str(atom) for atom in left_shared()] == ['"left"', '"left"']
    assert [str(atom) for atom in right_shared()] == [
        '"right"',
        '"right"',
        '"right"',
    ]
    assert left_shared.cache_info() == {"entries": 1, "answers": 2}
    assert right_shared.cache_info() == {"entries": 1, "answers": 3}


def test_exact_cache_replay_ignores_a_space_local_between_shadow() -> None:
    """Multiplicity uses the host builtin after a local operation is removed."""
    metta = MeTTa().space("&cache-between-shadow")
    metta.op(
        lambda _low, _high: "shadow",
        name="between",
        effect="pureStructural",
        arities=[2],
    )
    metta.unregister_op("between")

    @metta.cache(name="cache-between-replay")
    def replayed(left, right):
        yield S.Pair(left, right)
        yield S.Pair(left, right)

    assert Counter(map(str, replayed(S.a, S.b))) == Counter({"(Pair a b)": 2})


def test_exact_cache_invalidation_crosses_a_live_pool_engine() -> None:
    """A worker that populated a private SWI table must see the next generation."""
    metta = MeTTa().space("&cache-live-worker")

    def install_before():
        @metta.define(name="cache-live-source")
        def source(value):
            yield S.Before(value)
            yield S.Before(value)

        return source

    source = install_before()

    @metta.cache(name="cache-live-derived")
    def derived(value):
        yield source(value)

    with EnginePool(workers=1) as workers:
        first = workers.submit(
            lambda: Counter(map(str, derived(S.seed)))
        ).result(timeout=30)
        assert first == Counter({"(Before seed)": 2})

        def install_after():
            @metta.define(name="cache-live-source")
            def source(value):
                yield S.After(value)
                yield S.After(value)
                yield S.Extra(value)

            return source

        install_after()

        second = workers.submit(
            lambda: Counter(map(str, derived(S.seed)))
        ).result(timeout=30)
        assert second == Counter({"(After seed)": 2, "(Extra seed)": 1})


def test_cache_over_an_operation_refuses_before_definition_registration() -> None:
    """An operation is one definition door; host memoization names functools."""
    metta = MeTTa().space("&cache-over-op")

    @metta.op(effect="pureStructural")
    def cache_op_value(value):
        return value

    @functools.wraps(cache_op_value)
    def outer_wrapper(value):
        return cache_op_value(value)

    for candidate in (cache_op_value, cache_op_value.__wrapped__, outer_wrapper):
        with pytest.raises(TypeError) as raised:
            metta.cache(candidate)

        message = str(raised.value)
        assert "@metta.cache" in message
        assert "@metta.op" in message
        assert "functools.cache" in message
        assert "functools.lru_cache" in message
    assert metta.run("!(match &petta (defined &cache-over-op cache-op-value) yes)") == [[]]
    assert cache_op_value(3) == 3

    metta.unregister_op("cache-op-value")
    cached = metta.cache(cache_op_value, name="cache-after-op")
    assert cached(3) == [3]
