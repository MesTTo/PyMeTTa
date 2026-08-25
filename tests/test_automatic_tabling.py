"""Purpose: pin automatic, bag-preserving memoization through public MeTTa.

Assumes: the resident engine loads lib_memo's dispatch substrate; importing
  lib_memo below only makes its inspection and configuration forms callable.
Guarantees:
  - a pure doubly branching recursive SCC is selected while tail recursion is
    declined [tested:
    test_a_doubly_branching_recursion_is_tabled_automatically_and_a_tail_recursion_is_not;
    commit=9e7d5dc2cad810940e5386d52636ac6946df279d]
  - impurity remains a hard refusal and catalog force/refuse declarations move
    only the profitability decision [tested:
    test_an_impure_function_is_never_cached_automatically,
    test_automatic_cache_force_and_refuse_overrides; commit=9e7d5dc2cad810940e5386d52636ac6946df279d]
  - automatic caching preserves duplicate answer bags even above the manual
    answer limit and under a manual aggregate setting [tested:
    test_automatic_caching_preserves_multiplicity_and_answer_limit;
    commit=9e7d5dc2cad810940e5386d52636ac6946df279d]
Fails when: read as coverage of explicit SWI tabling, whose set semantics are
  separately pinned by test_explicit_tabling_takes_precedence_over_automatic_memoization.
"""

from collections import Counter

from metta import MeTTa


def _cache_item(metta: MeTTa, call: str):
    report = metta.run(f"!(explain {call})")[0][0]
    return next(item for item in report.children if str(item.children[0]) == "cache")


def _cache_text(metta: MeTTa, call: str) -> str:
    return str(_cache_item(metta, call))


def _memo_inspection(metta: MeTTa) -> None:
    metta.run("!(import! &self (library lib_memo))")


def test_a_doubly_branching_recursion_is_tabled_automatically_and_a_tail_recursion_is_not() -> None:
    """Select repeated SCC recursion and decline a single recursive call."""
    metta = MeTTa().space("&p14-auto-basic")
    metta.run(
        """
        (= (p14-auto-doub $n)
           (if (< $n 1)
               1
               (+ (p14-auto-doub (- $n 1))
                  (p14-auto-doub (- $n 1)))))
        (= (p14-auto-tail $n $acc)
           (if (< $n 1)
               $acc
               (p14-auto-tail (- $n 1) (+ $acc 1))))
        """
    )
    _memo_inspection(metta)

    assert metta.run("!(p14-auto-doub 20)") == [[1048576]]
    assert metta.run("!(p14-auto-tail 20 0)") == [[20]]
    assert metta.run("!(is-memoized p14-auto-doub)") == [[True]]
    assert metta.run("!(is-memoized p14-auto-tail)") == [[False]]
    assert _cache_text(metta, "(p14-auto-doub 20)") == (
        "(cache automatic "
        "(recursive-scc (p14-auto-doub) body-call-count 2))"
    )
    assert _cache_text(metta, "(p14-auto-tail 20 0)") == (
        "(cache declined single-recursive-call)"
    )


def test_an_impure_function_is_never_cached_automatically() -> None:
    """Keep the effect walk's impurity refusal stronger than force."""
    metta = MeTTa().space("&p14-auto-impure")
    declaration = "(cache p14-auto-impure force)"
    try:
        metta.run(f"!(add-atom &petta {declaration})")
        metta.run(
            """
            (= (p14-auto-impure $n)
               (if (< $n 1)
                   1
                   (let $_ (println! $n)
                     (+ (p14-auto-impure (- $n 1))
                        (p14-auto-impure (- $n 1))))))
            """
        )
        _memo_inspection(metta)
        assert metta.run("!(is-memoized p14-auto-impure)") == [[False]]
        assert _cache_text(metta, "(p14-auto-impure 3)").startswith(
            "(cache declined (impure "
        )
    finally:
        metta.run(f"!(remove-atom &petta {declaration})")


