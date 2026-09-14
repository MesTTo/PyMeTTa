"""Purpose: compare compiled receiver entries with equivalent native equations.

Guarantees:
  - canonical and inherited method bodies cost their handwritten equivalents;
    the public dispatch entry adds one inference per call [tested:
    test_method_entry_inferences_match_the_equivalent_native_body; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
"""

from dataclasses import dataclass

import pytest

from metta import MeTTa, S, Space
from metta._declare.classes import declaration


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
def test_method_entry_inferences_match_the_equivalent_native_body(grain):
    """Warm direct entries remove host overhead from the comparison."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @m.define
        @dataclass(frozen=grain == "value")
        class MeasuredMethodBase(base):
            x: int
            y: int

            def norm(self) -> int:
                return self.x * self.x + self.y * self.y

            def report(self) -> int:
                return self.norm()

        @m.define
        @dataclass(frozen=grain == "value")
        class MeasuredMethodChild(MeasuredMethodBase):
            z: int

        owner = declaration(MeasuredMethodBase)
        receiver = MeasuredMethodChild(3, 4, 5)
        if grain == "value":
            pattern = "(MeasuredMethodChild $x $y $z)"
            body = "(+ (* $x $x) (* $y $y))"
        else:
            pattern = "$receiver"
            body = ("(+ (* (MeasuredMethodBase-x $receiver) (MeasuredMethodBase-x $receiver)) "
                    "(* (MeasuredMethodBase-y $receiver) (MeasuredMethodBase-y $receiver)))")
        owner.space.run(
            f"(: written-method-norm (-> MeasuredMethodBase Number))\n"
            f"(= (written-method-norm {pattern}) {body})\n"
            "(: written-method-report (-> MeasuredMethodBase Number))\n"
            "(= (written-method-report $receiver) (norm $receiver))"
        )
        families = (("MeasuredMethodBase-norm", "norm", "written-method-norm"),
                    ("MeasuredMethodBase-report", "report", "written-method-report"))
        names = [name for family in families for name in family]
        for name in names:
            assert owner.space.eval(S[name](receiver)) == [25]
        for count in (100, 1000):
            row = m._rt.must(
                "space_module(Space,_Module),metta_py_decode_shared(Wire,_Term,_),"
                "findall([_Name,_Samples],(member(_Name,Names),_Goal=..[_Name,_Term,_Out],"
                "findall(_Cost,(between(1,3,_),with_metta_module(_Module,"
                "(metta_py_work(_Before),"
                "forall(between(1,Count,_),(call(_Module:_Goal),_Out=25)),"
                "metta_py_work(_After),_Cost is _After-_Before))),_Samples)),Costs)",
                Space=owner.space.name, Wire=receiver.__metta__().to_wire(),
                Names=names, Count=count,
            )
            assert all(len(set(samples)) == 1 for _, samples in row["Costs"])
            costs = {name: samples[0] for name, samples in row["Costs"]}
            for canonical, public, written in families:
                assert costs[canonical] == costs[written], (grain, count, costs)
                assert costs[public] == costs[written] + count, (grain, count, costs)
