"""Purpose: the explicit answer a provider or operation may yield in place
of a plain atom: bindings for the query's variables, an optional explicit
value, a residue and an annotation. The wire form is ["a", theta, residue,
k] with an optional trailing value, and it is transport-agnostic: the
Python side sends it over janus, a remote backend sends the same shape
over its own pipe, and a Prolog-side provider needs none of it because
unification is already the binding step.
Guarantees:
  - to_wire() emits exactly the seam's answer form, theta as
    [[name, atom-wire], ...] pairs with $-stripped names
    [tested 2026-08-17: test_answer_wire_form_is_exact].
  - Construction validates shapes eagerly, so a malformed answer fails at
    the yield site it was written, not inside an engine callback
    [tested 2026-08-17: test_answer_validates_eagerly].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .atoms import Atom, Var, encode

_SCALAR = (int, float, str, bool)


def _binding_name(key: Any) -> str:
    """A theta key as the bare variable name the wire carries."""
    if isinstance(key, Var):
        return key.name
    if isinstance(key, str):
        name = key.removeprefix("$")
        if name:
            return name
    raise TypeError(
        f"a theta key names a query variable, as 'x', '$x' or a Var, "
        f"not {key!r}"
    )


class Answer:
    """One explicit answer: theta binds the query's variables, and the
    atoms of the answer stay derivable as theta applied to the pattern.

    A provider may yield one from match() in place of a plain atom, and a
    non-raw operation may return or yield one; the two forms mix freely in
    one stream. `value` is an explicit answer atom: a provider's value is
    unified with the query pattern under theta (the candidate-with-
    bindings form), and an operation's value is what the call reduces to,
    `()` when omitted, the relational reading. This is Hyperon's
    execute_bindings, an answer atom together with the bindings it is
    returned under.

    `residue` and `k` complete the wire form; the engine's support for
    them lands by phase, and until it does a non-default value is a loud
    error rather than a silently dropped one.

    Theta values are encoded with the standard value encoder: atoms pass
    through, scalars become their atoms, and a value needing a registered
    projection should be projected by the author.
    """

    __slots__ = ("k", "residue", "theta", "value")

    def __init__(
        self,
        theta: Mapping[Any, Any] | None = None,
        *,
        value: Any = None,
        residue: Atom | None = None,
        k: Any = None,
    ) -> None:
        if theta is None:
            theta = {}
        if not isinstance(theta, Mapping):
            raise TypeError(
                f"theta is a mapping from variable names to values, "
                f"not {type(theta).__name__}"
            )
        self.theta = {_binding_name(key): value_ for key, value_ in theta.items()}
        self.value = value
        if residue is not None and not isinstance(residue, Atom):
            raise TypeError(
                f"residue is an Atom, the part of the query this answer "
                f"did not discharge, not {type(residue).__name__}"
            )
        self.residue = residue
        if k is not None and not isinstance(k, (*_SCALAR, Atom)):
            raise TypeError(
                f"k is an annotation in the declared semiring, a scalar "
                f"or an Atom (the prov semiring's values are source "
                f"terms), not {type(k).__name__}"
            )
        self.k = k

    def to_wire(self) -> list:
        theta = [[name, encode(value).to_wire()] for name, value in self.theta.items()]
        residue = True if self.residue is None else encode(self.residue).to_wire()
        k = encode(self.k).to_wire() if isinstance(self.k, Atom) else self.k
        wire = ["a", theta, residue, k]
        if self.value is not None:
            wire.append(encode(self.value).to_wire())
        return wire

    def __repr__(self) -> str:
        parts = [repr(self.theta)]
        if self.value is not None:
            parts.append(f"value={self.value!r}")
        if self.residue is not None:
            parts.append(f"residue={self.residue!r}")
        if self.k is not None:
            parts.append(f"k={self.k!r}")
        return f"{type(self).__name__}({', '.join(parts)})"


class Bindings(Answer):
    """The theta-only shorthand: Bindings({"x": 3}) answers by binding."""

    __slots__ = ()

    def __init__(self, theta: Mapping[Any, Any]) -> None:
        super().__init__(theta)
