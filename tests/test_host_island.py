"""Purpose: prove ``py(expr)`` is the explicit inline host boundary.
Guarantees:
  - ordinary Python sees an identity while compiled definitions execute the
    enclosed host expression once per engine application [tested:
    test_py_is_identity_outside_a_compiled_body,
    test_py_host_island_executes_per_engine_application; commit=WORKTREE]
  - exact marker identity prevents a parameter named ``py`` from silently
    becoming a host crossing [tested:
    test_a_shadowed_py_name_remains_an_engine_callee; commit=WORKTREE]
  - for, while, and comprehension crossings each produce one loop lint
    finding while a crossing outside them does not [tested:
    test_py_host_island_inside_loops_emits_exact_findings; commit=WORKTREE]
  - an unmarked host callee refuses before registration with a file/caret span
    and both public remedies [tested:
    test_unknown_host_callee_refusal_has_file_caret_and_both_remedies;
    commit=WORKTREE]
"""  # noqa: D205, D415  -- the test contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from pathlib import Path

import pytest

from metta import Expression, Grounded, py
from metta.errors import CompileError
from metta.vocabularies import EffectClass


class _Response:
    status_code = 204


class _UnregisteredClient:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, _url: str) -> _Response:
        self.calls += 1
        return _Response()


_UNKNOWN_CLIENT = _UnregisteredClient()


@pytest.fixture()
def m(metta):
    """Give each test an isolated native space."""
    with metta._new_space() as isolated:
        yield isolated


def test_py_is_identity_outside_a_compiled_body():
    """The visible marker changes nothing in ordinary Python execution."""
    marker = object()
    assert py(marker) is marker


def test_py_host_island_executes_per_engine_application(m):
    """Decoration is inert; each equation application crosses exactly once."""
    calls: list[int] = []
    factor = 3

    def host(value: int) -> int:
        calls.append(value)
        return value * factor

    island = py

    @m.define
    def island_triple(value):
        return island(host(value))

    assert calls == []
    assert island_triple.facts.effect is EffectClass.oracleIO
    assert m.run("!(island-triple 4)") == [[12]]
    assert m.run("!(island-triple 5)") == [[15]]
    assert calls == [4, 5]
    assert island_triple.py(6) == 18
    assert calls == [4, 5, 6]


def test_a_shadowed_py_name_remains_an_engine_callee(m):
    """Spelling alone is insufficient: only the exported callable marks an island."""
    @m.define
    def shadowed_py(py, value):
        return py(value)

    assert str(shadowed_py.body) == "($py $value)"
    assert not any(finding.kind == "host-island-in-loop" for finding in m.lint())


def test_py_host_island_inside_loops_emits_exact_findings(m):
    """For, while, and comprehensions warn; a one-shot island stays silent."""
    def host(value):
        return value * 2

    @m.define
    def outside_loop(value):
        return py(host(value))

    @m.define
    def for_loop(values):
        total = 0
        for value in values:
            total += py(host(value))
        return total

    @m.define
    def while_loop(value):
        while py(host(value) > 0):
            value -= 2
        return value

    @m.define
    def comprehension_loop(values):
        return [py(host(value)) for value in values]

    assert outside_loop(3) == [6]
    assert for_loop([1, 2, 3]) == [12]
    assert while_loop(2) == [0]
    assert comprehension_loop([1, 2]) == [Expression([Grounded(2), Grounded(4)])]

    findings = [
        finding for finding in m.lint() if finding.kind == "host-island-in-loop"
    ]
    assert len(findings) == 3
    assert {finding.subject for finding in findings} == {
        "py(host(value))",
        "py(host(value) > 0)",
    }
    assert sum(finding.subject == "py(host(value))" for finding in findings) == 2
    assert all(finding.severity == "warning" for finding in findings)
    assert all(
        finding.payload
        and finding.payload["file"] == str(Path(__file__).resolve())
        for finding in findings
    )
    assert all(finding.payload and finding.payload["line"] > 0 for finding in findings)


def test_unknown_host_callee_refusal_has_file_caret_and_both_remedies(m):
    """The refusal is located and teaches both named and inline crossings."""
    _UNKNOWN_CLIENT.calls = 0
    with pytest.raises(CompileError) as caught:

        @m.define
        def implicit_host_call(url):
            return _UNKNOWN_CLIENT.get(url).status_code

    message = str(caught.value)
    assert "refused: `_UNKNOWN_CLIENT.get(url)` is an unknown callee" in message
    assert f"--> {Path(__file__).resolve()}:" in message
    assert "^" in message
    assert "not a parameter, a known function, or a data constructor" in message
    assert '@metta.op(effect="oracleIO")' in message
    assert "py(_UNKNOWN_CLIENT.get(url).status_code)" in message
    assert _UNKNOWN_CLIENT.calls == 0
    assert m.is_function_here("implicit-host-call") is False
