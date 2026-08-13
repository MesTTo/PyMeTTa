"""Purpose: verify the legacy helper scopes one silent setting to each call
and restores the previous setting on success and failure.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import uuid

import pytest
from petta import EngineError


def _silent_state(runtime):
    return runtime.must(
        "aggregate_all(count, silent(_), Count), once(silent(Value))"
    )


@pytest.mark.parametrize(
    ("verbose", "during"),
    [("false", "true"), ("true", "false")],
)
def test_helper_uses_one_silent_value_and_restores_previous(metta, verbose, during):
    runtime = metta.runtime
    name = f"round2_helper_{uuid.uuid4().hex}"
    runtime.must("petta_py_set_silent(false)")
    runtime.must(
        f"assertz(({name}(_Arg, _Results) :- "
        f"findall(_Value, silent(_Value), _Results)))"
    )
    try:
        row = runtime.must(
            f"run_metta_helper({verbose}, {name}, ignored, Out)"
        )
        assert row["Out"] == [during]
        state = _silent_state(runtime)
        assert state["Count"] == 1
        assert state["Value"] == "false"
    finally:
        runtime.must(f"retractall({name}(_, _))")


def test_helper_restores_silent_after_an_error(metta):
    runtime = metta.runtime
    name = f"round2_helper_error_{uuid.uuid4().hex}"
    runtime.must("petta_py_set_silent(false)")
    runtime.must(
        f"assertz(({name}(_, _) :- throw(error(round2_helper_failed, none))))"
    )
    try:
        with pytest.raises(EngineError, match="round2_helper_failed"):
            runtime.must(f"run_metta_helper(false, {name}, ignored, Out)")
        state = _silent_state(runtime)
        assert state["Count"] == 1
        assert state["Value"] == "false"
    finally:
        runtime.must(f"retractall({name}(_, _))")
