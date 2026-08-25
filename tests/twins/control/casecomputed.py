"""Purpose: examples/control/casecomputed.metta in Python: cases as a value.

The cases of a `case` are usually written out, and then they are syntax: the
form compiles one nested conditional out of them once. They do not have to be
written out. A cases argument that arrives as a VALUE is compiled when it
arrives, so the branches can be decided while the program runs, and that is
what lets `case` be given another name as an ordinary definition.

`case` over branches a program computes is the one shape Python has no word
for at all, and the reason survives the lowering that landed: Python's `match`
IS a `case` and compiles as one, but its arms are SYNTAX, so no Python
spelling takes them as an argument. Written-out cases are stated beside
handed-over ones here on purpose, so writing half of them as `match`
statements would compare a Python construct with a MeTTa value and break the
very pairing the file exists to show.

Two things do move into Python. `cons-atom` onto a tail is writing the
expression, so `numbered-cases` says the pair list it builds; and a refusal
crosses the seam as a Python exception, so `catch` is `except` and the branch
that reads what came back is Python's own.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, equation
from metta.errors import MettaOperationError

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `case` whose branches arrive as a VALUE has no Python spelling: match's arms are syntax"

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 14134 to 14267, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 14267 to 14271, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 14271 to 14285, on the release tree:
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
BUDGET = 14285


def twin(m):
    """Write cases out, hand them over, and refuse a list that is not one."""
    numbers = ((1, S.one), (2, S.two))
    with_default = ((1, S.one), (S.Empty, S.none))

    # The top rung is Python's `match` statement, whose arms are SYNTAX. It
    # compiles, and it still cannot take its branches as an argument, which is
    # this file's whole subject. Residue: P14.4.
    # (= (switch $value $cases) (case $value $cases))
    m += equation(S.switch(V.value, V.cases)).to(S.case(V.value, V.cases))

    # !(test (switch 2 ((1 one) (2 two))) two)
    assert m.eval(S.switch(2, numbers)) == [S.two]

    # Handed over or written out, the same cases answer the same thing.
    # !(test (case 2 ((1 one) (2 two))) two)
    assert m.eval(S.case(2, numbers)) == [S.two]

    # Cases the program builds are cases too.
    # (= (numbered-cases) (cons-atom (1 one) ((2 two))))
    m += equation(S.numbered_cases()).to(numbers)

    # !(test (switch 1 (numbered-cases)) one)
    assert m.eval(S.switch(1, S.numbered_cases())) == [S.one]
    # !(test (switch 2 (numbered-cases)) two)
    assert m.eval(S.switch(2, S.numbered_cases())) == [S.two]

    # `Empty` is the branch a key with NO ANSWERS takes, and it means that on
    # both paths. Here the key is `(empty)`, so the default answers.
    # (= (key-of-nothing $cases) (case (empty) $cases))
    m += equation(S.key_of_nothing(V.cases)).to(S.case(S.empty(), V.cases))

    # !(test (key-of-nothing ((1 one) (Empty none))) none)
    assert m.eval(S.key_of_nothing(with_default)) == [S.none]
    # !(test (case (empty) ((1 one) (Empty none))) none)
    assert m.eval(S.case(S.empty(), with_default)) == [S.none]

    # A key that answers but matches no branch is a different thing, and it
    # answers nothing whether an `Empty` branch is there or not.
    # !(test (collapse (switch 9 ((1 one) (Empty none)))) ())
    assert m.eval(S.switch(9, with_default)) == []
    # !(test (collapse (case 9 ((1 one) (Empty none)))) ())
    assert m.eval(S.case(9, with_default)) == []

    # One case pair handed over on its own is a pair too, and the definition
    # keeps the head it was written with.
    # (= (one-case $pair) (case 1 ($pair)))
    m += equation(S.one_case(V.pair)).to(S.case(1, (V.pair,)))

    # !(test (one-case (1 hit)) hit)
    assert m.eval(S.one_case((1, S.hit))) == [S.hit]

    # Cases are checked when they arrive, because nothing after that point can
    # check them.
    # !(test (car-atom (catch (switch 1 foo))) Error)
    try:
        m.eval(S.switch(1, S.foo))
        refused = None
    except MettaOperationError as error:
        refused = error
    assert refused is not None

    # Written out, `(case 1 foo)` is not a case with bad cases, it is a program
    # using the name as data, and it still reduces to itself.
    # !(test (case 1 foo) (case 1 foo))
    assert m.eval(S.case(1, S.foo)) == [S.case(1, S.foo)]
