"""Purpose: discriminate source-derived door orders from plausible integers.

Guarantees: aliases, helper calls, native crossings, open callbacks and SCCs
have independent witnesses [tested: this file; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Declared supplied contracts, undeclared operations and dependent verdicts
have independent planted controls [tested: this file; commit=07976cf8b415390449863d803277b73102673b51].
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from textwrap import dedent

import pytest
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


@pytest.mark.parametrize("qualifier", ["Final", "ClassVar", "Annotated"])
def test_declared_mapping_keeps_its_values_through_type_qualifiers(tmp_path, qualifier):
    """A type qualifier cannot replace the mapping declared by its initializer."""
    annotation = f"{qualifier}[Mapping[str, str]" + (", 'description']" if qualifier == "Annotated" else "]")
    _, result = _program(tmp_path, f'''
        from collections.abc import Mapping
        from typing import Annotated, ClassVar, Final
        DISPATCH: {annotation} = {{"read": "table()", "call": "call()"}}
        class Space:
            @marked
            def describe(self, kind: str) -> str:
                """Read a source-declared string table."""
                return DISPATCH[kind].upper()
    ''')
    assert result["space:describe"].number == 0
    assert not result["space:describe"].open


@pytest.mark.parametrize("lookup", ["operations[key]", "operations.get(key, first)"])
def test_declared_callable_mapping_retains_every_door_target(tmp_path, lookup):
    """Runtime keys join the declared callees instead of inventing a host result."""
    _, result = _program(tmp_path, f'''
        from collections.abc import Callable, Mapping
        from typing import Final
        from metta._binding.runtime import Runtime
        class Space:
            @marked
            def first(self) -> int:
                """Cross once."""
                return Runtime().must("first")
            @marked
            def second(self) -> int:
                """Cross once on another path."""
                return Runtime().must("second")
            @marked
            def dispatch(self, key: str) -> int:
                """Select either declared door."""
                first = self.first
                operations: Final[Mapping[str, Callable]] = {{"a": first, "b": self.second}}
                return {lookup}()
    ''')
    assert result["space:dispatch"].calls == {"space:first", "space:second"}
    assert result["space:dispatch"].number == 2
    assert not result["space:dispatch"].native


@pytest.mark.parametrize("mutation", [
    "operations[key] = callback",
    "alias = operations; alias[key] = callback",
    "operations.update({key: callback})",
    "operations.setdefault(key, callback)",
])
def test_mapping_mutation_cannot_hide_a_supplied_callback(tmp_path, mutation):
    """Aliases and mutating calls retain an externally supplied implementation."""
    _, result = _program(tmp_path, f'''
        from typing import Callable, Final
        class Space:
            @marked
            def apply(self, key: str, callback: Callable) -> int:
                """Dispatch a callback inserted into a declared mapping."""
                operations: Final[dict] = {{}}
                {mutation}
                return operations[key]()
    ''')
    assert result["space:apply"].number is None
    assert any("callback" in site for site in result["space:apply"].open)


@pytest.mark.parametrize("operation", ["native", "recursive"])
def test_mapping_dispatch_exposes_planted_native_and_recursive_bodies(tmp_path, operation):
    """A table edge keeps a hidden crossing or recursion visible to the gate."""
    body = 'return Runtime().must("value")' if operation == "native" else 'return operations[key](key)'
    _, result = _program(tmp_path, f'''
        from metta._binding.runtime import Runtime
        def target(key: str) -> int:
            {body}
        operations = {{"call": target}}
        class Space:
            @marked
            def apply(self, key: str) -> int:
                """Dispatch the selected helper."""
                return operations[key](key)
    ''')
    value = result["space:apply"]
    if operation == "native":
        assert value.number == 1
        assert value.native
    else:
        assert value.number is None
        assert value.cycles


def test_tuple_unpacking_retains_each_declared_receiver(tmp_path):
    """Tuple fields retain their own receiver even when the other field differs."""
    _, result = _program(tmp_path, '''
        class First:
            def read(self) -> int:
                return 1
        class Second:
            def write(self) -> int:
                return 2
        class Space:
            @marked
            def pair(self) -> int:
                """Use each member's declared method."""
                first, second = (First(), Second())
                return first.read() + second.write()
    ''')
    assert result["space:pair"].number == 0


def test_sequence_mutation_keeps_callable_targets(tmp_path):
    """A list append cannot erase the door reached through its item."""
    _, result = _program(tmp_path, '''
        from metta._binding.runtime import Runtime
        class Space:
            @marked
            def first(self) -> int:
                """Read one native value."""
                return Runtime().must("value")
            @marked
            def collect(self) -> list:
                """Invoke a declared callback list."""
                operations = []
                operations.append(self.first)
                return [operation() for operation in operations]
    ''')
    assert result["space:collect"].calls == {"space:first"}
    assert result["space:collect"].number == 2


@pytest.mark.parametrize("container, key", [
    ("[42, first]", "1"),
    ("[42, first]", "-1"),
    ("{'data': 42, 'call': first}", "'call'"),
    ("{False: first, 'data': 42}", "0"),
    ("{1.0: first, 'data': 42}", "1"),
])
def test_literal_container_keys_select_the_declared_callable(tmp_path, container, key):
    """A literal key does not acquire an unrelated value or lose equal keys."""
    _, result = _program(tmp_path, f'''
        from metta._binding.runtime import Runtime
        class Space:
            @marked
            def first(self) -> int:
                """Cross once."""
                return Runtime().must("value")
            @marked
            def selected(self) -> int:
                """Read one declared member."""
                first = self.first
                operations = {container}
                return operations[{key}]()
    ''')
    assert result["space:selected"].calls == {"space:first"}
    assert result["space:selected"].number == 2


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


@pytest.mark.parametrize("construction,selection", [
    ("list([self.first])", "operations[0]()"),
    ("tuple([self.first])", "operations[0]()"),
    ("set([self.first])", "[operation() for operation in operations]"),
    ("frozenset([self.first])", "[operation() for operation in operations]"),
    ("dict(first=self.first)", "operations['first']()"),
    ("dict({'first': self.first})", "operations['first']()"),
])
def test_container_constructors_preserve_callable_contents(tmp_path, construction, selection):
    """Copying a declared container cannot erase its callable dependencies."""
    _, result = _program(tmp_path, f'''
        from metta._binding.runtime import Runtime
        class Space:
            @marked
            def first(self) -> int:
                """Cross once."""
                return Runtime().must("value")
            @marked
            def selected(self):
                """Read the copied declaration."""
                operations = {construction}
                return {selection}
    ''')
    assert result["space:selected"].calls == {"space:first"}
    assert result["space:selected"].number == 2


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


def _gate_report(monkeypatch, result):
    """Run the actual report and verdict over one planted source graph."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    import doororder

    monkeypatch.setattr(doororder.doorgen, "all_rows", lambda _root: ())
    monkeypatch.setattr(doororder, "core_paths", lambda _root: ())
    monkeypatch.setattr(doororder, "analyse", lambda *_: result)
    return doororder.report(), doororder.main(["--json"])


def test_registry_callable_is_a_defect_open_boundary(tmp_path, monkeypatch):
    """A registry result has no supplied-parameter contract to close its call."""
    _, result = _program(tmp_path, '''
        from plugins import registry
        class Space:
            @marked
            def selected(self):
                """Invoke the current plugin."""
                operations = {"current": registry.get("current")}
                return operations["current"]()
    ''')
    assert result["space:selected"].number is None
    report, status = _gate_report(monkeypatch, result)
    assert status == 1
    assert report["open_dependencies"] == ["space:selected"]
    assert report["defect_open_dependencies"] == ["space:selected"]
    assert report["unordered_by_contract"] == []


def test_supplied_callable_with_native_crossing_is_mixed(tmp_path, monkeypatch):
    """An open callback cannot hide a native crossing in the same body."""
    _, result = _program(tmp_path, '''
        from typing import Callable
        from metta._binding.runtime import Runtime
        class Space:
            @marked
            def apply(self, callback: Callable):
                """Cross and invoke the supplied operation."""
                Runtime().must("value")
                return callback()
    ''')
    assert result["space:apply"].number is None
    assert result["space:apply"].mixed
    _, status = _gate_report(monkeypatch, result)
    assert status == 1


def test_declared_supplied_callable_is_unordered_by_contract(tmp_path, monkeypatch):
    """A declared callback remains open while the gate accepts its contract."""
    _, result = _program(tmp_path, '''
        from collections.abc import Callable
        class Space:
            @marked
            def apply(self, callback: Callable[[], int]) -> int:
                """Invoke the caller's operation."""
                return callback()
    ''')
    assert result["space:apply"].number is None
    assert result["space:apply"].open
    report, status = _gate_report(monkeypatch, result)
    assert status == 0
    assert report["unordered_by_contract"] == ["space:apply"]


def test_composition_of_contract_open_door_is_unordered_by_dependency(tmp_path, monkeypatch):
    """A composition keeps its dependency instead of receiving an integer."""
    _, result = _program(tmp_path, '''
        from typing import Callable
        class Space:
            @marked
            def apply(self, callback: Callable):
                """Invoke the caller's operation."""
                return callback()
            @marked
            def compose(self, callback: Callable):
                """Forward the declared callback."""
                return self.apply(callback)
    ''')
    assert result["space:compose"].number is None
    assert result["space:compose"].blocked_by == {"space:apply"}
    report, status = _gate_report(monkeypatch, result)
    assert status == 0
    assert report["unordered_by_dependency"] == ["space:compose"]


@pytest.mark.parametrize(("annotation", "body"), [
    ("Iterable[int]", "return [item for item in source]"),
    ("Iterator[int]", "return next(source)"),
    ("Optional[Callable[[], int]]", "return source() if source is not None else 0"),
    ("Annotated[Callable[[], int], 'public callback']", "return source()"),
    ("Reader", "return source.read()"),
])
def test_parameter_contracts_follow_declared_protocols(tmp_path, monkeypatch, annotation, body):
    """Forward and qualified annotations preserve the public operation."""
    _, result = _program(tmp_path, f'''
        from typing import Annotated, Callable, Iterable, Iterator, Optional, Protocol
        class Reader(Protocol):
            def read(self) -> int: ...
        class Space:
            @marked
            def use(self, source: {annotation!r}):
                """Use the declared caller operation."""
                {body}
    ''')
    report, status = _gate_report(monkeypatch, result)
    assert status == 0
    assert report["unordered_by_contract"] == ["space:use"]
    assert all(call["annotation"] for call in report["rows"]["space:use"]["contracts"])


@pytest.mark.parametrize("annotation", ["Iterable[int]", "Reader", "Any"])
def test_undeclared_parameter_members_remain_defects(tmp_path, monkeypatch, annotation):
    """One declared protocol does not grant arbitrary dynamic attributes."""
    _, result = _program(tmp_path, f'''
        from typing import Any, Iterable, Protocol
        class Reader(Protocol):
            def read(self) -> int: ...
        class Space:
            @marked
            def use(self, source: {annotation}):
                """Invoke an undeclared operation."""
                return source.hidden()
    ''')
    report, status = _gate_report(monkeypatch, result)
    assert status == 1
    assert report["defect_open_dependencies"] == ["space:use"]


def test_contract_does_not_hide_a_separate_defect_or_its_dependents(tmp_path, monkeypatch):
    """A supplied callback cannot exempt a second unresolved call."""
    _, result = _program(tmp_path, '''
        from typing import Callable
        from plugins import registry
        class Space:
            @marked
            def apply(self, callback: Callable):
                """Invoke both known-contract and unknown operations."""
                callback()
                return registry.current()
            @marked
            def compose(self, callback: Callable):
                """Depend on the unresolved operation."""
                return self.apply(callback)
    ''')
    report, status = _gate_report(monkeypatch, result)
    assert status == 1
    assert report["defect_open_dependencies"] == ["space:apply"]
    assert report["unordered_by_contract"] == []
    assert report["unordered_by_dependency"] == []


@pytest.mark.parametrize("defect", ["mixed", "defect_open_dependencies", "recursive"])
def test_door_order_gate_refuses_each_boundary_defect(monkeypatch, capsys, defect):
    """Each unresolved boundary independently changes the command's exit."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "tools"))
    import doororder

    clean = {"mixed": [], "defect_open_dependencies": [], "recursive": [], "rows": {}}
    monkeypatch.setattr(doororder, "report", lambda: {**clean, defect: ["space:planted"]})
    assert doororder.main([]) == 1
    assert "space:planted" in capsys.readouterr().out
    monkeypatch.setattr(doororder, "report", lambda: clean)
    assert doororder.main([]) == 0
