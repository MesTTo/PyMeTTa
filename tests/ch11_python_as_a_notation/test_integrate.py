"""Purpose: the integration interface end to end: bulk module operations,
instance wrapping with the effect convention, protocol typing and printing,
py-field reasoning in both modes, the reflector registry, integrate() over
modules, and a real third-party library (networkx) integrated in a page.
Guarantees:
  - dropping a space invalidates its integration installation records [tested
    test_dropped_space_name_reinstalls_integrations]
  - a failed integration removes every framework-managed registration and
    transactional write, restores prior registry entries, and releases a
    completed nested dependency receipt [tested
    test_a_failed_integration_unwinds_every_framework_registration,
    test_a_failed_integration_restores_registry_preimages,
    test_a_failed_outer_installation_unwinds_its_completed_dependency]
  - installation refuses a best-effort home before invoking user code and a
    failed declarative Prolog install names source that may remain consulted
    [tested test_an_integration_refuses_a_best_effort_home_before_installing,
    test_a_failed_prolog_integration_names_its_possible_source_residue]
  - module operations use one transport selector and infer declarations from
    annotations [tested: test_module_ops_bulk_registers_a_stdlib_module;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - Prolog-only integrations preserve distinct dotted module names as library
    aliases, while callers may still compose several directories under one
    explicit alias [tested:
    test_prolog_integration_aliases_keep_fully_qualified_module_names,
    test_an_explicitly_shared_library_alias_keeps_all_directories;
    commit=a6681e54ded570684ba0e2969f2893ae016a841a]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import contextlib
import math
import types
from dataclasses import dataclass

import pytest

import metta.integrate as pi
from metta import Expression, MeTTa, MettaError, S, Symbol, V, convert, ground
from metta._declare import declarations as _space_declarations
from metta.convert import CastError


def test_module_ops_bulk_registers_a_stdlib_module(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    names = pi.module_ops(
        metta,
        math,
        ["sqrt", "floor", "gcd", "comb"],
        effect="pureStructural",
    )
    assert set(names) == {"sqrt", "floor", "gcd", "comb"}
    assert metta.run("!(sqrt 16.0)") == [[4.0]]
    assert metta.run("!(gcd 12 18)") == [[6]]
    assert metta.run("!(comb 5 2)") == [[10]]


def test_uninspectable_callable_errors_are_classified(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Uninspectable:
        @property
        def __signature__(self):
            msg = "unsupported callable type"
            raise TypeError(msg)

        def __call__(self, value):
            return value

    target = Uninspectable()
    module = types.SimpleNamespace(__name__="uninspectable", target=target)
    assert pi.module_ops(
        metta,
        module,
        ["target"],
        effect="pureStructural",
    ) == ["target"]
    assert metta.run("!(target 7)") == [[7]]
    with pytest.raises(MettaError, match=r"pass arities=\[\.\.\.\]") as caught:
        pi.wrap_callable(
            metta,
            "strict-target",
            target,
            effect="pureStructural",
        )
    assert isinstance(caught.value.__cause__, TypeError)


def test_wrap_callable_rejects_required_keyword_only_parameters(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def target(value, *, required):
        return value + required

    with pytest.raises(MettaError, match="required keyword-only parameter 'required'"):
        pi.wrap_callable(
            metta,
            "keyword-only",
            target,
            effect="pureStructural",
        )


def test_wrap_object_methods_with_effect_convention(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Store:
        def __init__(self):
            self.items = []

        def put(self, x):
            self.items.append(x)  # returns None: the effect convention

        def size(self):
            return len(self.items)

    store = Store()
    pi.wrap_object(
        metta,
        "store",
        store,
        ["put", "size"],
        effects={"put": "writesState", "size": "readOnlyLookup"},
    )
    r = metta.run("!(store-put 42)\n!(store-put 43)\n!(store-size)")
    assert r == [[True], [True], [2]]
    assert store.items == [42, 43]
    # The instance is enumerable as a fact.
    rows = metta.match(S.wrapped(S.store, V.obj))
    assert rows and rows[0].obj == store


def test_register_object_type_makes_protocols_types(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Quacks:
        def quack(self):
            return "quack"

    pi.register_object_type(lambda x: hasattr(x, "quack"), "Duck")
    space = metta._new_space()
    space.add(S.pet(ground(Quacks())))
    # The match runs first and get-type reads the object it found. get-type
    # does not evaluate its argument, so asking it about an unreduced match
    # would type the match expression rather than the pet.
    (answers,) = space.run(
        "!(collapse (let $p (match (context-space) (pet $q) $q) (get-type $p)))"
    )
    names = {str(a) for a in answers[0]}
    assert "Duck" in names and "Quacks" in names


def test_register_repr_protocol(metta):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    class Sized:
        def __len__(self):
            return 7

    pi.register_repr(lambda x: hasattr(x, "__len__") and type(x).__name__ == "Sized",
                     lambda x: f"<Sized of {len(x)}>")
    assert "Sized of 7" in repr(ground(Sized()))


def test_protocol_and_reflector_registrations_can_be_removed(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class ExtensionTarget:
        pass

    target = ExtensionTarget()

    def type_predicate(value):
        return isinstance(value, ExtensionTarget)

    def repr_predicate(value):
        return isinstance(value, ExtensionTarget)

    def formatter(_value):
        return "<extension target>"

    def reflector(m, name, _value):
        return pi.facts(m, [S.reflected(Symbol(name))])

    pi.register_object_type(type_predicate, "ExtensionTargetProtocol")
    pi.register_repr(repr_predicate, formatter)
    pi.register_reflector(type_predicate, reflector)
    try:
        assert metta.cast(target, "ExtensionTargetProtocol") is target
        assert str(ground(target)) == "<extension target>"
        assert pi.reflect(metta, "registered", target) == 1
    finally:
        pi.unregister_reflector(type_predicate, reflector)
        pi.unregister_repr(repr_predicate, formatter)
        pi.unregister_object_type(type_predicate, "ExtensionTargetProtocol")

    with pytest.raises(CastError):
        metta.cast(target, "ExtensionTargetProtocol")
    assert str(ground(target)) == "<ExtensionTarget>"
    with pytest.raises(MettaError, match="no reflector claims ExtensionTarget"):
        pi.reflect(metta, "removed", target)
    with pytest.raises(KeyError, match="ExtensionTargetProtocol"):
        pi.unregister_object_type(type_predicate, "ExtensionTargetProtocol")
    with pytest.raises(KeyError, match="protocol repr"):
        pi.unregister_repr(repr_predicate, formatter)
    with pytest.raises(KeyError, match="reflector"):
        pi.unregister_reflector(type_predicate, reflector)


def test_py_field_reasons_in_both_modes(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    @dataclass
    class Config:
        depth: int
        name: str

    pi.install_reflection_ops(metta)
    space = metta._new_space()
    space.add(S.config(ground(Config(3, "deep"))))
    # Bound mode: fetch one field.
    r = space.run(
        "!(match (context-space) (config $c) (py-field $c depth))"
    )
    (group,) = r
    (pair,) = group
    assert pair[0] == S.depth and int(pair[1].value) == 3
    # Unbound mode: enumerate every field, one answer each.
    r = space.run(
        "!(collapse (match (context-space) (config $c) (py-field $c $f)))"
    )
    names = {str(p[0]) for p in r[0][0]}
    assert names == {"depth", "name"}


def test_py_attr_and_bound_py_field_read_a_property_once(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class Counted:
        def __init__(self):
            self.reads = 0

        @property
        def item(self):
            self.reads += 1
            return self.reads

    pi.install_reflection_ops(metta)
    target = Counted()
    space = metta._new_space()
    try:
        space.add(S.target(ground(target)))
        assert space.run(
            "!(match (context-space) (target $x) (py-attr $x item))"
        ) == [[1]]
        assert target.reads == 1
        (pair,) = space.run(
            "!(match (context-space) (target $x) (py-field $x item))"
        )[0]
        assert int(pair[1].value) == 2
        assert target.reads == 2
    finally:
        space.drop()


def test_pi_protocol_and_idempotence(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    calls = []
    fake = types.SimpleNamespace(
        __name__="fake_integration", install_metta=lambda m: calls.append(m)
    )

    name = pi.integrate(metta, fake)
    assert name == "fake_integration"
    pi.integrate(metta, fake)
    assert len(calls) == 1  # idempotent per process
    # Installation is per (space, name): a second space installs again.
    assert (metta.name, "fake_integration") in pi.installed()
    other = metta._new_space()
    try:
        pi.integrate(other, fake)
        assert len(calls) == 2
    finally:
        other.drop()


def test_an_integration_installed_on_a_context_reaches_its_home_space():
    """An installer is handed a SPACE, whichever of the two the caller holds.

    MeTTa refuses a Space door rather than forwarding it, deliberately, so
    every installer that reached one died on a context: `integrate(m, target)`
    raised on `m.name` before calling anything, and `metta_arrays.install(m)`
    raised `MeTTa has no 'is_function'` with every operation unregistered.
    The context resolves to its home space once, here, so the installer still
    receives the object whose storage it writes into.
    """
    seen = []
    fake = types.SimpleNamespace(
        __name__="context_integration", install_metta=seen.append
    )
    context = MeTTa()
    home = context.self

    assert pi.integrate(context, fake) == "context_integration"
    assert seen == [home]
    assert (home.name, "context_integration") in pi.installed()

    # And it is the same installation the space itself would have made, so
    # handing the context a second time installs nothing further.
    pi.integrate(home, fake)
    assert len(seen) == 1


def test_a_failed_integration_unwinds_every_framework_registration(
    metta, repo_root
):
    """The reporter's operation, marker, library fact, and type all disappear."""
    import importlib

    ops = importlib.import_module("metta._declare.operations")
    operation_name = "failed-integration-operation"
    integration_name = "failed_integration_rollback_probe"
    library_alias = "failed.integration.rollback"
    type_name = "FailedIntegrationType"
    library_directory = repo_root / "extensions" / "python" / "tests" / "fixtures"
    marker = S["integration-install-marker"](S.present)

    class InstalledType:
        def __init__(self, value):
            self.value = value

    class ReclaimedType:
        def __init__(self, value):
            self.value = value

    class ProtocolTarget:
        pass

    target = ProtocolTarget()

    def predicate(value):
        return isinstance(value, ProtocolTarget)

    def formatter(_value):
        return "<failed integration target>"

    def reflector(space, name, _value):
        return pi.facts(space, [S.reflected(Symbol(name))])

    def install(space):
        @space.op(name=operation_name, effect="pureStructural")
        def installed_operation(value: int) -> int:
            return value

        space.add(marker)
        space.register_library_path(library_directory, library_alias)
        pi.register_type(
            InstalledType,
            name=type_name,
            to_atom=lambda value: (value.value,),
            from_atom=InstalledType,
            fields=("value",),
        )
        pi.register_object_type(predicate, "FailedIntegrationProtocol")
        pi.register_repr(predicate, formatter)
        pi.register_reflector(predicate, reflector)
        message = "injected integration failure"
        raise RuntimeError(message)

    integration = types.SimpleNamespace(
        __name__=integration_name,
        install_metta=install,
    )

    with metta._new_space() as space:
        try:
            with pytest.raises(
                RuntimeError, match="injected integration failure"
            ) as caught:
                pi.integrate(space, integration)

            notes = getattr(caught.value, "__notes__", ())
            assert any("process-global side effects" in note for note in notes)
            assert operation_name not in ops.registered()
            assert not space.is_function(operation_name)
            assert marker not in space
            assert not space.runtime.once(
                "user:file_search_path(Alias, Directory)",
                Alias=library_alias,
                Directory=str(library_directory),
            )
            assert S["type-image"](S[type_name], S.expression) not in space._at(
                "&metta"
            )
            with pytest.raises(TypeError, match="has no default image"):
                convert.ensure_registered(InstalledType)
            assert (space.name, integration_name) not in pi.installed()
            with pytest.raises(CastError):
                space.cast(target, "FailedIntegrationProtocol")
            assert str(ground(target)) == "<ProtocolTarget>"
            with pytest.raises(MettaError, match="no reflector claims ProtocolTarget"):
                pi.reflect(space, "removed", target)

            # The public names are reclaimable, and a typed operation retry
            # republishes every declaration rather than trusting stale Python
            # ownership counts left by the failed first attempt.
            pi.register_type(
                ReclaimedType,
                name=type_name,
                to_atom=lambda value: (value.value,),
                from_atom=ReclaimedType,
                fields=("value",),
            )
            pi.unregister_type(ReclaimedType)

            def replacement_operation(value: int) -> int:
                return value

            space.op(
                replacement_operation,
                name=operation_name,
                effect="pureStructural",
            )
            declarations = ops.registered()[operation_name].declarations
            assert declarations
            assert all(declaration in space for declaration in declarations)
        finally:
            if operation_name in ops.registered() or space.is_function(operation_name):
                with contextlib.suppress(KeyError, MettaError):
                    space.unregister_op(operation_name)
            for cls in (InstalledType, ReclaimedType):
                with contextlib.suppress(KeyError):
                    pi.unregister_type(cls)
            with contextlib.suppress(KeyError):
                pi.unregister_reflector(predicate, reflector)
            with contextlib.suppress(KeyError):
                pi.unregister_repr(predicate, formatter)
            with contextlib.suppress(KeyError):
                pi.unregister_object_type(predicate, "FailedIntegrationProtocol")
            while marker in space:
                space.remove(marker)
            space.runtime.must(
                "retractall(user:file_search_path(Alias, Directory))",
                Alias=library_alias,
                Directory=str(library_directory),
            )


