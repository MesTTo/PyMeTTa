"""examples/ch18-performance/18-02-memoisation-and-tabling/17-memo_controls.metta in Python: what lib_memo lets you ask and change.

`get-memoize-config` and the no-argument `get-memoize-stats` take NOTHING,
because what they describe is one global budget rather than a per-function
setting; the per-function question is the other arity of the same name.

WHAT THIS TWIN CANNOT SHOW is the counters' values, for the reason
`08-memo_stats.py` already records: a memoized function called from Python
does not reach lib_memo's dispatch hook, so two calls record a miss each where
two `!` forms in a file record one hit and one miss, and the per-function
entries stay at zero. Every claim below is one that holds either way -- the
answers, the shapes, and what each control DELETES -- and the counter
divergence is in the residue table with its reproduction.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib


def counters(report):
    """Whether a stats answer is pairs of a name and a non-negative count."""
    return all(
        len(pair) == 2 and isinstance(pair[1].value, int) and pair[1].value >= 0
        for pair in report
    )


def twin(m):
    """Memoize exactly, read the policy and the counters, then clear both."""
    m += lib.memo

    @m.define
    def sq(x: int) -> int:
        # (= (sq $x) (* $x $x))
        return x * x

    exact = m.fn["memoize-exact"]
    config, stats = m.fn["get-memoize-config"], m.fn["get-memoize-stats"]
    clear_stats, invalidate = m.fn["clear-memoize-stats"], m.fn["invalidate-memoize"]
    clear, memoized = m.fn["clear-memoize"], m.fn["is-memoized"]

    # `memoize-exact` is `memoize` with the policies that change what a
    # function ANSWERS switched off.
    exact(S.sq).one()
    assert memoized(S.sq) == [True]
    assert m.fn.sq(9) == [81]
    assert m.fn.sq(9) == [81]

    # The policy the library is running under, which takes no argument.
    assert len(config()[0]) == 6
    assert config()[0][0][0] == S.strategy

    # Two arities, two questions: the global counters, and one function's
    # stored entries and answers.
    assert counters(stats()[0])
    assert [pair[0] for pair in stats(S.sq)[0]] == [S.entries, S.answers]
    assert counters(stats(S.sq)[0])

    # A second key is a second call, and the report keeps its shape.
    assert m.fn.sq(4) == [16]
    assert counters(stats(S.sq)[0])
    assert len(stats(S.sq)[0]) == 2

    # `clear-memoize-stats` DELETES the global counters rather than zeroing
    # them, so the report is empty until something is counted again.
    clear_stats().one()
    assert stats() == [()]
    assert m.fn.sq(9) == [81]
    assert counters(stats()[0])
    assert len(stats()[0]) >= 1
    assert counters(stats(S.sq)[0])

    # `invalidate-memoize` drops ONE function's cached answers in this space
    # and leaves the decision to cache it standing.
    invalidate(S.sq).one()
    assert stats(S.sq) == [(S.entries(0), S.answers(0))]
    assert memoized(S.sq) == [True]
    assert m.fn.sq(9) == [81]
    assert counters(stats(S.sq)[0])

    # `clear-memoize` is the wide one: every space's cache, because the
    # memory budget it resets is global. It clears ANSWERS, not decisions.
    clear().one()
    assert stats(S.sq) == [(S.entries(0), S.answers(0))]
    assert memoized(S.sq) == [True]
    assert m.fn.sq(9) == [81]
    assert counters(stats(S.sq)[0])


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 43181 inferences, 0.8699x the example's 49638; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 43181
