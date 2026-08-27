"""examples/integration/python_import.metta in Python: importing a .py file.

`import!` on a Python file makes that module's functions reachable by their
dotted names, and the two claims call one of each kind: one answering text and
one answering a number.

The example asserts the text answer through `repr` because a MeTTa program
cannot look at a symbol any other way. Here the answer is an atom, so the claim
names it: a Python string comes back from `py-call` as a SYMBOL, which is
upstream's conversion and is exactly what the claim now says.

The file is named by its path ATOM, spelled through the same S[...] bracket
every unspeakable name takes, and the lib door carries the exact form:
the engine resolves it by its own rules, never against the host's working
directory. Resolving it against the importing FILE is what a MeTTa program
gets for free and a Python-authored one does not, so the path is written
from the repository root.
"""

from metta import S, ground, lib

#: The file the import reads, named by the atom the example itself writes.
FIXTURE = S["examples/integration/_fixtures/python_import_file.py"]


def twin(m):
    """Import a Python file, then call two of its functions."""
    # (import! &self examples/integration/_fixtures/python_import_file.py):
    # the write door imports, and the lib door carries the path atom.
    m += lib(FIXTURE)

    py = m.fn.py_call
    greeting = py(S["python_import_file.greet"](ground("MeTTa User")))
    assert greeting == [S["Hello, MeTTa User from Python!"]]
    assert py(S["python_import_file.add"](10, 20)) == [30]   # [30]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 1847 to 1908, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 1908 to 1909, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 1909 to 1921, on the release tree:
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
#: RE-PINNED 2026-08-26, 1921 to 1942 (+21), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 1942
