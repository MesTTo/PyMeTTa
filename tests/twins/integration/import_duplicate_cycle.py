"""examples/integration/import_duplicate_cycle.metta in Python: importing twice, and in a circle.

One file imported under two spellings of its path loads ONCE, so the marker it
adds is there once and not twice; and two files that import each other both
finish, so both of their functions answer.

The paths are written from the repository root, which also flattens the `./`
and `.` segments the example's second form exists to exercise: a Python program
has no importing file to resolve a relative import against. That is the residue
this file carries; the space itself is the handle, which crosses into the built
term as a grounded operand.
"""

from petta import S

#: The same file twice: once by module name and once with its suffix. Written
#: from the repository root, where the lane runs.
DUPLICATE = S["examples/integration/_fixtures/imports/overhaul/duplicate"]
DUPLICATE_METTA = S["examples/integration/_fixtures/imports/overhaul/duplicate.metta"]
CYCLE = S["examples/integration/_fixtures/imports/overhaul/cycle_a"]

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Import one file twice and a cycle once, then read all three."""
    # Known issue, two halves. `import!` has no Python door on the handle: the
    # perfect spelling is `m.import_(target)`, or `m += lib.<name>` for a
    # shipped library (appendix stamp 1), and neither exists yet. And the
    # generic call door cannot stand in for it, because a call through the
    # function namespace answers a LAZY view: `m.fn["import!"](m, target)` as a
    # statement IMPORTS NOTHING until something pulls its answers [measured
    # 2026-08-23]. The term door evaluates eagerly, so the directive is written
    # that way.
    for target in (DUPLICATE, DUPLICATE_METTA, CYCLE):
        m.eval(S["import!"](m, target))

    # Loaded once, so the marker answers once.
    assert m.fn.duplicate_import_result().one() == S["loaded-once"]

    # Both halves of the cycle finished loading.
    assert m.fn.cycle_a().one() == S.a
    assert m.fn.cycle_b().one() == S.b
