"""Purpose: project Python callable and record documentation into portable
``@doc`` atoms, including kinds, types, descriptions, and MeTTa doctests.
Assumes: structured callable prose uses Google docstring sections; examples
  intended for MeTTa start with ``!(`` and answer with a Python literal.
Guarantees:
  - docstring-parser owns Google section parsing while signature order owns
    positional ``@param`` order [tested:
    test_a_docstring_emits_the_whole_doc_vocabulary; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - annotations project through ``metta_type_for`` and missing annotations stay
    explicit as ``%Undefined%`` [tested:
    test_a_docstring_emits_the_whole_doc_vocabulary; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
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

from ._type_annotations import metta_type_for
from .atoms import Expression, S, _expr, parse

DocstringStyle = _docstring_parser.DocstringStyle
parse_docstring = _docstring_parser.parse

__all__ = ["attribute_docstrings", "documentation_atom"]


def _signature(source: object) -> inspect.Signature | None:
    if not callable(source):
        return None
    try:
        return inspect.signature(source)
    except (TypeError, ValueError):
        return None


def _description(text: str | None) -> Expression:
    return _expr(S["@desc"], " ".join((text or "").split()))


def _type(annotation: Any) -> Expression:
    return _expr(S["@type"], S[metta_type_for(annotation)])


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
    parameters: Sequence[str] | None = None,
    annotations: Mapping[str, Any] | None = None,
    parameter_descriptions: Mapping[str, str] | None = None,
) -> Expression | None:
    """Return one complete portable ``@doc`` atom for ``source``."""
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
        signature.return_annotation
        if signature is not None
        else (annotations or {}).get("return", inspect.Parameter.empty)
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
