"""Purpose: prove the stack byte ceiling through the direct Janus host seam.

Guarantees:
  - ``petta_py_limited/6`` restores the calling thread's prior stack limit on
    success and on an exception [tested: test_janus_stack_scope_restores_on_all_exits;
    commit=81c50d3ae4c03ddfd70ed3f1ff70e085cfee3978]
"""


def test_janus_stack_scope_restores_on_all_exits(metta):
    """Restore the calling thread's exact stack ceiling on every exit."""
    runtime = metta.runtime
    success = runtime.once(
        "current_prolog_flag(stack_limit, Before), "
        "Scoped is Before + 1048576, "
        "petta_py_limited(-1, -1, Scoped, petta_py_run, "
        "['!(+ 1 2)', '&self'], Out), "
        "current_prolog_flag(stack_limit, After)"
    )
    assert success["Out"]
    assert success["After"] == success["Before"]

    failure = runtime.once(
        "current_prolog_flag(stack_limit, Before), "
        "Scoped is Before + 1048576, "
        "catch(petta_py_limited(-1, -1, Scoped, petta_py_run, "
        "['!(+ $left $right)', '&self'], _), _, true), "
        "current_prolog_flag(stack_limit, After)"
    )
    assert failure["After"] == failure["Before"]