def test_a_failed_integration_restores_registry_preimages(metta):
    """Removal and replacement roll back to exact entries and list precedence."""
    class ExistingType:
        def __init__(self, value):
            self.value = value

    class ExistingTarget:
        pass

    type_name = "ExistingIntegrationType"
    protocol_name = "ExistingIntegrationProtocol"
    target = ExistingTarget()

    def predicate(value):
        return isinstance(value, ExistingTarget)

    def formatter(_value):
        return "<existing integration target>"

    def reflector(space, name, _value):
        return pi.facts(space, [S.reflected(Symbol(name))])

    pi.register_type(
        ExistingType,
        name=type_name,
        to_atom=lambda value: (value.value,),
        from_atom=ExistingType,
        fields=("value",),
    )
    pi.register_object_type(predicate, protocol_name)
    pi.register_repr(predicate, formatter)
    pi.register_reflector(predicate, reflector)

    def install(_space):
        pi.unregister_object_type(predicate, protocol_name)
        pi.unregister_repr(predicate, formatter)
        pi.unregister_reflector(predicate, reflector)
        pi.register_type(ExistingType, image="handle", name=type_name)
        message = "restore registry preimages"
        raise RuntimeError(message)

    integration = types.SimpleNamespace(
        __name__="failed_registry_preimage_probe",
        install_metta=install,
    )

    with metta._new_space() as space:
        try:
            with pytest.raises(RuntimeError, match="restore registry preimages"):
                pi.integrate(space, integration)

            assert space.cast(target, protocol_name) is target
            assert str(ground(target)) == "<existing integration target>"
            assert pi.reflect(space, "restored", target) == 1
            assert str(convert.project(ExistingType(7)).atom) == (
                f"({type_name} 7)"
            )
            images = space._at("&metta").match(
                S["type-image"](S[type_name], V.image)
            )
            assert [str(answer.image) for answer in images] == ["expression"]
        finally:
            with contextlib.suppress(KeyError):
                pi.unregister_reflector(predicate, reflector)
            with contextlib.suppress(KeyError):
                pi.unregister_repr(predicate, formatter)
            with contextlib.suppress(KeyError):
                pi.unregister_object_type(predicate, protocol_name)
            with contextlib.suppress(KeyError):
                pi.unregister_type(ExistingType)


