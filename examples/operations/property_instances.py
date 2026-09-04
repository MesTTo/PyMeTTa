"""Purpose: generate ground property-test instances from a symbolic pattern.

Named variables share one generated value, while each anonymous occurrence is
an independent hole. The strategy therefore preserves the engine's binding
law instead of flattening a pattern into unrelated leaves.
"""

from _common import check, done
from hypothesis import find

from metta import S, V, Variable, testing

shared = find(
    testing.from_pattern(S.edge(V.node, V.node), max_leaves=2),
    lambda _atom: True,
)
check("generated instances are ground", shared.vars, ())
check("repeated named variables share a draw", shared[1], shared[2])

anonymous = find(
    testing.from_pattern(S.pair(Variable("_"), Variable("_")), max_leaves=2),
    lambda atom: atom[1] != atom[2],
)
check("anonymous occurrences draw independently", anonymous[1] != anonymous[2])

done("property_instances")
