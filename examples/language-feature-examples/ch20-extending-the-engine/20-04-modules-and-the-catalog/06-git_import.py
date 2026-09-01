"""examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/06-git_import.metta in Python: a repository as a library.

Four acts, then one question. A fixture Prolog file answers a clone URL,
`git-import!` clones that repository into `./repos`, the clone is imported as
an ordinary named library, and the function it ships answers.

The Prolog step is Python's own door: `m.register_prolog(path=, names=)` is
what `import_prolog_functions_from_file` names in MeTTa, and it takes the file
and the predicates to export in the same order. The two imports take the
write door with the receiver as the target space, and the clone's entry
point is the dotted part, `FIXTURE_LIB.fixture`, the two-argument
`(library alias inner)` form. `git-import!` stays the engine's own
function: cloning is packaging, and packaging's Python spelling is pip.

Two library names take lib's bracket door: `lib_import` strips to the
keyword `import`, which Python cannot say after a dot, and
`metta_fixture_lib` sits outside the `lib_` family the attribute map
prefixes. `git_fixture_url` keeps fn's bracket for the same reason it
always did: its underscores are real and the function map writes hyphens.
"""

from pathlib import Path

from metta import S, lib

#: The directory `git-import!` clones into, and the fixture's own Prolog file.
#: Both are paths, so both are `pathlib.Path`: a path is never text, at the
#: call door or at the Python one.
REPOS = Path("./repos")
FIXTURE_PL = Path("examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/git_fixture.pl")

#: The library shipped with the engine, the Prolog predicate the fixture
#: exports, and the library the clone provides. Every one carries a genuine
#: underscore, so every one takes rung 5.
LIB_IMPORT = lib["lib_import"]
FIXTURE_URL = S["git_fixture_url"]
FIXTURE_LIB = lib["metta_fixture_lib"]


def twin(m):
    """Build a repository, clone it, import it, ask it a question."""
    # (import! &self (library lib_import)): the write door imports, and the
    # receiver is the target space.
    m += LIB_IMPORT

    # The URL comes from Prolog, which register_prolog installs as a MeTTa
    # function of one argument: the base directory in, the clone URL out.
    m.register_prolog(path=FIXTURE_PL, names=["git_fixture_url"])
    m.fn["git-import!"](FIXTURE_URL(REPOS))     # (git-import! (git_fixture_url "./repos"))

    # The clone is now an ordinary named library, and the dotted part is the
    # two-argument (library metta_fixture_lib fixture) form.
    m += FIXTURE_LIB.fixture

    assert m.fn.fixture_answer(14) == [42]   # [42]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 34545 to 34621, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 34621 to 34632, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 34632 to 34640, on the release tree:
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
#: RE-PINNED 2026-08-26, 34640 to 34108 (-532), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 34108 to 34342 (+234), one corpus pricing pass on the
#: merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 34342 to 34334 (-8), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 34334