def test_a_failed_outer_installation_unwinds_its_completed_dependency(metta):
    """A child commit is relative to the outer installer's transaction."""
    calls = []
    marker = S.completed_dependency(S.marker)

    def install_dependency(space):
        calls.append(space.name)
        space.add(marker)

    dependency = types.SimpleNamespace(
        __name__="completed_dependency_probe",
        install_metta=install_dependency,
    )

    def install_outer(space):
        pi.integrate(space, dependency)
        message = "outer installer failure"
        raise RuntimeError(message)

    outer = types.SimpleNamespace(
        __name__="failed_outer_integration_probe",
        install_metta=install_outer,
    )

    with metta._new_space() as space:
        with pytest.raises(RuntimeError, match="outer installer failure"):
            pi.integrate(space, outer)
        assert marker not in space
        assert (space.name, dependency.__name__) not in pi.installed()
        assert (space.name, outer.__name__) not in pi.installed()

        def fail_after_dependency_commit():
            pi.integrate(space, dependency)
            message = "user transaction failure"
            raise RuntimeError(message)

        with pytest.raises(RuntimeError, match="user transaction failure"):
            space.transaction(fail_after_dependency_commit)
        assert marker not in space
        assert (space.name, dependency.__name__) not in pi.installed()

        pi.integrate(space, dependency)
        assert calls == [space.name, space.name, space.name]
        assert marker in space


