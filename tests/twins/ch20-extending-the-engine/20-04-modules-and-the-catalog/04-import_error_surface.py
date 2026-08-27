"""examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/04-import_error_surface.metta in Python: an import that fails.

A file that does not parse and a file that does not exist both surface the same
way: the import raises, `catch` turns the raise into an `(Error ...)` atom, and
the example reads that atom with `if-error`. The twin keeps `catch`, because
the error ALGEBRA is what the file is about, and reads the atom the way Python
reads any expression, by its head.

The paths stay relative and unresolvable, unlike the sibling import twins:
these two claims are that the import FAILS, and a path that resolves against
nothing fails exactly as the example's does. The space each import names is the
handle itself, which crosses into a built term as a grounded operand.
"""

from metta import S, lib

#: The engine library the example opens first. Its underscore is real, so it
#: takes the bracket door: `S.lib_he` would name `lib-he`, which is not a
#: library the tree ships.
LIB_HE = lib.he

#: The two ways an import can fail: a file that will not parse, and one that is
#: not there.
BROKEN = S["examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/imports/import_error_broken"]
MISSING = S["examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/imports/definitely_missing_import"]


def twin(m):
    """Import two files that cannot load, and read what came back."""
    # (import! &self (library lib_he)): the write door imports, and the
    # receiver is the target space.
    m += LIB_HE

    def caught(target):
        """The atom `catch` hands back when importing `target` raises."""
        answer, = m.eval(S.catch(S["import!"](m, target)))   # (catch (import! &self ...))
        return answer

    # (if-error (catch (import! ...)) Error NoError) is the head of the atom,
    # which Python reads off the expression it already holds.
    assert caught(BROKEN)[0] == S.Error
    assert caught(MISSING)[0] == S.Error


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 3562 to 3581, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 3581 to 3582, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 3582 to 3586, on the release tree:
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
#: RE-PINNED 2026-08-26, 3586 to 3580 (-6), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 3580
