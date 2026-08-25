"""Purpose: examples/control/cut.metta in Python: keeping the first answer only.

`(foo 1)` and `(foo 2)` both match, and `cut` throws the second away, so the
`let` above sees one answer and one `(bar 1)` is stored.

`match-single` takes its space, its pattern and its template as PARAMETERS and
is an ordinary compiled definition: `match(space, pattern, template)` is the
expression-position ask, which a compiled body lowers to the instruction, so
the space the call hands over is the one the equation reads. The two
assignments in the body are the `let*` pair the original writes flat. Outside
the body a write is `space += atom` and a read is the subscript door.

One thing about the answer view is worth knowing here: a call answers what
it evaluated to whether or not its arguments carry the caller's variables, in
a `stats()` scope and outside one, and the bindings those variables took are
the parallel row face on the same view [re-measured 2026-08-24:
`m.fn.unify(V.x, S.f(V.x), S.cyclic, S.sound)` answers `[sound]` either way and
its `.rows` answers `[Row(x=$_70)]`; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, match

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 4622 to 4641, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 4641 to 4647, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 4647 to 4616, on the release tree:
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
BUDGET = 4616


def twin(m):
    """Store one answer out of two, then read back what was stored."""
    # (foo 1)
    m += S.foo(1)
    # (foo 2)
    m += S.foo(2)

    @m.define
    def match_single(space, pat, ret):
        # (= (match-single $space $pat $ret)
        #    (let* (($x (match $space $pat $ret)) ($temp (cut))) $x))
        x = match(space, pat, ret)
        _temp = S.cut()
        return x

    # !(let $x (match-single &self (foo $1) $1) (add-atom &self (bar $x)))
    # Calling IS evaluation, and a `let` over a value that answers once is a
    # loop that runs once.
    for hit in match_single(m, S.foo(V.hit), V.hit):
        m += S.bar(hit)

    # !(test (collapse (match &self (bar $1) (bar $1))) ((bar 1)))
    assert [S.bar(row.hit) for row in m[S.bar(V.hit)]] == [S.bar(1)]
