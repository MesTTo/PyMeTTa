"""Purpose: exchange CSV through every library head and both typed arities.

Guarantees: the twin preserves the example's field lists, duplicate answers,
live queries and numbered snapshots
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/17-csv_lib.metta; commit=bd027d8b7a9ef1d96fb4cdb160c9b3eb4157d52e].
Owns resources: the temporary directory removes its CSV and writer lock;
snapshots follow the engine's ordinary space lifetime.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import metta
from metta import G, S, V, lib


def twin(m):
    """Use Python values and native space queries around the CSV functions."""
    m += lib.csv
    parse, encode = m.fn.csv_parse, m.fn.csv_encode
    records = ((G("001"), G("a,b")), (G("002"), G("9")))
    assert [list(row) for row in parse(G('001,"a,b"\r\n002,9\r\n')).one()] == [list(row) for row in records]
    assert encode(records) == [G('001,"a,b"\r\n002,9\r\n')]
    skipped = S.quote(((S.separator, G(";")), (S.skip, 1)))
    assert [list(row) for row in parse(G("id;value\n001;a\n001;a\n"), skipped).one()] == [[G("001"), G("a")], [G("001"), G("a")]]
    assert encode(((G("001"), G("a;b")),), S.quote(((S.separator, G(";")), (S.newline, G("\n"))))) == [G('001;"a;b"\n')]
    assert list(parse(G("")).one()) == []
    assert encode(()) == [G("")]
    assert [list(row) for row in parse(G('\n""\n,\n'), S.quote(((S.width, S.any),))).one()] == [[], [G("")], [G(""), G("")]]
    assert [list(row) for row in parse(G('a"b,c\n'), S.quote(((S.quote, G("")),))).one()] == [[G('a"b'), G("c")]]
    unicode_dialect = S.quote(((S.separator, G("🦊")), (S.quote, G("λ"))))
    text = encode(((G("é🦊"), G("λ\r\n")),), unicode_dialect).one()
    assert [list(row) for row in parse(G(text), unicode_dialect).one()] == [[G("é🦊"), G("λ\r\n")]]

    m += lib.file
    with TemporaryDirectory(prefix="metta-csv-") as directory:
        path = G(str(Path(directory) / "records.csv"))
        assert m.fn["csv-write!"](path, records).one() is True
        assert [list(row) for row in m.fn["csv-read!"](path)] == [list(row) for row in records]
        assert m.fn["csv-append!"](path, ((G("002"), G("9")),)).one() is True
        original = [[G("001"), G("a,b")], [G("002"), G("9")], [G("002"), G("9")]]
        assert [list(row) for row in m.fn["csv-read!"](path)] == original
        live = metta.space(m.fn.csv_space(path).one())
        assert [[row.id, row.value] for row in live[S.row(V.id, V.value)]] == original
        snapshot = metta.space(m.fn["csv-snapshot!"](path).one())
        numbered = [[1, G("001"), G("a,b")], [2, G("002"), G("9")], [3, G("002"), G("9")]]
        assert [[row.n, row.id, row.value] for row in snapshot[S.row(V.n, V.id, V.value)]] == numbered

        dialect = S.quote(((S.separator, G(";")),))
        assert m.fn["csv-write!"](path, ((G("id"), G("value")), (G("003"), G("a;b"))), dialect).one() is True
        assert m.fn["csv-append!"](path, ((G("004"), G("7")),), dialect).one() is True
        changed = [[G("003"), G("a;b")], [G("004"), G("7")]]
        assert [list(row) for row in m.fn["csv-read!"](path, skipped)] == changed
        configured = metta.space(m.fn.csv_space(path, skipped).one())
        assert [[row.id, row.value] for row in configured[S.row(V.id, V.value)]] == changed
        kept = metta.space(m.fn["csv-snapshot!"](path, skipped).one())
        assert [[row.n, row.id, row.value] for row in kept[S.row(V.n, V.id, V.value)]] == [[2, G("003"), G("a;b")], [3, G("004"), G("7")]]
        assert [[row.n, row.id, row.value] for row in snapshot[S.row(V.n, V.id, V.value)]] == numbered
        m.fn["csv-write!"](path, ((G("id"), G("value")), (G("005"), G("later"))), dialect).one()
        assert [[row.id, row.value] for row in configured[S.row(V.id, V.value)]] == [[G("005"), G("later")]]


#: CSV text, files, live views and snapshots prove all twenty-two example
#: claims through seven heads and both arities. Configuration uses the
#: language's quote barrier; stored rows retain duplicates and record numbers.
#: [measured 2026-09-11: 103630 inferences, minimum of three serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/17-csv_lib.metta
#: examples/ch08-data/08-03-the-shipped-libraries/05-json_lib.metta; commit=bd027d8b7a9ef1d96fb4cdb160c9b3eb4157d52e].
#: RE-PINNED 2026-09-11, 103630 to 163857 (+60227), String now imports its
#: complete typed native surface and checks its declared native inputs; an
#: unchanged-cut control with identical engine and MORK binaries attributes
#: these exact movements to the String provider and shared native_object/6
#: dependency argument [measured 2026-09-11: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=3aaad3435292e4c7d5cc3a01bfda39430aacc6e8].
#: RE-PINNED 2026-09-12, 163857 to 188409 (+24552), The File library publishes
#: 56 documented heads at 60 arities where it published 32, so every direct and
#: transitive importer pays the larger generated face and the module's own
#: export list. An identical-binary control at 8eb04b55a with artifacts purged
#: measured each of these ten twins before the change (ai-tmp/ai-lib2-file-
#: importers-before.log) and attributes the whole movement to that face:
#: +22,479 on the four twins that only import it through another library,
#: +24,552 to +24,862 where the example also calls it, and +30,258 and +30,687
#: on the two whose own claims are file operations [measured 2026-09-12: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=e40ef941310bddd1f57074eb559e78aac8a263b0].
#: RE-PINNED 2026-09-12, 188409 to 188422 (+13), File transfers newly owned
#: streams through adopt_file_stream/2 and claims a close atomically; HTTP also
#: verifies transaction refusal before server lifecycle effects [measured
#: 2026-09-12: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f22b69cfca5c108e4126bdd56ab9bb2e493744d].
#: RE-PINNED 2026-09-13, 188422 to 188443 (+21), File exports its shared stream
#: borrowing and rollback operations; failed Socket and HTTP publication now
#: withdraws the registered stream before closing it [measured 2026-09-13: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=781ee98e188c23ea7ef9298636d6e5e6c7fdc727].
#: RE-PINNED 2026-09-13, 188443 to 188456 (+13), File privately exports its
#: existing staged publisher with callback qualification; Compression shares
#: that ownership and publication protocol [measured 2026-09-13: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
#: RE-PINNED 2026-09-13, 188456 to 188987 (+531), File exports its staged
#: publisher to Compression; the shared native builder accepts the private
#: archive provider recipe. All consumers are remeasured after those dependency
#: changes [measured 2026-09-13: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
BUDGET = 188987
