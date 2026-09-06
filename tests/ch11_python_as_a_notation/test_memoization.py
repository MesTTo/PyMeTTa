"""Purpose: pin lib_memo's exact answer-bag memo as reached from Python.
Assumes: lib_memo is imported into the space under test; nothing here declares
  a table by hand.
Guarantees:
  - a memoized definition answers from the engine memo, so an exponential
    recursion becomes linear, and its counters and its invalidation are
    lib_memo's own forms rather than a host door; the unmemoized control
    declares the automatic memo policy's explicit refusal.
  [tested: test_a_cached_definition_memoizes_its_complete_answer_bag;
   commit=205f818240658af34bda4a383084c42cf1383275]
  - memo replay preserves duplicate occurrences because multiplicity is part
    of the result law, even after the owning space shadows the replay loop's
    host spelling.
  [tested: test_a_cached_definition_preserves_duplicate_answers,
   test_exact_cache_replay_ignores_a_space_local_between_shadow; commit=205f818240658af34bda4a383084c42cf1383275]
  - memoized and unmemoized answer bags agree for ground recursion, open calls
    and a dependency whose definition changes between calls, including when an
    already-live pool engine populated the old private answer table.
  [tested: test_exact_cache_matches_uncached_answer_bags,
   test_exact_cache_invalidation_crosses_a_live_pool_engine; commit=205f818240658af34bda4a383084c42cf1383275]
  - memoizing a registered operation is admitted whatever its declared effect
    class, for every seat, because the declaration is the caller's own word
    about their own program, and the cache SERVES: the operation runs once for
    two calls, including through a caller compiled before the declaration.
  [tested: test_memoizing_an_effectful_operation_is_the_callers_own_word,
   test_memoizing_an_operation_caches_its_calls; commit=295f4c80ace06f6bf8e132ea936777afd79ac3d5]
  - enabling a cache does not rewrite the space's stored program, so a body
    that writes its own space keeps its one equation and runs once on a miss.
  [tested: test_memoizing_a_body_that_writes_its_own_space_runs_it_once;
   commit=295f4c80ace06f6bf8e132ea936777afd79ac3d5]
Fails when: read as a fixed-size cache. The memo holds the answers for the calls
  that were made and has no maxsize.
  Also when a counter is read after a LAZY call. The exact store is an SWI
  table and a private table belongs to the table space that fills it, so an
  answer cursor's engine keeps its own copy; `_answers` below is why every
  counter assertion evaluates eagerly.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from collections import Counter

from metta import MeTTa, S, V, space
from metta.parallel import EnginePool


def _memoized(space, *, name=None):
    """Define, then memoize through lib_memo's own forms.

    There is no host door for this. A hardcoded Python verb for ONE library is
    the special-case surface the universal seam exists to avoid, and every
    capability the removed decorator had is a library form reachable from every
    seat: `memoize-exact` declares it, `get-memoize-stats` reports it and
    `invalidate-memoize` clears it. This is the test's own convenience over
    that route.
    """

    def install(fn):
        defined = space.define(fn, name=name) if name else space.define(fn)
        # Into THIS space, and S["lib_memo"] rather than S.lib_memo, whose
        # attribute door would apply the underscore-to-hyphen map to a
        # LIBRARY name that really does carry an underscore.
        space.eval(S["import!"](space, S.library(S["lib_memo"])))
        space.eval(S.memoize_exact(S[defined.name]))
        return defined

    return install


def _answers(defined, *args):
    """Call in the caller's own table space, which is where the counters live.

    lib_memo's exact store is an SWI table, and a private table belongs to the
    table space that fills it: `enable_exact_memoization`'s own note says so and
    makes the memo generation an ordinary first argument for exactly that
    reason. A lazy answer cursor runs its goal in an engine created by
    `engine_create/3`, which is its own table space, so a call consumed one
    answer at a time memoizes correctly and at the same cost but leaves nothing
    the counters here can read [measured 2026-08-31: fib(25) flat in n through
    both doors; entries 26 eager, 0 through the cursor]. Every assertion below
    that reads a counter therefore calls eagerly.
    """
    return defined.space.eval(S[defined.name](*args))


def _memo_stats(defined) -> dict[str, int]:
    """lib_memo's own counters, which the removed cache_info() wrapped."""
    answers = defined.space.eval(S.get_memoize_stats(S[defined.name]))
    if not answers:
        return {}
    return {str(row[0]): int(row[1]) for row in answers[0] if len(row) == 2}


