"""Purpose: reference_loading.metta in Python with the same admission policy.

The load pragma belongs to the receiver. A lazy call compiles its body and
a background call waits for the defining home.
[tested: examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/13-reference_loading.metta; commit=WORKTREE].
"""

from metta import MettaError, S

MAPS = S["../examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/references/maps"]
BACKGROUND = S["../examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/references/background"]
EFFECTFUL = S["../examples/ch20-extending-the-engine/20-04-modules-and-the-catalog/_fixtures/references/effectful"]


def twin(m):
    """Call deferred homes and refuse the initializer under both policies."""
    m.fn["pragma!"](S.load, S.lazy)
    m.from_(MAPS, S.prefix(S["lazy."]))
    assert m.fn["lazy.map-value"](41) == [42]
    assert m.fn["lazy.map-label"]() == [S.label]
    m.fn["pragma!"](S.load, S.background)
    m.from_(BACKGROUND)
    assert m.fn.background_value(41) == [42]
    for policy in (S.background, S.lazy):
        m.fn["pragma!"](S.load, policy)
        try:
            m.from_(EFFECTFUL)
        except MettaError as error:
            assert "println!" in str(error)
            assert "eager" in str(error)
        else:
            raise AssertionError("an effectful initializer was accepted")
    m.fn["pragma!"](S.load, S.eager)


#: Background loading joins a worker. Its counter includes work whose timing
#: depends on the complete lane, so this declaration records that protocol's
#: observed extrema. The ten samples were 332588, 329737, 332267, 330250,
#: 332432, 332041, 330564, 330886, 332217 and 330653, with no missing costs.
#: [measured 2026-09-10: 329737..332588 inferences over 10 observations;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/280/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 329737,
    "maximum": 332588,
    "observations": 10,
    "protocol": "full-lane/280/workers=32",
}
