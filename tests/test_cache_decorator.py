"""Purpose: pin the tabling decorator as notation over the engine's tabling.
Assumes: lib_tabling is importable from the space, which the decorator does
  itself; nothing here declares a table by hand.
Guarantees:
  - a cached definition answers from SWI's answer trie, so an exponential
    recursion becomes linear, and its counters and clear are reachable under
    functools.lru_cache's own names; the uncached control declares the
    automatic memo policy's explicit refusal.
  [tested: test_a_cached_definition_tables_and_answers_from_its_trie; commit=9e7d5dc2cad810940e5386d52636ac6946df279d]
  - a table normalises duplicate answers away, which the arbiter SPECIFIES for
    an untabled function, so the decorator is where a program asks for that
    trade rather than something it discovers.
  [tested: test_a_cached_definition_normalises_duplicate_answers_away; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
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
    metta = MeTTa().space("&cachedecorator")

    @metta.cache
    def cachedec_fib(n):
        return n if n < 2 else cachedec_fib(n - 1) + cachedec_fib(n - 2)

    with metta.stats() as tabled:
        assert cachedec_fib(_N) == [75025]

    # The counters are the TABLE's, under lru_cache's names.
    info = cachedec_fib.cache_info()
    assert info["tables"] == _N + 1
    assert info["answers"] == _N + 1
    assert info["invalidated"] == 0
    cachedec_fib.cache_clear()
    assert cachedec_fib.cache_info()["tables"] == 0

    # The same definition without the table is exponential, and on this input
    # it does not finish inside the default evaluation fuel at all. Automatic
    # bag-preserving memoization would deliberately accelerate this shape, so
    # the control uses its public refuse declaration.
    plain = MeTTa().space("&cachedecorator-plain")
    refusal = "(cache cachedec_plain refuse)"
    plain.run(f"!(add-atom &petta {refusal})")
    try:

        @plain.define
        def cachedec_plain(n):
            return n if n < 2 else cachedec_plain(n - 1) + cachedec_plain(n - 2)

        with plain.stats() as untabled:
            overrun = list(cachedec_plain(_N))

        assert [str(atom) for atom in overrun] == ["(Error 1 StackOverflow)"]
        assert untabled.inferences > 100 * tabled.inferences
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
    assert cachedec_named.cache_info()["answers"] == 21


def test_a_cached_definition_normalises_duplicate_answers_away() -> None:
    """A table is a SET of answers, and the arbiter specifies multiplicity.

    "Result order within one directive's list is unspecified; result
    multiplicity is specified" [source: LeaTTa wiki/Specification.md:22], and
    lib_tabling says the same thing from the other side: tabling normalises
    "answer ORDER and DUPLICATES" away. So a function with non-exclusive
    equations means something different once cached, and this is where a
    program asks for that. lib_memo's `(memoized ...)` is the door that keeps
    the bag.
    """
    plain = MeTTa().space("&cachedup-plain")
    plain.run("(= (cachedup) a)\n(= (cachedup) a)\n(= (cachedup) b)")
    assert sorted(str(atom) for atom in plain.run("!(cachedup)")[0]) == ["a", "a", "b"]

    tabled = MeTTa().space("&cachedup-tabled")
    tabled.run("!(import! &self (library lib_tabling))")
    tabled.run("(= (cachedup) a)\n(= (cachedup) a)\n(= (cachedup) b)")
    assert tabled.run("!(tabled (cachedup))") == [[True]]
    assert sorted(str(atom) for atom in tabled.run("!(cachedup)")[0]) == ["a", "b"]

    # lib_memo keeps the bag, which is why it is the other door rather than a
    # slower spelling of this one.
    memoized = MeTTa().space("&cachedup-memo")
    memoized.run("!(import! &self (library lib_memo))")
    memoized.run("(= (cachedup) a)\n(= (cachedup) a)\n(= (cachedup) b)")
    memoized.run("!(memoized (cachedup))")
    answers = sorted(str(atom) for atom in memoized.run("!(cachedup)")[0])
    assert answers == ["a", "a", "b"]
