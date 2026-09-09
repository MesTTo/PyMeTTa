"""Purpose: discriminate source-derived door orders from plausible integers.

Guarantees: aliases, helper calls, native crossings, open callbacks and SCCs
have independent witnesses [tested: this file; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from textwrap import dedent

from hypothesis import given
from hypothesis import strategies as st

from metta.doors import AnswersAs, Sugar
from metta.doors._analysis import Calls
from metta.doors._order import analyse, components, derive
from metta.doors._scan import scan

MARK = "@door(Kind.query, answers=AnswersAs.value, effect=EffectClass.pureStructural, determinism=Determinism.det, tiers=(Tier.sync,), evidence=('fixture',))"
RUNTIME = "class Runtime:\n    def __init__(self):\n        pass\n    def must(self, goal: str) -> int:\n        return 1\n"


def _program(tmp_path, body, *, module="example"):
    source = dedent(body).replace("@marked", MARK)
    path = tmp_path / "example.py"
    path.write_text(source)
    rows = scan(path, module)
    sources = {module: source, "metta._binding.runtime": RUNTIME}
    return rows, analyse(rows, sources)


def test_door_order_follows_aliases_and_helpers(tmp_path):
    """An imported receiver and a helper alias retain the actual callee."""
    _, result = _program(tmp_path, '''
        from metta._binding.runtime import Runtime as Engine
        class Space:
            def __init__(self):
                self._rt = Engine()
            @marked
            def first(self) -> int:
                """Read one engine value."""
                return self._rt.must("value")
            @marked
            def second(self) -> int:
                """Compose the first door through a helper alias."""
                operation = helper
                return operation(self)
        def helper(receiver: Space) -> int:
            call = receiver.first
            return call()
    ''')
    assert result["space:first"].number == 1
    assert result["space:second"].number == 2
    assert result["space:second"].calls == {"space:first"}
    assert not result["space:second"].native


def test_door_order_keeps_mixed_crossings_as_findings(tmp_path):
    """Adding a local crossing to a composition removes its integer order."""
    _, result = _program(tmp_path, '''
        from metta._binding.runtime import Runtime
        class Space:
            def __init__(self):
                self._rt = Runtime()
            @marked
            def first(self) -> int:
                """Read a value."""
                return self._rt.must("value")
            @marked
            def mixed(self) -> int:
                """Cross and compose."""
                self._rt.must("write")
                return self.first()
    ''')
    value = result["space:mixed"]
    assert value.number is None
    assert value.mixed
    assert value.calls == {"space:first"}
    assert value.native


def test_sugar_equivalence_is_an_edge_only_when_it_supplies_the_implementation(tmp_path):
    """An independent implementation does not call its documented longhand."""
    rows, _ = _program(tmp_path, '''
        class Space:
            @marked
            def first(self) -> int:
                """Return a host value."""
                return 1
            @marked
            def equivalent(self) -> int:
                """Compute the same host value independently."""
                return 1
    ''')
    rows = tuple(replace(row, sugar_of=Sugar("space:first", ())) if row.python == "equivalent"
                 else row for row in rows)
    sources = {"example": (tmp_path / "example.py").read_text()}
    independent = analyse(rows, sources)["space:equivalent"]
    assert independent.number == 0
    assert not independent.calls
    forwarding = analyse(tuple(replace(row, body=None) if row.python == "equivalent" else row
                               for row in rows), sources)["space:equivalent"]
    assert forwarding.number == 1
    assert forwarding.calls == {"space:first"}


def test_door_order_retains_unresolved_callbacks(tmp_path):
    """A supplied callable stays open, and its caller stays unnumbered."""
    _, result = _program(tmp_path, '''
        from typing import Callable
        class Space:
            @marked
            def apply(self, callback: Callable) -> int:
                """Invoke the caller's operation."""
                return callback()
            @marked
            def compose(self, callback: Callable) -> int:
                """Compose an open door."""
                return self.apply(callback)
    ''')
    assert result["space:apply"].number is None
    assert any("callback" in site for site in result["space:apply"].open)
    assert result["space:compose"].number is None
    assert result["space:compose"].blocked_by == {"space:apply"}


def test_door_order_resolves_inherited_properties_and_distinguishes_foreign_names(tmp_path):
    """A marked property is a dependency; a foreign same-named method is not."""
    _, result = _program(tmp_path, '''
        from metta._binding.runtime import Runtime
        class Other:
            def first(self) -> int:
                return 3
        class Space:
            def __init__(self):
                self._rt = Runtime()
            @property
            @marked
            def first(self) -> int:
                """Read a value through a property."""
                return self._rt.must("value")
            @marked
            def composed(self) -> int:
                """Read the inherited property."""
                return Child().first
            @marked
            def host(self) -> int:
                """Call a different object's similarly named method."""
                return Other().first()
        class Child(Space):
            pass
    ''')
    assert "space:first" in result["space:composed"].calls
    assert result["space:composed"].mixed  # Construction also crosses Runtime.
    assert result["space:host"].number == 0
    assert not result["space:host"].calls


def test_door_order_keeps_supplied_iterator_open(tmp_path):
    """Iterating an arbitrary supplied source cannot imply a closed order."""
    _, result = _program(tmp_path, '''
        from collections.abc import Iterator
        class Space:
            @marked
            def consume(self, source: Iterator) -> list:
                """Read a source whose implementation belongs to its caller."""
                return list(source)
    ''')
    assert result["space:consume"].number is None
    assert any("__iter__" in site for site in result["space:consume"].open)


def test_wrapper_unwrapping_has_a_finite_abstract_domain(tmp_path):
    """Repeated wrapper attributes become one open value instead of growing names."""
    _, result = _program(tmp_path, '''
        from functools import reduce
        class Space:
            @marked
            def unwrap(self) -> int:
                """Follow an externally supplied wrapper chain."""
                function = reduce
                while hasattr(function, "__wrapped__"):
                    function = function.__wrapped__
                return function()
    ''')
    assert result["space:unwrap"].number is None
    assert any("external value" in site for site in result["space:unwrap"].open)


def test_bounded_type_variables_and_nullable_native_receivers(tmp_path):
    """A bound type variable and a None fallback preserve the native receiver."""
    _, result = _program(tmp_path, '''
        from typing import TypeVar
        from metta._binding.runtime import Runtime
        class Space:
            def __init__(self, runtime: Runtime | None = None):
                self._rt = Runtime() if runtime is None else runtime
            @marked
            def first(self) -> int:
                """Read the selected runtime."""
                return self._rt.must("value")
            @marked
            def second(self) -> int:
                """Compose through a bounded helper."""
                return helper(self)
        T = TypeVar("T", bound="Space")
        def helper(value: T) -> int:
            return value.first()
    ''')
    assert result["space:first"].number == 1
    assert result["space:second"].number == 2


def test_owned_generator_context_and_stdlib_state_keep_their_actual_boundary(tmp_path):
    """An owned generator context is resolved through its body, not its annotation."""
    _, result = _program(tmp_path, '''
        from collections.abc import Iterator
        from contextlib import contextmanager
        from contextvars import ContextVar
        from metta._binding.runtime import Runtime
        active: ContextVar[int] = ContextVar("active", default=0)
        @contextmanager
        def scoped() -> Iterator[None]:
            token = active.set(1)
            try:
                yield
            finally:
                active.reset(token)
        class Space:
            def __init__(self):
                self._rt = Runtime()
            @marked
            def first(self) -> int:
                """Cross while the host context is selected."""
                with scoped():
                    return self._rt.must("value")
    ''')
    assert result["space:first"].number == 1


def test_isinstance_selects_the_receiver_before_reading_its_runtime(tmp_path):
    """A union's string alternative cannot acquire the space's runtime field."""
    _, result = _program(tmp_path, '''
        from metta._binding.runtime import Runtime
        class Space:
            def __init__(self, other: Space | str | None = None):
                if isinstance(other, Space):
                    self._rt = other._rt
                else:
                    self._rt = Runtime()
            @marked
            def first(self) -> int:
                """Read the selected runtime."""
                return self._rt.must("value")
    ''')
    assert result["space:first"].number == 1
    assert not result["space:first"].open


def test_returning_the_receiver_does_not_reenter_its_protocol(tmp_path):
    """Returning a borrowed iterator does not create a recursive call edge."""
    rows, _ = _program(tmp_path, '''
        class Space:
            @marked
            def identity(self) -> Space:
                """Return this existing receiver."""
                return self
    ''')
    assert rows[0].python == "identity"
    result = analyse(tuple(replace(row, answers=AnswersAs.stream) for row in rows),
                     {"example": (tmp_path / "example.py").read_text()})
    assert result["space:identity"].number == 0


def test_door_order_reports_recursion_before_longest_paths(tmp_path):
    """Every member and caller of a recursive component is unnumbered."""
    _, result = _program(tmp_path, '''
        class Space:
            @marked
            def first(self) -> int:
                """Call the other door."""
                return self.second()
            @marked
            def second(self) -> int:
                """Close the recursive component."""
                return self.first()
            @marked
            def caller(self) -> int:
                """Reach the recursive component."""
                return self.first()
    ''')
    assert result["space:first"].cycles == (("space:first", "space:second"),)
    assert result["space:second"].cycles == result["space:first"].cycles
    assert result["space:caller"].blocked_by == {"space:first"}
    assert all(value.number is None for value in result.values())


@given(st.sets(st.tuples(st.integers(0, 8), st.integers(0, 8))))
def test_components_equal_mutual_reachability(edges):
    """SCC membership agrees with an independent reachability oracle."""
    graph = {str(node): {str(right) for left, right in edges if left == node} for node in range(9)}
    reached = {}
    for node in graph:
        pending, seen = [node], {node}
        while pending:
            for target in graph[pending.pop()] - seen:
                seen.add(target)
                pending.append(target)
        reached[node] = seen
    actual = {node: frozenset(group) for group in components(graph) for node in group}
    for node in graph:
        assert actual[node] == {other for other in graph if other in reached[node] and node in reached[other]}


def test_components_have_no_python_recursion_depth_limit():
    """A long chain and a long cycle require no recursive Python traversal."""
    graph = {str(index): {str(index + 1)} for index in range(5000)}
    assert len(components(graph)) == 5001
    graph["5000"] = {"0"}
    assert len(components(graph)) == 1


def test_binding_metadata_and_open_helper_cycles_are_independent(tmp_path):
    """A native declaration cannot hide an unmarked recursive helper."""
    rows, _ = _program(tmp_path, '''
        class Space:
            @marked
            def first(self) -> int:
                """Return a host constant."""
                return 1
    ''')
    graph = {
        "example.Space.first": Calls(targets=frozenset({"helper"})),
        "helper": Calls(targets=frozenset({"helper"}), native=frozenset({"Runtime.must"})),
    }
    result = derive(rows, graph)["space:first"]
    assert result.number is None
    assert result.cycles == (("helper",),)
    assert result.native == {"Runtime.must"}


def test_door_order_report_is_not_a_gate(monkeypatch, capsys):
    """Mixed and open findings print without failing the report lane."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    import doororder

    monkeypatch.setattr(doororder, "report", lambda: {"mixed": ["space:eval"], "rows": {}})
    assert doororder.main([]) == 0
    assert "space:eval" in capsys.readouterr().out
