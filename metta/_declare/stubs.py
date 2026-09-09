"""Purpose: render one space's declaration rows as a PEP 484 stub a checker reads.

The arrow a program declares is a type, and a `.pyi` is where Python keeps
types that have no runtime object to hang on. `(: area (-> Number Number))`
becomes `def area(x1: int | float, /) -> int | float`, the `(@doc ...)` beside
it becomes the docstring, and an editor completes and checks calls into a MeTTa
program the same way it does any other module.

The scalar half of the projection is the Python column of the one type table
every surface reads [source: extensions/python/metta/_catalog/types.py:120;
commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e], and the shapes Python spells structurally are this file's own:

    (-> A B) argument   Callable[[A], B]    (Literal 1 2)      Literal[1, 2]
    (->) return         None                NoneType           None
    $t $u               T1, T2              (: X Type)         class X(Atom)

A symbol the space does not declare as a type is an atom to Python, and a
non-arrow expression type is an `Expression`, which is where the forward table
sends every container.

Assumes:
  - the parameter names are `x1..xn`, positional-only, which is what
    `_EngineFunction.__signature__` already answers for the same arrow, so the
    stub and `inspect.signature` agree [source:
    extensions/python/metta/_declare/functions.py:254; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]
Guarantees:
  - the text parses as Python, and a consumer calling a declared head with the
    wrong argument type fails `mypy --strict` while the right one passes
    [tested: test_a_generated_stub_checks_its_consumer; commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - a head whose MeTTa name Python cannot spell as an identifier is named in
    the trailing note with the bracket door that reaches it, rather than
    dropped [tested: test_a_head_python_cannot_spell_is_named_not_dropped;
    commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - rendering reads rows only; nothing in the described program runs [tested:
    test_stubs_read_the_space_without_evaluating_it; commit=dd4f82100a052e2c5254a2ef9e91f6eb9d2e0c49]
  - a head the space defines and never declares is rendered from the arrow
    its stored atoms justify, with the proposal named in the docstring rather
    than presented as a declaration [tested:
    test_the_signature_and_the_stub_both_say_inferred; commit=8d67307403c1e41ccf058bd3c8d4c079dd7cf7d5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import metta._declare.functions as _declare_functions_module
from metta._atoms.factories import Atom, Expression, Grounded, Symbol, Variable, _decode
from metta._atoms.names import python_name
from metta._catalog.declarations import (
    ARROW,
    INFERRED_NOTE,
    Declaration,
    Inference,
    declarations,
    inferred,
    is_arrow,
)
from metta._catalog.types import PYTHON as _SCALARS
from metta._version import __version__

#: Which module each name a rendered stub can mention comes from. The order of
#: the modules here is the order the imports are written, which is isort's:
#: the standard library, then this package.
# closed-set: decides; policy=which module each name a rendered stub can mention comes from, in isort's own order; reads=none, it is the source
_IMPORTS = {
    "Callable": "collections.abc",
    "Any": "typing",
    "Literal": "typing",
    "overload": "typing",
    "Space": "metta",
    "Atom": "metta._atoms.factories",
    "Symbol": "metta._atoms.factories",
    "Variable": "metta._atoms.factories",
    "Expression": "metta._atoms.factories",
    "Grounded": "metta._atoms.factories",
}
_IMPORT_ORDER = ("collections.abc", "typing", "metta", "metta._atoms.factories")

_LITERAL = Symbol("Literal")


def _literal_annotation(atom: Expression) -> str | None:
    """`(Literal 1 "a")` as `Literal[1, 'a']`, the forward rule reversed."""
    values = []
    for child in atom.children[1:]:
        if not isinstance(child, Grounded):
            return None
        value = _decode(child)
        if not isinstance(value, (bool, int, str)):
            return None
        values.append(repr(value))
    return f"Literal[{', '.join(values)}]" if values else None


class _Projection:
    """One rendering pass: the annotations, and what they made necessary."""

    def __init__(self, types: set[str]) -> None:
        #: The names the space declares with `(: X Type)`, which are the
        #: classes this stub also renders and therefore may name.
        self.types = types
        #: Every import the rendered annotations turned out to need.
        self.needs: set[str] = set()
        #: The type parameters the arrow being rendered mentions, in first-use
        #: order, so `def pick[T1](x1: T1, /) -> T1` binds them where MeTTa
        #: does, and the variable each one stands for.
        self.parameters: list[str] = []
        self.variables: dict[str, str] = {}

    def annotation(self, atom: Atom) -> str:
        """One MeTTa type as the Python annotation that carries the most of it."""
        if isinstance(atom, Variable):
            return self.parameter(atom)
        if isinstance(atom, Symbol):
            spelled = str(atom)
            if spelled in self.types:
                rendered = python_name(spelled)
                if rendered is not None:
                    return rendered
            scalar = _SCALARS.get(spelled)
            if scalar is None:
                # A type symbol this space does not declare: an imported one,
                # or a type whose declaration lives where the program does not
                # say. It crosses as an atom, which is what Python can promise.
                return self.need("Atom")
            # A scalar spelled as one imported name needs that import; the
            # rest (`int | float`, `str`, `bool`, `None`) need nothing.
            return self.need(scalar) if scalar in _IMPORTS else scalar
        if isinstance(atom, Expression) and atom.children:
            if is_arrow(atom):
                return self.callable_annotation(atom)
            if atom.children[0] == _LITERAL:
                literal = _literal_annotation(atom)
                if literal is not None:
                    self.need("Literal")
                    return literal
        return self.need("Expression")

    def callable_annotation(self, atom: Expression) -> str:
        """`(-> A B)` in a type position, which Python spells `Callable`."""
        parts = atom.children[1:]
        if not parts:
            return f"{self.need('Callable')}[..., {self.need('Any')}]"
        arguments = ", ".join(self.annotation(part) for part in parts[:-1])
        return f"{self.need('Callable')}[[{arguments}], {self.annotation(parts[-1])}]"

    def need(self, name: str) -> str:
        """Record that the stub must import `name`, and answer it."""
        self.needs.add(name)
        return name

    def parameter(self, atom: Variable) -> str:
        """The type parameter one MeTTa type variable binds in this signature.

        Numbered by first appearance rather than named after the source,
        because the engine renames a variable when it stores the atom: `(:
        pick (-> $t $t $t))` reads back as `(-> $_1 $_1 $_1)`, so the name the
        author wrote is not there to carry [measured 2026-09-07]. `T1..Tn` is
        then Python's own spelling of the concept rather than a gensym leaked
        into a published signature.
        """
        spelled = str(atom)
        if spelled not in self.variables:
            self.variables[spelled] = f"T{len(self.variables) + 1}"
            self.parameters.append(self.variables[spelled])
        return self.variables[spelled]

    def signature(self, arrow: Expression) -> tuple[str, str]:
        """One arrow as a parameter list and a return annotation.

        The parameters are `x1..xn` and positional-only because a MeTTa head
        takes its arguments by position; `(->)` as the whole arrow is the unit
        return every effect form answers, and it is `None`.
        """
        self.parameters = []
        self.variables = {}
        parts = arrow.children[1:]
        if not parts:
            return "", "None"
        arguments = [self.annotation(part) for part in parts[:-1]]
        returns = "None" if _is_unit(parts[-1]) else self.annotation(parts[-1])
        rendered = ", ".join(
            f"x{position}: {annotation}"
            for position, annotation in enumerate(arguments, start=1)
        )
        return (f"{rendered}, /" if rendered else ""), returns


def _is_unit(atom: Atom) -> bool:
    """Whether a return type is `(->)`, the arrow with nothing after it."""
    return isinstance(atom, Expression) and len(atom.children) == 1 and atom.children[0] == ARROW


def _documentation_lines(
    row: Declaration, indent: str, *, note: str | None = None
) -> list[str]:
    """The head's docstring, which is the text `help()` prints for it.

    A head with no `(@doc ...)` row still says what it is: its declarations,
    which is the same fallback `_EngineFunction.__doc__` gives. `note` is the
    one line an inferred signature adds, so the stub says which of its
    signatures the program promised and which this library proposed.
    """
    if row.documentation is not None:
        text = _declare_functions_module._format_doc_atom(row.documentation)
    elif row.types:
        text = "\n".join(f"{row.name}: {declared}" for declared in row.types)
    else:
        text = row.name
    if note is not None:
        text = f"{text}\n{note}"
    # The text is a MeTTa string and may hold anything. Backslashes escape
    # first, then the delimiter itself; a text ending in a quote takes the
    # multi-line form, whose closing delimiter is on a line of its own and
    # therefore cannot run into it.
    text = text.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    lines = text.split("\n")
    if len(lines) == 1 and not lines[0].endswith('"'):
        return [f'{indent}"""{lines[0]}"""']
    return [
        f'{indent}"""{lines[0]}',
        *(f"{indent}{line}".rstrip() for line in lines[1:]),
        f'{indent}"""',
    ]


