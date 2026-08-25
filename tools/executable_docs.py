"""Purpose: check adjacent emitted-MeTTa and shown-output comments by source span.

Assumes:
  - an executable claim calls ``claim(label, emitted, execute)`` and places one
    ``# ->`` translation plus one or more ``# =>`` answers immediately after
    that call; ``# => <none>`` is the empty multiset
  - ``execute`` receives the exact emitted atom, so the output check observes
    execution of the term whose translation comment was checked
Guarantees:
  - Python token positions, rather than text search, bind comments to the call
    they document; missing, duplicate, unmappable, or drifting comments fail loudly
    [tested: test_source_spans_bind_translation_and_output_comments_to_one_call,
    test_unmappable_checked_comment_is_rejected,
    test_translation_drift_is_rejected,
    test_shown_output_drift_is_rejected; commit=WORKTREE]
  - emitted ``@example`` atoms run through both the owning MeTTa space and the
    compiled function's Python twin, comparing all three answer bags with the
    twins lane's alpha-equivalent multiset relation
    [tested: test_emitted_doctests_run_in_both_languages_as_alpha_multisets;
    commit=WORKTREE]
Fails when: a claim cannot be mapped to adjacent comments, an answer drifts,
  or a documented call cannot be executed in either language.
"""

from __future__ import annotations

import ast
import io
import sys
import tokenize
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import twin_coverage

from metta._documentation import documentation_atom
from metta.atoms import (
    Atom,
    Expression,
    Grounded,
    S,
    Symbol,
    _decode,
    _encode,
    parse,
)

TRANSLATION = "# ->"
OUTPUT = "# =>"
NO_OUTPUT = "<none>"


class DocumentationDriftError(AssertionError):
    """A checked source comment no longer describes its executable claim."""


def _drift(message: str) -> DocumentationDriftError:
    """Build one documentation failure without hiding its exact diagnostic."""
    return DocumentationDriftError(message)


@dataclass(frozen=True, slots=True)
class SourceExpectation:
    """The comments attached to one ``claim`` call's exact source span."""

    path: Path
    start: int
    end: int
    emitted: Atom
    answers: tuple[Atom, ...]


def _is_claim(call: ast.Call) -> bool:
    function = call.func
    return (isinstance(function, ast.Name) and function.id == "claim") or (
        isinstance(function, ast.Attribute) and function.attr == "claim"
    )


def _comments(source: str) -> tuple[dict[int, str], dict[int, str]]:
    """Return full-line comments and every checked marker token by line."""
    lines = source.splitlines()
    full_line: dict[int, str] = {}
    checked: dict[int, str] = {}
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        row, column = token.start
        comment = token.string.strip()
        if any(
            comment == marker or comment.startswith(f"{marker} ")
            for marker in (TRANSLATION, OUTPUT)
        ):
            checked[row] = comment
        if lines[row - 1][:column].strip():
            continue
        full_line[row] = comment
    return full_line, checked


def _payload(comment: str, marker: str, *, path: Path, line: int) -> str:
    payload = comment.removeprefix(marker).strip()
    if payload:
        return payload
    message = f"{path}:{line}: {marker} needs a MeTTa value"
    raise _drift(message)


def _marked(comment: str, marker: str) -> bool:
    """Require a complete marker token rather than an accidental prefix."""
    return comment == marker or comment.startswith(f"{marker} ")


@lru_cache(maxsize=64)
def _parse_expectations(path_text: str, source: str) -> tuple[SourceExpectation, ...]:
    path = Path(path_text)
    try:
        tree = ast.parse(source, filename=path_text)
    except SyntaxError as error:
        message = f"{path}:{error.lineno}: source does not parse: {error.msg}"
        raise _drift(message) from error
    comments, checked_comments = _comments(source)
    calls = sorted(
        (node for node in ast.walk(tree) if isinstance(node, ast.Call) and _is_claim(node)),
        key=lambda node: (node.lineno, node.col_offset),
    )
    seen_spans: set[tuple[int, int]] = set()
    consumed_comments: set[int] = set()
    expectations: list[SourceExpectation] = []
    for call in calls:
        end = call.end_lineno or call.lineno
        span = (call.lineno, end)
        if span in seen_spans:
            message = f"{path}:{call.lineno}: two claim calls share one source span"
            raise _drift(message)
        seen_spans.add(span)
        line = end + 1
        translation = comments.get(line)
        if translation is None or not _marked(translation, TRANSLATION):
            message = f"{path}:{call.lineno}: claim needs an adjacent {TRANSLATION} comment"
            raise _drift(message)
        consumed_comments.add(line)
        try:
            emitted = parse(_payload(translation, TRANSLATION, path=path, line=line))
        except Exception as error:
            if isinstance(error, DocumentationDriftError):
                raise
            message = f"{path}:{line}: translation comment is not one MeTTa atom: {error}"
            raise _drift(message) from error

        line += 1
        output_comments: list[tuple[int, str]] = []
        while (comment := comments.get(line)) is not None and _marked(comment, OUTPUT):
            output_comments.append((line, comment))
            line += 1
        if not output_comments:
            message = f"{path}:{call.lineno}: claim needs an adjacent {OUTPUT} output comment"
            raise _drift(message)
        consumed_comments.update(comment_line for comment_line, _ in output_comments)
        payloads = [
            _payload(comment, OUTPUT, path=path, line=comment_line)
            for comment_line, comment in output_comments
        ]
        if NO_OUTPUT in payloads:
            if payloads != [NO_OUTPUT]:
                message = f"{path}:{output_comments[0][0]}: {NO_OUTPUT} must be the sole output"
                raise _drift(message)
            answers: tuple[Atom, ...] = ()
        else:
            try:
                answers = tuple(parse(payload) for payload in payloads)
            except Exception as error:
                message = (
                    f"{path}:{output_comments[0][0]}: output comment is not one MeTTa atom: {error}"
                )
                raise _drift(message) from error
        expectations.append(SourceExpectation(path, call.lineno, end, emitted, answers))
    if unmappable := sorted(set(checked_comments) - consumed_comments):
        line = unmappable[0]
        message = (
            f"{path}:{line}: checked comment {checked_comments[line]!r} is not attached "
            "to a claim source span"
        )
        raise _drift(message)
    return tuple(expectations)