def test_automatic_cache_force_and_refuse_overrides() -> None:
    """Apply and withdraw both profitability overrides through the catalog."""
    metta = MeTTa().space("&p14-auto-overrides")
    force = "(cache p14-auto-forced force)"
    refuse = "(cache p14-auto-refused refuse)"
    metta.run(
        """
        (= (p14-auto-forced $n $acc)
           (if (< $n 1)
               $acc
               (p14-auto-forced (- $n 1) (+ $acc 1))))
        (= (p14-auto-refused $n)
           (if (< $n 1)
               1
               (+ (p14-auto-refused (- $n 1))
                  (p14-auto-refused (- $n 1)))))
        """
    )
    _memo_inspection(metta)
    assert _cache_text(metta, "(p14-auto-forced 4 0)") == (
        "(cache declined single-recursive-call)"
    )
    assert _cache_text(metta, "(p14-auto-refused 4)").startswith(
        "(cache automatic "
    )
    try:
        metta.run(f"!(add-atom &petta {force})")
        metta.run(f"!(add-atom &petta {refuse})")
        assert metta.run("!(is-memoized p14-auto-forced)") == [[True]]
        assert metta.run("!(is-memoized p14-auto-refused)") == [[False]]
        assert _cache_text(metta, "(p14-auto-forced 4 0)") == (
            "(cache forced declaration)"
        )
        assert _cache_text(metta, "(p14-auto-refused 4)") == (
            "(cache refused declaration)"
        )
    finally:
        metta.run(f"!(remove-atom &petta {force})")
        metta.run(f"!(remove-atom &petta {refuse})")

    assert metta.run("!(is-memoized p14-auto-forced)") == [[False]]
    assert metta.run("!(is-memoized p14-auto-refused)") == [[True]]


def test_automatic_caching_preserves_multiplicity_and_answer_limit() -> None:
    """Preserve bags, exact floats, and full answers past the manual limit."""
    metta = MeTTa().space("&p14-auto-bag")
    refuse = "(cache p14-bag-plain refuse)"
    _memo_inspection(metta)
    metta.run(f"!(add-atom &petta {refuse})")
    try:
        metta.run(
            """
            (= (p14-bag-auto Z) 1)
            (= (p14-bag-auto Z) 1)
            (= (p14-bag-auto Z) 2)
            (= (p14-bag-auto (S $n))
               (+ (p14-bag-auto $n) (p14-bag-auto $n)))
            (= (p14-bag-plain Z) 1)
            (= (p14-bag-plain Z) 1)
            (= (p14-bag-plain Z) 2)
            (= (p14-bag-plain (S $n))
               (+ (p14-bag-plain $n) (p14-bag-plain $n)))
            (= (p14-float-exact Z $x) $x)
            (= (p14-float-exact (S $n) $x)
               (+ (p14-float-exact $n $x)
                  (p14-float-exact $n $x)))
            """
        )
        metta.run("!(config-memoize (answer-limit 2) (aggregate count) (float 0))")
        metta.run("!(clear-memoize)")
        automatic = Counter(str(atom) for atom in metta.run("!(p14-bag-auto (S Z))")[0])
        plain = Counter(str(atom) for atom in metta.run("!(p14-bag-plain (S Z))")[0])
        assert automatic == plain == Counter({"2": 4, "3": 4, "4": 1})
        assert metta.run("!(p14-float-exact (S Z) 1.25)") == [[2.5]]
        assert metta.run("!(p14-float-exact (S Z) 1.75)") == [[3.5]]
        stats = {
            str(pair.children[0]): int(str(pair.children[1]))
            for pair in metta.run("!(get-memoize-stats)")[0][0].children
        }
        assert stats["automatic_answer_limit_bypass"] > 0
    finally:
        metta.run(
            "!(config-memoize (answer-limit 2048) (aggregate none) (float 12))"
        )
        metta.run("!(clear-memoize)")
        metta.run(f"!(remove-atom &petta {refuse})")


def test_scc_profitability_is_per_rhs_and_selects_a_mutual_component() -> None:
    """Count per body, select a mutual SCC, and ignore calls held as data."""
    metta = MeTTa().space("&p14-auto-scc")
    metta.run(
        """
        (= (p14-separate Z) 0)
        (= (p14-separate (S $n)) (p14-separate $n))
        (= (p14-separate (T $n)) (p14-separate $n))
        (= (p14-mutual-a Z) 1)
        (= (p14-mutual-a (S $n))
           (+ (p14-mutual-b $n) (p14-mutual-b $n)))
        (= (p14-mutual-b $n) (p14-mutual-a $n))
        (= (p14-quoted-recursion $n)
           (quote ((p14-quoted-recursion $n)
                   (p14-quoted-recursion $n))))
        (= (p14-noeval-recursion $n)
           (noeval ((p14-noeval-recursion $n)
                    (p14-noeval-recursion $n))))
        (= (p14-error-payload $n)
           (Error (p14-error-payload $n)
                  (p14-error-payload $n)))
        """
    )
    _memo_inspection(metta)
    assert metta.run("!(is-memoized p14-separate)") == [[False]]
    assert _cache_text(metta, "(p14-separate (S Z))") == (
        "(cache declined single-recursive-call)"
    )
    assert metta.run("!(is-memoized p14-mutual-a)") == [[True]]
    assert metta.run("!(is-memoized p14-mutual-b)") == [[True]]
    assert metta.run("!(p14-mutual-a (S (S (S Z))))") == [[8]]
    assert metta.run("!(is-memoized p14-quoted-recursion)") == [[False]]
    assert metta.run("!(is-memoized p14-noeval-recursion)") == [[False]]
    assert metta.run("!(is-memoized p14-error-payload)") == [[False]]


