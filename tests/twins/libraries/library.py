"""examples/libraries/library.metta in Python: lib_roman's flat map.

One claim, and both halves of it are MeTTa's own: `map-flat` is the library
function under test and `(+ 1)` is a partial application, which Python spells
with `functools.partial` over host callables and not over an engine function.
So the twin names both and states the answer as an ordinary comparison.

The partial takes the operator's WORD, `S.add(1)`: a fixed table maps every
operator symbol to `operator`'s own name for it, so `S.add` IS `+` and the
bracket stays the exact door for a head literally named `add`.

The import hands its target over as the HANDLE it is. `import!` takes that
space as an ARGUMENT, and a space crosses a term position as a grounded
operand, so no space is named as a symbol here. The library's own name keeps
the bracket: `lib_roman` really has an underscore, and the attribute door maps
every underscore to a hyphen.
"""

from metta import Expression, S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1


def twin(m):
    """Import lib_roman, then map (+ 1) over three numbers."""
    m.fn["import!"](m, S.library(S["lib_roman"]))

    # (map-flat (+ 1) (1 2 3))
    assert m.fn.map_flat(S.add(1), (1, 2, 3)) == [Expression((2, 3, 4))]