def test_an_integration_refuses_a_best_effort_home_before_installing(metta):
    """A known non-transactional home cannot start an all-or-nothing install."""
    from metta.foreign import SpaceProvider

    class Store(SpaceProvider):
        def __init__(self):
            self.rows = []

        def atoms(self):
            return iter(self.rows)

        def add(self, atom):
            self.rows.append(atom)

    store = Store()
    space_name = "&best_effort_integration_probe"
    _space_declarations._register_space(metta, store, space_name)
    space = metta._at(space_name)
    space.atomicity("best-effort")
    calls = []

    def install(target):
        calls.append(target)

    integration = types.SimpleNamespace(
        __name__="best_effort_integration_probe",
        install_metta=install,
    )
    try:
        with pytest.raises(MettaError, match="declares best-effort writes") as caught:
            pi.integrate(space, integration)
        assert not calls
        assert not store.rows
        assert not getattr(caught.value, "__notes__", ())
        assert (space.name, integration.__name__) not in pi.installed()
    finally:
        _space_declarations._unregister_space(metta, space_name)


def test_a_failed_prolog_integration_names_its_possible_source_residue(
    metta, tmp_path
):
    """Dynamic extension state unwinds; consulted source is named and remains."""
    package = tmp_path
    module_name = "failed.prolog.integration"
    extension_name = "failed_prolog_integration_residue"
    operation_name = "failed-prolog-integration-residue"
    first = package / "first-residue.pl"
    first.write_text(
        f":- metta_extension({extension_name}, [version('0.0.0')]).\n"
        f':- metta_export("(: {operation_name} (-> Number Number))").\n'
        f"'{operation_name}'(X, Y) :- Y is X + 1.\n"
    )
    module = types.ModuleType(module_name)
    module.__file__ = str(package / "__init__.py")
    module.METTA_PROLOG = ["first-residue.pl", "second-residue.pl"]

    with metta._new_space() as space:
        with pytest.raises(
            ValueError, match="register_prolog needs one of three things"
        ) as caught:
            pi.integrate(space, module)

        notes = getattr(caught.value, "__notes__", ())
        joined = "\n".join(notes)
        assert "consulted Prolog source" in joined
        for filename in module.METTA_PROLOG:
            assert str(package / filename) in joined
        assert not space.runtime.once(
            "user:file_search_path(Alias, Directory)",
            Alias=module_name,
            Directory=str(package),
        )
        assert not space.runtime.once(
            "metta_extension_info(Extension, _, _)",
            Extension=extension_name,
        )
        assert not space.is_function(operation_name)
        assert (space.name, module_name) not in pi.installed()
        assert space.runtime.once(
            f"current_predicate('{operation_name}'/2)"
        ), "consulted Prolog clauses are the documented non-transactional residue"


