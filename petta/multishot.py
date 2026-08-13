"""Purpose: clingo's multi-shot solving vocabulary on the engine (Gebser,
Kaminski, Kaufmann, Schaub, "Multi-shot ASP solving with clingo", arXiv
1705.09811): programs that change between solves without rebuilding the
world. A Part is a named, parameterized program template grounded once per
instantiation, clingo's #program directive; an External is an atom whose
truth toggles cheaply between solves via assign and ends with release,
clingo's #external. On an engine with no grounding step an external is
exactly a togglable fact and grounding a part is exactly instantiating its
template into the space, which is the honest translation; the solve side of
the loop is the query surface the space already has, m.query, m.prepare and
m.assuming. One divergence, deliberate: assigning a released external is a
hard error here where clingo makes it a silent noop.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from .atoms import Atom, encode

__all__ = ["external", "part", "External", "Part"]


class External:
    """One togglable truth: present while assigned True, absent while
    False, finished by release().

        query1 = multishot.external(m, S.query(1))
        query1.assign(True)
        ... m.query(...) ...
        query1.assign(False)          # next solve sees a different world
        query1.release()              # permanently gone
    """

    def __init__(self, m, atom: Atom) -> None:
        self._m = m
        self._atom = atom
        self._value = False
        self._released = False

    @property
    def atom(self) -> Atom:
        return self._atom

    @property
    def value(self) -> bool:
        return self._value

    @property
    def released(self) -> bool:
        return self._released

    def assign(self, value: bool) -> None:
        """Set the truth for the solves that follow; idempotent."""
        if self._released:
            raise RuntimeError(
                f"{self._atom} was released; a released external has no "
                f"truth left to assign. clingo would ignore this silently, "
                f"which hides a lifecycle bug; here it is an error."
            )
        if value and not self._value:
            self._m.add(self._atom)
        elif not value and self._value:
            self._m.remove(self._atom)
        self._value = bool(value)

    def release(self) -> None:
        """End the external: false from here on, permanently."""
        if self._released:
            return
        if self._value:
            self._m.remove(self._atom)
        self._value = False
        self._released = True


def external(m, atom: Any) -> External:
    """Declare an atom external: initially false, toggled by assign."""
    return External(m, atom if isinstance(atom, Atom) else encode(atom))


class Part:
    """One named program template, grounded once per instantiation.

        step = multishot.part(m, "step", lambda t: f\"\"\"
            (= (reach $x {t}) (and (reach $y {t - 1}) (edge $y $x)))
        \"\"\")
        step.ground(1)
        step.ground(2)
        step.ground(1)     # error: this instantiation already grounded

    The template answers MeTTa source or an iterable of atoms for its
    parameters; grounding adds it to the space. Grounding one
    instantiation twice would duplicate its rules, the multi-shot
    discipline clingo's documentation warns about, so it is refused."""

    def __init__(self, m, name: str, template: Callable[..., Any]) -> None:
        self._m = m
        self.name = name
        self._template = template
        self._grounded: set[tuple] = set()

    def ground(self, *args: Any) -> None:
        key = tuple(args)
        if key in self._grounded:
            raise RuntimeError(
                f"part {self.name!r} is already grounded for {key!r}; "
                f"grounding an instantiation twice duplicates its rules"
            )
        produced = self._template(*args)
        if isinstance(produced, str):
            self._m.run(produced)
        elif isinstance(produced, Iterable):
            for atom in produced:
                self._m.add(atom)
        else:
            raise TypeError(
                f"part {self.name!r} answered {type(produced).__name__}; "
                f"a template answers MeTTa source or an iterable of atoms"
            )
        self._grounded.add(key)

    def grounded(self) -> set[tuple]:
        """Every instantiation grounded so far."""
        return set(self._grounded)


def part(m, name: str, template: Callable[..., Any]) -> Part:
    """Declare a parameterized program part, clingo's #program."""
    return Part(m, name, template)