def _memo_clear(defined) -> None:
    """lib_memo's own invalidation, which the removed cache_clear() wrapped."""
    defined.space.eval(S.invalidate_memoize(S[defined.name]))


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
            (index for index, candidate in enumerate(remaining) if answer.alpha_eq(candidate)),
            None,
        )
        assert match is not None
        remaining.pop(match)
    assert remaining == []


def _install_recursive_bag_pair(memo, plain):
    @_memoized(memo, name="p14-diff-recursive")
    def memo_recursive(n: int):
        yield n
        yield n
        if n > 0:
            yield from memo_recursive(n - 1)

    @plain.define(name="p14-diff-recursive-plain")
    def plain_recursive(n: int):
        yield n
        yield n
        if n > 0:
            yield from plain_recursive(n - 1)

    return memo_recursive, plain_recursive


def test_a_cached_definition_memoizes_its_complete_answer_bag() -> None:
    """The decorator is notation; the answers come from the engine memo."""
    metta = MeTTa().space("&cachedecorator")

    @_memoized(metta)
    def cachedec_fib(n: int) -> int:
        return n if n < 2 else cachedec_fib(n - 1) + cachedec_fib(n - 2)

    with metta.stats() as cached:
        assert _answers(cachedec_fib, _N) == [75025]

    # Counts describe this definition's call-key entries and answer bag.
    info = _memo_stats(cachedec_fib)
    assert info["entries"] == _N + 1
    assert info["answers"] == _N + 1
    _memo_clear(cachedec_fib)
    assert _memo_stats(cachedec_fib) == {"entries": 0, "answers": 0}

    # The same definition without the memo is exponential. It ANSWERS, since
    # the evaluation fuel is opt-in and upstream has none, and the cost is the
    # point. Automatic bag-preserving memoization would deliberately
    # accelerate this shape, so the control uses its public refuse
    # declaration.
    plain = MeTTa().space("&cachedecorator-plain")
    refusal = S.cache(S["cachedec-plain"], S.refuse)
    plain.eval(S.add_atom(S["&metta"], refusal))
    try:

        @plain.define
        def cachedec_plain(n: int) -> int:
            return n if n < 2 else cachedec_plain(n - 1) + cachedec_plain(n - 2)

        with plain.stats() as untabled:
            overrun = list(cachedec_plain(_N))

        assert [str(atom) for atom in overrun] == ["75025"]
        # Measured 2026-08-26: 830,770 inferences uncached against 2,548
        # cached, a ratio of 326.0. The bag-counting trie costs 1.57x the old
        # 1,622-inference set table and recovers 4.49x from the 11,433-
        # inference Prolog-list memo. The floor stays just below the measured
        # ratio so another move away from direct answer-trie dispatch is red.
        assert untabled.inferences > 320 * cached.inferences
    finally:
        plain.eval(S.remove_atom(S["&metta"], refusal))

    # The Python twin is untouched: a cached definition is still a definition.
    assert cachedec_fib.py(10) == 55

    # name= is define's own.
    @_memoized(metta, name="cachedec-named")
    def cachedec_named(n: int) -> int:
        return n if n < 2 else cachedec_named(n - 1) + cachedec_named(n - 2)

    assert _answers(cachedec_named, 20) == [6765]
    assert _memo_stats(cachedec_named) == {"entries": 21, "answers": 21}


def test_a_cached_definition_preserves_duplicate_answers() -> None:
    """Caching preserves the language law that answer multiplicity is visible.

    "Result order within one directive's list is unspecified; result
    multiplicity is specified". A cache may change when an answer is
    computed, but cannot turn the bag
    ``a, a, b`` into the set ``a, b``. This test used to assert that defect;
    it now pins the law on the public decorator itself.
    """
    metta = MeTTa().space("&cachedup")

    @_memoized(metta)
    def cachedup():
        yield "a"
        yield "a"
        yield "b"

    metta.eval(S.config_memoize(S.answer_limit(2), S.aggregate(S.count), S.float(0)))
    try:
        metta.eval(S.clear_memoize_stats())
        assert sorted(str(atom) for atom in _answers(cachedup)) == ['"a"', '"a"', '"b"']
        assert sorted(str(atom) for atom in _answers(cachedup)) == [
            '"a"',
            '"a"',
            '"b"',
        ]
        assert _memo_stats(cachedup) == {"entries": 1, "answers": 3}
        stats = {str(pair[0]): int(pair[1]) for pair in metta.eval(S.get_memoize_stats())[0]}
        assert stats == {"cache_hit": 1, "cache_miss": 1}
    finally:
        metta.eval(S.config_memoize(S.answer_limit(2048), S.aggregate(S.none), S.float(12)))