def test_prolog_integration_aliases_keep_fully_qualified_module_names(
    metta, tmp_path
):
    """Two dotted modules ending in ``tools`` retain distinct file doors."""
    alpha_dir = tmp_path / "alpha"
    beta_dir = tmp_path / "beta"
    alpha_dir.mkdir()
    beta_dir.mkdir()
    (alpha_dir / "probe.metta").write_text("(= (qualified-alpha-probe) alpha)\n")
    (beta_dir / "probe.metta").write_text("(= (qualified-beta-probe) beta)\n")

    def prolog_only_module(name, directory):
        module = types.ModuleType(name)
        module.__file__ = str(directory / "__init__.py")
        module.METTA_PROLOG = []
        return module

    aliases = ("alpha.tools", "beta.tools")
    with metta._new_space() as space:
        try:
            assert (
                pi.integrate(space, prolog_only_module(aliases[0], alpha_dir))
                == aliases[0]
            )
            assert (
                pi.integrate(space, prolog_only_module(aliases[1], beta_dir))
                == aliases[1]
            )

            for alias, directory in zip(aliases, (alpha_dir, beta_dir), strict=True):
                assert space.runtime.once(
                    "user:file_search_path(Alias, Directory)",
                    Alias=alias,
                    Directory=str(directory),
                )
            assert not space.runtime.once(
                "user:file_search_path(Alias, Directory)",
                Alias=aliases[0],
                Directory=str(beta_dir),
            )
            assert not space.runtime.once(
                "user:file_search_path(Alias, Directory)",
                Alias=aliases[1],
                Directory=str(alpha_dir),
            )
            for directory in (alpha_dir, beta_dir):
                assert not space.runtime.once(
                    "user:file_search_path(Alias, Directory)",
                    Alias="tools",
                    Directory=str(directory),
                )

            space.fn["import!"](
                space, S.library(S[aliases[0]], S["probe.metta"])
            ).one()
            space.fn["import!"](
                space, S.library(S[aliases[1]], S["probe.metta"])
            ).one()
            assert space.run("!(qualified-alpha-probe)") == [[S.alpha]]
            assert space.run("!(qualified-beta-probe)") == [[S.beta]]
        finally:
            for alias in (*aliases, "tools"):
                space.runtime.must(
                    "retractall(user:file_search_path(Alias, _))", Alias=alias
                )


