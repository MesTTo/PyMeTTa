"""Purpose: one operation set for every DLPack library: NumPy flows through
the same MeTTa functions torch does, a mixed call converts through DLPack,
and DLTensor is a protocol type the engine really checks.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done, skip

try:
    import array_api_compat  # noqa: F401
    import numpy
except ImportError:
    skip("numpy and array-api-compat are needed")

from metta import MeTTa, S, V, arrays, Expression, ground, wire

m = MeTTa().space()
arrays.install(m, default=numpy)

check("matmul over numpy",
      m.run("!(t-tolist (matmul (tensor ((1.0 2.0))) (tensor ((3.0) (4.0)))))"),
      [[Expression(Expression(11.0))]])
# The tensor is built first and the type read off the VALUE. get-type does
# not evaluate its argument, so asking about the unreduced call `(tensor
# (1.0))` reports what the expression is declared to be, not what building it
# would produce; both arbiters answer %Undefined% there.
(types,) = m.run("!(collapse (let $t (tensor (1.0)) (get-type $t)))")
check("protocol typing", S.DLTensor in list(types[0]))

array = numpy.arange(4.0)
m.add(S.holds(ground(array)))
check("identity through the space", wire.decode(m.match(S.holds(V.a))[0].a) is array)

try:
    import torch
    left, right = numpy.ones((2, 2), dtype=numpy.float32), torch.ones(2, 2)
    m.add(S.pair(ground(left), ground(right)))
    (out,) = m.run("!(t-item (t-sum (match (context-space) (pair $a $b) (matmul $a $b))))")
    check("mixed numpy@torch via DLPack", float(out[0]), 8.0)
except ImportError:
    print("  (torch absent: mixed-library half skipped)")
done("array_interop")
