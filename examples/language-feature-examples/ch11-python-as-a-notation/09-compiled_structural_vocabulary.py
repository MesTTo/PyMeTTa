"""Purpose: collect engine answers and bind structural values in compiled Python.

The source counterpart is examples/ch11-python-as-a-notation/09-compiled_structural_vocabulary.metta.
list of a known generator gathers answers into one engine expression. A host
iterable such as range still produces an ordinary Python list; py(list(...))
also requests host execution explicitly. type queries the engine metatype;
py(type(...)) requests the host class instead.

Tuple assignment is relational let*: a mismatching shape answers nothing.
Generator matches carry captures into later yields. Empty denotes a subject
that answered nothing, independently of ordinary pattern mismatch.
"""

from metta import Expression, S, superpose


def twin(m):
    """Run each compiled spelling against its structural engine answer."""
    @m.define
    def alternatives():
        yield 1
        yield 2
        yield 2

    @m.define
    def collected():
        return list(alternatives())

    @m.define
    def unpack(value):
        left, (middle, right) = value
        return right, middle, left

    @m.define
    def selected(value):
        match value:
            case (S.Box, item):
                yield item
            case _:
                yield S.Miss
        yield S.Done

    @m.define
    def absent():
        match superpose():
            case 1:
                return S.Unexpected
            case S.Empty:
                return S.Missing

    @m.define
    def metatype(value):
        return type(value)

    # !(test (collected) (1 2 2))
    assert collected() == [Expression([1, 2, 2])]
    # !(test (unpack (1 (2 3))) (3 2 1))
    assert unpack((1, (2, 3))) == [Expression([3, 2, 1])]
    # !(test (collapse (selected (Box 7))) (7 Done))
    assert selected(S.Box(7)) == [7, S.Done]
    # !(test (collapse (selected Other)) (Miss Done))
    assert selected(S.Other) == [S.Miss, S.Done]
    # !(test (absent) Missing)
    assert absent() == [S.Missing]
    # !(test (metatype tag) Symbol)
    assert metatype(S.tag) == [S.Symbol]


#: The final image includes the provisioned engine and MORK artifacts.
#: [measured: 12875, 12875, 12875 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch11-python-as-a-notation/09-compiled_structural_vocabulary.py').resolve()).cost)"; fixture=three independent fresh harness processes; commit=9958c72363d2fbc640d2ae39ee6f0670ecfbff67]
#: RE-PINNED 2026-09-06, 12875 to 13013 (+138), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 13013 to 13391 (+378), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
BUDGET = 13391