def test_an_explicitly_shared_library_alias_keeps_all_directories(metta, tmp_path):
    """SWI's additive alias remains available when sharing is deliberate."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "left.metta").write_text("(= (shared-left-probe) left)\n")
    (second / "right.metta").write_text("(= (shared-right-probe) right)\n")
    alias = "shared.integration.paths"

    with metta._new_space() as space:
        try:
            space.register_library_path(first, alias)
            space.register_library_path(second, alias)
            space.fn["import!"](
                space, S.library(S[alias], S["left.metta"])
            ).one()
            space.fn["import!"](
                space, S.library(S[alias], S["right.metta"])
            ).one()
            assert space.run("!(shared-left-probe)") == [[S.left]]
            assert space.run("!(shared-right-probe)") == [[S.right]]
        finally:
            space.runtime.must(
                "retractall(user:file_search_path(Alias, _))", Alias=alias
            )


def test_dropped_space_name_reinstalls_integrations(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    calls = []

    class Reinstallable:
        name = "space-reuse-probe"

        def install(self, target):
            calls.append(target.name)
            target.add(S.integration_marker(len(calls)))

    integration = Reinstallable()
    space_name = "&integration_reuse_probe"
    first = metta._at(space_name)
    first.clear()
    pi.integrate(first, integration)
    assert first.match(S.integration_marker(V.value)).one().value == 1

    first.drop()
    assert (space_name, integration.name) not in pi.installed()

    second = metta._at(space_name)
    try:
        pi.integrate(second, integration)
        assert second.match(S.integration_marker(V.value)).one().value == 2
        assert calls == [space_name, space_name]
    finally:
        second.drop()


def test_facts_bulk_load(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    space = metta._new_space()
    count = pi.facts(space, [S.n(1), S.n(2), (S.pair, 1, 2)])
    assert count == 3
    assert len(space) == 3


def test_networkx_integrates_in_a_page(metta):
    """The acid test the interface exists for: a real library, deeply usable,
    with only public toolkit calls.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    nx = pytest.importorskip("networkx")

    graph = nx.Graph()
    graph.add_edge("a", "b", weight=1.0)
    graph.add_edge("b", "c", weight=2.0)
    graph.add_edge("a", "c", weight=9.0)

    space = metta._new_space()
    # Structure as facts:
    pi.facts(space, (Expression(S.nx_edge, S[u], S[v], d["weight"]) for u, v, d in graph.edges(data=True)))
    # Behaviour as an operation:
    def shortest_path(a, b):
        names = nx.shortest_path(graph, str(a), str(b), weight="weight")
        return Expression(*(S[n] for n in names))

    space.op(shortest_path, name="nx-path", effect="readOnlyLookup")
    # And both compose with reasoning:
    assert space.run("!(nx-path a c)") == [[Expression(S.a, S.b, S.c)]]
    rows = space.match(S.nx_edge(S.a, V.to, V.w))
    assert {(str(r.to), float(r.w)) for r in rows} == {("b", 1.0), ("c", 9.0)}


