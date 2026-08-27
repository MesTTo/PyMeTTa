"""Purpose: the completeness of the torn-tail classifier, over every point a
record can be cut at rather than over the two or three a hand-written case
happens to pick.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from pathlib import Path

import pytest

from metta import MettaError, S, ground
from metta._persistent import PersistentFactSpace
from metta.errors import EngineError

SCHEMA = {"edge": 2}


def _journal(path: Path, kept, torn) -> tuple[bytes, bytes]:
    """A journal holding `kept`, plus the bytes one `torn` record occupies.

    The record's own text comes from the engine that wrote it, so this reads
    whatever library(persistency) actually spells rather than a guess at it.
    """
    space = PersistentFactSpace(path, SCHEMA, sync="close")
    space.add(kept)
    space.close()
    prefix = path.read_bytes()

    space = PersistentFactSpace(path, SCHEMA, sync="close")
    space.add(torn)
    space.close()
    whole = path.read_bytes()
    return prefix, whole[len(prefix) :].rstrip(b"\n")


def test_every_truncation_point_of_the_torn_tail_classifies(tmp_path):
    """A record is written whole or it is torn, and every torn prefix of it
    is recoverable.

    library(persistency) writes one action and its newline in a single call,
    so a file that ends without that newline ended inside the write. Which
    prefix it stopped at is not the caller's business and cannot be, since a
    crash picks it: the classifier has to answer the same way for all of
    them. The terminating full stop is what separates the two cases, and
    SWI's own reader tests for it. `read_term/2` on a string stream raises
    `syntax_error(end_of_file)` for a term with no full stop, while
    `read_term_from_atom/3` documents the opposite, "It is not required for
    Atom to end with a full-stop"
    [source: https://www.swi-prolog.org/pldoc/doc_for?object=read_term_from_atom/3].

    Measured 2026-08-19 with the atom reader: of the 18 truncation points of
    `assert(edge(a,b)).`, SEVEN were refused. Six of them are prefixes of
    the action's own name, `a` through `assert`, each a perfectly good
    Prolog atom on its own; the seventh is `assert(edge(a,b))`, complete but
    for the full stop. The header promises recovery unconditionally, so
    every one of those seven was a journal an operator had to repair by
    hand after an ordinary crash.

    The shapes cover what a prefix can end inside: a quoted atom holding a
    full stop, a float whose own dot is not one, and a string.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    shapes = {
        "plain": S.edge(S.a, S.b),
        "dotted-symbol": S.edge(S["a.b"], S.b),
        "float": S.edge(S.a, ground(1.5)),
        "string": S.edge(S.a, ground("a.b")),
    }
    refused = []
    for label, torn in shapes.items():
        prefix, record = _journal(tmp_path / f"{label}.db", S.edge(S.kept, S.whole), torn)
        assert record.endswith(b"."), f"{label}: {record!r} is not a full-stop record"
        for cut in range(1, len(record)):
            path = tmp_path / f"{label}-{cut:02d}.db"
            path.write_bytes(prefix + record[:cut])
            try:
                space = PersistentFactSpace(path, SCHEMA, sync="close")
            except MettaError as exc:
                refused.append((label, cut, record[:cut], str(exc).splitlines()[0]))
                continue
            try:
                assert list(space.atoms()) == [S.edge(S.kept, S.whole)], (
                    f"{label} cut {cut}: recovery lost or invented a record"
                )
            finally:
                space.close()
            assert Path(f"{path}.tail").read_bytes() == record[:cut], (
                f"{label} cut {cut}: the torn bytes were not kept beside the journal"
            )
            assert path.read_bytes() == prefix

    assert not refused, "\n".join(
        f"{label} cut {cut} {text!r}: {why}" for label, cut, text, why in refused
    )


def test_a_terminated_record_is_refused_rather_than_truncated(tmp_path):
    """The other side of the same test, so the property above cannot be
    satisfied by recovering everything.

    A tail carrying its terminating full stop was written whole. Only its
    newline is missing, so truncating would throw away a record the writer
    finished, and the answer is to refuse and name it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    path = tmp_path / "terminated.db"
    space = PersistentFactSpace(path, SCHEMA, sync="close")
    space.add(S.edge(S.kept, S.whole))
    space.close()
    before = path.read_bytes() + b"foreign(edge(a,b))."
    path.write_bytes(before)

    with pytest.raises(EngineError, match="complete but invalid record"):
        PersistentFactSpace(path, SCHEMA, sync="close")
    assert path.read_bytes() == before
    assert not Path(f"{path}.tail").exists()
