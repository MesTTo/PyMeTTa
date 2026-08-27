"""examples/ch19-spaces-backed-by-anything/19-03-a-builtin-in-c/01-c_extension.metta in Python: C, called directly.

`cbump.so` holds one foreign predicate, `loader.pl` loads it, and MeTTa calls
it with nothing in between. From Python the loading step is
`m.register_prolog(path=, names=)`, which is what
`import_prolog_functions_from_file` names in MeTTa, and the call is
`m.fn.c_bump(41)`, rung 4's map applied at the function namespace.

The example splits its import and its call into two runnables because a
runnable is compiled just before it runs, so a call written beside its own
import compiles while the name is still unregistered. A Python program has no
runnables and no such ordering hazard: the registration is a statement and the
call is the next one.

The two libraries take the bracket door because their underscores are real:
`S.lib_import` would name `lib-import`, which the tree does not ship. The space
each import writes is the handle itself, a grounded operand in the built term.

The skip stays, because a C compiler is not one of the engine's requirements
and `check.sh` builds this artefact before any tier runs. What a twin cannot do
is SAY it skipped: a string constant reaches the engine only as an atom's name
or as `ground()` data, so the example's `println!` has no image here.
"""

from pathlib import Path

from metta import lib

#: The two engine libraries the example opens, spelled with their real
#: underscores.
LIB_IMPORT, LIB_FILE = lib["lib_import"], lib.file

#: The build artefact and the Prolog file that loads it, as host paths for a
#: Python door.
CBUMP_SO = Path("examples/ch19-spaces-backed-by-anything/19-03-a-builtin-in-c/cbump.so")
LOADER_PL = Path("examples/ch19-spaces-backed-by-anything/19-03-a-builtin-in-c/loader.pl")


def twin(m):
    """Load the C predicate, then call it."""
    # (import! &self (library lib_import)) and (library lib_file): the write
    # door imports, and the receiver is the target space.
    for library in (LIB_IMPORT, LIB_FILE):
        m += library

    if not CBUMP_SO.exists():
        # The example prints its skip here. A twin has no door for prose.
        return

    m.register_prolog(path=LOADER_PL, names=["c-bump"])
    assert m.fn.c_bump(41) == [42]   # (test (eval (c-bump 41)) 42)


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 69812 to 69869, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 69869 to 69878, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 69878 to 69886, on the release tree:
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
#: RE-PINNED 2026-08-26, 69886 to 69320 (-566), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 69320
