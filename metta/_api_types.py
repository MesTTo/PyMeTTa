"""Purpose: the types the API boundary is written in: how a space is designated,
the one resolution from the receiver a caller holds to the space a door works
in, and the structural contract program text with holes is accepted by.
Guarantees:
  - type checkers distinguish engine space identifiers from operation names
    without exporting either implementation detail [tested:
    test_canonical_context_types_replace_public_newtypes; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - every public door that wants a space takes a context or a space and reaches
    the same space either way [tested:
    test_every_space_door_takes_a_context_or_a_space; commit=f25ac80f93e7c3626b87e593117d09b9c9bc8c95]
  - ``string.templatelib.Template`` satisfies ``TemplateLike`` and a plain class
    carrying the two attributes does too, so the 3.14 literal and a backport
    reach one door [tested:
    test_a_hand_built_template_object_reaches_the_same_door,
    mypy-template-surface; commit=WORKTREE]
Assumes:
  - it imports nothing but ``typing``, which is what lets the LEAF modules use
    it: ``metta.casting`` costs 10.9ms to import and ``metta.integrate``, where
    the public ``space_of`` door lives, costs 41.2ms, so a leaf reaching the
    resolution through the satellite would have quadrupled its own import
    [measured 2026-09-06 with ``python -X importtime``; commit=f25ac80f93e7c3626b87e593117d09b9c9bc8c95]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from typing import Any, Final, NewType, Protocol

_SpaceId = NewType("_SpaceId", str)
_OperationName = NewType("_OperationName", str)
_DEFAULT_SPACE: Final[_SpaceId] = _SpaceId("&self")


class InterpolationLike(Protocol):
    """One hole of a template: its value and how the author wrote it.

    PEP 750's ``string.templatelib.Interpolation``, stated structurally so the
    3.14 class, a backport's object and a plain class of four attributes are
    one type. ``value`` is already evaluated, ``expression`` is the source text
    inside the braces, and ``conversion`` and ``format_spec`` are recorded
    rather than applied, which is what lets the reader decide what they mean.

    Read-only members, deliberately: a mutable protocol attribute is
    invariant, and ``Interpolation.conversion`` is ``Literal['a', 'r', 's'] |
    None`` rather than ``str | None``, so an attribute protocol would reject
    the class it exists to describe.
    """

    @property
    def value(self) -> Any:
        """The evaluated value at this hole."""

    @property
    def expression(self) -> str:
        """The source text between the braces, up to any ``!``, ``:`` or ``=``."""

    @property
    def conversion(self) -> str | None:
        """``r``, ``s``, ``a``, or None when the author wrote no ``!``."""

    @property
    def format_spec(self) -> str:
        """The text after the ``:``, empty when the author wrote none."""


class TemplateLike(Protocol):
    """Program text with holes: the literal segments and the interpolations.

    Satisfied by a 3.14 ``t"..."`` literal, by ``tstrings-backport``'s
    ``t("...")``, and by anything else carrying the same two tuples. The doors
    check for the two tuples rather than for a class, because the class does
    not exist below 3.14 and this library's floor is 3.12.

    ``strings`` is one longer than ``interpolations``, so the two interleave
    exactly: segment, hole, segment, hole, segment.
    """

    @property
    def strings(self) -> tuple[str, ...]:
        """The literal segments, one more of them than there are holes."""

    @property
    def interpolations(self) -> tuple[InterpolationLike, ...]:
        """The holes, in the order they appear."""


def space_of(m: Any) -> Any:
    """The space a door works in, given a context or a space.

    A door that reads, writes, declares or introspects wants a SPACE, and
    what a caller holds is usually a context. ``MeTTa`` refuses a Space door
    rather than forwarding it, deliberately, so a door written the natural
    way failed on the first storage or introspection door it reached:
    ``metta.lint.lint(m)`` raised ``MeTTa has no 'name'`` and
    ``metta.tables.declare(m, ...)`` raised ``MeTTa has no 'parse'``.

    Duck-typed rather than an isinstance, because the leaf modules that use
    it deliberately do not import the facade. A context is exactly the object
    with a home space to give; a space has none, and answers for itself.

    ``metta.integrate.space_of`` is this resolution's public spelling.
    """
    home = getattr(m, "self", None)
    return m if home is None else home


__all__ = ["InterpolationLike", "TemplateLike"]