def test_the_routing_frame_metta_subsumes_dispatch(metta):
    """The express() frame, run rather than argued: an app is a space, every
    route is an equation, a request reduces through whichever route matches,
    and the catch-all equation is the 404. Clause order plus once is the
    dispatcher; nothing was built to make this work, which is the point.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    app = metta._new_space()
    app.run(
        '(= (route home) (Page 200 "Welcome"))\n'
        '(= (route about) (Page 200 "About us"))\n'
        "(= (route $other) (NotFound 404 $other))\n"
        "(= (handle $request) (once (route $request)))"
    )
    assert app.run("!(handle home)") == [[Expression(S.Page, 200, "Welcome")]]
    assert app.run("!(handle nowhere)") == [[Expression(S.NotFound, 404, S.nowhere)]]
    # And a middleware chain is function composition, for free:
    app.run('(= (logged $req) (let $res (handle $req) (Logged $req $res)))')
    (group,) = app.run("!(logged about)")
    assert group == [Expression(S.Logged, S.about, Expression(S.Page, 200, "About us"))]


def test_entry_point_discovery_is_unloaded_and_loading_is_by_name(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    from importlib import metadata as importlib_metadata

    advertised = (
        importlib_metadata.EntryPoint("db", "sqlite3:connect", "metta.spaces"),
        importlib_metadata.EntryPoint("paths", "sys:path", "metta.libraries"),
    )

    def fake_entry_points(*, group):
        return tuple(entry for entry in advertised if entry.group == group)

    monkeypatch.setattr(pi.metadata, "entry_points", fake_entry_points)

    # discovery answers names without importing or registering anything
    assert list(pi.entry_points()) == ["db"]
    assert list(pi.entry_points(pi.LIBRARIES_GROUP)) == [
        "paths"
    ]

    # a callable target is a factory: called with the caller's arguments
    connection = pi.load_entry_point("db", ":memory:")
    connection.execute("CREATE TABLE t (x)")
    connection.close()

    # a non-callable target answers as-is, and refuses arguments
    import sys as sys_module

    assert (
        pi.load_entry_point("paths", group=pi.LIBRARIES_GROUP)
        is sys_module.path
    )
    with pytest.raises(MettaError, match="not callable"):
        pi.load_entry_point("paths", "extra", group=pi.LIBRARIES_GROUP)

    # a typo reads as one: the refusal lists what IS installed
    with pytest.raises(MettaError, match=r"no metta\.spaces entry point named 'nope'; installed: db"):
        pi.load_entry_point("nope")
