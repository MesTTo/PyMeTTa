"""Purpose: the four structural images this seat ships, as fallback rows.

Every row here reads a class's OWN structure and names no library: an Enum is a
symbol, a dataclass and a NamedTuple destructure field-wise, and a plain class
that states `__match_args__` for Python's own `match` has said how it comes
apart. A framework's model is a library's business and arrives as its own
distribution's row against the same point.

The four are FALLBACKS, pluggy's trylast, and that is load-bearing rather than
tidy: a validated model is also a class with `__match_args__`, so the specific
reading has to be asked first, and once the specific row lives in another
distribution there is no order for a package to arrange. Registration order used
to decide it and cannot any more.

Loaded LAZILY, at the first dispatch of the `image` point, which names this
module in `shipped=`; a program that never projects an unregistered class pays
nothing for these.

Assumes:
  - `_convert_registry` is fully imported before a dispatch reaches here, which
    holds because this is a separate module and the point names THIS one
Guarantees:
  - a class a package's row claims wins over the structural reading of the same
    class, whatever order the two registered in [tested:
    test_a_fallback_row_is_consulted_after_every_other_row; commit=94057a0f073c0fab0a35c42beff2c324d8a0addd]
  - the four keep the behaviour the chain had before the seam, the existing
    conversion suites being the differential [tested:
    extensions/python/tests/ch03_atoms_and_expressions/test_convert.py; commit=94057a0f073c0fab0a35c42beff2c324d8a0addd]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import dataclasses
import inspect
from enum import Enum
from typing import Any

from . import seam
from ._convert_registry import (
    _dataclass_registration,
    _match_args_registration,
    _named_tuple_registration,
)


def _enum_image(cls: type) -> Any:
    """An Enum crosses as a bare symbol, and runs backwards too."""
    if not issubclass(cls, Enum):
        return None
    return seam.image_of("symbol", None, None, cls.__name__)


def _dataclass_image(cls: type) -> Any:
    """A dataclass destructures field-wise, its constructor the reverse."""
    if not dataclasses.is_dataclass(cls) or cls is type(None):
        return None
    return _dataclass_registration(cls)


def _named_tuple_image(cls: type) -> Any:
    """A NamedTuple is a tuple that already names its fields."""
    if not (issubclass(cls, tuple) and hasattr(cls, "_fields")):
        return None
    return _named_tuple_registration(cls)


def _match_args_image(cls: type) -> Any:
    """A plain class that states its own destructuring for Python's match.

    A class that says how it crosses through __metta__ has spoken; a default
    derived beside it would claim the type name for a projection the hook
    never uses.
    """
    match_args = getattr(cls, "__match_args__", None)
    if not (
        isinstance(match_args, tuple)
        and match_args
        and all(isinstance(name, str) for name in match_args)
        and inspect.getattr_static(cls, "__metta__", None) is None
    ):
        return None
    return _match_args_registration(cls, match_args)


# The order among these four is still their own reading order, because they are
# all fallbacks and the partition is stable: a NamedTuple is also a tuple and a
# dataclass is also a class with __match_args__, so the more specific structural
# reading stays ahead of the more general one.
for _name, _claims in (
    ("enum", _enum_image),
    ("dataclass", _dataclass_image),
    ("namedtuple", _named_tuple_image),
    ("match-args", _match_args_image),
):
    seam.image.register(_name, source="shipped", fallback=True, claims=_claims)

del _name, _claims
