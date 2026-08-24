"""Purpose: prove Space is the executable Handle operand for every space-taking face.

Guarantees:
  - import!, metta/3, Linda waits, built writes, spawned writes, computed
    targets, context-space, and Python constants accept Space directly
    [tested: this module; commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - a carried Space survives the public wire codec, strict writer, text and
    fast snapshots, and content digest without becoming a Symbol or object
    [tested: test_space_handles_are_term_operands_and_round_trip;
    commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
Open Obligations:
  To Do: None.
  Hacks: None.
  Future Enhancements: None.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import metta
from metta import Atom, Expression, Handle, S, Space, V, wire


@pytest.fixture
def spaces():
    """Two isolated handles in one runtime, released after each scenario."""
    context = metta.MeTTa()
    host = context.space()
    target = context.space()
    try:
        yield context, host, target
    finally:
        target.drop()
        host.drop()


def _import(space: Space, library: str) -> list[Atom]:
    return space.eval(S["import!"](space, S.library(S[library])))


def test_a_space_is_the_grounded_handle_species_and_import_operand(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _context, _host, target = spaces

    assert isinstance(target, Atom)
    assert isinstance(target, Handle)
    assert target.metatype == "Grounded"
    assert target == S[target.name]
    assert S[target.name] == target
    assert {target, S[target.name]} == {target}
    assert _import(target, "lib_thread") == [Expression()]
    assert target.is_function_here("cpu-count")
    assert len(target.eval(S["cpu-count"]())) == 1


def test_metta_evaluates_in_a_space_handle_operand(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _context, host, target = spaces
    target.add(S["="](S["r2-local"](), S.target_only))

    assert host.eval(
        S.metta(S["r2-local"](), S["%Undefined%"], target)
    ) == [S.target_only]


def test_space_handle_peek_and_take_are_linda_verbs(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _context, _host, target = spaces
    job = S.job(S.ready)
    target.add(job)

    assert target.peek(S.job(V.state), deadline=0.1) == job
    assert job in target
    assert target.take(S.job(V.state), deadline=0.1) == job
    assert job not in target
    with pytest.raises(TimeoutError, match="no atom matching"):
        target.take(S.job(V.state), deadline=0.001)


def test_add_atom_accepts_a_space_handle_inside_a_built_term(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _context, host, target = spaces
    fact = S.direct(S.ok)

    assert host.eval(S["add-atom"](target, fact)) == [Expression()]
    assert fact in target


def test_a_spawned_write_carries_its_target_as_a_space_handle(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _context, host, target = spaces
    _import(host, "lib_thread")
    fact = S.spawned(S.ok)

    future = host.eval(S.spawn(S["add-atom"](target, fact)))[0]
    assert isinstance(future, Space)
    assert host.eval(S["await"](future)) == [Expression()]
    assert fact in target
    future.drop()


def test_add_atom_accepts_a_computed_space_handle(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _context, host, target = spaces
    host.add(S["="](S["r2-target"](), target))
    fact = S.computed(S.ok)

    assert host.eval(S["add-atom"](S["r2-target"](), fact)) == [Expression()]
    assert fact in target


def test_context_space_round_trips_as_a_handle_without_a_symbol_rebuild(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    context, _host, target = spaces
    (here,) = target.eval(S["context-space"]())

    assert isinstance(here, Space)
    assert here == target
    assert context.space(here.name) == target


def test_a_python_self_constant_is_the_space_handle_itself(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _context, host, target = spaces
    self_handle = target
    host.add(S.owner(self_handle))

    (stored,) = host.atoms()
    assert isinstance(stored.children[1], Space)
    assert stored.children[1] == self_handle


def test_an_ampersand_symbol_is_not_reclassified_as_a_space(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _context, host, target = spaces

    operator = metta.parse("&&&")
    assert type(operator) is metta.Symbol
    assert type(host.eval(operator)[0]) is metta.Symbol
    explicit_symbol = wire.atom_from_wire(["s", target.name])
    assert type(explicit_symbol) is metta.Symbol
    assert wire.atom_from_wire(["p", target.name]) == target


@pytest.mark.parametrize("save_format", ["metta", "fast"])
def test_space_handles_are_term_operands_and_round_trip(  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    spaces, tmp_path: Path, save_format: str
):
    context, host, target = spaces
    carried = S.carried(target)
    host.add(carried)
    before = host.digest()

    encoded = json.loads(json.dumps(carried.to_wire()))
    decoded = wire.atom_from_wire(encoded)
    assert decoded == carried
    assert isinstance(decoded.children[1], Space)
    assert host.runtime.apply_must("petta_py_swrite", encoded) == str(carried)

    snapshot = tmp_path / f"space-handle.{save_format}"
    assert host.save(snapshot, format=save_format) == 1
    if save_format == "metta":
        assert snapshot.read_text(encoding="utf-8") == f"{carried}\n"

    loaded = context.space()
    try:
        loaded.load(snapshot)
        (restored,) = loaded.atoms()
        assert restored == carried
        assert isinstance(restored.children[1], Space)
        assert loaded.digest() == before
    finally:
        loaded.drop()


@pytest.mark.parametrize("wire_value", [["p", "plain"], ["p", 1]])
def test_malformed_space_handle_wire_payloads_are_refused(wire_value):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with pytest.raises(ValueError, match="wire space payload"):
        wire.atom_from_wire(wire_value)


def test_linda_deadline_misses_raise_the_package_timeout(spaces):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    import metta as package

    _context, _host, target = spaces
    with pytest.raises(package.Timeout):
        target.take(S.job(V.state), deadline=0.001)
    with pytest.raises(package.Timeout):
        target.peek(S.job(V.state), deadline=0.001)