def test_exact_cache_matches_uncached_answer_bags() -> None:
    """Match an uncached oracle across duplicate, open, recursive, and changed calls."""
    memo = MeTTa().space("&p14-differential-memo")
    plain = MeTTa().space("&p14-differential-plain")
    refusal = S.cache(S["p14-diff-recursive-plain"], S.refuse)
    plain.eval(S.add_atom(S["&metta"], refusal))

    memo_recursive, plain_recursive = _install_recursive_bag_pair(memo, plain)

    @_memoized(memo, name="p14-diff-open")
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

    @_memoized(memo, name="p14-diff-state")
    def memo_state(value):
        yield memo_source(value)

    @plain.define(name="p14-diff-state-plain")
    def plain_state(value):
        yield plain_source(value)

    try:
        _assert_ground_bags_equal(memo_recursive, plain_recursive, (0, 1, 3))
        _assert_alpha_bags_equal(memo_open(V.x), plain_open(V.x))

        assert Counter(map(str, _answers(memo_state, S.seed))) == Counter(
            map(str, plain_state(S.seed))
        )
        assert _memo_stats(memo_state) == {"entries": 1, "answers": 2}

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

        assert _memo_stats(memo_state) == {"entries": 0, "answers": 0}
        assert Counter(map(str, _answers(memo_state, S.seed))) == Counter(
            map(str, plain_state(S.seed))
        )
        assert _memo_stats(memo_state) == {"entries": 1, "answers": 3}
    finally:
        plain.eval(S.remove_atom(S["&metta"], refusal))


def test_exact_memo_wrappers_keep_named_space_owners_separate() -> None:
    """Each cached wrapper enters the dispatch of the space that owns it."""
    left = MeTTa().space("&cache-owner-left")
    right = MeTTa().space("&cache-owner-right")

    @_memoized(left, name="cache-owner-shared")
    def left_shared():
        yield "left"
        yield "left"

    @_memoized(right, name="cache-owner-shared")
    def right_shared():
        yield "right"
        yield "right"
        yield "right"

    assert [str(atom) for atom in _answers(left_shared)] == ['"left"', '"left"']
    assert [str(atom) for atom in _answers(right_shared)] == [
        '"right"',
        '"right"',
        '"right"',
    ]
    assert _memo_stats(left_shared) == {"entries": 1, "answers": 2}
    assert _memo_stats(right_shared) == {"entries": 1, "answers": 3}


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

    @_memoized(metta, name="cache-between-replay")
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

    @_memoized(metta, name="cache-live-derived")
    def derived(value):
        yield source(value)

    with EnginePool(workers=1) as workers:
        first = workers.submit(lambda: Counter(map(str, derived(S.seed)))).result(timeout=30)
        assert first == Counter({"(Before seed)": 2})

        def install_after():
            @metta.define(name="cache-live-source")
            def source(value):
                yield S.After(value)
                yield S.After(value)
                yield S.Extra(value)

            return source

        install_after()

        second = workers.submit(lambda: Counter(map(str, derived(S.seed)))).result(timeout=30)
        assert second == Counter({"(After seed)": 2, "(Extra seed)": 1})