def test_bounded_left_recursive_search_is_not_cached_automatically() -> None:
    """Decline bounded search whose pruning conflicts with eager collection."""
    metta = MeTTa().space("&p14-auto-variant")
    metta.run(
        """
        (= (p14-path a b) (once True))
        (= (p14-path b c) (once True))
        (= (p14-path $a $c)
           (once (and (p14-path $a $b) (p14-path $b $c))))
        """
    )
    _memo_inspection(metta)

    assert metta.run("!(is-memoized p14-path)") == [[False]]
    assert _cache_text(metta, "(p14-path a c)") == (
        "(cache declined (bounded-search once))"
    )
    assert metta.run("!(p14-path a c)") == [[True]]


def test_explicit_tabling_takes_precedence_over_automatic_memoization() -> None:
    """Disable automatic bag caching while an explicit answer trie is live."""
    metta = MeTTa().space("&p14-auto-explicit-table")
    metta.run(
        """
        (= (p14-explicit-table $n)
           (if (< $n 1)
               1
               (+ (p14-explicit-table (- $n 1))
                  (p14-explicit-table (- $n 1)))))
        """
    )
    _memo_inspection(metta)
    assert metta.run("!(is-memoized p14-explicit-table)") == [[True]]

    metta.run("!(import! &self (library lib_tabling))")
    assert metta.run("!(tabled (p14-explicit-table $n))") == [[True]]
    assert metta.run("!(is-memoized p14-explicit-table)") == [[False]]
    assert _cache_text(metta, "(p14-explicit-table 10)") == (
        "(cache declined explicit-tabling)"
    )
    assert metta.run("!(p14-explicit-table 20)") == [[1048576]]

    assert metta.run("!(untabled (p14-explicit-table $n))") == [[True]]
    assert metta.run("!(is-memoized p14-explicit-table)") == [[True]]


def test_automatic_decisions_follow_source_replacement(tmp_path) -> None:
    """Recompute the SCC decision when one source replaces another."""
    source = tmp_path / "automatic-reload.metta"
    metta = MeTTa().space("&p14-auto-reload")
    _memo_inspection(metta)
    source.write_text(
        "(= (p14-auto-reload $n) "
        "(if (< $n 1) 1 (+ (p14-auto-reload (- $n 1)) "
        "(p14-auto-reload (- $n 1)))))\n"
    )
    metta.load(source)
    assert metta.run("!(is-memoized p14-auto-reload)") == [[True]]

    source.write_text(
        "(= (p14-auto-reload $n) "
        "(if (< $n 1) 1 (p14-auto-reload (- $n 1))))\n"
    )
    metta.load(source)
    assert metta.run("!(is-memoized p14-auto-reload)") == [[False]]
    assert metta.run("!(p14-auto-reload 8)") == [[1]]

    source.write_text(
        "(= (p14-auto-reload $n) "
        "(if (< $n 1) 1 (+ (p14-auto-reload (- $n 1)) "
        "(p14-auto-reload (- $n 1)))))\n"
    )
    metta.load(source)
    assert metta.run("!(is-memoized p14-auto-reload)") == [[True]]
    assert metta.run("!(p14-auto-reload 8)") == [[256]]


def test_automatic_decisions_are_isolated_between_same_name_spaces() -> None:
    """Key decisions by execution module as well as function name."""
    branching = MeTTa().space("&p14-auto-isolated-branching")
    tail = MeTTa().space("&p14-auto-isolated-tail")
    branching.run(
        "(= (p14-auto-same $n) "
        "(if (< $n 1) 1 (+ (p14-auto-same (- $n 1)) "
        "(p14-auto-same (- $n 1)))))"
    )
    tail.run(
        "(= (p14-auto-same $n) "
        "(if (< $n 1) 1 (p14-auto-same (- $n 1))))"
    )
    _memo_inspection(branching)
    _memo_inspection(tail)
    assert branching.run("!(is-memoized p14-auto-same)") == [[True]]
    assert tail.run("!(is-memoized p14-auto-same)") == [[False]]
    assert _cache_text(branching, "(p14-auto-same 4)").startswith(
        "(cache automatic "
    )
    assert _cache_text(tail, "(p14-auto-same 4)") == (
        "(cache declined single-recursive-call)"
    )
