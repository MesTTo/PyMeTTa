"""Purpose: preserve automatic memo decisions after real inference interruptions.

Guarantees: the original recursive-profile and occurrence-bag assertions pass
after sweeping an actual reconciliation through its first completing budget
[tested: test_profile_counts_after_interrupted_reconciliation,
test_occurrences_after_interrupted_reconciliation; commit=WORKTREE].
"""

from itertools import count

import janus_swi as janus

from metta import MeTTa

from . import test_occurrence_memo, test_profile_counts


def interrupt_reconciliation(context):
    """Send every inference limit through the first completed reconciliation."""
    context.self.run("!(import! &self (library lib_memo))")
    janus.consult("memo_interrupt_regression", data="""
        :- module(memo_interrupt_regression, [reconcile/2]).
        reconcile(Budget, Interrupted) :-
            lib_memo:memo_automatic_mark_dirty('$python_memo_interrupt'),
            call_with_inference_limit(lib_memo:memo_automatic_reconcile_dirty,
                                      Budget, Result),
            ( Result == inference_limit_exceeded -> Interrupted = true
            ; Interrupted = false ),
            retractall(lib_memo:memo_automatic_dirty('$python_memo_interrupt')).
    """)
    for budget in count(1):
        answer = janus.query_once(
            "memo_interrupt_regression:reconcile(Budget,Interrupted)",
            {"Budget": budget},
        )
        assert answer["truth"]
        if answer["Interrupted"] == "false":
            assert budget > 1
            return


def test_profile_counts_after_interrupted_reconciliation():
    """A real quota interruption must not suppress automatic recursive caching."""
    with MeTTa() as context:
        interrupt_reconciliation(context)
        with context.space() as space:
            space.run(test_profile_counts.PROGRAM)
            test_profile_counts.test_a_recursive_head_reports_its_own_calls_beside_its_entries(space)


def test_occurrences_after_interrupted_reconciliation():
    """The same interruption preserves the automatic coefficient declaration."""
    with MeTTa() as context:
        interrupt_reconciliation(context)
        test_occurrence_memo.test_recursive_memo_coefficients()
