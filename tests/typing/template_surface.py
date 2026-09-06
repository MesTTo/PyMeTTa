"""Purpose: make the template protocols' 3.14 conformance executable in mypy.

The library's floor is 3.12, so nothing in ``metta`` may name
``string.templatelib.Template``; the doors accept the structural
``TemplateLike`` instead. That leaves one claim nothing else can check: the
class the protocol exists to describe actually satisfies it. This file is
checked at ``--python-version 3.14``, where typeshed has the module, which is
the only configuration in which the question can be asked at all.

The members are read-only PROPERTIES on the protocol rather than attributes,
because a mutable protocol attribute is invariant and
``Interpolation.conversion`` is ``Literal['a', 'r', 's'] | None`` rather than
``str | None``. An attribute protocol type-checks against a hand-written
double and rejects the stdlib class, which is the failure this lane catches.

Guarantees:
  - the 3.14 ``Template`` and ``Interpolation`` satisfy ``TemplateLike`` and
    ``InterpolationLike``, and a plain class of four attributes satisfies the
    latter too, so the backport and a test double reach the same door
    [tested: mypy-template-surface; commit=4481c32eb0e922047199c54cea97c24995c6959e]
  - every door that takes program text with holes accepts a ``Template``, a
    ``str``, and the keyword face's values [tested: mypy-template-surface;
    commit=4481c32eb0e922047199c54cea97c24995c6959e]
"""

from string.templatelib import Interpolation, Template
from typing import Any

from metta import Space
from metta.atoms import InterpolationLike, TemplateLike, parse


class Backported:
    """What ``tstrings-backport``'s object and a test double look like."""

    def __init__(self, strings: tuple[str, ...], interpolations: tuple[Any, ...]) -> None:
        """The two tuples the doors check for."""
        self.strings = strings
        self.interpolations = interpolations


class Hole:
    """An interpolation written as plain mutable attributes."""

    def __init__(self, value: Any, expression: str) -> None:
        """The four fields, as plain mutable attributes."""
        self.value = value
        self.expression = expression
        self.conversion: str | None = None
        self.format_spec = ""


def takes_source(source: str | TemplateLike) -> None:
    """The annotation every text door carries."""


def check_stdlib(template: Template, interpolation: Interpolation) -> None:
    """The 3.14 classes are the protocols, structurally."""
    as_template: TemplateLike = template
    as_hole: InterpolationLike = interpolation
    takes_source(template)
    takes_source("!(fib 10)")
    _ = (as_template, as_hole)


def check_doubles(backported: Backported, hole: Hole) -> None:
    """A hand-written class of the same shape is the same type."""
    as_template: TemplateLike = backported
    as_hole: InterpolationLike = hole
    takes_source(backported)
    _ = (as_template, as_hole)


def check_doors(space: Space, template: Template) -> None:
    """Every door named in llms.txt takes both faces."""
    space.run(template)
    space.run("!(fib {n})", n=10)
    space.eval(template)
    space.eval("(fib {n})", n=10)
    space.answers(template)
    space.eval_status(template)
    space.match(template)
    space.parse(template)
    space.profile(template)
    parse(template)
    parse("(fib {n})", n=10)
