"""examples/basics/reading_forms.metta in Python: still typing, or wrong?

This is the example where s-expression text is the SUBJECT rather than the
spelling. `parse-command` reads text and answers `(complete $term)`,
`incomplete`, or refuses; the text it reads is a datum, so it is written the
way the original writes it, marked `ground(...)` so that reading this file
says which strings are data and which would have been programs. The expected
terms are built at the `S.` door, because a twin may not reach the engine
through `parse` either.

The last claim is where Python's own vocabulary takes over. One bracket too
many cannot be repaired by more typing, so the reader refuses, and a refusal
crosses into Python as an EXCEPTION rather than as an atom: the original's
`(if-error (catch ...) Error NoError)` is a try/except here, and the `lib_he`
import that form needed goes with it. `EngineError` is a detailed error, so it
arrives from the errors satellite rather than from the narrow root.
"""

from metta import S, ground
from metta.errors import EngineError


def twin(m):
    """Read eleven fragments, and refuse the twelfth."""
    read = m.fn.parse_command

    assert read(ground("(f a)")) == [S.complete(S.f(S.a))]

    # Still typing. More text could finish any of these.
    assert read(ground("(f a")) == [S.incomplete]
    assert read(ground("(a (b (c")) == [S.incomplete]
    assert read(ground("(= (f $x)")) == [S.incomplete]

    # An empty line re-prompts rather than erroring, which is the commonest
    # input in any console.
    assert read(ground("")) == [S.incomplete]
    assert read(ground("   ")) == [S.incomplete]
    assert read(ground("; only a comment")) == [S.incomplete]

    # A bare atom is a whole form.
    assert read(ground("hello")) == [S.complete(S.hello)]

    # Not "just count parens": a bracket inside a string or a comment must
    # not count.
    assert read(ground('(f "a)b")')) == [S.complete(S.f(ground("a)b")))]
    assert read(ground("(f a) ; )))")) == [S.complete(S.f(S.a))]

    # An unterminated string IS incomplete, because a MeTTa string may span
    # lines.
    assert read(ground('(f "a')) == [S.incomplete]

    # One bracket too many is not incomplete: no amount of further typing
    # repairs it, so the reader refuses and Python sees an exception.
    refused = False
    try:
        read(ground("(f a))")).one()
    except EngineError:
        refused = True
    assert refused


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 3299 to 3508, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 3508 to 3510, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 3510 to 3534, on the release tree:
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
#: RE-PINNED 2026-08-26, 3534 to 3554 (+20), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 3554
