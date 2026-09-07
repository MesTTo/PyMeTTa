"""Purpose: a Python module written to be read BY a face, carrying one of each
shape the face generator has a rule for, so the tests derive a face from real
signatures rather than from a description of them.

The shapes, in the order they appear: an annotated function with a Google
docstring; a defaulted positional parameter, which makes two call forms; a
keyword-only parameter with a default, which makes none; `*args`; `**kwargs`; a
function nothing annotates and nothing documents; a tuple result; a container
result; a `None` result; a REQUIRED keyword-only parameter, which no positional
MeTTa call can reach; a class with a method and a property; and a callable
shaped like a C function, whose signature lives in its docstring because the
runtime refuses one.

Assumes: nothing. Nothing here imports, and every function is total.
Guarantees:
  - `stamped` and `opaque` are the two names whose face generation refuses,
    one for a keyword-only parameter no positional call reaches and one for a
    signature neither the runtime nor the docstring states [tested:
    test_a_required_keyword_only_parameter_refuses,
    test_a_name_with_no_signature_anywhere_is_refused; commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations


def area(width: float, height: float) -> float:
    """The area of a rectangle.

    Args:
        width: how wide the rectangle is.
        height: how tall the rectangle is.

    Returns:
        The product of the two.
    """
    return width * height


def scale(value: float, factor: float = 2.0) -> float:
    """One number scaled, by two when nothing says otherwise.

    Args:
        value: the number to scale.
        factor: what to scale it by.
    """
    return value * factor


def label(text: str, *, upper: bool = False) -> str:
    """One string, upper-cased on request.

    Args:
        text: the string to label.
        upper: whether to upper-case it.
    """
    return text.upper() if upper else text


def total(*values: float) -> float:
    """Every argument added together."""
    return sum(values)


def tally(**counts: int) -> int:
    """Every keyword's value added together."""
    return sum(counts.values())


def anything(value):  # noqa: D103  -- the fixture's point is a name the module says nothing about
    return value


def bounds(low: int, high: int) -> tuple:
    """The pair of bounds, as a tuple.

    Args:
        low: the lower bound.
        high: the upper bound.
    """
    return (low, high)


def names() -> list:
    """The three names this module knows about."""
    return ["one", "two", "three"]


def store(value: int) -> None:
    """Take a number and answer nothing at all.

    Args:
        value: the number to take.
    """
    _ = value


def stamped(value: int, *, when: str) -> str:
    """One number stamped with a time that has no default.

    Args:
        value: the number to stamp.
        when: the stamp, which a positional call cannot supply.
    """
    return f"{value}@{when}"


class Box:
    """A box holding one number, so a method and a property have a receiver."""

    def __init__(self, held: int = 0) -> None:
        """Hold a number."""
        self._held = held

    def get(self) -> int:
        """The number this box holds."""
        return self._held

    @property
    def size(self) -> int:
        """How much this box holds, read rather than called."""
        return self._held


class _Clinic:
    """A callable shaped like a C function: no signature, one in the docstring.

    `inspect.signature` answers from `__signature__` when an object has one,
    and a C function without an Argument Clinic text signature raises
    ValueError there instead. This raises the same thing with the same words,
    so the ladder's second rung is exercised by an object rather than by a
    description of one [source: /usr/lib/python3.14/inspect.py:2321,
    _signature_from_function's text-signature branch; commit=7229962705d199fb08796b3090ec5a8a3a0ae393].
    """

    def __init__(self, documentation: str) -> None:
        """Carry the docstring the signature has to be read out of."""
        self.__doc__ = documentation

    def __call__(self, *arguments: object) -> tuple:
        """Answer the arguments, which is all a stand-in has to do."""
        return arguments

    @property
    def __signature__(self) -> object:
        """Refuse a signature exactly as a C function without one refuses."""
        msg = "no signature found for builtin <built-in function clipped>"
        raise ValueError(msg)


clipped = _Clinic(
    "clipped(value, low, high=10) -> int\n"
    "\n"
    "One number held between two bounds.\n"
    "\n"
    "Args:\n"
    "    value: the number to clip.\n"
    "    low: the floor.\n"
    "    high: the ceiling.\n"
)

opaque = _Clinic("One number, described in prose and in no signature at all.\n")
