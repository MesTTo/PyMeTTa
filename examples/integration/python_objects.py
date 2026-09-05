"""Purpose: the two-way translator and reflective reasoning: an Enum becomes
symbols, a dataclass a constructor expression, answers rebuild real objects,
and py-field turns any object's fields into a relation MeTTa enumerates.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from dataclasses import dataclass
from enum import Enum

from _common import check, done

from metta import MeTTa, S, V, ground, spaces
from metta.convert import build, project
from metta.integrate import install_reflection_ops

m = MeTTa().space()


class Mood(Enum):
    calm = 1
    stormy = 2


@dataclass
class Robot:
    name: str
    mood: Mood


projected = project(Robot("R2", Mood.calm))
check("projection", str(projected.atom), '(Robot "R2" calm)')
m.add(*projected.declarations, projected.atom)
m.add(project(Robot("HAL", Mood.stormy)).atom)

rows = m.match(S.Robot(V.name, S.stormy))
check("match on parts", str(rows[0].name), '"HAL"')

rebuilt = build(projected.atom)
check("rebuild", isinstance(rebuilt, Robot) and rebuilt.mood, Mood.calm)

named_view = m.metta.space(
    backing=spaces.object_view(
        Robot("C3", Mood.calm),
        relation="robot-field",
    )
)
named_fields = named_view.match(S["robot-field"](V.object, V.field, V.value))
check("custom object-view relation", {str(row.field) for row in named_fields}, {"name", "mood"})
named_view.drop()


class Tagged:
    """An owned type that converts without process-wide registration."""

    def __init__(self, label: str) -> None:
        """Retain the label reconstructed from MeTTa."""
        self.label = label

    def __metta__(self):
        """Project this value as a constructor term."""
        return S.Tagged(self.label)

    @classmethod
    def __from_metta__(cls, label):
        """Rebuild a value from that constructor's fields."""
        return cls(label)


tagged_atom = project(Tagged("checked")).atom
tagged = build(tagged_atom, Tagged)
check("owned conversion hook projects", str(tagged_atom), '(Tagged "checked")')
check("owned conversion hook rebuilds", isinstance(tagged, Tagged) and tagged.label, "checked")

# Reflection: fields of any live object become a two-mode relation.
install_reflection_ops(m)
m.add(S.config(ground(Robot("Probe", Mood.calm))))
(fields,) = m.run("!(collapse (match (context-space) (config $c) (py-field $c $f)))")
check("enumerated fields", {str(pair[0]) for pair in fields[0]}, {"name", "mood"})
done("python_objects")
