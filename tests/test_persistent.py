"""Purpose: journal-backed fact spaces, including registered matching,
validation, replay, compaction, and isolation between independent journals.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import pytest

from petta import PettaError, S, V, val
from petta.persistent import PersistentFactSpace


def test_registered_space_writes_queries_and_persists_remove(metta, tmp_path):
    journal = tmp_path / "registered.db"
    schema = {"edge": 2, "other": 1}
    provider = PersistentFactSpace(journal, schema)
    name = f"&persistent{id(provider)}"
    metta.register_space(name, provider)
    try:
        provider.add(S.edge(S.a, S.b))
        provider.add(S.edge(S.b, S.c))
        provider.add(S.other(S.hidden))
        metta.run(f"!(add-atom {name} (edge c d))")

        assert metta.run(f"!(match {name} (edge b $target) $target)") == [[S.c]]
        assert list(provider.match(S.edge(V.source, V.target))) == [
            S.edge(S.a, S.b),
            S.edge(S.b, S.c),
            S.edge(S.c, S.d),
        ]
        assert metta.run(f"!(remove-atom {name} (edge a b))") == [[True]]
        assert not provider.remove(S.edge(S.a, S.b))
    finally:
        metta.unregister_space(name)
        provider.close()

    reopened = PersistentFactSpace(journal, schema)
    try:
        assert list(reopened.atoms()) == [
            S.edge(S.b, S.c),
            S.edge(S.c, S.d),
            S.other(S.hidden),
        ]
    finally:
        reopened.close()


def test_journal_replays_every_supported_native(tmp_path):
    journal = tmp_path / "natives.db"
    facts = [
        S.fact(S.symbol),
        S.fact("grounded text"),
        S.fact(7),
        S.fact(-2.5),
        S.fact(True),
        S.fact(False),
        S.fact(S.true),
        S.fact(S.false),
    ]
    # On this engine the symbol true IS the boolean atom; every crossing
    # canonicalizes, and the journal follows the engine, so a stored
    # Sym('true') replays as the boolean, exactly like parse("true").
    expected = facts[:6] + [S.fact(True), S.fact(False)]
    first = PersistentFactSpace(journal, {"fact": 1})
    try:
        for fact in facts:
            first.add(fact)
    finally:
        first.close()

    second = PersistentFactSpace(journal, {"fact": 1})
    try:
        assert list(second.atoms()) == expected
    finally:
        second.close()


def test_schema_and_native_refusals_name_the_offender(tmp_path):
    space = PersistentFactSpace(tmp_path / "refusals.db", {"edge": 2})
    try:
        with pytest.raises(PettaError, match="unknown persistent head 'other'"):
            space.add(S.other(S.a, S.b))
        with pytest.raises(PettaError, match="'edge' has arity 2, got 1"):
            space.add(S.edge(S.a))
        with pytest.raises(PettaError, match="live Python object of type object"):
            space.add(S.edge(val(object()), S.b))
        with pytest.raises(PettaError, match=r"argument 1 \(\$x\) is not ground"):
            space.add(S.edge(V.x, S.b))
        with pytest.raises(PettaError, match="argument 1 .* is not a number"):
            space.add(S.edge(S.node(S.a), S.b))
    finally:
        space.close()


def test_compaction_replays_the_same_remaining_facts(tmp_path):
    journal = tmp_path / "compact.db"
    facts = [
        S.edge(S.a, S.b),
        S.edge(S.b, S.c),
        S.edge(S.c, S.d),
        S.edge(S.d, S.e),
    ]
    space = PersistentFactSpace(journal, {"edge": 2})
    try:
        for fact in facts:
            space.add(fact)
        for fact in facts[:3]:
            assert space.remove(fact)
        expected = [facts[-1]]
        # The fast default buffers; flush() is the checkpoint that puts
        # the actions on disk for the journal inspection below.
        space.flush()
        before = journal.read_text()
        assert "retractall(" in before

        space.compact()

        after = journal.read_text()
        assert list(space.atoms()) == expected
        assert len(after) <= len(before)
        assert "retractall(" not in after
    finally:
        space.close()

    reopened = PersistentFactSpace(journal, {"edge": 2})
    try:
        assert list(reopened.atoms()) == expected
    finally:
        reopened.close()


def test_two_journal_paths_do_not_interfere(tmp_path):
    left_path = tmp_path / "left.db"
    right_path = tmp_path / "right.db"
    left = PersistentFactSpace(left_path, {"edge": 2})
    right = PersistentFactSpace(right_path, {"edge": 2})
    try:
        left.add(S.edge(S.left, S.only))
        right.add(S.edge(S.right, S.only))
        assert list(left.atoms()) == [S.edge(S.left, S.only)]
        assert list(right.atoms()) == [S.edge(S.right, S.only)]
        assert left.remove(S.edge(S.left, S.only))
        assert list(right.atoms()) == [S.edge(S.right, S.only)]
    finally:
        left.close()
        right.close()

    left_reopened = PersistentFactSpace(left_path, {"edge": 2})
    right_reopened = PersistentFactSpace(right_path, {"edge": 2})
    try:
        assert list(left_reopened.atoms()) == []
        assert list(right_reopened.atoms()) == [S.edge(S.right, S.only)]
    finally:
        left_reopened.close()
        right_reopened.close()


def test_sync_mode_is_validated():
    with pytest.raises(ValueError, match="sync must be one of"):
        PersistentFactSpace("/tmp/never-created.db", {"x": 1}, sync="fsync")


def _crash_writer(journal, sync_mode, checkpoint):
    """Run a subprocess that adds facts and dies by SIGKILL, no cleanup."""
    import os
    import signal
    import subprocess
    import sys
    import textwrap

    program = textwrap.dedent(
        f"""
        import os, signal
        from petta import S
        from petta.persistent import PersistentFactSpace

        space = PersistentFactSpace({str(journal)!r}, {{"survivor": 1}}, sync={sync_mode!r})
        space.add(S.survivor(1))
        space.add(S.survivor(2))
        {"space.flush()" if checkpoint else "pass"}
        print("WROTE", flush=True)
        os.kill(os.getpid(), signal.SIGKILL)
        """
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    done = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert done.returncode == -signal.SIGKILL, done.stderr
    assert "WROTE" in done.stdout


def test_facts_survive_a_killed_process(tmp_path):
    """The safety ladder, proven with a real SIGKILL: per-write flush
    survives with no cooperation, and the fast default survives exactly
    when flush() checkpointed before the crash."""
    flushed_mode = tmp_path / "flushed-mode.db"
    _crash_writer(flushed_mode, "flush", checkpoint=False)
    replayed = PersistentFactSpace(flushed_mode, {"survivor": 1})
    try:
        assert list(replayed.atoms()) == [S.survivor(1), S.survivor(2)]
    finally:
        replayed.close()

    checkpointed = tmp_path / "checkpointed.db"
    _crash_writer(checkpointed, "none", checkpoint=True)
    replayed = PersistentFactSpace(checkpointed, {"survivor": 1})
    try:
        assert list(replayed.atoms()) == [S.survivor(1), S.survivor(2)]
    finally:
        replayed.close()
