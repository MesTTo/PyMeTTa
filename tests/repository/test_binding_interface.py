"""Purpose: discriminate binding declarations from unchecked native crossings.

Guarantees: service, load, kind and projection defects fail the actual checker
[tested: this file; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
"""

from __future__ import annotations

import ast
import copy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "extensions/python/tools"))

import bindinggen as binding  # noqa: E402 -- exercise the checkout generator


@pytest.fixture(scope="module")
def model():
    """Parse the production sources once; each plant gets an independent copy."""
    return binding.source_model(ROOT)


def test_binding_macros_do_not_tax_unrelated_goals(tmp_path):
    """Importing the macros preserves unrelated expansion cost and scope."""
    source = tmp_path / "expansion.pl"
    options = ROOT / binding.BINDING / "options.pl"
    macros = ROOT / binding.BINDING / "source_macros.pl"
    source.write_text(f"""
        :- use_module(library(apply_macros)).
        work(N, Cost) :-
            statistics(inferences, Before),
            forall(between(1,N,_),expand_goal(binding_unrelated_goal(_),_)),
            statistics(inferences, After), Cost is After-Before.
        sample(Cost) :- work(100,_), work(1000,Cost).
        main :-
            sample(Before),
            use_module({str(options)!r}, []),
            use_module({str(macros)!r}, []),
            sample(After), assertion(Before =:= After),
            Original = metta_py_option_record([unknown_field], _),
            expand_goal(Original, Untouched), assertion(Original == Untouched),
            use_module({str(options)!r}, [binding_options_expansion/2]),
            expand_goal(metta_py_option_record([answers(count)], Record), Expanded),
            call(Expanded), assertion(arg(3,Record,count)).
    """)
    result = subprocess.run(["swipl", "-q", "-f", "none", "-s", str(source), "-g", "main", "-t", "halt"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_binding_source_keeps_call_shapes(tmp_path):
    """Variables, strings, operators and zero-arity calls remain distinguishable."""
    source = tmp_path / "calls.pl"
    source.write_text('sample(X) :- S=metta_ops:heartbeat_tick(), py_call(S,@true), X="text".\n')
    record, = binding.source_model(ROOT, [source])[source]
    head, body = binding.head_body(record["term"])
    assert binding.indicator(head) == "sample/1"
    assert [":", "metta_ops", ["heartbeat_tick"]] in list(binding.walk(body))
    assert {"string": "text"} in list(binding.walk(body))
    assert ["@", "true"] in list(binding.walk(body))
    assert source.read_text()[record["start"]:record["end"]].endswith('X="text"')


def test_binding_source_refuses_syntax_errors_instead_of_skipping_clauses(tmp_path):
    """A malformed clause cannot disappear while later clauses still pass."""
    source = tmp_path / "broken.pl"
    source.write_text("broken :- ).\nvalid :- true.\n")
    with pytest.raises(ValueError, match="Syntax error"):
        binding.source_model(ROOT, [source])


@pytest.mark.parametrize("plant", [
    ("planted :- py_call(metta_ops:unregistered()).", "undeclared Python service metta_ops:unregistered/0"),
    ("planted :- py_call(metta_ops:heartbeat_tick(1)).", "Python service metta_ops:heartbeat_tick refuses arity 1"),
    ("planted(Object) :- py_call(Object:'__call__'()).", "undeclared dynamic Python crossing"),
    ("planted :- metta_py_call(resolve(unexpected, extra, argument), out, all).", "undeclared Python service"),
    ("planted :- py_call(metta_ops:heartbeat_tick(), a, [], extra).", "invalid py_call arity"),
])
def test_binding_crossing_mutations_refuse(model, tmp_path, monkeypatch, capsys, plant):
    """A clean interface and an independent bad crossing receive opposite exits."""
    clause, message = plant
    source = tmp_path / "plant.pl"
    source.write_text(clause)
    records = binding.source_model(ROOT, [source])[source]
    planted = {**model, ROOT / binding.BINDING / "plant.pl": records}
    with monkeypatch.context() as patch:
        patch.setattr(binding, "source_model", lambda _root: planted)
        assert binding.main([]) == 1
    assert message in capsys.readouterr().out
    assert binding.findings() == []


def test_binding_native_forward_requires_the_engine_service_kind(model, monkeypatch, capsys):
    """A same-spelled ownership hook cannot replace an imported service."""
    planted = copy.deepcopy(model)
    row = next(record for record in planted[ROOT / "engine/ext_points.pl"]
               if record["term"] == ["kind", ["/", "metta_host_hold_close", 1], "host_service"])
    row["term"][2] = "ownership"
    monkeypatch.setattr(binding, "source_model", lambda _root: planted)
    assert binding.main([]) == 1
    assert "metta_host_hold_close/1 is not an engine service" in capsys.readouterr().out


@pytest.mark.parametrize("defect", ["kind", "audience", "module", "include"])
def test_binding_provisions_keep_audience_and_kind(model, monkeypatch, capsys, defect):
    """A moved clause must retain its seam kind and actual loading namespace."""
    planted = copy.deepcopy(model)
    records = planted[ROOT / binding.BINDING / "provides/event.pl"]
    row = next(record for record in records if binding.compound(record["term"], "provides", 3))
    if defect == "kind":
        row["term"][-1][1][2][0] = "host_error_reason"
    elif defect == "audience":
        row["term"][1] = "unknown"
    elif defect == "module":
        row["term"][2] = "planted_namespace"
    else:
        shim = planted[ROOT / binding.BINDING / "shim.pl"]
        row = next(record for record in shim if record["term"] == [":-", ["include", "provides_host_user.pl"]])
        row["term"][1][1] = "provides_engine_user.pl"
    monkeypatch.setattr(binding, "source_model", lambda _root: planted)
    assert binding.main([]) == 1
    message = capsys.readouterr().out
    assert any(text in message for text in ("engine kind", "invalid load audience", "binding load audience"))


@pytest.mark.parametrize("name", ["callbacks.py", "services.pl", "provides_host_user.pl", "source_macros.pl"])
def test_binding_projection_mutations_refuse(model, monkeypatch, name):
    """An independent edit to every projection family is rejected."""
    path = ROOT / binding.BINDING / name
    read = Path.read_text
    original = read(path)
    planted = original.replace("heartbeat_tick", "planted_callback", 1) if name == "callbacks.py" else original + "% planted drift\n"
    assert planted != original
    monkeypatch.setattr(Path, "read_text", lambda file, *a, **kw: planted if file == path else read(file, *a, **kw))
    monkeypatch.setattr(binding, "source_model", lambda _root: model)
    assert f"binding projection drift: {path.relative_to(ROOT)}" in binding.findings()


def test_binding_controlled_entries_derive_from_native_shapes(model, tmp_path):
    """New admitted handles and packets extend the maps without a name roster."""
    source = tmp_path / "controlled.pl"
    source.write_text("""
        metta_py_wrappable(planted_create_controlled).
        planted_create_controlled(_, _, prolog(_)).
        metta_py_wrappable(planted_continue_controlled).
        planted_continue_controlled(_, [_,_]).
        planted_private_controlled(_, prolog(_)).
    """)
    planted = {**model, **binding.source_model(ROOT, [source])}

    def tables(sources):
        return {node.targets[0].id: ast.literal_eval(node.value)
                for node in ast.parse(binding.controlled_projection(sources)).body}

    before, after = tables(model), tables(planted)
    assert after["_DEFERRED_EXECUTION_OPENERS"] == {
        **before["_DEFERRED_EXECUTION_OPENERS"], "planted_create": "planted_create_controlled",
    }
    assert after["_DEFERRED_EXECUTION_RESUMES"] == {
        **before["_DEFERRED_EXECUTION_RESUMES"], "planted_continue": "planted_continue_controlled",
    }


@pytest.mark.parametrize("clause", [
    "",
    "planted_controlled(_, _).",
    "planted_controlled(prolog(_)).",
    "planted_controlled(_, prolog(_)). planted_controlled(_, [_,_]).",
])
def test_binding_controlled_signature_mutations_refuse(model, tmp_path, monkeypatch, capsys, clause):
    """An admitted entry cannot lack a definition or conceal its return shape."""
    source = tmp_path / "controlled.pl"
    source.write_text("metta_py_wrappable(planted_controlled).\n" + clause)
    planted = {**model, **binding.source_model(ROOT, [source])}
    monkeypatch.setattr(binding, "source_model", lambda _root: planted)
    assert binding.main([]) == 1
    assert "controlled entry planted_controlled" in capsys.readouterr().out


@pytest.mark.parametrize("plant", [
    ('"metta_py_debug_open": "metta_py_debug_open_controlled"',
     '"metta_py_debug_open": "planted"', "binding projection drift:"),
    (binding.EXECUTION_BEGIN, "# missing begin", "needs one ordered generated controlled entries region"),
])
def test_binding_controlled_projection_mutations_refuse(model, monkeypatch, capsys, plant):
    """The real lane detects a stale generated pair or a deleted region marker."""
    old, new, message = plant
    path = ROOT / "extensions/python/metta/_spaces/execution.py"
    read = Path.read_text
    original = read(path)
    planted = original.replace(old, new, 1)
    assert planted != original
    monkeypatch.setattr(Path, "read_text", lambda file, *a, **kw: planted if file == path else read(file, *a, **kw))
    monkeypatch.setattr(binding, "source_model", lambda _root: model)
    assert binding.main([]) == 1
    assert message in capsys.readouterr().out


def test_binding_standard_library_services():
    """The C callable shapes without inspect.signature execute with real values."""
    values = [(), ("x",), (b"x", "ascii"), (b"x", "ascii", "strict")]
    assert [str(*args) for args in values] == ["", "x", "x", "x"]
    value = 1
    assert type(value) is int
    assert type("Example", (), {}).__name__ == "Example"
    mapping = {"x": 1}
    assert mapping.pop("x") == 1
    assert mapping.pop("missing", 2) == 2
    for target, arities in binding.interface.C_SIGNATURES.items():
        module, member = target.split(":", 1)
        assert all(binding.accepts(ROOT, (module, member), count) for count in arities)
        assert not binding.accepts(ROOT, (module, member), max(arities) + 1)


@pytest.mark.parametrize("defect", ["missing", "duplicate", "unknown", "hand-written"])
def test_binding_native_forward_declarations_are_complete(model, monkeypatch, capsys, defect):
    """A declaration expands once, while policy clauses keep their own bodies."""
    planted = copy.deepcopy(model)
    records = planted[ROOT / binding.BINDING / "cursors.pl"]
    marker = next(record for record in records
                  if record["term"] == ["binding_forward", ["/", "metta_py_cursor_close", 1]])
    if defect == "missing":
        records.remove(marker)
    elif defect == "duplicate":
        records.append(copy.deepcopy(marker))
    elif defect == "unknown":
        marker["term"][1][2] = 2
    else:
        variable = {"var": 0}
        records.append({"term": [":-", ["metta_py_cursor_close", variable],
                                 ["metta_host_hold_close", variable]]})
    monkeypatch.setattr(binding, "source_model", lambda _root: planted)
    assert binding.main([]) == 1
    message = capsys.readouterr().out
    assert any(text in message for text in
               ("expected one declaration", "undeclared native forward", "hand-written native forward"))


def test_binding_native_forward_allows_local_policy_and_other_arities(model):
    """A service import does not confiscate its alias's other clauses."""
    variable = {"var": 0}
    planted = {**model, ROOT / binding.BINDING / "plant.pl": [
        {"term": [":-", ["metta_py_cursor_close", "special"], "true"]},
        {"term": [":-", ["metta_py_clear", variable, "true"], ["metta_py_clear", variable]]},
    ]}
    assert binding.native_forward_findings(ROOT, planted, set(binding.projections(ROOT, model))) == []
