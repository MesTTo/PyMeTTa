"""examples/ch11-python-as-a-notation/10-torch-library-surface.metta in Python: the rest of lib_torch's surface.

lib_torch is MeTTa equations over `py-call`, so its names are MeTTa functions
and the twin calls them through the function namespace rather than reaching
for `torch` directly: what is being checked is the LIBRARY, not the package
under it.

Whether torch is importable is asked the way the original asks it: one call
under `catch`, read with `if-error`. Python's own `find_spec` would be the
shorter question and the module NAME it takes is host text a twin may not
write, so the engine's guard is the one that stays.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib

TOLERANCE = 1e-6

#: The question the original asks, built rather than called: try one torch
#: call under `catch` and read the answer. `find_spec` would be the Python
#: way to ask, and the module NAME it takes is host text a twin may not
#: write, so the engine's own guard is the one that stays.
AVAILABLE = S.if_error(S.catch(S.py_call(S["torch.zeros"](1))), S.no, S.yes)


def twin(m):
    """Constructors, elementwise operations, a reduction, two activations."""
    m += lib.torch
    if m.answers(AVAILABLE) == [S.no]:
        # The example prints its skip here. A twin has no door for prose.
        return

    tensor, to_list, item = m.fn.torch_tensor, m.fn.torch_tolist, m.fn.torch_item
    zeros, ones = m.fn.torch_zeros, m.fn.torch_ones
    randn, arange = m.fn.torch_randn, m.fn.torch_arange

    # The four constructors. Each is one `py-call`, so what comes back is a
    # Python object held as a grounded atom and `torch-tolist` is the exit.
    assert to_list(zeros(3)[0]) == [(0.0, 0.0, 0.0)]
    assert to_list(ones(3)[0]) == [(1.0, 1.0, 1.0)]
    assert to_list(arange(4)[0]) == [(0, 1, 2, 3)]
    assert len(to_list(randn(5)[0])[0]) == 5

    # `torch-randn` draws from a normal distribution, so the one claim that
    # does not depend on the draw is that two of them differ.
    assert to_list(randn(8)[0]) != to_list(randn(8)[0])

    # The four elementwise operations.
    left, right = tensor((1.0, 2.0))[0], tensor((10.0, 20.0))[0]
    assert to_list(m.fn.torch_add(left, right)[0]) == [(11.0, 22.0)]
    assert to_list(m.fn.torch_sub(right, left)[0]) == [(9.0, 18.0)]
    assert to_list(m.fn.torch_mul(tensor((2.0, 3.0))[0], tensor((4.0, 5.0))[0])[0]) == [
        (8.0, 15.0)
    ]
    assert to_list(m.fn.torch_div(right, tensor((4.0, 5.0))[0])[0]) == [(2.5, 4.0)]

    # `torch-mean` is a reduction, so it answers a zero-dimensional tensor
    # and `torch-item` is what takes the number out of one.
    assert item(m.fn.torch_mean(tensor((1.0, 2.0, 3.0))[0])[0]) == [2.0]
    assert item(m.fn.torch_mean(ones(4)[0])[0]) == [1.0]

    # The two activations, on the values that pin their shape: relu is the
    # hinge at zero and sigmoid is a half at zero.
    assert to_list(m.fn.torch_relu(tensor((-2.0, 0.0, 3.0))[0])[0]) == [(0.0, 0.0, 3.0)]
    assert item(m.fn.torch_sigmoid(tensor(0.0)[0])[0]) == [0.5]

    # They compose the way any other function does, which is the point of the
    # library being MeTTa equations over `py-call`. The comparison is a
    # tolerance because torch's default tensor is float32 and MeTTa's number
    # is a double, so a third is not the same third on both sides.
    hinged = m.fn.torch_relu(
        m.fn.torch_sub(tensor((1.0, 2.0, 3.0))[0], tensor((2.0, 2.0, 2.0))[0])[0]
    )[0]
    assert abs(item(m.fn.torch_mean(hinged)[0])[0].value - 1 / 3) < TOLERANCE


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 38332 inferences, 0.8389x the example's 45695; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=WORKTREE].
BUDGET = 38332
