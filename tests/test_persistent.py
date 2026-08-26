"""Purpose: journal-backed fact spaces, including registered matching,
validation, replay, terminal-tail repair, failed-write containment,
compaction, and isolation between independent journals.
Guarantees:
  - replay rename maps migrate every journal action atomically, name absent
    old heads with a remedy, and cannot be applied to the migrated journal a
    second time [tested:
    test_a_replay_rename_migrates_every_journal_action_once,
    test_a_replay_rename_with_an_absent_old_name_refuses_with_the_remedy,
    test_a_second_replay_does_not_reapply_the_rename,
    test_replay_rename_composes_with_terminal_tail_recovery; commit=ee43d4a0585593b4f40d0c3c0557db8214688829]
  - live State cells are refused before journal append and leave no replayable
    residue after close and reopen [tested:
    test_a_live_state_cell_never_enters_the_persistent_journal;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - journaled spaces stage transaction/speculation writes, publish only a
    committed event segment, and replay no rolled-back fact [tested:
    test_a_journal_transaction_publishes_only_its_committed_delta,
    test_a_speculative_journal_write_is_neither_persisted_nor_published;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import logging
import os
import signal
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from metta import (
    Expression,
    PettaError,
    S,
    State,
    V,
    ground,
)
from metta._persistent import PersistentFactSpace
from metta.errors import EngineError


def test_registered_space_writes_queries_and_persists_remove(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "registered.db"
    schema = {"edge": 2, "other": 1}
    provider = PersistentFactSpace(journal, schema)
    name = f"&persistent{id(provider)}"
    metta._register_space(provider, name)
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
        # Unit, not True: remove-atom is typed (-> spaceType Atom (->)), so a
        # removal that happened answers the unit value. Absence answers an
        # error instead, and this atom is there, so unit is the answer here
        # [tested test_removing_an_absent_atom_is_an_error_not_a_silent_unit].
        assert metta.run(f"!(remove-atom {name} (edge a b))") == [[Expression()]]
        # The provider's own bool is the other half of the same fact: the
        # removal above took the edge, so the second one finds nothing.
        assert not provider.remove(S.edge(S.a, S.b))
    finally:
        metta._unregister_space(name)
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


def test_journal_replays_every_supported_native(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "natives.db"
    facts = [
        S.fact(S.symbol),
        S.fact("grounded text"),
        S.fact(7),
        S.fact(-2.5),
        S.fact(True),  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        S.fact(False),  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
        S.fact(S.true),
        S.fact(S.false),
    ]
    # On this engine the symbol true IS the boolean atom; every crossing
    # canonicalizes, and the journal follows the engine, so a stored
    # Symbol('true') replays as the boolean, exactly like parse("true").
    expected = [*facts[:6], S.fact(True), S.fact(False)]  # noqa: FBT003  -- the boolean literal is atom or wire data at this site, not a behavior switch
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


def _write_old_head_journal(journal) -> None:
    space = PersistentFactSpace(journal, {"old": 1}, sync="close")
    try:
        space.add(S.old(S.value))
    finally:
        space.close()


def test_a_replay_rename_migrates_every_journal_action_once(tmp_path):
    """Only stored fact heads change; action kind, arguments, and order stay."""
    journal = tmp_path / "all-rename-actions.db"
    journal.write_text(
        "created(1).\n"
        "assert(old(old)).\n"
        "assert(old(drop)).\n"
        "retract(old(drop)).\n"
        "assert(old(swept)).\n"
        "retractall(old(swept),1).\n"
        "asserta(old(first)).\n"
        "assert(old(last)).\n",
        encoding="utf-8",
    )

    migrated = PersistentFactSpace(
        journal,
        {"new": 1},
        sync="close",
        rename={"old": "new"},
    )
    try:
        assert list(migrated.atoms()) == [
            S.new(S.first),
            S.new(S.old),
            S.new(S.last),
        ]
        with pytest.raises(PettaError, match="unknown persistent head 'old'"):
            migrated.add(S.old(S.alias))
    finally:
        migrated.close()

    text = journal.read_text(encoding="utf-8")
    assert "assert(new(old))." in text
    assert "asserta(new(first))." in text
    assert "retract(new(drop))." in text
    assert "retractall(new(swept),1)." in text


def test_a_replay_rename_with_an_absent_old_name_refuses_with_the_remedy(tmp_path):
    """A typo cannot turn a requested migration into a silent partial one."""
    journal = tmp_path / "absent-old.db"
    _write_old_head_journal(journal)
    original = journal.read_bytes()

    with pytest.raises(PettaError, match=r"absent old.*'missing'.*remove.*rename="):
        PersistentFactSpace(
            journal,
            {"new": 1, "other": 1},
            sync="close",
            rename={"old": "new", "missing": "other"},
        )
    assert journal.read_bytes() == original


def test_a_second_replay_does_not_reapply_the_rename(tmp_path):
    """The materialized migration leaves no live old-name alias behind."""
    journal = tmp_path / "one-shot.db"
    _write_old_head_journal(journal)

    migrated = PersistentFactSpace(
        journal,
        {"new": 1},
        sync="close",
        rename={"old": "new"},
    )
    migrated.close()

    with pytest.raises(PettaError, match=r"absent old.*'old'.*remove.*rename="):
        PersistentFactSpace(
            journal,
            {"new": 1},
            sync="close",
            rename={"old": "new"},
        )

    replayed = PersistentFactSpace(journal, {"new": 1}, sync="close")
    try:
        assert list(replayed.atoms()) == [S.new(S.value)]
    finally:
        replayed.close()


def test_replay_rename_composes_with_terminal_tail_recovery(tmp_path):
    """A crashed old-schema append is repaired before its one-time rename."""
    journal = tmp_path / "rename-torn-tail.db"
    _write_old_head_journal(journal)
    torn = b"assert(old(torn)"
    with journal.open("ab") as stream:
        stream.write(torn)

    migrated = PersistentFactSpace(
        journal,
        {"new": 1},
        sync="close",
        rename={"old": "new"},
    )
    try:
        assert list(migrated.atoms()) == [S.new(S.value)]
    finally:
        migrated.close()

    assert Path(f"{journal}.tail").read_bytes() == torn
    assert "old" not in journal.read_text(encoding="utf-8")


def test_schema_and_native_refusals_name_the_offender(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = PersistentFactSpace(tmp_path / "refusals.db", {"edge": 2})
    try:
        with pytest.raises(PettaError, match="unknown persistent head 'other'"):
            space.add(S.other(S.a, S.b))
        with pytest.raises(PettaError, match="'edge' has arity 2, got 1"):
            space.add(S.edge(S.a))
        with pytest.raises(PettaError, match="live Python object of type object"):
            space.add(S.edge(ground(object()), S.b))
        with pytest.raises(PettaError, match=r"argument 1 \(\$x\) is not ground"):
            space.add(S.edge(V.x, S.b))
        with pytest.raises(PettaError, match=r"argument 1 .* is not a number"):
            space.add(S.edge(S.node(S.a), S.b))
    finally:
        space.close()


def test_a_live_state_cell_never_enters_the_persistent_journal(metta, tmp_path):
    """A generated cell handle is process state, not durable symbol data."""
    journal = tmp_path / "state-cell.db"
    cell = State(1, space=metta)
    space = PersistentFactSpace(journal, {"Hits": 1}, sync="close")
    try:
        with pytest.raises(PettaError, match="live State cell"):
            space.add(S.Hits(cell))
    finally:
        space.close()

    reopened = PersistentFactSpace(journal, {"Hits": 1}, sync="close")
    try:
        assert list(reopened.atoms()) == []
    finally:
        reopened.close()


def test_a_journal_transaction_publishes_only_its_committed_delta(metta, tmp_path):
    """The provider stages behind the existing transaction coordinator."""
    journal = tmp_path / "transaction.db"
    space = metta.metta.space(
        journal=journal,
        schema={"entry": 1},
        sync="close",
    )
    space.events("per-write-exactly", "ordered")
    seen = []
    subscription = space.subscribe(S.entry(V.value), seen.append)
    try:
        def rolled_back():
            space.add(S.entry(S.rolled_back))
            assert space.atoms() == [S.entry(S.rolled_back)]
            assert seen == []
            msg = "discard journal transaction"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="discard journal transaction"):
            space.transaction(rolled_back)
        assert space.atoms() == []
        assert seen == []

        def committed():
            space.add(S.entry(S.first), S.entry(S.second))
            assert space.atoms() == [S.entry(S.first), S.entry(S.second)]
            assert seen == []

        space.transaction(committed)
        assert [event.atom for event in seen] == [
            S.entry(S.first),
            S.entry(S.second),
        ]
    finally:
        subscription.cancel()
        space.drop()

    reopened = PersistentFactSpace(journal, {"entry": 1}, sync="close")
    try:
        assert list(reopened.atoms()) == [S.entry(S.first), S.entry(S.second)]
    finally:
        reopened.close()


def test_a_speculative_journal_write_is_neither_persisted_nor_published(
    metta, tmp_path
):
    """Snapshot rollback includes an enlisted journal provider savepoint."""
    journal = tmp_path / "speculative.db"
    space = metta.metta.space(
        journal=journal,
        schema={"entry": 1},
        sync="close",
    )
    space.events("per-write-exactly", "ordered")
    seen = []
    subscription = space.subscribe(S.entry(V.value), seen.append)
    try:
        with space.speculative():
            space.run("(entry discarded)")
        assert space.atoms() == []
        assert seen == []
    finally:
        subscription.cancel()
        space.drop()

    reopened = PersistentFactSpace(journal, {"entry": 1}, sync="close")
    try:
        assert list(reopened.atoms()) == []
    finally:
        reopened.close()


def test_compaction_replays_the_same_remaining_facts(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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
        # One `retract(` per removal, because removal is multiset
        # subtraction and the journal records what was done rather than
        # what was asked for.
        assert before.count("retract(") == 3

        space.compact()

        after = journal.read_text()
        assert list(space.atoms()) == expected
        assert len(after) <= len(before)
        assert "retract(" not in after
    finally:
        space.close()

    reopened = PersistentFactSpace(journal, {"edge": 2})
    try:
        assert list(reopened.atoms()) == expected
    finally:
        reopened.close()


def test_two_journal_paths_do_not_interfere(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
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


def test_sync_mode_is_validated():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="sync must be one of"):
        PersistentFactSpace("/tmp/never-created.db", {"x": 1}, sync="fsync")


def _crash_writer(journal, sync_mode, checkpoint):
    """Run a subprocess that adds facts and dies by SIGKILL, no cleanup."""
    program = textwrap.dedent(
        f"""
        import os, signal
        from metta import S
        from metta._persistent import PersistentFactSpace

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
    when flush() checkpointed before the crash.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
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