def _type_parameters(names: _collections_abc.Sequence[str]) -> str:
    """PEP 695's parameter list, which scopes a variable to its own signature."""
    return f"[{', '.join(names)}]" if names else ""


def _import_lines(needed: set[str]) -> list[str]:
    """One import line per module, in the order a formatter would leave them."""
    from_module: dict[str, list[str]] = {}
    for name in needed:
        from_module.setdefault(_IMPORTS[name], []).append(name)
    return [
        f"from {module} import {', '.join(sorted(from_module[module]))}"
        for module in _IMPORT_ORDER
        if module in from_module
    ]


def _render_function(
    row: Declaration,
    name: str,
    projection: _Projection,
    proposals: _collections_abc.Sequence[Inference] = (),
) -> list[str]:
    """One head as `def`s: one per declared arrow, or one open signature.

    A head the space never declares takes the arrows its stored atoms justify
    instead, one overload each, and says so in its docstring; the same
    proposal `Space.infer_types()` answers and `inspect.signature()` shows.
    """
    arrows = row.arrows
    lines: list[str] = []
    note: str | None = None
    if not arrows and proposals:
        note = INFERRED_NOTE
        signatures = []
        for proposal in proposals:
            arguments, returns = projection.signature(proposal.arrow)
            signatures.append((arguments, returns, _type_parameters(projection.parameters)))
    elif not arrows:
        # No arrow and nothing observed is `(*args)` in __signature__ too. The
        # arities its equations answer at are still known, and each is its own
        # overload, so a call with the wrong number of arguments is caught.
        signatures = [
            (
                ", ".join(f"x{position}: {projection.need('Any')}" for position in range(1, arity + 1))
                + (", /" if arity else ""),
                projection.need("Any"),
                "",
            )
            for arity in row.arities
        ] or [(f"*args: {projection.need('Any')}", projection.need("Any"), "")]
    else:
        signatures = []
        for arrow in arrows:
            arguments, returns = projection.signature(arrow)
            signatures.append((arguments, returns, _type_parameters(projection.parameters)))
    for arguments, returns, parameters in signatures:
        if len(signatures) > 1:
            lines.append(f"@{projection.need('overload')}")
        lines.append(f"def {name}{parameters}({arguments}) -> {returns}:")
        lines.extend(_documentation_lines(row, "    ", note=note))
        lines.append("")
    return lines


