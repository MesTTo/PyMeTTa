"""Purpose: pin MeTTa and Python import rollback, cycles, and path identity.
Guarantees:
  - the minimal library remains idempotent after signature-registration and
    cross-space specialization traffic
    [tested: test_minimal_lib_install_is_idempotent_after_cross_file_traffic;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

import builtins
import sys
import types
import uuid
from pathlib import Path

import pytest

from metta._engine import bridge


def _texts(groups):
    """Flatten grouped runtime answers into their stable textual spelling."""
    return [str(atom) for group in groups for atom in group]


def write_increment_dependency(tmp_path):
    """Write dependency.metta defining a fresh increment function; return its name and the root path."""
    fn = f"late_inc_{uuid.uuid4().hex}"
    dependency_file = tmp_path / "dependency.metta"
    dependency_file.write_text(f"(= ({fn} $x) (+ $x 1))\n")
    return fn, tmp_path / "root.metta"


def test_failed_import_can_be_retried(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    module_name = f"petta_retry_{uuid.uuid4().hex}"
    root_file = tmp_path / "root.metta"
    dependency_file = tmp_path / "dependency.metta"
    python_file = tmp_path / f"{module_name}.py"

    root_file.write_text("!(import! &self dependency)\n!(retry-result)\n")
    dependency_file.write_text(
        f'!(import! &self "{module_name}.py")\n(= (retry-result) retry-ok)\n'
    )
    python_file.write_text('raise RuntimeError("first import fails")\n')
    previous_path = list(sys.path)

    with pytest.raises(Exception, match="first import fails"):
        metta.load(str(root_file))

    assert sys.path == previous_path
    assert module_name not in sys.modules

    python_file.write_text("RETRY_SUCCEEDED = True\n")
    results = metta.load(str(root_file))

    assert "retry-ok" in _texts(results)


def test_failed_import_rolls_back_partial_definitions(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    module_name = f"petta_partial_{uuid.uuid4().hex}"
    function_name = f"partial_definition_{uuid.uuid4().hex}"
    dependency_file = tmp_path / "dependency.metta"
    python_file = tmp_path / f"{module_name}.py"
    dependency_file.write_text(
        f'(= ({function_name}) retry-ok)\n!(import! &self "{module_name}.py")\n'
    )
    python_file.write_text('raise RuntimeError("partial import fails")\n')

    with pytest.raises(Exception, match="partial import fails"):
        metta.load(str(dependency_file))

    python_file.write_text("RETRY_SUCCEEDED = True\n")
    metta.load(str(dependency_file))
    # &self compiles into a module of its own, so the clause is not in `user`,
    # which is where janus resolves a goal by default. space_module/2 answers
    # which module it IS, so the test follows the engine instead of naming one.
    result = bridge().query_once(
        f"space_module('&self', M), metta_ensure_compiled('{function_name}'), "
        f"aggregate_all(count, clause(M:'{function_name}'(_), _), Count)"
    )

    assert result["Count"] == 1


def test_entry_file_breaks_direct_import_cycle(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    function_name = f"entry_cycle_{uuid.uuid4().hex}"
    entry_file = tmp_path / "a.metta"
    sibling_file = tmp_path / "b.metta"
    entry_file.write_text(f"!(import! &self b)\n(= ({function_name}) a)\n")
    sibling_file.write_text("!(import! &self a)\n")

    metta.load(str(entry_file))
    result = bridge().query_once(
        f"space_module('&self', M), metta_ensure_compiled('{function_name}'), "
        f"aggregate_all(count, clause(M:'{function_name}'(_), _), Count)"
    )

    assert result["Count"] == 1


def test_definition_before_import_resolves(metta, tmp_path, capfd):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    fn, root_file = write_increment_dependency(tmp_path)
    root_file.write_text(
        f"(= (uses-{fn} $x) ({fn} $x))\n!(import! &self dependency)\n!(uses-{fn} 41)\n"
    )

    results = metta.load(str(root_file))
    stderr = capfd.readouterr().err

    # The definition compiled before the import is recompiled when the import
    # registers the function, so the cross-file call reduces regardless of order.
    assert "42" in _texts(results)
    assert "Move the import or definition above the first use" not in stderr


def test_definition_before_dynamic_import_resolves(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The import target is computed at runtime, so no scan could know it upfront;
    # the definition still heals when the loaded file registers the function.
    fn, root_file = write_increment_dependency(tmp_path)
    root_file.write_text(
        f"(= (uses-{fn} $x) ({fn} $x))\n"
        "(= (dynamic-import-path) dependency)\n"
        "!(import! &self (dynamic-import-path))\n"
        f"!(uses-{fn} 41)\n"
    )

    results = metta.load(str(root_file))

    assert "42" in _texts(results)


def test_execution_before_import_warns(metta, tmp_path, capfd):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    fn, root_file = write_increment_dependency(tmp_path)
    root_file.write_text(f"!({fn} 41)\n!(import! &self dependency)\n!({fn} 41)\n")

    results = metta.load(str(root_file))
    stderr = capfd.readouterr().err

    # The call that ran before the import treated the name as a plain symbol...
    assert f"({fn} 41)" in _texts(results)
    # ...the same call after the import reduces...
    assert "42" in _texts(results)
    # ...and the unrepairable early execution is called out.
    assert fn in stderr
    assert "Move the import or definition above the first use" in stderr


def test_python_import_uses_canonical_path(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    module_name = f"same_name_{uuid.uuid4().hex}"
    event_name = f"PETTA_IMPORT_EVENTS_{uuid.uuid4().hex}"
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    setattr(builtins, event_name, [])
    previous_module = types.ModuleType(module_name)
    sys.modules[module_name] = previous_module

    try:
        for directory, value in ((left, "left"), (right, "right")):
            (directory / f"{module_name}.py").write_text(
                "import builtins\n"
                f"builtins.{event_name}.append({value!r})\n"
                f"def origin(): return {value!r}\n"
            )
            (directory / "root.metta").write_text(
                f'!(import! &self "{module_name}.py")\n!(py-call ({module_name}.origin))\n'
            )

        left_results = metta.load(str(left / "root.metta"))
        assert "left" in _texts(left_results)
        assert sys.modules[module_name] is previous_module

        right_results = metta.load(str(right / "root.metta"))
        assert "right" in _texts(right_results)

        assert getattr(builtins, event_name) == ["left", "right"]
        assert sys.modules[module_name] is previous_module
    finally:
        sys.modules.pop(module_name, None)
        delattr(builtins, event_name)


def test_python_calls_remain_bound_to_canonical_module(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    module_name = f"bound_module_{uuid.uuid4().hex}"
    left_function = f"left_call_{uuid.uuid4().hex}"
    right_function = f"right_call_{uuid.uuid4().hex}"
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()

    for directory, value, function_name in (
        (left, "left", left_function),
        (right, "right", right_function),
    ):
        (directory / f"{module_name}.py").write_text(f"def origin(): return {value!r}\n")
        (directory / "root.metta").write_text(
            f'!(import! &self "{module_name}.py")\n'
            f"(= ({function_name}) (py-call ({module_name}.origin)))\n"
        )

    metta.load(str(left / "root.metta"))
    metta.load(str(right / "root.metta"))

    assert "left" in _texts(metta.run(f"!({left_function})"))
    assert "right" in _texts(metta.run(f"!({right_function})"))


def test_python_import_can_load_sibling_module(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    module_name = f"python_sibling_{uuid.uuid4().hex}"
    helper_name = f"python_helper_{uuid.uuid4().hex}"
    module_file = tmp_path / f"{module_name}.py"
    helper_file = tmp_path / f"{helper_name}.py"
    root_file = tmp_path / "root.metta"
    helper_file.write_text('VALUE = "sibling-import-ok"\n')
    module_file.write_text(
        f"import {helper_name}\ndef sibling_value(): return {helper_name}.VALUE\n"
    )
    root_file.write_text(
        f'!(import! &self "{module_name}.py")\n!(py-call ({module_name}.sibling_value))\n'
    )
    previous_path = list(sys.path)

    try:
        results = metta.load(str(root_file))

        assert "sibling-import-ok" in _texts(results)
        assert sys.path == previous_path
        assert module_name not in sys.modules
    finally:
        sys.modules.pop(module_name, None)
        sys.modules.pop(helper_name, None)


def test_python_sibling_modules_do_not_collide(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    helper_name = f"shared_helper_{uuid.uuid4().hex}"
    left_module = f"left_module_{uuid.uuid4().hex}"
    right_module = f"right_module_{uuid.uuid4().hex}"
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()

    for directory, module_name, value in (
        (left, left_module, "left"),
        (right, right_module, "right"),
    ):
        (directory / f"{helper_name}.py").write_text(f"VALUE = {value!r}\n")
        (directory / f"{module_name}.py").write_text(
            f"import {helper_name}\ndef sibling_value(): return {helper_name}.VALUE\n"
        )
        (directory / "root.metta").write_text(
            f'!(import! &self "{module_name}.py")\n!(py-call ({module_name}.sibling_value))\n'
        )

    try:
        assert "left" in _texts(metta.load(str(left / "root.metta")))
        assert "right" in _texts(metta.load(str(right / "root.metta")))
        assert helper_name not in sys.modules
    finally:
        sys.modules.pop(helper_name, None)
        sys.modules.pop(left_module, None)
        sys.modules.pop(right_module, None)


def test_all_overloads_are_registered_before_repair(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    function_name = f"overloaded_{uuid.uuid4().hex}"
    caller_name = f"caller_{uuid.uuid4().hex}"
    (tmp_path / "dependency.metta").write_text(
        f"(= ({function_name} $x) one)\n(= ({function_name} $x $y $z) three)\n"
    )
    root = tmp_path / "root.metta"
    root.write_text(
        f"(= ({caller_name}) ({function_name} 1 2))\n"
        "!(import! &self dependency)\n"
        f"!({caller_name} 3)\n"
    )

    results = metta.load(str(root))

    assert "three" in _texts(results)


def test_missing_relative_import_does_not_fall_back_to_cwd(metta, tmp_path, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    fallback_name = f"cwd_fallback_{uuid.uuid4().hex}"
    (tmp_path / "dependency.metta").write_text(f"(= ({fallback_name}) wrong-cwd)\n")
    child = tmp_path / "sub"
    child.mkdir()
    root = child / "root.metta"
    root.write_text("!(import! &self dependency)\n")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(Exception, match="source_sink"):
        metta.load(str(root))


def test_minimal_lib_install_is_idempotent_after_cross_file_traffic(metta):
    """Exercise the minimized ordered trigger before installing twice.

    A notebook cell re-run, or two packages that both install it, calls
    install() twice on one space. It registers process-wide, so a second call
    that duplicated equations would double every answer. Signature prepasses
    followed by a copied specialization were the cross-file traffic that once
    made the installed base equation lose precedence to a generated equation.
    """
    metta.run("!(import! &self (library lib_reflect))")
    assert metta.run(
        "!(engine-knows p017-later)\n"
        "!(engine-arity p017-later)\n"
        "(= (p017-later $x) (+ $x 1))\n"
    ) == [[True], [2]]

    metta.run("(= (p017-inc $x) (+ $x 1))")
    metta.run("(= (p017-map $f $x) ($f $x))")
    metta.run("(= (p017-use $z) (p017-map p017-inc $z))")
    assert metta.run("!(p017-use 1)") == [[2]]
    clone = metta.copy()
    clone.drop()

    lib = Path(__file__).resolve().parents[3] / "lib"
    sys.path.insert(0, str(lib))
    try:
        import minimal_metta_lib
    finally:
        sys.path.remove(str(lib))

    with metta._new_space() as space:
        first = minimal_metta_lib.install(space)
        second = minimal_metta_lib.install(space)
        assert first == second
        assert first, "install answered no names"
        # The instruction set still answers once, not twice.
        assert space.run("!(function (return 42))") == [[42]]