def test_clear_journal_reopens_after_variable_retractall(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "clear.db"
    schema = {"edge": 2, "label": 1}
    space = PersistentFactSpace(journal, schema, sync="close")
    try:
        space.add(S.edge(S.a, S.b))
        space.add(S.edge(S.b, S.c))
        space.add(S.label(S.kept))
        space.clear()
        assert list(space.atoms()) == []
    finally:
        space.close()

    assert "retractall(" in journal.read_text()
    reopened = PersistentFactSpace(journal, schema, sync="close")
    try:
        assert list(reopened.atoms()) == []
    finally:
        reopened.close()


@pytest.mark.parametrize(
    ("action", "error_name"),
    [
        ("retractall(edge(_),1).\n", "persistent_schema"),
        ("retractall(other(_,_),1).\n", "persistent_schema"),
        ("retractall(edge(_,_),-1).\n", "persistent_retract_count"),
        ("retractall(edge(node(a),_),1).\n", "persistent_native"),
    ],
)
def test_retractall_validation_keeps_schema_count_and_native_checks(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    tmp_path, action, error_name
):
    journal = tmp_path / f"invalid-retractall-{error_name}.db"
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    space.add(S.edge(S.valid, S.prefix))
    space.close()
    with journal.open("a") as stream:
        stream.write(action)

    with pytest.raises(EngineError, match=error_name):
        PersistentFactSpace(journal, {"edge": 2}, sync="close")


def test_failed_append_rolls_back_memory_and_refuses_more_writes(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "failed-append.db"
    saved = tmp_path / "failed-append.saved"
    first = S.edge(S.a, S.b)
    rejected = S.edge(S.c, S.d)
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    try:
        space.add(first)
        journal.replace(saved)
        journal.mkdir()
        with pytest.raises(EngineError, match="source_sink"):
            space.add(rejected)
        assert list(space.atoms()) == [first]
        with pytest.raises(PettaError, match=r"unusable for writes.*earlier add"):
            space.add(S.edge(S.e, S.f))
    finally:
        if journal.is_dir():
            journal.rmdir()
        if saved.exists():
            saved.replace(journal)
        space.close()

    reopened = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    try:
        assert list(reopened.atoms()) == [first]
    finally:
        reopened.close()


@pytest.mark.parametrize("operation", ["remove", "clear"])
def test_failed_retract_append_rolls_back_every_memory_change(tmp_path, operation):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / f"failed-{operation}.db"
    saved = tmp_path / f"failed-{operation}.saved"
    facts = [S.edge(S.a, S.b), S.edge(S.c, S.d)]
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    try:
        for fact in facts:
            space.add(fact)
        journal.replace(saved)
        journal.mkdir()
        with pytest.raises(EngineError, match="source_sink"):
            if operation == "remove":
                space.remove(facts[0])
            else:
                space.clear()
        assert list(space.atoms()) == facts
        with pytest.raises(PettaError, match=f"earlier {operation}"):
            space.clear()
    finally:
        if journal.is_dir():
            journal.rmdir()
        if saved.exists():
            saved.replace(journal)
        space.close()

    reopened = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    try:
        assert list(reopened.atoms()) == facts
    finally:
        reopened.close()


def test_incomplete_terminal_record_is_backed_up_and_removed(tmp_path, caplog):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "terminal-tail.db"
    prefix_facts = [S.edge(S.a, S.b), S.edge(S.b, S.c)]
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    try:
        for fact in prefix_facts:
            space.add(fact)
    finally:
        space.close()

    complete_prefix = journal.read_bytes()
    incomplete_tail = b"assert(edge(c,"
    with journal.open("ab") as stream:
        stream.write(incomplete_tail)

    with caplog.at_level(logging.WARNING, logger="metta._persistent"):
        recovered = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    try:
        assert list(recovered.atoms()) == prefix_facts
    finally:
        recovered.close()
    assert journal.read_bytes() == complete_prefix
    assert (tmp_path / "terminal-tail.db.tail").read_bytes() == incomplete_tail
    assert "recovered persistent journal" in caplog.text
    assert "truncating at byte" in caplog.text


def test_tail_backup_is_durable_before_truncation(tmp_path, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "durable-tail.db"
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    space.add(S.edge(S.a, S.b))
    space.close()
    with journal.open("ab") as stream:
        stream.write(b"assert(edge(c,")

    synced = []
    real_fsync = os.fsync

    def record_fsync(descriptor):
        mode = os.fstat(descriptor).st_mode
        synced.append("directory" if stat.S_ISDIR(mode) else "file")
        real_fsync(descriptor)

    monkeypatch.setattr("metta._persistent.os.fsync", record_fsync)
    recovered = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    recovered.close()

    expected = ["file", "directory", "file"] if os.name == "posix" else ["file", "file"]
    assert synced == expected


def test_corruption_before_an_incomplete_tail_is_refused_unchanged(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "earlier-corruption.db"
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    space.add(S.edge(S.valid, S.prefix))
    space.close()
    corrupt = journal.read_bytes() + b"foreign(edge(a,b)).\nassert(edge(c,"
    journal.write_bytes(corrupt)

    with pytest.raises(
        EngineError, match="corrupt before its incomplete terminal record"
    ):
        PersistentFactSpace(journal, {"edge": 2}, sync="close")
    assert journal.read_bytes() == corrupt
    assert not (tmp_path / "earlier-corruption.db.tail").exists()


def test_complete_invalid_terminal_record_is_not_treated_as_truncation(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "terminal-corruption.db"
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    space.add(S.edge(S.valid, S.prefix))
    space.close()
    corrupt = journal.read_bytes() + b"foreign(edge(a,b))."
    journal.write_bytes(corrupt)

    with pytest.raises(EngineError, match="complete but invalid record"):
        PersistentFactSpace(journal, {"edge": 2}, sync="close")
    assert journal.read_bytes() == corrupt
    assert not (tmp_path / "terminal-corruption.db.tail").exists()


def test_two_records_glued_by_a_lost_newline_are_refused(tmp_path):
    """The one torn shape where truncating would DESTROY data, so it does not.

    Recovery works by finding the last newline and treating what follows as a
    partially written record. If the newline BETWEEN two records is the byte
    that was lost, the first of the two was fully written and synced, and
    truncating would throw it away to repair damage it was not part of.

    Nor can the two be split back apart. SWI reads `assert(a).assert(b).` as
    ONE term, the full stop between them being an operator rather than an end
    token, so there is nothing but a guess to say where the boundary was, and
    guessing at the shape of a record is how a repair silently invents data.

    What it does instead is name the glued term in the refusal, which is what
    an operator needs to repair the file by hand.
    """
    journal = tmp_path / "glued.db"
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    space.add(S.edge(S.first, S.record))
    space.add(S.edge(S.second, S.record))
    space.close()
    whole = journal.read_bytes()
    assert whole.count(b"\n") >= 2
    # Lose the newline between the last two records, and nothing else.
    boundary = whole.rfind(b"\n", 0, whole.rfind(b"\n"))
    glued = whole[:boundary] + whole[boundary + 1 :]
    journal.write_bytes(glued)

    with pytest.raises(EngineError, match="corrupt before its terminal record") as caught:
        PersistentFactSpace(journal, {"edge": 2}, sync="close")
    # Both records are named, so the repair is a text edit rather than a hunt.
    assert "assert(edge(first,record)).assert(edge(second,record))" in str(caught.value)
    # Refused UNCHANGED, which is the point: the operator still has both.
    assert journal.read_bytes() == glued
    assert not (tmp_path / "glued.db.tail").exists()


def test_prolog_journal_errors_use_the_petta_error_taxonomy(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "invalid-action.db"
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    space.add(S.edge(S.valid, S.prefix))
    space.close()
    with journal.open("ab") as stream:
        stream.write(b"foreign(edge(a,b)).\n")

    with pytest.raises(EngineError, match="persistent_journal_action") as caught:
        PersistentFactSpace(journal, {"edge": 2}, sync="close")
    assert caught.value.__cause__ is not None


def test_invalid_tail_status_keeps_validation_failure_as_cause(tmp_path, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "invalid-tail-status.db"
    space = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    space.add(S.edge(S.valid, S.prefix))
    space.close()
    with journal.open("ab") as stream:
        stream.write(b"assert(edge(c,")

    original_call = PersistentFactSpace._call

    def invalid_tail_status(self, action, *args, **kwargs):
        if action == "tail_status":
            return {"Status": object()}
        return original_call(self, action, *args, **kwargs)

    monkeypatch.setattr(PersistentFactSpace, "_call", invalid_tail_status)
    with pytest.raises(EngineError, match="invalid status") as caught:
        PersistentFactSpace(journal, {"edge": 2}, sync="close")
    assert isinstance(caught.value.__cause__, PettaError)


def test_detached_modules_are_reused_without_weakening_path_claims(tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "module-pool.db"
    first = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    first_module = first._module
    try:
        with pytest.raises(PettaError, match="already attached"):
            PersistentFactSpace(journal, {"edge": 2}, sync="close")
    finally:
        first.close()

    second = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    try:
        assert second._module == first_module
    finally:
        second.close()


def test_constructor_failure_releases_path_and_unattached_module(tmp_path, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    journal = tmp_path / "constructor-rollback.db"
    original = PersistentFactSpace._validate_or_repair_tail
    attempted_modules = []

    def fail_once(space):
        attempted_modules.append(space._module)
        if len(attempted_modules) == 1:
            msg = "validation probe failed"
            raise RuntimeError(msg)
        return original(space)

    monkeypatch.setattr(PersistentFactSpace, "_validate_or_repair_tail", fail_once)

    with pytest.raises(RuntimeError, match="validation probe failed"):
        PersistentFactSpace(journal, {"edge": 2}, sync="close")

    recovered = PersistentFactSpace(journal, {"edge": 2}, sync="close")
    try:
        assert attempted_modules == [recovered._module, recovered._module]
    finally:
        recovered.close()
