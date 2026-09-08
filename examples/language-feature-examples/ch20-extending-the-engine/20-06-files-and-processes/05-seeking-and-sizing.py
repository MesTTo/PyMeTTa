"""examples/ch20-extending-the-engine/20-06-files-and-processes/05-seeking-and-sizing.metta in Python: moving the cursor, and measuring the file.

`file-get-size!` answers the size of the FILE rather than of what is left, so
it does not move or consult the cursor; `file-seek!` moves the cursor, which
makes a handle a random-access read rather than a stream.

Each claim opens its own handle and removes its own file, so nothing here
outlives the run.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, lib

TEXT = G("hello world")


def twin(m):
    """Size against the cursor, rewinding, seeking, and exact reads."""
    m += lib.file
    make = m.fn["temp-path!"]
    write, read = m.fn["write-file!"], m.fn["file-read-to-string!"]
    exact = m.fn["file-read-exact!"]
    open_, close = m.fn["file-open!"], m.fn["file-close!"]
    size, seek = m.fn["file-get-size!"], m.fn["file-seek!"]
    remove = m.fn["delete-file!"]

    def opened():
        """A fresh file holding the same eleven characters, and its handle."""
        path = make(G("seek"))[0]
        write(path, TEXT).one()
        return path, open_(path, G("r"))[0]

    # The size does not move or consult the cursor: asking twice, once at the
    # start and once after everything has been read, answers the same number.
    path, handle = opened()
    before = size(handle)
    assert read(handle) == [TEXT]
    assert size(handle) == before == [11]
    close(handle).one()
    remove(path).one()

    # Reading to the end, seeking back, and reading again is how a file is
    # read twice without being opened twice.
    path, handle = opened()
    assert read(handle) == [TEXT]
    assert seek(handle, 0) == [True]
    assert read(handle) == [TEXT]
    close(handle).one()
    remove(path).one()

    # Seeking to an offset in the middle answers the tail from there.
    path, handle = opened()
    seek(handle, 6).one()
    assert read(handle) == [G("world")]
    close(handle).one()
    remove(path).one()

    # After seeking to the end there is nothing left to read, and the SIZE is
    # unchanged.
    path, handle = opened()
    seek(handle, size(handle)[0]).one()
    assert read(handle) == [G("")]
    assert size(handle) == [11]
    close(handle).one()
    remove(path).one()

    # `file-read-exact!` takes at most n characters from the cursor, so seek
    # and exact read together walk a file in fixed-size pieces.
    path, handle = opened()
    assert exact(handle, 5) == [G("hello")]
    seek(handle, 6).one()
    assert exact(handle, 5) == [G("world")]
    close(handle).one()
    remove(path).one()


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 99426 inferences, 0.9749x the example's 101985; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 99426 to 99419 (-7), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 99419 to 99304 (-115), the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-PINNED 2026-09-08, 99304 to 105992 (+6688), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 105992 to 106567 (+575), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-09, 106567 to 107265 (+698), structured concurrency landed
#: (feat/structured-concurrency merged at f80cc416d): every space mint records
#: its allocation in the library's lifetime rows, every write and run pays the
#: ownership hook and every drop asks the library whether a scope owns the
#: name, measured on a pristine control as 32 per mint, 2 per write and 44 per
#: drop with none per read; measured on the merged tree [measured 2026-09-09:
#: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 107265
