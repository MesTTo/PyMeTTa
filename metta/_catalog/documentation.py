"""Purpose: project Python callable and record documentation into portable
``@doc`` atoms, including kinds, types, descriptions, and MeTTa doctests.
Assumes: structured callable prose uses Google docstring sections; examples
  intended for MeTTa start with ``!(`` and answer with a Python literal.
Guarantees:
  - a caller may supply the prose to read, so a face that has already read a
    C function's docstring signature does not publish that line as the
    description [tested: test_a_face_documents_what_the_docstring_says;
    commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
  - a caller supplying annotations supplies the RETURN through the same
    mapping, so a reader that resolved a postponed annotation does not have
    its parameters honoured and its result read back off the raw signature
    [tested: test_a_face_documents_what_the_docstring_says; commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
  - docstring-parser owns Google section parsing while signature order owns
    positional ``@param`` order [tested:
    test_a_docstring_emits_the_whole_doc_vocabulary; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - annotations project through ``metta_type_for`` and missing annotations stay
    explicit as ``%Undefined%`` [tested:
    test_a_docstring_emits_the_whole_doc_vocabulary; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - typing.no_type_check keeps syntax-only compiler annotations out of both
    declarations and portable documentation [tested:
    test_no_type_check_keeps_annotations_as_a_compile_proof_only;
    commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301]
  - adjacent attribute docstrings become record-field descriptions [tested:
    test_record_attribute_docstrings_describe_parameters; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
Fails when: a MeTTa doctest expectation is not a Python literal. Emission
  refuses it rather than publishing a different example than the author wrote.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import doctest
import inspect
import textwrap
from collections.abc import Mapping, Sequence
from typing import Any

# The runtime dependency does not publish typing metadata.
import docstring_parser as _docstring_parser  # type: ignore[import-not-found]

from metta._atoms.factories import Atom, Expression, S, _expr, parse
from metta._catalog.annotations import metta_type_for

DocstringStyle = _docstring_parser.DocstringStyle
parse_docstring = _docstring_parser.parse

#: Every Google section title the parser knows, read from the parser rather
#: than listed here, so a section it learns to read is a section this stops
#: swallowing into a summary.
_SECTION_TITLES = frozenset(
    f"{section.title}:" for section in _docstring_parser.google.DEFAULT_SECTIONS
)

__all__ = ["attribute_docstrings", "documentation_atom", "first_paragraph"]


def first_paragraph(documentation: str) -> str:
    """One docstring with its opening paragraph joined into a single line.

    The parser reads a summary as the first LINE when no blank line follows
    it, so a sentence a module wrapped at eighty columns arrives cut in half:
    torch's `zeros` summary ends at "with the shape defined". Joining the
    paragraph puts the sentence back before the parse, and the paragraph ends
    where the docstring's own structure does -- a blank line, or one of the
    parser's section titles -- so nothing below it is drawn into the summary.
    """
    lines = documentation.splitlines()
    opening: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped in _SECTION_TITLES:
            return "\n".join([" ".join(opening), *lines[index:]])
        opening.append(stripped)
    return " ".join(opening)


def _signature(source: object) -> inspect.Signature | None:
    if not callable(source):
        return None
    try:
        signature = inspect.signature(source)
    except (TypeError, ValueError):
        return None
    if not getattr(source, "__no_type_check__", False):
        return signature
    return signature.replace(
        parameters=[
            parameter.replace(annotation=inspect.Parameter.empty)
            for parameter in signature.parameters.values()
        ],
        return_annotation=inspect.Signature.empty,
    )


def _description(text: str | None) -> Expression:
    return _expr(S["@desc"], " ".join((text or "").split()))


def _type(annotation: Any) -> Expression:
    # An ATOM in annotation position is the type itself rather than a Python
    # name for one, so it travels into the doc as written; everything else
    # keeps the scalar name the table reports.
    named = annotation if isinstance(annotation, Atom) else S[metta_type_for(annotation)]
    return _expr(S["@type"], named)


def _parameters(
    source: object,
    described: Mapping[str, str],
    *,
    names: Sequence[str] | None,
    annotations: Mapping[str, Any] | None,
) -> Expression | None:
    signature = _signature(source)
    if names is None:
        if signature is None:
            return None
        parameters = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.name != "self"
            and parameter.kind is not inspect.Parameter.VAR_KEYWORD
        ]
    else:
        annotations = annotations or {}
        parameters = [
            inspect.Parameter(
                name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=annotations.get(name, inspect.Parameter.empty),
            )
            for name in names
        ]
    if not parameters:
        return None
    entries = [
        _expr(
            S["@param"],
            _type(parameter.annotation),
            _description(described.get(parameter.name)),
        )
        for parameter in parameters
    ]
    return _expr(S["@params"], _expr(*entries))


def _examples(documentation: str) -> list[Expression]:
    emitted: list[Expression] = []
    for example in doctest.DocTestParser().get_examples(documentation):
        source = example.source.strip()
        if not source.startswith("!("):
            continue
        call = parse(source[1:])
        try:
            expected = ast.literal_eval(example.want.strip())
        except (SyntaxError, ValueError) as exc:
            msg = f"MeTTa doctest {source!r} must answer with a Python literal"
            raise ValueError(msg) from exc
        answers = expected if isinstance(expected, (list, tuple)) else [expected]
        emitted.append(_expr(S["@example"], call, _expr(*answers)))
    return emitted


def documentation_atom(
    name: str,
    source: object,
    *,
    kind: str,
    documentation: str | None = None,
    parameters: Sequence[str] | None = None,
    annotations: Mapping[str, Any] | None = None,
    parameter_descriptions: Mapping[str, str] | None = None,
) -> Expression | None:
    """Return one complete portable ``@doc`` atom for ``source``.

    ``documentation`` is the prose to read instead of the source's own
    docstring, for a caller that has already taken something out of it: a C
    function states its SIGNATURE in the docstring's first lines, and a face
    that has read those lines as the signature would otherwise publish them
    again as the description.
    """
    if documentation is None:
        documentation = inspect.getdoc(source)
    if not documentation:
        return None
    parsed = parse_docstring(documentation, style=DocstringStyle.GOOGLE)
    described = {item.arg_name: item.description or "" for item in parsed.params}
    described.update(parameter_descriptions or {})
    fields: list[Any] = [
        _expr(S["@kind"], S[kind]),
        _description(parsed.short_description or documentation),
    ]
    params = _parameters(
        source,
        described,
        names=parameters,
        annotations=annotations,
    )
    if params is not None:
        fields.append(params)

    signature = _signature(source)
    return_annotation = (
        annotations["return"]
        if annotations is not None and "return" in annotations
        else signature.return_annotation
        if signature is not None
        else inspect.Parameter.empty
    )
    if kind != "record" and (
        parsed.returns is not None or return_annotation is not inspect.Parameter.empty
    ):
        fields.append(
            _expr(
                S["@return"],
                _type(return_annotation),
                _description(parsed.returns.description if parsed.returns else None),
            )
        )
    fields.extend(_examples(documentation))
    return _expr(S["@doc"], S[name], *fields)


def attribute_docstrings(target: type) -> dict[str, str]:
    """Read string literals immediately following annotated class fields."""
    try:
        source = textwrap.dedent(inspect.getsource(target))
    except (OSError, TypeError):
        return {}
    tree = ast.parse(source)
    class_node = next(
        (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)),
        None,
    )
    if class_node is None:
        return {}
    found: dict[str, str] = {}
    for declaration, prose in zip(class_node.body, class_node.body[1:], strict=False):
        if (
            isinstance(declaration, ast.AnnAssign)
            and isinstance(declaration.target, ast.Name)
            and isinstance(prose, ast.Expr)
            and isinstance(prose.value, ast.Constant)
            and isinstance(prose.value.value, str)
        ):
            found[declaration.target.id] = inspect.cleandoc(prose.value.value)
    return found
