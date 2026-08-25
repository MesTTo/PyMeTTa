"""Purpose: examples/syntax/parse.metta in Python: reading text back into an atom.

`parse` is the reader, and its input is MeTTa source. The first five forms hand
it source written into the program (`"A"`, `"(R A B)"`, and three more), which
is exactly what a twin may not carry, so those five are declined and the
residue table records each against P14.1.

The last three are different, and they are the ones a Python program can state:
each starts from ordinary string DATA and lets the program itself print that
data before reading it back. `str(ground(text))` is the printing half, the same
`str` that answers `repr`'s text in syntax/repr.py, and the engine's own
`parse` reads it, so the claim is that printing and reading are inverse over a
string with backslashes, one with embedded quotes, and one whose backslash-n is
two characters rather than a newline.
"""

from metta import ground

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 327 to 384, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 384 to 385, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 385 to 391, on the release tree:
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
BUDGET = 391


def twin(m):
    """Print three awkward strings, and read each of them back."""
    read = m.fn.parse

    # A Windows path: every backslash is a backslash, doubled on the way out
    # and single again on the way back.
    # !(test (parse (repr "C:\\Users\\bob")) "C:\\Users\\bob")
    assert read(str(ground("C:\\Users\\bob"))) == ["C:\\Users\\bob"]

    # Quotes inside the string, escaped by the printer and unescaped by
    # the reader.
    # !(test (parse (repr "say \"hi\"")) "say \"hi\"")
    assert read(str(ground('say "hi"'))) == ['say "hi"']

    # Backslash-n as two characters, which survives because the printer
    # escapes the backslash rather than the n.
    # !(test (parse (repr "a\\nb")) "a\\nb")
    assert read(str(ground("a\\nb"))) == ["a\\nb"]