def test_memoizing_an_operation_caches_its_calls() -> None:
    """A registered operation is cached where its calls actually look.

    An operation has no equations, so two things that work for an ordinary
    function do not work here by themselves. Its calls are keyed by the module
    that REGISTERED it, not by the space that spoke the declaration, and its
    call sites are its callers' bodies rather than its own. Enabling used to
    record the declaration in the speaking space, where no call ever looked:
    `memoize-exact` answered true, `is-memoized` answered true, and the
    operation ran on every call.

    The caller below is compiled BEFORE the declaration, which is the half that
    needs the callers rebuilt, and the second space is the half that shows what
    caching an operation means: one predicate, one cache, every space.
    """
    metta = MeTTa().space("&cache-op-reach")
    metta.eval(S["import!"](metta, S.library(S["lib_memo"])))
    calls = []

    @metta.op(name="cache-reach-op", effect="pureStructural")
    def reach(value):
        calls.append(value)
        return value

    metta.run("(= (cache-reach-wrap $x) (cache-reach-op $x))")
    assert metta.run("!(cache-reach-wrap 1)") == [[1]]
    assert calls == [1]

    assert metta.run("!(memoize-exact cache-reach-op)") == [[True]]
    assert metta.run("!(cache-reach-wrap 4)") == metta.run("!(cache-reach-wrap 4)") == [[4]]
    assert calls == [1, 4]

    # One predicate, imported into every space's execution module, so its cache
    # is process-wide. That is what caching an operation is.
    elsewhere = space("&cache-op-elsewhere")
    assert elsewhere.run("!(cache-reach-op 4)") == [[4]]
    assert calls == [1, 4]
    assert elsewhere.run("!(cache-reach-op 9)") == [[9]]
    assert calls == [1, 4, 9]

    metta.unregister_op("cache-reach-op")


def test_memoizing_a_body_that_writes_its_own_space_runs_it_once() -> None:
    """Enabling a cache must not rewrite the program it is enabled over.

    Enabling used to remove each stored equation and add it back around the
    enable. That is not the same term: the source says `(add-atom &self ...)`
    and the retained form the compiler kept carries the space's resolved name,
    so the removal matched nothing, the add left a second copy, and a
    one-equation function became a two-equation one. It then wrote twice and
    answered a doubled bag on its first call, which is a cache changing what
    the program says rather than how often it runs.
    """
    metta = MeTTa().space("&cache-writer")
    metta.eval(S["import!"](metta, S.library(S["lib_memo"])))
    metta.run("(= (cache-writer $x) (let $_ (add-atom &self (cache-wrote $x)) $x))")
    metta.run("!(cache-writer 1)")

    def equations():
        return [a for a in metta.atoms() if str(a).startswith("(= (cache-writer")]

    before = equations()
    assert metta.run("!(memoize cache-writer)") == [[True]]
    assert len(equations()) == len(before) == 1

    assert metta.run("!(cache-writer 7)") == [[7]]
    assert metta.run("!(cache-writer 7)") == [[7]]
    # The 1 is the uncached warm-up; 7 is written once for the two calls.
    assert sorted(str(row.x) for row in metta.match(S.cache_wrote(V.x))) == ["1", "7"]


def test_memoizing_an_effectful_operation_is_the_callers_own_word() -> None:
    """The effect class no longer decides, and no seat's door decides either.

    The removed decorator refused to wrap ANY registered operation, from one
    host, with a message naming functools. lib_memo replaced that with a
    narrower refusal reading the declared effect class, which was still the
    library answering a question the caller had already answered: whether to
    cache their own program is theirs (user ruling, 2026-09-06). What remains
    is that both spellings behave the same wherever `memoize-exact` is written,
    which is what moving the rule off one host bought.

    An `oracleIO` operation is the strongest case there is, and it is admitted
    and served; `test_memoizing_an_operation_caches_its_calls` is where the
    serving is pinned.
    """
    metta = MeTTa().space("&cache-over-op")
    metta.eval(S["import!"](metta, S.library(S["lib_memo"])))

    @metta.op(effect="pureStructural")
    def cache_pure_op(value):
        return value

    @metta.op(effect="oracleIO")
    def cache_io_op(value):
        return value

    assert metta.eval(S.memoize_exact(S["cache-io-op"])) == [True]
    assert metta.eval(S.is_memoized(S["cache-io-op"])) == [True]
    assert cache_io_op(3) == 3

    assert metta.eval(S.memoize_exact(S["cache-pure-op"])) == [True]
    assert cache_pure_op(3) == 3

    # A compiled body over the same operation is where the cache does serve,
    # and it does so whatever the operation's class.
    calls = []

    @metta.op(name="cache-counted-op", effect="oracleIO")
    def counted(value):
        calls.append(value)
        return len(calls)

    metta.run("(= (cache-io-wrap $x) (cache-counted-op $x))")
    assert metta.run("!(memoize cache-io-wrap)") == [[True]]
    assert metta.run("!(cache-io-wrap 4)") == metta.run("!(cache-io-wrap 4)") == [[1]]
    assert calls == [4]

    metta.unregister_op("cache-pure-op")
    metta.unregister_op("cache-io-op")
    metta.unregister_op("cache-counted-op")