def _render_type(row: Declaration, name: str, projection: _Projection) -> list[str]:
    """One declared type as a class, with the constructor arrow as `__init__`.

    `(: Point Type)` with `(: Point (-> Number Number Point))` beside it is
    what `install_type` writes for one annotated Python class, so reading the
    pair back as one class is that door's own inverse. A value of the type
    crosses as an atom, which is the base the class carries.
    """
    lines = [f"class {name}({projection.need('Atom')}):"]
    lines.extend(_documentation_lines(row, "    "))
    constructors = [
        arrow
        for arrow in row.arrows
        if arrow.children and arrow.children[-1] == Symbol(row.name)
    ]
    for arrow in constructors:
        arguments, _ = projection.signature(arrow)
        if len(constructors) > 1:
            lines.append(f"    @{projection.need('overload')}")
        parameters = _type_parameters(projection.parameters)
        opening = f"    def __init__{parameters}(self"
        lines.append(f"{opening}, {arguments}) -> None: ..." if arguments else f"{opening}) -> None: ...")
    lines.append("")
    return lines


def _module_documentation(sources: _collections_abc.Sequence[str], space_name: str) -> list[str]:
    """The stub's own docstring: where it came from and what wrote it."""
    origin = ", ".join(sources) if sources else space_name
    return [
        f'"""MeTTa declarations from {origin}, as Python.',
        "",
        f"Generated by metta {__version__} from the space's own rows. The space is",
        "the authority: regenerate rather than editing, and reach a head this file",
        'could not name with m.fn["<name>"].',
        '"""',
        "",
    ]


