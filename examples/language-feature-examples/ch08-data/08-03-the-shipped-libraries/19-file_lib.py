"""Purpose: reach every File head from Python.

Bytes, publication, renames, trees, traversal, globbing, paths, kinds, links,
scopes and handles, in the order the MeTTa original walks them.

A path is text, so paths are `G(...)` strings joined by the library's own
`path-join`. Bytes are tuples of integers, traversal and globbing are answer
streams a list comprehension drains, and a scope takes a FUNCTION: `@m.define`
gives the engine one it applies to the handle or directory it acquired, and a
generator there is the nondeterministic body the MeTTa original writes with
`superpose`.

Guarantees: the same claims as 19-file_lib.metta
[tested: python extensions/python/tools/twin_coverage.py examples/ch08-data/08-03-the-shipped-libraries/19-file_lib.metta; commit=e40ef941310bddd1f57074eb559e78aac8a263b0].
Owns resources: one temporary directory holds everything and `delete-tree!`
removes it at the end; every handle this file opens is closed.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import G, S, V, lib
from metta._errors.errors import MettaError


def twin(m):
    """Every File operation, through the functions the library publishes."""
    m += lib.file

    join = m.fn.path_join
    read, write, append = m.fn["read-file!"], m.fn["write-file!"], m.fn["append-file!"]
    read_bytes, write_bytes = m.fn["read-bytes!"], m.fn["write-bytes!"]
    kind, exists, dir_exists = m.fn.file_kind, m.fn["file-exists"], m.fn["dir-exists"]
    open_, close = m.fn["file-open!"], m.fn["file-close!"]
    size, seek, exact = m.fn["file-get-size!"], m.fn["file-seek!"], m.fn["file-read-exact!"]
    read_all, read_some = m.fn["file-read-to-string!"], m.fn["file-read-bytes!"]
    walk, glob, listing = m.fn.dir_walk, m.fn.dir_glob, m.fn["list-dir!"]
    remove_tree, link_at, link_of = m.fn["delete-tree!"], m.fn["make-link!"], m.fn["read-link"]

    def refused(call):
        """Whether evaluating a call raises, which is what if-error reads."""
        try:
            list(m.eval(call))
        except MettaError:
            return True
        return False

    # A fresh directory, minted exclusively, is where the whole twin works.
    directory = m.fn["temp-dir!"](G("file-lib")).one()

    def under(relative):
        """A path inside that directory, built the way the original builds it."""
        return join(directory, relative).one()

    assert dir_exists(directory) == [True]
    assert kind(directory) == [S.directory]

    # Text files: the whole-file trio and the lines as data.
    notes = under(G("notes.txt"))
    assert write(notes, G("alpha\nbeta\n")) == [True]
    assert append(notes, G("gamma\n")) == [True]
    assert read(notes) == [G("alpha\nbeta\ngamma\n")]
    assert list(m.fn["file-lines!"](notes).one()) == [G("alpha"), G("beta"), G("gamma")]
    lines = metta.space(m.fn["file-space!"](notes).one())
    assert [row.text for row in lines[S.line(2, V.text)]] == [G("beta")]
    assert exists(notes) == [True]
    assert kind(notes) == [S.file]

    # Bytes are integers 0 to 255, whole-file and by handle.
    blob = under(G("blob.bin"))
    assert write_bytes(blob, (0, 1, 255, 10)) == [True]
    assert m.fn["append-bytes!"](blob, (7,)) == [True]
    assert list(read_bytes(blob).one()) == [0, 1, 255, 10, 7]
    handle = open_(blob, G("rb")).one()
    assert list(read_some(handle, 2).one()) == [0, 1]
    assert list(read_some(handle).one()) == [255, 10, 7]
    close(handle).one()
    handle = open_(blob, G("wb")).one()
    assert m.fn["file-write-bytes!"](handle, (65, 66)) == [True]
    close(handle).one()
    assert read(blob) == [G("AB")]

    # A byte operation on a text handle, and an invalid byte, refuse by name.
    handle = open_(blob, G("r")).one()
    assert refused(S["file-read-bytes!"](handle))
    close(handle).one()
    assert refused(S["write-bytes!"](blob, (1, 300)))

    # The handle surface: size, seek, exact reads, and the three streams.
    handle = open_(notes, G("r")).one()
    assert size(handle) == [17]
    assert exact(handle, 5) == [G("alpha")]
    assert seek(handle, 6) == [True]
    assert exact(handle, 4) == [G("beta")]
    assert read_all(handle) == [G("\ngamma\n")]
    close(handle).one()
    handle = open_(notes, G("a")).one()
    assert m.fn["file-write!"](handle, G("delta\n")) == [True]
    close(handle).one()
    assert list(m.fn["file-lines!"](notes).one()) == [
        G("alpha"), G("beta"), G("gamma"), G("delta"),
    ]
    assert m.fn.stdin() == [0]
    assert m.fn.stdout() == [1]
    assert m.fn.stderr() == [2]
    assert m.fn["stderr!"](G("")) == [True]

    # replace-file! publishes by rename, so a reader holding the old file keeps
    # reading it while the path already names the new one.
    handle = open_(notes, G("r")).one()
    assert m.fn["replace-file!"](notes, G("fresh")) == [True]
    assert exact(handle, 5) == [G("alpha")]
    close(handle).one()
    assert read(notes) == [G("fresh")]
    assert m.fn["replace-file!"](blob, (104, 105)) == [True]
    assert read(blob) == [G("hi")]

    # copy-file! publishes the same way, byte for byte, replacing on success only.
    copied = under(G("blob-copy.bin"))
    assert m.fn["copy-file!"](blob, copied) == [True]
    assert list(read_bytes(copied).one()) == [104, 105]
    assert refused(S["copy-file!"](under(G("absent.bin")), copied))
    assert list(read_bytes(copied).one()) == [104, 105]

    # Directories, trees and links.
    tree = under(G("tree"))
    assert m.fn["make-dir!"](under(G("tree/deep/deeper"))) == [True]
    assert write(under(G("tree/deep/deeper/leaf.txt")), G("leaf")) == [True]
    assert write(under(G("tree/deep/note.md")), G("note")) == [True]
    assert write(under(G("tree/.hidden")), G("h")) == [True]
    assert link_at(G("deep"), under(G("tree/shortcut"))) == [True]
    assert link_at(G(".."), under(G("tree/deep/up"))) == [True]
    assert kind(under(G("tree/shortcut"))) == [S.link]
    assert link_of(under(G("tree/shortcut"))) == [G("deep")]
    assert m.fn["same-file"](under(G("tree/shortcut")), under(G("tree/deep"))) == [True]
    assert m.fn["same-file"](under(G("tree/deep")), under(G("tree/deep/note.md"))) == [False]
    assert list(listing(tree).one()) == [G(".hidden"), G("deep"), G("shortcut")]

    # A walk answers every descendant, depth first, names in codepoint order;
    # links are reported and not entered unless asked.
    assert list(walk(tree)) == [
        under(G("tree/.hidden")), under(G("tree/deep")), under(G("tree/deep/deeper")),
        under(G("tree/deep/deeper/leaf.txt")), under(G("tree/deep/note.md")),
        under(G("tree/deep/up")), under(G("tree/shortcut")),
    ]
    assert len(list(walk(tree, ((S.follow_links, True),)))) == 11

    # A glob selects by pattern: a literal component joins without listing,
    # * ? [] {} filter one directory, and ** matches zero or more levels.
    assert list(glob(tree, G("deep/*.md"))) == [under(G("tree/deep/note.md"))]
    assert list(glob(tree, G("**/*.txt"))) == [under(G("tree/deep/deeper/leaf.txt"))]
    assert list(glob(tree, G("*"))) == [under(G("tree/deep")), under(G("tree/shortcut"))]
    assert list(glob(tree, G("*"), ((S.hidden, True),))) == [
        under(G("tree/.hidden")), under(G("tree/deep")), under(G("tree/shortcut")),
    ]
    assert list(glob(tree, G("{deep,other}/note.m?"))) == [under(G("tree/deep/note.md"))]
    assert list(glob(tree, G("**/*.md"), ((S.follow_links, True),))) == [
        under(G("tree/deep/note.md")), under(G("tree/shortcut/note.md")),
    ]
    assert list(glob(tree, G("nowhere/*"))) == []
    assert refused(S.dir_glob(tree, G("[unclosed")))

    # copy-dir! builds the copy beside its destination and publishes it with one
    # rename; links are recreated with the text they hold.
    copy = under(G("copies/tree"))
    assert m.fn["copy-dir!"](tree, copy) == [True]
    assert read(join(copy, G("deep/deeper/leaf.txt")).one()) == [G("leaf")]
    assert link_of(join(copy, G("shortcut")).one()) == [G("deep")]
    assert refused(S["copy-dir!"](tree, copy))
    assert refused(S["copy-dir!"](tree, join(tree, G("inside")).one()))

    # rename-file! is the host's rename, and nothing is ever copied.
    note, renamed = join(copy, G("deep/note.md")).one(), join(copy, G("deep/renamed.md")).one()
    assert m.fn["rename-file!"](note, renamed) == [True]
    assert kind(note) == [S.missing]
    assert read(renamed) == [G("note")]
    assert refused(S["rename-file!"](join(copy, G("deep")).one(),
                                     join(copy, G("deep/deeper")).one()))

    # delete-tree! unlinks a link root and leaves its target alone, then
    # removes a whole tree.
    assert remove_tree(join(copy, G("shortcut")).one()) == [True]
    assert dir_exists(join(copy, G("deep")).one()) == [True]
    assert remove_tree(copy) == [True]
    assert dir_exists(copy) == [False]
    assert m.fn["delete-dir!"](under(G("copies"))) == [True]

    # Lexical paths never touch the filesystem; path-resolve does.
    assert join(G("reports"), G("sales.csv")) == [G("reports/sales.csv")]
    assert m.fn.path_parent(G("reports/sales.csv")) == [G("reports")]
    assert m.fn.path_name(G("reports/sales.csv")) == [G("sales.csv")]
    assert m.fn.path_extension(G("reports/sales.tar.gz")) == [G("gz")]
    assert m.fn.path_stem(G("reports/sales.tar.gz")) == [G("sales.tar")]
    assert list(m.fn.path_parts(G("/reports/2026/sales.csv")).one()) == [
        G("/"), G("reports"), G("2026"), G("sales.csv"),
    ]
    assert m.fn.path_normalize(G("reports/./2026/../sales.csv")) == [G("reports/sales.csv")]
    assert m.fn.path_normalize(G("/x/../../y")) == [G("/y")]
    assert m.fn.path_relative(G("/a/b/c"), G("/a/d")) == [G("../b/c")]
    assert m.fn.path_absolute(G("/x/./y")) == [G("/x/y")]
    assert m.fn.path_parent(m.fn.path_absolute(G("rel")).one()) == m.fn.path_absolute(G("."))
    assert m.fn.path_resolve(under(G("tree/shortcut/deeper/leaf.txt"))) == [
        under(G("tree/deep/deeper/leaf.txt")),
    ]
    assert m.fn.path_resolve(under(G("tree/deep/up/.hidden"))) == [under(G("tree/.hidden"))]

    # Metadata is a queryable snapshot; file-kind names what is missing.
    metadata = metta.space(m.fn["file-metadata!"](notes).one())
    assert [row.bytes for row in metadata[S.size(V.bytes)]] == [5]
    assert kind(under(G("nothing"))) == [S.missing]
    assert refused(S.read_link(notes))

    # A scope applies a function to the resource it acquired and releases it on
    # every exit, so every answer of a nondeterministic body streams while the
    # handle is still open. These three are the example's three lambdas, and a
    # compiled body reads a library head as the MeTTa call it is.
    @m.define
    def size_then_two(handle):
        # (|-> ($h) (superpose ((file-get-size! $h) (file-read-exact! $h 2))))
        yield S["file-get-size!"](handle)
        yield S["file-read-exact!"](handle, 2)

    # The name to write is a PARAMETER, so the compiled body carries no text of
    # its own and the scope receives the partial application.
    @m.define
    def fill_and_list(name, work):
        # (|-> ($work) (let $written (write-file! (path-join $work "scratch") "x")
        #                (list-dir! $work)))
        _written = S["write-file!"](S.path_join(work, name), name)
        return S["list-dir!"](work)

    @m.define
    def close_then_read(handle):
        # (|-> ($h) (let $closed (file-close! $h) (file-read-to-string! $h)))
        _closed = S["file-close!"](handle)
        return S["file-read-to-string!"](handle)

    assert m.fn["with-file"](notes, G("r"), S["file-read-to-string!"]) == [G("fresh")]
    assert m.fn["with-file"](notes, G("r"), S["|->"]((V.h,), S["file-get-size!"](V.h))) == [5]
    assert list(m.fn["with-file"](notes, G("r"), S.size_then_two)) == [5, G("fr")]
    assert list(m.fn["with-temp-dir"](G("file-lib-scope"),
                                      S.fill_and_list(G("scratch"))).one()) == [G("scratch")]
    assert refused(S.with_file(notes, G("r"), S.close_then_read))

    # temp-path! mints a fresh file the caller owns; a prefix names, never places.
    scratch = m.fn["temp-path!"](G("file-lib")).one()
    assert exists(scratch) == [True]
    assert m.fn["delete-file!"](scratch) == [True]
    assert refused(S["temp-path!"](G("logs/run")))

    # Everything the twin made goes with the one directory.
    assert remove_tree(directory) == [True]
    assert dir_exists(directory) == [False]


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move. The 90 claims cover 56 heads at 60 arities; the
#: example pays 245,536 inferences for the same work
#: [measured 2026-09-12: 209508 inferences, minimum of three serial fresh
#: processes and five single runs with zero spread (ai-tmp/ai-lib3-file-spread.log);
#: command=python extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch08-data/08-03-the-shipped-libraries/19-file_lib.metta;
#: fixture=the File library at its functional commit, artifacts purged before
#: the run; commit=e40ef941310bddd1f57074eb559e78aac8a263b0].
#: RE-PINNED 2026-09-12, 209508 to 209603 (+95), File transfers newly owned
#: streams through adopt_file_stream/2 and claims a close atomically; HTTP also
#: verifies transaction refusal before server lifecycle effects [measured
#: 2026-09-12: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f22b69cfca5c108e4126bdd56ab9bb2e493744d].
#: RE-PINNED 2026-09-13, 209603 to 209621 (+18), File exports its shared stream
#: borrowing and rollback operations; failed Socket and HTTP publication now
#: withdraws the registered stream before closing it [measured 2026-09-13: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=781ee98e188c23ea7ef9298636d6e5e6c7fdc727].
#: RE-PINNED 2026-09-13, 209621 to 209635 (+14), File privately exports its
#: existing staged publisher with callback qualification; Compression shares
#: that ownership and publication protocol [measured 2026-09-13: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
#: RE-PINNED 2026-09-13, 209635 to 210166 (+531), File exports its staged
#: publisher to Compression; the shared native builder accepts the private
#: archive provider recipe. All consumers are remeasured after those dependency
#: changes [measured 2026-09-13: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=7b42d5ee5cecb82709617b7ed08dfa2c1441f268].
BUDGET = 210166
