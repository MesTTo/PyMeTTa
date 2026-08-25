"""examples/integration/c_extension/handle.metta in Python: an opaque native handle.

A thousand-element C vector reaches MeTTa as ONE value whose contents never
cross: reading an element is a call into C, not a walk over text. The four
predicates arrive through `m.register_prolog(path=, names=)`, and every
question about the vector is an ordinary Python call whose argument is the term
that builds the vector, so the handle never leaves the engine.

`bump-thrice` compiles. Its body names three C-backed functions at the static
function namespace, where rung 4's map turns each underscore back into the
hyphen the loader registered, and the original's `let` plus `progn` is the
Python it means: bind the vector, act on it twice, answer the third act. Three
separate calls landing on the same memory is what the claim measures, and
three separate statements is how Python says it.

Two claims dissolve. `get-metatype` is the atom's own `metatype`, a property of
the atom Python already holds, and the example's `let` around it exists only
because `get-metatype` does not reduce its argument, which a Python name does
not need to be told. The identity claim stays a call into the engine, because
MeTTa's `==` on a grounded value is what the example is asking about and Python
comparing a name with itself would be asking something else; `fn.eq` is that
operator's word at the attribute door.
"""

from pathlib import Path

from metta import Grounded, S, fn, lib

#: The two engine libraries the example opens, spelled with their real
#: underscores.
LIB_IMPORT, LIB_FILE = lib["lib_import"], lib.file

#: The build artefact and the Prolog file that loads it, as host paths for a
#: Python door.
HANDLE_SO = Path("examples/integration/c_extension/handle.so")
HANDLE_LOADER_PL = Path("examples/integration/c_extension/handle_loader.pl")

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=e70eaeba6b6c0afc9081239041b8459eb8bb1b92].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 76421 to 76554, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 76554 to 76570, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 76570 to 76549, on the release tree:
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
#: RE-PINNED 2026-08-25, 76549 to 76556, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
BUDGET = 76556


def twin(m):
    """Make native vectors, read them, bump them, and ask what one is."""
    # (import! &self (library lib_import)) and (library lib_file): the write
    # door imports, and the receiver is the target space.
    for library in (LIB_IMPORT, LIB_FILE):
        m += library

    if not HANDLE_SO.exists():
        # The example prints its skip here. A twin has no door for prose, and
        # a body cannot compile a call to a function nothing registered, so
        # `bump-thrice` is below this line rather than above it.
        return

    m.register_prolog(
        path=HANDLE_LOADER_PL,
        names=["vector-new", "vector-nth", "vector-bump", "vector-length"],
    )

    # A thousand elements, one value: length and element access are C calls.
    assert m.fn.vector_length(S.vector_new(1000)) == [1000]
    assert m.fn.vector_nth(S.vector_new(1000), 700) == [700]

    @m.define
    def bump_thrice():                     # (= (bump-thrice)
        vector = fn.vector_new(4)          #    (let $v (vector-new 4)
        _first = fn.vector_bump(vector, 0)  #        (progn (vector-bump $v 0)
        _second = fn.vector_bump(vector, 0)  #               (vector-bump $v 0)
        return fn.vector_bump(vector, 0)   #               (vector-bump $v 0))))

    # The state behind the handle is the native one, so three bumps through
    # three separate calls land on the same memory.
    assert bump_thrice() == [3]

    # It is an ordinary grounded value, and it compares by identity. The
    # design's rule holds in the class tree now: a Handle IS a Grounded
    # species (the canonical glossary's own law), so isinstance is the whole
    # claim. `metatype` answering the string rather than the symbol is a
    # separate surface decision, recorded with its consumer list in the
    # known-issues ledger rather than flipped blind.
    vector = m.answers(S.vector_new(1)).one()
    assert isinstance(vector, Grounded)
    assert vector.metatype == S.Grounded.name
    assert m.fn.eq(vector, vector).one() is True   # (eval (let $v (vector-new 1) (== $v $v)))
