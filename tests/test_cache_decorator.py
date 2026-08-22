"""Purpose: pin the tabling decorator as notation over the engine's tabling.
Assumes: lib_tabling is importable from the space, which the decorator does
  itself; nothing here declares a table by hand.
Guarantees:
  - a cached definition answers from SWI's answer trie, so an exponential
    recursion becomes linear, and its counters and clear are reachable under
    functools.lru_cache's own names.
  [tested: test_a_cached_definition_tables_and_answers_from_its_trie; commit=WORKTREE]
Fails when: read as a fixed-size cache. A table holds the answers for the calls
  that were made and has no maxsize; `unchecked=True` is the staleness the
  engine's own `(cache <name> unchecked)` accepts, not a size.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from petta import MeTTa

#: Big enough that the untabled twin cannot finish inside the default
#: evaluation fuel, which is the point being made, and small enough that the
#: tabled one is instant.
_N = 25


def test_a_cached_definition_tables_and_answers_from_its_trie() -> None:
    """The decorator is notation; the answers come from the engine's table."""
    metta = MeTTa("&cachedecorator")

    @metta.cache
    def cachedec_fib(n):
        return n if n < 2 else cachedec_fib(n - 1) + cachedec_fib(n - 2)

    with metta.stats() as tabled:
        assert metta.eval(cachedec_fib(_N)) == [75025]

    # The counters are the TABLE's, under lru_cache's names.
    info = cachedec_fib.cache_info()
    assert info["tables"] == _N + 1
    assert info["answers"] == _N + 1
    assert info["invalidated"] == 0
    cachedec_fib.cache_clear()
    assert cachedec_fib.cache_info()["tables"] == 0

    # The same definition without the table is exponential, and on this input
    # it does not finish inside the default evaluation fuel at all.
    plain = MeTTa("&cachedecorator-plain")

    @plain.define
    def cachedec_plain(n):
        return n if n < 2 else cachedec_plain(n - 1) + cachedec_plain(n - 2)

    with plain.stats() as untabled:
        overrun = plain.eval(cachedec_plain(_N))

    assert [str(atom) for atom in overrun] == ["(Error 1 StackOverflow)"]
    assert untabled.inferences > 100 * tabled.inferences

    # The Python twin is untouched: a cached definition is still a definition.
    assert cachedec_fib.py(10) == 55

    # unchecked=True is the engine's own staleness-accepting declaration, and
    # name= is define's own.
    @metta.cache(name="cachedec-named", unchecked=True)
    def cachedec_named(n):
        return n if n < 2 else cachedec_named(n - 1) + cachedec_named(n - 2)

    assert metta.eval(cachedec_named(20)) == [6765]
    assert cachedec_named.cache_info()["answers"] == 21
