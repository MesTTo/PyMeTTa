"""Purpose: the t-string literals the template-hole suite needs.

This is the one file allowed to contain 3.14 syntax.

A ``t"..."`` literal is a SyntaxError below 3.14, so it cannot sit in a module
any 3.12 run parses. This one is imported only from inside a
``sys.version_info >= (3, 14)`` guard, is not collected (no ``test_`` prefix),
and carries the one Ruff ``per-file-target-version`` entry in
``extensions/python/pyproject.toml``. Everything that can be written without
the literal is written without it, in ``test_template_holes.py``, so this file
holds nothing but the literals themselves.

Guarantees:
  - each function answers a real ``string.templatelib.Template`` built by the
    compiler, not a hand-assembled object, so the literal path is what the
    suite exercises [tested: test_a_literal_template_binds_an_int;
    commit=4481c32eb0e922047199c54cea97c24995c6959e]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from typing import Any


def fib_of(n: Any) -> Any:
    """A value in call position: the PEP 750 example, in MeTTa."""
    return t"!(+ {n} 1)"


def identity_of(value: Any) -> Any:
    """One value through the engine's identity head."""
    return t"!(id {value})"


def term_identity_of(value: Any) -> Any:
    """The same, as a term rather than a program."""
    return t"(id {value})"


def person_pattern(name: Any) -> Any:
    """A match pattern whose first argument is a hole."""
    return t"(person {name} $age)"


def debug_of(x: Any) -> Any:
    """The debug fold, which PEP 750 folds into the preceding segment."""
    return t"!(debug-line {x=})"


def spaced_debug_of(x: Any) -> Any:
    """The debug fold with the author's own spacing kept."""
    return t"!(debug-line {x = })"


def repr_of(value: Any) -> Any:
    """An explicit conversion, applied before the value enters."""
    return t"!(id {value!r})"


def spec_of(name: Any, text: Any, obj: Any) -> Any:
    """The three specs, each sugar for one atom constructor."""
    return t"!(triple {name:sym} {text:expr} {obj:py})"


def unknown_spec_of(value: Any) -> Any:
    """A Python format spec, which is not a hole spec."""
    return t"!(id {value:.2f})"


def nested_sum(inner: Any) -> Any:
    """A template inside a template: its text and holes compose into this one."""
    return t"!(+ {inner} 100)"


def inner_sum(x: Any) -> Any:
    """The inner half of the nesting case."""
    return t"(+ 1 {x})"


def in_string_literal(value: Any) -> Any:
    """A hole the reader would swallow into a string."""
    return t'!(id "a {value} b")'


def in_symbol(value: Any) -> Any:
    """A hole glued to the symbol before it."""
    return t"!(foo{value})"


def in_comment(value: Any) -> Any:
    """A hole the reader would discard as comment text."""
    return t"!(id 1) ; {value}"


def after_a_string(value: Any) -> Any:
    """A hole right after a closing quote.

    The reader reads it as its own token, so an adjacency rule would refuse
    text the engine accepts.
    """
    return t'!(pair "a"{value})'


def spelling_the_prefix(value: Any) -> Any:
    """Author text spelling the reserved prefix, which cannot be told apart."""
    return t"!(id __metta_hole_0 {value})"


def two_terms(left: Any, right: Any) -> tuple[Any, Any]:
    """Two targets of one call, whose holes must not collide."""
    return t"(id {left})", t"(id {right})"


def malformed() -> Any:
    """A template whose tuples do not interleave."""

    class Broken:
        strings = ("a", "b", "c")
        interpolations = ()

    return Broken()
