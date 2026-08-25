"""Purpose: pin the cache decorator as notation over the engine's memo store.
Assumes: lib_memo is importable from the space, which the decorator does
  itself; nothing here declares a table by hand.
Guarantees:
  - a cached definition answers from the engine memo, so an exponential
    recursion becomes linear, and its counters and clear are reachable under
    functools.lru_cache's own names; the uncached control declares the
    automatic memo policy's explicit refusal.
  [tested: test_a_cached_definition_memoizes_its_complete_answer_bag;
   commit=WORKTREE]
  - cached answer replay preserves duplicate occurrences because multiplicity
    is part of the result law.
  [tested: test_a_cached_definition_preserves_duplicate_answers; commit=WORKTREE]
  - stacking cache over op refuses before definition registration and sends
    host-only memoization to functools.
  [tested: test_cache_over_an_operation_refuses_before_definition_registration;
   commit=WORKTREE]
Fails when: read as a fixed-size cache. The memo holds the answers for the calls
  that were made and has no maxsize; `unchecked=True` is the staleness the
  engine's own `(cache <name> unchecked)` accepts, not a size.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

import functools

import pytest

from metta import MeTTa

#: Big enough that the uncached twin cannot finish inside the default
#: evaluation fuel, which is the point being made, and small enough that the
#: memoized one is instant.
_N = 25


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
        assert untabled.inferences > 20 * cached.inferences
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
