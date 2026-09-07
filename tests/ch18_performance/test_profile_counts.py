"""Purpose: the profile row's own name, arity and recursive-call count.

They carry a repair: profile_extension(names=) reported 0 calls for every
compiled MeTTa head, because the printed predicate was read back apart in the
host and a quoted module atom holding a colon defeats that.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import contextlib

import pytest

PROGRAM = """
(= (aa-fib $n) (if (< $n 2) $n (+ (aa-fib (- $n 1)) (aa-fib (- $n 2)))))
(= (aa-twice $n) (+ (aa-fib $n) (aa-fib $n)))
"""


@pytest.fixture()
def m(metta):
    """A scratch space holding the two recursive heads, dropped afterwards."""
    with metta._new_space() as space:
        space.run(PROGRAM)
        yield space


@contextlib.contextmanager
def declared(space, *rows):
    """Put catalog rows in &metta for one block and take them out again.

    &metta is the catalog and it is process-wide, so a row left there is a row
    every later test compiles under.
    """
    for row in rows:
        space.run(f"!(add-atom &metta {row})")
    try:
        yield space
    finally:
        for row in rows:
            space.run(f"!(remove-atom &metta {row})")


def head_row(profile, name):
    """The one profile row for a head, by NAME rather than by spelling."""
    rows = [row for row in profile.nodes if row.name == name]
    assert len(rows) == 1, [str(row.predicate) for row in rows]
    return rows[0]


def test_a_profile_row_carries_its_predicate_name_and_arity_apart(m):
    """The parts the profiler knows, sent rather than re-derived in the host."""
    _, profile = m.profile("!(aa-twice 12)")
    row = head_row(profile, "aa-fib")
    assert row.arity == 2
    # The spelling packs the module, the quoting and the arity together:
    # `'$metta_exec:&pyspace_1':'aa-fib'/2` for a head named with a hyphen.
    spelling = str(row.predicate)
    assert spelling.endswith("/2")
    assert "aa-fib" in spelling
    assert spelling.count(":") == 2
    assert row.calls > 0
    assert all(isinstance(int(node.arity), int) for node in profile.nodes)
    assert all(str(node.name) for node in profile.nodes)


def test_profile_extension_counts_a_compiled_head(m):
    """The repair: the same run, the same counts, through the narrower door.

    Every compiled MeTTa head is written `'$metta_exec:&pyspace_N':name/arity`,
    a quoted module atom carrying a colon. Reading the name back out of that
    spelling answered `&pyspace_N':aa-fib`, so the lookup missed and the row
    read 0 calls while profile() showed the real number in the same process.
    """
    with m._new_space() as other:
        other.run(PROGRAM)
        _, profile = other.profile("!(aa-twice 12)")
        expected = head_row(profile, "aa-fib").calls
    _, costs = m.profile_extension("!(aa-twice 12)", names=["aa-fib", "aa-twice"])
    by_name = {cost.name: cost for cost in costs}
    assert by_name["aa-fib"].calls == expected > 0
    assert by_name["aa-twice"].calls == 1
    assert by_name["aa-fib"].arity == 2
    assert by_name["aa-fib"].tier == "equation"


def test_a_recursive_head_reports_its_own_calls_beside_its_entries(m):
    """A head's entries and its own recursion are two numbers, and both are here.

    SWI keeps the recursion on a `<recursive>` caller, which the node's `call`
    count does NOT include, so a caller can ask how often a head really ran
    without taking a second profile.
    """
    with declared(m, "(cache aa-fib refuse)", "(cache aa-twice refuse)"):
        with m._new_space() as uncached:
            uncached.run(PROGRAM)
            _, profile = uncached.profile("!(aa-twice 12)")
            row = head_row(profile, "aa-fib")
            assert row.calls == 2
            assert row.recursive_calls > row.calls
    with m._new_space() as cached:
        cached.run(PROGRAM)
        _, memoised = cached.profile("!(aa-twice 12)")
        memo_row = head_row(memoised, "aa-fib")
        # Under the automatic memo the head is entered once per DISTINCT
        # argument and a hit never reaches it, so its recursion disappears from
        # the profile entirely. That is the pair of readings the memo advisor
        # needs, and the reason it measures two configurations rather than one.
        assert memo_row.recursive_calls == 0
        assert memo_row.calls == 13
