"""Purpose: declare two overloads for one compiled Python implementation.

Guarantees:
  - both correlated signatures are stored before their shared equation
    [tested: test_define_emits_each_overload_from_one_source; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
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
#: [measured: 4769, 4769, 4769 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch09-types/18-compiled_overloads.py').resolve()).cost)"; fixture=three independent fresh harness processes; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
#: RE-PINNED 2026-09-06, 4769 to 4800 (+31), the one pricing pass at the 0.8.0
#: release cut, and trunk's own movement rather than any mechanism in this
#: twin: each pin was taken on the base its own branch had, and the September
#: merge wave has moved the engine's clause layout, the evaluation path and the
#: library's write doors since [measured 2026-09-06: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 4800 to 4905 (+105), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 4905
