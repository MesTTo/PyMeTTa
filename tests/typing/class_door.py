"""Purpose: make the class door's PEP 681 declaration executable in mypy.

`@metta.define` on an annotated class builds `__init__` at run time, and
`typing.dataclass_transform` on the declaring overload is what tells a checker
so. Asserted here rather than in a test because the gate's mypy reads
``files = ["metta"]`` and never opens the suite, so a claim about what a
checker infers has to sit in a file a checker is pointed at.

Both spellings appear on purpose, because they do not agree. Mypy resolves a
decorator expression to a definition node: a module attribute has one and an
instance member access does not, so it reads the declaration on
``metta.define`` and not on ``m.define``. Pyright, PEP 681's reference
implementation, reads both [measured 2026-09-07: mypy 2.3.0 and pyright
1.1.411; https://github.com/python/mypy/issues/19824 is SQLAlchemy meeting the
same wall with ``registry.mapped_as_dataclass``].

Guarantees:
  - the module door synthesises the constructor, so `Point(1.0, 2.0)` checks
    and a wrong-arity call does not [tested: mypy-class-door; commit=WORKTREE]
  - each ignore below is load-bearing under the repository's
    ``warn_unused_ignores``: the day mypy reads the declaration through a
    bound method, the two ignores on the method spelling go unused and this
    lane turns red, which is how the limitation gets retired rather than
    remembered [tested: mypy-class-door; commit=WORKTREE]
"""

from typing import assert_type

import metta


@metta.define
class Point:
    """Two coordinates, declared into the default context's space."""

    x: float
    y: float


@metta.define
class Tagged:
    """A field with a default, which the transform reads as optional."""

    name: str
    weight: float = 1.0


# The class keeps its own identity through the decorator: before the overload
# said `type[_T]` this was bare `type`, and pyright lost the class entirely.
assert_type(Point(1.0, 2.0), Point)
assert_type(Point(1.0, 2.0).x, float)
assert_type(Tagged("a"), Tagged)
assert_type(Tagged("a", 2.0), Tagged)

# Wrong arity, both directions. The ignores ARE the assertion that mypy
# catches these.
Point(1.0)  # type: ignore[call-arg]
Point(1.0, 2.0, 3.0)  # type: ignore[call-arg]
Tagged()  # type: ignore[call-arg]

_wrong_type: str = Point(1.0, 2.0).x  # type: ignore[assignment]


m = metta.MeTTa()


@m.define
class Pair:
    """The method spelling, whose constructor mypy does not synthesise."""

    left: int
    right: int


assert_type(Pair, type[Pair])
Pair(1, 2)  # type: ignore[call-arg]
