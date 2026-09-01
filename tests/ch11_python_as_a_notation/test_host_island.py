"""Purpose: prove ``py(expr)`` is the explicit inline host boundary.
Guarantees:
  - ordinary Python sees an identity while compiled definitions execute the
    enclosed host expression once per engine application [tested:
    test_py_is_identity_outside_a_compiled_body,
    test_py_host_island_executes_per_engine_application; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - exact marker identity prevents a parameter named ``py`` from silently
    becoming a host crossing [tested:
    test_a_shadowed_py_name_remains_an_engine_callee; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - for, while, and comprehension crossings each produce one loop lint
    finding while a crossing outside them does not [tested:
    test_py_host_island_inside_loops_emits_exact_findings; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - an unmarked host callee islands implicitly: nothing runs at compile
    time and the author's own call runs per application [tested:
    test_unknown_host_callee_islands_implicitly; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - nested Python scopes inside an island see the compiled locals supplied at
    application time [tested:
    test_host_island_nested_scopes_see_compiled_locals; commit=WORKTREE]
"""  # noqa: D205, D415  -- the test contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from pathlib import Path

import pytest

from metta import Expression, Grounded, S, py
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


def test_unknown_host_callee_islands_implicitly(m):
    """An unknown host call compiles to an island, never touched at compile.

    The refusal was the old law; under the fallback law the whole call
    islands, exactly as py(...) would spell it, so the author's own
    Python runs at application time and nothing runs at compile time.
    """
    _UNKNOWN_CLIENT.calls = 0

    @m.define
    def implicit_host_call(url):
        return _UNKNOWN_CLIENT.get(url).status_code

    assert _UNKNOWN_CLIENT.calls == 0
    assert m.is_function_here("implicit-host-call") is True
    # The eager door commits per answer; the lazy cursor's resumed redo
    # re-runs effectful bodies today, which
    # test_a_lazy_drain_runs_an_effectful_island_once pins as the open
    # defect in ch18's cursor suite.
    assert m.eval(S["implicit-host-call"]("https://example.test")) == [204]
    assert _UNKNOWN_CLIENT.calls == 1


def test_host_island_nested_scopes_see_compiled_locals(m):
    """Generator and lambda frames resolve the island's runtime bindings."""
    @m.define
    def island_generator(values):
        return py(tuple(value * 2 for value in values))

    @m.define
    def island_lambda(value):
        return py((lambda: value + 1)())  # noqa: PLC3002 -- the nested scope is the scenario

    assert list(island_generator((1, 2, 3))) == [Expression(2, 4, 6)]
    assert list(island_lambda(41)) == [42]