def stubs(space: _root.Space | Any, *, sources: _collections_abc.Iterable[str | os.PathLike[str]] = ()) -> str:
    """Render one space's declared heads as the text of a `.pyi` stub.

        print(metta.stubs(m.self))
        python -m metta stubs program.metta -o program.pyi

    One `def` per declared head, one `class` per declared type, the arrow
    projected to annotations and the `(@doc ...)` to the docstring. `sources`
    names the files the module docstring credits.
    """
    named = [os.fspath(source) for source in sources]
    rows = declarations(space)
    proposals: dict[str, list[Inference]] = {}
    for proposal in inferred(space):
        proposals.setdefault(proposal.name, []).append(proposal)
    types = {row.name for row in rows if row.is_type}
    projection = _Projection(types)
    body: list[str] = []
    exported: list[str] = []
    unspellable: list[str] = []
    taken: set[str] = set()
    spelled: list[tuple[Declaration, str]] = []
    for row in rows:
        if not row.types and not row.defined:
            # Documented and nothing else: there is no declaration to render,
            # and the documentation reaches a reader through get-doc already.
            continue
        name = python_name(row.name)
        if name is None or name in taken:
            unspellable.append(row.name)
            continue
        taken.add(name)
        spelled.append((row, name))
    # The types first, in the order the space declares them, then everything
    # that can mention them. A stub resolves its own forward references, so
    # this is for whoever reads the file rather than for the checker.
    for row, name in sorted(spelled, key=lambda pair: not pair[0].is_type):
        if row.is_type:
            body.extend(_render_type(row, name, projection))
        elif row.arrows or row.defined:
            body.extend(
                _render_function(row, name, projection, proposals.get(row.name, []))
            )
        else:
            # Declared as a plain type of something, `(: pi Number)`: a value,
            # not a head, and a value's stub declaration is its annotation.
            body.extend((f"{name}: {projection.annotation(row.types[0])}", ""))
        exported.append(name)
    lines = _module_documentation(named, str(getattr(space, "name", space)))
    imports = _import_lines(projection.needs)
    if imports:
        lines.extend([*imports, ""])
    lines.append("__all__ = [")
    lines.extend(f'    "{name}",' for name in sorted(exported))
    lines.extend(["]", ""])
    lines.extend(body)
    if unspellable:
        lines.extend((
            "# Heads whose MeTTa names Python cannot spell as identifiers, or that",
            '# collide once spelled. Reach each one with m.fn["<name>"]:',
        ))
        lines.extend(f"#   {head}" for head in sorted(unspellable))
    return "\n".join(lines).rstrip("\n") + "\n"

# Resolve annotations after definitions so peer imports can finish.
import collections.abc as _collections_abc  # noqa: E402 -- deferred annotation bindings

from metta._lazy import lazy  # noqa: E402 -- deferred annotation bindings

if TYPE_CHECKING:
    import metta as _root
else:
    _root = lazy('metta')
