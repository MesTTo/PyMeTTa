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

from petta import MeTTa, S, V, val
from petta.convert import build, project
from petta.integrate import install_reflection_ops

m = MeTTa().new_space()


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

rows = m.query(S.Robot(V.name, S.stormy))
check("match on parts", str(rows[0].name), '"HAL"')

rebuilt = build(projected.atom)
check("rebuild", isinstance(rebuilt, Robot) and rebuilt.mood, Mood.calm)

# Reflection: fields of any live object become a two-mode relation.
install_reflection_ops(m)
m.add(S.config(val(Robot("Probe", Mood.calm))))
(fields,) = m.run("!(collapse (match (context-space) (config $c) (py-field $c $f)))")
check("enumerated fields", {str(pair[0]) for pair in fields[0]}, {"name", "mood"})
done("python_objects")
