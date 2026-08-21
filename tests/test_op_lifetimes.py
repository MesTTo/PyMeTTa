"""Purpose: what a Python-backed operation OWNS, and when it lets go of it.
A nondeterministic operation answers through a generator, and a generator is
a one-shot stream that can hold a file, a database cursor or a lock open
between yields. This file pins who closes it and what happens when closing
fails.
Guarantees:
  - unannotated generator operations need no typed declaration switch
    [tested: test_a_nondeterministic_ops_generator_releases_what_it_holds;
    commit=6fbd5872cc0ff7abf9c99b90f915f8a31470a861]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import gc
import uuid

import pytest

from petta import S, Sym
from petta._ops import dispatch_many


def unique(prefix: str) -> str:  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_a_nondeterministic_ops_generator_releases_what_it_holds(metta, tmp_path):
    """Two halves: the release happens, and a release that FAILS is heard.

    The first half runs with the cycle collector off. PEP 533 records that
    on an implementation which does not reference-count, "calls to __del__
    may be arbitrarily delayed" [source: https://peps.python.org/pep-0533/],
    so a resource contract that holds only because CPython refcounts is not
    a contract.

    The second half is the one that was silent. `dispatch_many` is the entry
    point shim.pl drives through py_iter, and abandoning a stream means
    closing it. When nothing closes it and the deallocator does, CPython
    swallows whatever the release raised and prints "Exception ignored while
    closing generator" [measured 2026-08-19: an OSError raised while
    releasing reached stderr and no caller, at every abandonment shape].
    Closing what this module opened puts that failure back in front of
    whoever abandoned the stream.
    """
    source = tmp_path / "rows.txt"
    source.write_text("a\nb\nc\n", encoding="utf-8")
    released = []
    reading = unique("rows")

    @metta.register_op(name=reading)
    def rows():
        handle = source.open(encoding="utf-8")
        try:
            for line in handle:
                yield Sym(line.strip())
        finally:
            handle.close()
            released.append(handle)

    gc.disable()
    try:
        assert metta.run(f"!(once ({reading}))") == [[S.a]]
    finally:
        gc.enable()
    assert released, f"{reading} was abandoned after one answer and never released"
    assert released[0].closed

    failing = unique("leaky")

    @metta.register_op(name=failing)
    def leaky():
        try:
            yield from range(10**6)
        finally:
            msg = "releasing the cursor failed"
            raise OSError(msg)

    stream = dispatch_many(failing, [])
    assert next(stream) == ["n", 0]
    with pytest.raises(OSError, match="releasing the cursor failed"):
        stream.close()
