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
BUDGET = 99426
