"""examples/libraries/text_lib.metta in Python: lib_string and lib_file.

Both libraries are the subject, so every function here is named through the
function namespace, where a typo raises on the line that writes it. What Python
takes over is the plumbing around them: the `let` chain that threads a file
handle through three calls is three statements, the file space is queried
through the handle's own subscript door, and every answer is compared as
ordinary Python data.

Two heads keep their MeTTa spelling with a stated reason rather than
dissolving. `format-args` is MeTTa HE's own formatter and this file is HE's
example of it, including what it does with too few arguments, which an f-string
cannot reproduce; `sort-strings` is the library function under test, not a
request to sort a Python list.

A trailing `!` has no Python image, so `write_file` and its siblings resolve to
`write-file!`: rung 4 of the descent ladder, applied at the function namespace.

The file this writes is named for the twin rather than for the example, so the
two can never meet on one path, and it is a `pathlib.Path` rather than text:
a path crosses the call door as the atom its codec makes of it.
"""

from pathlib import Path

import metta
from metta import G, S, V, lib

#: Written, appended to, read back four ways, then removed.
SCRATCH = Path("/tmp/petta-text-twin.txt")


def twin(m):
    """Walk lib_string's measuring, slicing, testing and padding, then lib_file."""
    m += lib.string
    m += lib.file

    # Measuring and slicing. string-slice is half-open, From included, To not.
    string_length = m.fn.string_length
    assert string_length(G("hello")) == [5]
    string_slice = m.fn.string_slice
    assert string_slice(G("hello world"), 0, 5) == [G("hello")]
    # An over-long end clamps instead of erroring, as slicing does everywhere.
    assert string_slice(G("hello"), 3, 999) == [G("lo")]
    assert string_slice(G("hello"), 99, 120) == [G("")]

    # Splitting and joining are inverses.
    [pieces] = m.fn.string_split(G(","), G("a,b,c"))
    assert list(pieces) == [G("a"), G("b"), G("c")]
    assert m.fn.string_join(G(", "), (G("a"), G("b"), G("c"))) == [G("a, b, c")]
    assert m.fn.string_trim(G("  padded  ")) == [G("padded")]
    string_upper = m.fn.string_upper
    assert string_upper(G("shout")) == [G("SHOUT")]
    assert m.fn.string_lower(G("QUIET")) == [G("quiet")]

    # The tests answer True or False, so they guard a query.
    assert m.fn.string_starts_with(G("hello"), G("he")) == [True]
    assert m.fn.string_ends_with(G("hello"), G("lo")) == [True]
    contains = m.fn.string_contains
    assert contains(G("hello"), G("ell")) == [True]
    assert contains(G("hello"), G("zzz")) == [False]

    # index-of answers -1 rather than failing: asking "where is it" deserves an
    # answer either way.
    index_of = m.fn.string_index_of
    assert index_of(G("hello"), G("l")) == [2]
    assert index_of(G("hello"), G("z")) == [-1]

    # replace changes every occurrence.
    assert m.fn.string_replace(G("banana"), G("a"), G("X")) == [G("bXnXnX")]

    # chars are one-character STRINGS, not char symbols, so the pieces are the
    # same kind of thing as the whole and feed straight back in.
    [chars] = m.fn.string_chars(G("abc"))
    assert list(chars) == [G("a"), G("b"), G("c")]
    assert m.fn.string_from_chars(chars) == [G("abc")]
    assert m.fn.string_repeat(G("ab"), 3) == [G("ababab")]
    assert m.fn.string_pad_left(G("7"), 3, G("0")) == [G("007")]
    assert m.fn.string_pad_right(G("7"), 3, G(".")) == [G("7..")]

    # rung: format-args is MeTTa HE's own formatter and this is HE's example of
    # it; an f-string cannot show what it does with too few arguments, which is
    # the second claim.
    format_args = m.fn.format_args
    assert format_args(G("Probability of {} is {}%"), (S.head, 50)) == [
        G("Probability of head is 50%")
    ]
    # A short argument list produces NOTHING for the placeholders it cannot
    # fill, which is the dyn_fmt formatter upstream interpolates through.
    assert format_args(G("{} and {}"), (S.only,)) == [G("only and ")]

    [sorted_strings] = m.fn.sort_strings((G("pear"), G("apple"), G("fig")))  # rung: sort-strings is the library function under test, not a request to sort a Python list
    assert list(sorted_strings) == [G("apple"), G("fig"), G("pear")]
    assert m.fn.parse_number(G("42")) == [42]
    assert m.fn.number_to_string(42) == [G("42")]

    # Text operations accept a Symbol or a Number where a String is wanted,
    # because a symbol arriving where a string was meant is ordinary in MeTTa.
    assert string_length(S.hello) == [5]
    assert string_upper(S.hello) == [G("HELLO")]

    # Files.
    assert m.fn.write_file(SCRATCH, G("one\ntwo\nthree\n")) == [True]
    assert m.fn.read_file(SCRATCH) == [G("one\ntwo\nthree\n")]
    # file-lines! drops the trailing empty line a final newline would produce.
    file_lines = m.fn.file_lines
    [lines] = file_lines(SCRATCH)
    assert list(lines) == [G("one"), G("two"), G("three")]
    assert m.fn.append_file(SCRATCH, G("four\n")) == [True]
    [lines] = file_lines(SCRATCH)
    assert list(lines) == [G("one"), G("two"), G("three"), G("four")]

    # The handle surface is MeTTa HE's exactly: r read, w write, c create,
    # a append, t truncate. The example's `let` chain is three statements.
    handle = m.fn.file_open(SCRATCH, G("r")).one()
    head = m.fn.file_read_exact(handle, 3).one()
    m.fn.file_close(handle).one()
    assert head == G("one")

    # file-space! is the mettafied reading of reading a file: its lines become
    # (line Number Text) atoms in a space, so the file is QUERYABLE rather than
    # one long string you then have to take apart. The line number is kept
    # because a space is unordered.
    log = metta.space(m.fn.file_space(SCRATCH).one())
    assert [(row.n, row.t) for row in log[S.line(V.n, V.t)]] == [
        (1, G("one")), (2, G("two")), (3, G("three")), (4, G("four")),
    ]
    # Asking for one line is a match, not a scan.
    assert [row.t for row in log[S.line(2, V.t)]] == [G("two")]

    assert m.fn.delete_file(SCRATCH) == [True]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 75180 to 75940, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 75940 to 75949, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 75949 to 76031, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 76031 to 75571 (-460), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 75571
