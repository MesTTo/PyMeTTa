"""Purpose: declare two overloads for one compiled Python implementation.

Guarantees:
  - both correlated signatures are stored before their shared equation
    [tested: test_define_emits_each_overload_from_one_source; commit=WORKTREE]
"""

from typing import overload

from metta import S, arrow, fn, ground


def twin(m):
    """Use typing.overload as declarations and keep one executable body."""

    @overload
    def compiled_identity(value: int) -> int: ...

    @overload
    def compiled_identity(value: str) -> str: ...

    @m.define
    def compiled_identity(value):
        return value

    assert set(m.eval(fn.get_type(S.compiled_identity))) == {
        arrow(int, int), arrow(str, str)
    }
    assert compiled_identity(7) == [7]
    assert compiled_identity(ground("word")) == [ground("word")]


#: The final image includes the provisioned engine and MORK artifacts.
#: [measured: 4769, 4769, 4769 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch09-types/18-compiled_overloads.py').resolve()).cost)"; fixture=three independent fresh harness processes; commit=WORKTREE]
BUDGET = 4769
