"""examples/ch11-python-as-a-notation/02-python_booleans.metta in Python: booleans crossing.

MeTTa's `true` and `false` become Python's `True` and `False` on the way in, in
argument position and inside lists, and Python's booleans come back as MeTTa's.
Every claim runs through `m.fn.py_call`, the host-call door read as an ordinary
Python callable through rung 4's map, because the CROSSING is this example's
subject: calling `str` or `sorted` from Python directly would test nothing.

The example asserts its string answers through `repr` because a MeTTa program
has no other way to look at a symbol. Here the answer is an atom in hand, so
each claim names the atom: `py(...) == S["True"]` says both that the text is
"True" and that it came back as a SYMBOL rather than a String, which is the
conversion the file is about.
"""

from metta import FALSE, TRUE, Expression, S


def twin(m):
    """Ten crossings of the boolean, and what each one answers."""
    py = m.fn.py_call

    # str() sees a Python bool, and its text returns as a symbol.
    assert py(S.str(TRUE)) == [S["True"]]   # (repr (py-call (str true))) is "True"
    assert py(S.str(FALSE)) == [S["False"]]

    # A list argument converts its booleans in, and a list answer converts them
    # back out, elementwise.
    assert py(S.sorted((TRUE, FALSE))) == [Expression((FALSE, TRUE))]
    assert py(S.len((TRUE, FALSE, TRUE))) == [3]

    # Python sees bool all the way down, so isinstance and bool() agree.
    assert py(S.isinstance(TRUE, S.py_call(S.type(FALSE)))).one() is True
    assert py(S.bool(1)).one() is True
    assert py(S.bool(0)).one() is False

    # A boolean RECEIVER dispatches on bool, not on the text "true".
    assert py(S[".bit_length"](TRUE)) == [1]

    # Only the boolean atoms convert; every other symbol stays text.
    assert py(S[".upper"](S.abc)) == [S.ABC]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 6417 to 6588, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 6588 to 6589, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 6589 to 6637, on the release tree:
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
#: RE-PINNED 2026-08-25, 6637 to 6639, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 6639 to 6702 (+63), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 6702
