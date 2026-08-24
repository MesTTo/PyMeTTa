"""examples/integration/import_duplicate_cycle.metta in Python: twice, and in a circle.

One file imported under two spellings of its path loads ONCE, so the marker it
adds is there once and not twice; and two files that import each other both
finish, so both of their functions answer.

A module name is a NAME rather than text, which is why each one is minted at
the naming factory: slashes, dots and a suffix are all things Python's grammar
cannot say in an attribute, so rung 5's bracket spells them exactly. The second
spelling keeps the original's `./` and `.` segments, because resolving those to
the same module is half of what the first claim is about.

The paths are written from the repository root, where a Python program runs;
resolving one against the importing FILE is what a MeTTa program gets for free
and this does not (friction, P14.13). The space is the handle itself, which
crosses into the built term as a grounded operand.
"""

from metta import S

#: The same file twice: once by module name, once with `./` and `.` segments
#: and a suffix. Written from the repository root, where the lane runs.
DUPLICATE = S["examples/integration/_fixtures/imports/overhaul/duplicate"]
DUPLICATE_METTA = S["examples/integration/_fixtures/imports/overhaul/./duplicate.metta"]
CYCLE = S["examples/integration/_fixtures/imports/overhaul/cycle_a"]

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
BUDGET = 1


def twin(m):
    """Import one file twice and a cycle once, then read all three."""
    # Known issue: `import!` has no Python door on the handle. The perfect
    # spelling is `m.import_(target)`, or `m += lib.<name>` for a shipped
    # library (appendix stamp 1), and neither exists yet, so the directive is
    # reached by its own bang name, which performs it where it is written.
    for target in (DUPLICATE, DUPLICATE_METTA, CYCLE):
        m.fn["import!"](m, target)

    # Loaded once, so the marker answers once.
    assert m.fn.duplicate_import_result().one() == S["loaded-once"]

    # Both halves of the cycle finished loading.
    assert m.fn.cycle_a().one() == S.a
    assert m.fn.cycle_b().one() == S.b
