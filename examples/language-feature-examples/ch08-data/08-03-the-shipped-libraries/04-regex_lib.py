"""Purpose: examples/ch08-data/08-03-the-shipped-libraries/04-regex_lib.metta in Python: PCRE2 through lib_regex.

Every claim is about one of the library's six functions, so the twin names all
six through the function namespace. Two things are Python's: the patterns,
written as raw strings so a backslash is a backslash without the doubling
MeTTa's string reader needs, and the answer shapes, which are lists and plain
values.

`re-find` answers one match per solution, so the whole answer view is the list
of matches; `re-captures` answers whole-match, named and typed groups in one
expression, which stays an expression because that is what the library returns.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, G, S, lib


def twin(m):
    """Match, find, capture, split and replace, all through lib_regex."""
    m += lib.regex

    # A boolean guard: (?i) is PCRE2's inline case-insensitivity flag.
    re_match = m.fn.re_match
    assert re_match(G("(?i)^needle"), G("Needle in a haystack")) == [True]
    assert re_match(G("^x"), G("abc")) == [False]

    # Enumeration: one answer per match, which is nondeterminism, not a list.
    found = m.fn.re_find(G(r"\d+"), G("a1 b22 c333"))
    assert found == [G("1"), G("22"), G("333")]

    # A capture name ending in _I asks for the group as a Number, so `month`
    # and `year` arrive as 4 and 2017 rather than as "04" and "2017".
    [captures] = m.fn.re_captures(
        G(r"(?<year_I>\d\d\d\d)-(?<month_I>\d\d)"), G("2017-04-20")
    )
    assert list(captures) == [Expression((0, G("2017-04"))), S.month(4), S.year(2017)]

    # Split keeps the separator it matched, so the pieces and the gaps alternate.
    [pieces] = m.fn.re_split(G(r":\s*"), G("Age: 33"))
    assert list(pieces) == [G("Age"), G(": "), G("33")]

    assert m.fn.re_replace_all(G("a+"), G("X"), G("banana")) == [G("bXnXnX")]
    assert m.fn.re_replace(G(r"(?<y>\d+)"), G("[$y]"), G("n 42 n")) == [G("n [42] n")]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 42651 to 42803, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 42803 to 42812, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 42812 to 42828, on the release tree:
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
#: RE-PINNED 2026-08-26, 42828 to 42274 (-554), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 42274