def source_expectations(path: str | Path) -> tuple[SourceExpectation, ...]:
    """Read all checked claims in one Python source file."""
    resolved = Path(path).resolve()
    with tokenize.open(resolved) as stream:
        source = stream.read()
    return _parse_expectations(str(resolved), source)


def expectation_at(path: str | Path, line: int) -> SourceExpectation:
    """Find the one checked call whose span contains ``line``."""
    matches = [
        expectation
        for expectation in source_expectations(path)
        if expectation.start <= line <= expectation.end
    ]
    if len(matches) != 1:
        message = (
            f"{Path(path).resolve()}:{line}: runtime claim maps to {len(matches)} source spans"
        )
        raise _drift(message)
    return matches[0]


def _answer_atoms(value: Any) -> list[Atom]:
    if value is None:
        return []
    if isinstance(value, Atom):
        return [value]
    if isinstance(value, (str, bytes, bytearray)):
        return [_encode(value)]
    if isinstance(value, Iterable):
        return [_encode(item) for item in value]
    return [_encode(value)]


def _render(values: Iterable[Atom]) -> str:
    return "[" + ", ".join(sorted(str(value) for value in values)) + "]"


def _assert_same(
    expected: Iterable[object],
    actual: Iterable[object],
    *,
    location: str,
    subject: str,
) -> None:
    expected_list = list(expected)
    actual_list = list(actual)
    expected_only, actual_only = twin_coverage.answer_multiset_diff(expected_list, actual_list)
    if expected_only or actual_only:
        message = (
            f"{location}: {subject} drift: comment={_render(_answer_atoms(expected_list))} "
            f"actual={_render(_answer_atoms(actual_list))}; "
            f"missing={_render(expected_only)} extra={_render(actual_only)}"
        )
        raise _drift(message)


def verify_claim(
    emitted: object,
    execute: Callable[[Atom], Any],
    *,
    path: str | Path,
    line: int,
) -> tuple[Atom, ...]:
    """Execute one emitted term and check its adjacent source comments."""
    expectation = expectation_at(path, line)
    actual_emitted = _encode(emitted)
    location = f"{expectation.path}:{expectation.start}"
    _assert_same(
        [expectation.emitted],
        [actual_emitted],
        location=location,
        subject="emitted MeTTa",
    )
    actual_answers = tuple(_answer_atoms(execute(actual_emitted)))
    _assert_same(
        expectation.answers,
        actual_answers,
        location=location,
        subject="shown output",
    )
    return actual_answers


def render_answers(values: Iterable[Atom]) -> str:
    """Render one answer multiset deterministically for gallery stdout."""
    return _render(values)


def _examples(documentation: Expression) -> tuple[tuple[Atom, tuple[Atom, ...]], ...]:
    return tuple(
        (field.children[1], tuple(field.children[2].children))
        for field in documentation.children[2:]
        if (
            isinstance(field, Expression)
            and len(field.children) == 3
            and field.children[0] == S["@example"]
            and isinstance(field.children[2], Expression)
        )
    )


def _python_argument(atom: Atom) -> Any:
    return _decode(atom) if isinstance(atom, Grounded) else atom


def verify_defined_examples(defined: Any) -> int:
    """Run every emitted doctest through a Defined's MeTTa and Python sides."""
    documentation = documentation_atom(
        defined.name,
        defined.py,
        kind="function",
    )
    if documentation is None:
        message = f"{defined.name}: definition emits no @doc atom"
        raise _drift(message)
    if documentation not in defined.space.atoms():
        message = f"{defined.name}: emitted @doc atom is not installed in {defined.space.name}"
        raise _drift(message)
    examples = _examples(documentation)
    if not examples:
        message = f"{defined.name}: @doc atom emits no @example"
        raise _drift(message)
    for call, expected in examples:
        if (
            not isinstance(call, Expression)
            or not call.children
            or call.children[0] != Symbol(defined.name)
        ):
            message = f"{defined.name}: @example call {call} does not call its documented function"
            raise _drift(message)
        arguments = [_python_argument(argument) for argument in call.children[1:]]
        engine_answers = _answer_atoms(defined.space.eval(call))
        python_answers = _answer_atoms(defined.py(*arguments))
        location = f"{defined.name} @example {call}"
        _assert_same(expected, engine_answers, location=location, subject="MeTTa output")
        _assert_same(expected, python_answers, location=location, subject="Python output")
        _assert_same(
            engine_answers,
            python_answers,
            location=location,
            subject="bilingual output",
        )
    return len(examples)


__all__ = [
    "DocumentationDriftError",
    "SourceExpectation",
    "expectation_at",
    "render_answers",
    "source_expectations",
    "verify_claim",
    "verify_defined_examples",
]
