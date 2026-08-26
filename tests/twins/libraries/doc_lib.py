"""examples/libraries/doc_lib.metta in Python: documentation is atoms in a space.

MeTTa HE's design, and the mettafied one: a `(@doc ...)` form is an ordinary
atom, so retrieval is a match and a program can reason about its own
documentation. Both halves of that land in Python without a new mechanism. A
`@m.define` docstring EMITS the `@doc` atom, so the example's two hand-written
forms are simply the docstrings of the two functions they document, and a
Google-style docstring emits all four parts.

The scoped formal `get-doc` is the receiver verb `m.doc(subject)`. This
example instead imports lib_doc and tests that library's unary raw-document
function: it returns the exact `(@doc ...)` atom and gives no answer for an
undocumented subject. The rung comments keep that semantic distinction
visible. `undocumented` remains lib_doc's own function and stays named.

Neither function is ANNOTATED, and that is the example's own program rather
than an omission: `(= (greet $who) $who)` declares no type, so each parameter's
`@type` comes back as `%Undefined%`, the marked name of the unconstrained type,
which is exactly what an undeclared parameter has. Annotating would emit
`(: greet (-> String String))` beside the doc and make `(greet 5)` a BadType
error the example never asked for.

The summaries end with a full stop where the example's prose does not, because
the `@desc` atom IS the docstring, verbatim, and a docstring that carries no
terminal punctuation is a pydocstyle finding. One character of prose is the
twin's own datum, the way its scratch file names are; what the claims are about
is the round trip.
"""

from metta import G, S, lib

#: What an undeclared parameter's type comes back as. `%Undefined%` is a marked
#: name rather than an identifier, so it takes rung 5's exact door.
UNDECLARED = S["@type"](S["%Undefined%"])

#: The two summaries, written once here and once as the docstring they are. A
#: drift between the two copies is the defect these claims exist to catch.
GREET_SUMMARY = G("Greets somebody by name.")
ADD_TWO_SUMMARY = G("Adds two numbers.")


def twin(m):
    """Document two functions from Python, then ask the space what it knows."""
    m += lib.doc

    @m.define
    def greet(who):
        """Greets somebody by name."""
        return who

    @m.define
    def add_two(a, b):
        """Adds two numbers.

        Args:
            a: the first
            b: the second

        Returns:
            their sum
        """
        return a + b

    # Retrieval answers the atom the docstring became.
    assert m.fn.get_doc(  # rung: lib_doc's unary raw-document query, not scoped m.doc
        S.greet
    ) == [
        S["@doc"](
            S.greet,
            S["@kind"](S.function),
            S["@desc"](GREET_SUMMARY),
            S["@params"]((S["@param"](UNDECLARED, S["@desc"](G(""))),)),
        )
    ]

    # @doc carries the kind, the summary and the parameters always, and the
    # return as well when the docstring says what comes back.
    assert m.fn.get_doc(  # rung: lib_doc's unary raw-document query, not scoped m.doc
        S.add_two
    ) == [
        S["@doc"](
            S.add_two,
            S["@kind"](S.function),
            S["@desc"](ADD_TWO_SUMMARY),
            S["@params"]((
                S["@param"](UNDECLARED, S["@desc"](G("the first"))),
                S["@param"](UNDECLARED, S["@desc"](G("the second"))),
            )),
            S["@return"](UNDECLARED, S["@desc"](G("their sum"))),
        )
    ]

    # An undocumented name answers nothing at all rather than an empty doc.
    assert list(m.fn.get_doc(  # rung: unary raw get-doc has an empty missing result
        S.greet_nobody
    )) == []
    assert list(m.fn.get_doc(  # rung: unary raw get-doc has an empty missing result
        S.missing
    )) == []

    # And a program can ask what it has NOT documented, which is the gap worth
    # closing in a real codebase. Both functions above are documented.
    assert list(m.fn.undocumented()) == []

    assert greet(G("ann")) == [G("ann")]
    assert add_two(2, 3) == [5]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 7938 to 9051, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 9051 to 9080, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 9080 to 9018, on the release tree:
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
#: RE-PINNED 2026-08-25, 9018 to 9008, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 9008 to 9663 (+655), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 9663 to 9699 (+36), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
BUDGET = 9699
