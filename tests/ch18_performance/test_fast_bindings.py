"""Purpose: preserve stored equations and resolved bindings through fast images.

Guarantees:
  - reader, native and mixed equation occurrences retain their answer bags,
    source atoms and later recompilation behavior after relocation
    [tested: test_fast_images_preserve_each_equations_binding;
    commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
"""

import hashlib
from collections import Counter

import pytest

from metta import MeTTa, S, V
from metta.errors import EngineError


@pytest.mark.parametrize(
    "ingresses",
    [
        ("reader",),
        ("native",),
        ("reader", "native"),
        ("native", "reader"),
        ("reader", "native", "reader"),
    ],
)
def test_fast_images_preserve_each_equations_binding(tmp_path, ingresses):
    """Equal stored atoms can carry different resolved space references."""
    first = tmp_path / "bindings.fast"
    second = tmp_path / "recompiled.fast"
    definition = S["="](
        S.cache_binding(V.x, V.y),
        S.match(S["&self"], S.cache_edge(V.x, V.y), S.cache_box(V.y)),
    )
    readers = ingresses.count("reader")
    query = S.cache_binding(S.a, S.b)
    with MeTTa() as m, m.space() as source, m.space() as restored, m.space() as again:
        source.add(S.cache_edge(S.a, S.b), S.cache_edge(S.a, S.b))
        for ingress in ingresses:
            if ingress == "reader":
                source.run(str(definition))
            else:
                source.add(definition)

        expected = ["(cache-box b)"] * (2 * readers)
        assert list(map(str, source.eval(query))) == expected
        original_atoms = source.source()
        assert source.save(first, format="fast") == 2 + len(ingresses)
        for _ in range(2):
            restored.load(first)
            assert restored.source() == original_atoms
            assert list(map(str, restored.eval(query))) == expected

        restored.add(S.cache_edge(S.a, S.b))
        assert list(map(str, restored.eval(query))) == ["(cache-box b)"] * (3 * readers)
        restored.run("(= (cache-box $value) (cache-rebound $value))")
        recompiled = ["(cache-rebound b)"] * (3 * readers)
        assert list(map(str, restored.eval(query))) == recompiled
        restored.save(second, format="fast")
        again.load(second)
        assert again.source() == restored.source()
        assert list(map(str, again.eval(query))) == recompiled


@pytest.mark.parametrize("force_before_save", [False, True])
def test_fast_images_keep_pending_equations_beside_resolved_equations(
    tmp_path, force_before_save
):
    """A later eager equation cannot replace an earlier deferred occurrence."""
    path = tmp_path / "pending.fast"
    with MeTTa() as m, m.space() as source, m.space() as restored:
        source.run(
            "(pending-edge a local) "
            "(= (pending-binding $x) plain) "
            "(= (pending-binding $x) (match &self (pending-edge $x $y) $y))"
        )
        query = S.pending_binding(S.a)
        if force_before_save:
            assert sorted(map(str, source.eval(query))) == ["local", "plain"]
        source.save(path, format="fast")
        restored.load(path)
        assert restored.source() == source.source()
        assert sorted(map(str, restored.eval(query))) == ["local", "plain"]
        assert sorted(map(str, source.eval(query))) == ["local", "plain"]


def test_forcing_a_deferred_equation_keeps_a_resolved_sibling_once():
    """The engine's literal self makes an accidental raw recompile visible."""
    with MeTTa() as m, m.space() as source:
        # The process root cannot be reached through this context's named self.
        m.runtime.must("'add-atom'('&self', ['binding-edge', a, global], _)")
        try:
            source.run(
                "(binding-edge a local) "
                "(= (binding-deferred $x) plain) "
                "(= (binding-deferred $x) (match &self (binding-edge $x $y) $y))"
            )
            assert sorted(map(str, source.eval(S.binding_deferred(S.a)))) == [
                "local", "plain"
            ]
        finally:
            m.runtime.must("'remove-atom'('&self', ['binding-edge', a, global], _)")


@pytest.mark.parametrize("ingresses", [("reader", "native"), ("native", "reader")])
def test_removal_retires_the_same_stored_equation_after_recompilation(
    tmp_path, ingresses
):
    """A duplicate source atom can name either a local or a literal-self call."""
    path = tmp_path / "removal.fast"
    equation = S["="](
        S.binding_remove(V.x),
        S.match(S["&self"], S.removal_edge(V.x, V.y), S.removal_box(V.y)),
    )
    with MeTTa() as m, m.space() as source, m.space() as restored:
        m.runtime.must("'add-atom'('&self', ['removal-edge', a, global], _)")
        try:
            source.add(S.removal_edge(S.a, S.local))
            for ingress in ingresses:
                if ingress == "reader":
                    source.run(str(equation))
                else:
                    source.add(equation)
            source.save(path, format="fast")
            restored.load(path)
            restored.run("(= (removal-box $x) (changed $x))")
            assert Counter(map(str, restored.eval(S.binding_remove(S.a)))) == {
                "(changed local)": 1, "(changed global)": 1
            }
            assert restored.remove(equation) is True
            expected = "global" if ingresses[0] == "reader" else "local"
            assert list(map(str, restored.eval(S.binding_remove(S.a)))) == [
                f"(changed {expected})"
            ]
            restored.save(path, format="fast")
            source.clear()
            source.load(path)
            assert list(map(str, source.eval(S.binding_remove(S.a)))) == [
                f"(changed {expected})"
            ]
        finally:
            m.runtime.must("'remove-atom'('&self', ['removal-edge', a, global], _)")


def test_fast_images_relocate_resolved_head_arguments(tmp_path):
    """Resolved references in flat and nested heads keep their input meaning."""
    path = tmp_path / "heads.fast"
    with MeTTa() as m, m.space() as source, m.space() as restored:
        source.run(
            "(= (binding-head &self) flat) "
            "(= (binding-head (holder &self)) nested) "
            "(= (binding-head $x $x) repeated) "
            "(= (binding-head a b) ground)"
        )
        source.save(path, format="fast")
        restored.load(path)
        assert source.source() == restored.source()
        for space in (source, restored):
            own_name = S[space.name]
            assert space.eval(S.binding_head(own_name)) == [S.flat]
            assert space.eval(S.binding_head(S.holder(own_name))) == [S.nested]
            assert space.eval(S.binding_head(S.a, S.a)) == [S.repeated]
            assert space.eval(S.binding_head(S.a, S.b)) == [S.ground]


def test_source_replacement_retains_recompiled_binding_ownership(tmp_path):
    """A reload replaces its resolved clause while a native equation remains."""
    program = tmp_path / "owner.metta"
    cache = tmp_path / "owner.fast"
    definition = (
        "(= (binding-owner $x) "
        "(match &self (owner-edge $x $y) (owner-box $y)))"
    )
    program.write_text(f"(owner-edge a old) {definition}")
    with MeTTa() as m, m.space() as source, m.space() as restored:
        source.load(program)
        source.run("(= (owner-box $x) (owner-result $x))")
        source.add(S["="](S.binding_owner(V.x), S.native_owner(V.x)))
        program.write_text(f"(owner-edge a new) {definition}")
        source.load(program)
        expected = Counter({"(owner-result new)": 1, "(native-owner a)": 1})
        assert Counter(map(str, source.eval(S.binding_owner(S.a)))) == expected
        source.save(cache, format="fast")
        restored.load(cache)
        assert Counter(map(str, restored.eval(S.binding_owner(S.a)))) == expected


def test_binding_records_leave_with_failed_loads_clear_and_release(tmp_path):
    """Reference ownership is private state, so inspect its resource rows."""
    program = tmp_path / "failed.metta"
    program.write_text(
        "(= (binding-failed $x) (match &self (failed-edge $x $y) $y)) "
        "!(+ $left $right)"
    )
    with MeTTa() as m:
        with m.space() as source:
            name = str(source.name)
            with pytest.raises(EngineError):
                source.load(program)
            assert source.source() == ""
            assert m.runtime.once(
                "aggregate_all(count, "
                "filereader:translated_equation_binding(Space, _, _), Count)",
                Space=name,
            )["Count"] == 0
            source.run("(= (binding-cleared &self) held)")
            assert m.runtime.once(
                "aggregate_all(count, "
                "filereader:translated_equation_binding(Space, _, _), Count)",
                Space=name,
            )["Count"] == 1
            source.clear()
            assert m.runtime.once(
                "aggregate_all(count, "
                "filereader:translated_equation_binding(Space, _, _), Count)",
                Space=name,
            )["Count"] == 0
            source.run("(= (binding-released &self) held)")
        assert m.runtime.once(
            "aggregate_all(count, "
            "filereader:translated_equation_binding(Space, _, _), Count)",
            Space=name,
        )["Count"] == 0


@pytest.mark.parametrize("change", ["remove", "clear", "recompile"])
def test_rolled_back_binding_changes_keep_a_restorable_source(tmp_path, change):
    """Rollback restores the atom, executable clause and reference association."""
    path = tmp_path / "rollback.fast"
    definition = S["="](
        S.binding_rollback(V.x),
        S.match(S["&self"], S.rollback_edge(V.x, V.y), S.rollback_box(V.y)),
    )
    with MeTTa() as m, m.space() as source, m.space() as restored:
        source.add(S.rollback_edge(S.a, S.b))
        source.run(str(definition))

        def failing_change():
            if change == "remove":
                source.remove(definition)
            elif change == "clear":
                source.clear()
            else:
                source.run("(= (rollback-box $x) changed)")
            message = "discard binding change"
            raise RuntimeError(message)

        with pytest.raises(RuntimeError, match="discard binding change"):
            source.transaction(failing_change)
        source.save(path, format="fast")
        restored.load(path)
        assert restored.source() == source.source()
        for space in (source, restored):
            assert list(map(str, space.eval(S.binding_rollback(S.a)))) == [
                "(rollback-box b)"
            ]


@pytest.mark.parametrize(
    "bindings",
    [
        "[binding(0, [=, [f, X], X])]",
        "[binding(-1, [=, [f, X], X])]",
        "[binding(18446744073709551616, [=, [f, X], X])]",
        "[binding(1.0, [=, [f, X], X])]",
        "[binding(1, [=, [f, X], X]), binding(1, [=, [f, X], X])]",
        "[binding(1, _)]",
        "[binding(1, [=, [_F, X], X])]",
        "[binding(1, [=, [f, X], '$metta_fast_space_ref'(1)])]",
    ],
)
def test_fast_load_refuses_malformed_equation_bindings(tmp_path, bindings):
    """A valid hash does not make malformed provenance a loadable program."""
    path = tmp_path / "bindings.fast"
    payload_path = tmp_path / "payload.bin"
    with MeTTa() as m, m.space() as target:
        target.add(S.kept(S.value))
        target.save(path, format="fast")
        header = path.read_bytes().split(b"\n", 1)[0].rsplit(b"\t", 1)[0]
        # fastrw is engine-owned; use its writer to exercise the public loader
        # past the integrity check with intentionally invalid metadata.
        m.runtime.must(
            "term_string(_Image, Text), "
            "setup_call_cleanup(open(Path, write, _Out, [type(binary)]), "
            "fast_write(_Out, _Image), close(_Out))",
            Text=(
                "metta_fast_image([space(0, root, [[=, [f, X], X]], "
                f"{bindings})], [], [], [])"
            ),
            Path=str(payload_path),
        )
        payload = payload_path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest().encode()
        path.write_bytes(header + b"\t" + digest + b"\n" + payload)
        with pytest.raises(EngineError, match="corrupt or incomplete"):
            target.load(path)
        assert target.source() == "(kept value)\n"


try:
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st
except ModuleNotFoundError:
    pass
else:

    @settings(
        max_examples=40,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        st.lists(st.tuples(st.booleans(), st.integers(0, 4)), min_size=2, max_size=12),
        st.booleans(),
    )
    def test_fast_images_preserve_generated_overloaded_ingress(
        tmp_path, definitions, force_before_save
    ):
        """Partially compiled arities and duplicate ingress retain their bags."""
        equations = [
            "(= (generated-binding $x) (generated-plain $x))",
            "(= (generated-binding $x) "
            "(match &self (generated-edge $x $y) (generated-one $y)))",
            "(= (generated-binding $x $x) "
            "(match &self (generated-edge $x $y) (generated-pair $y)))",
            "(= (generated-binding a $y) "
            "(match &self (generated-edge a $y) (generated-ground $y)))",
            "(= (generated-binding (wrapped $x)) "
            "(match &self (generated-edge $x $y) (generated-nested $y)))",
        ]
        queries = [
            S.generated_binding(S.a),
            S.generated_binding(S.a, S.a),
            S.generated_binding(S.a, S.b),
            S.generated_binding(S.wrapped(S.a)),
        ]
        path = tmp_path / "generated-bindings.fast"
        with MeTTa() as m, m.space() as source, m.space() as restored:
            source.add(S.generated_edge(S.a, S.b), S.generated_edge(S.a, S.b))
            for reader, shape in definitions:
                if reader:
                    source.run(equations[shape])
                else:
                    source.add(source.parse(equations[shape]))
            if force_before_save:
                query_index = 1 if definitions[0][1] in (2, 3) else 0
                source.eval(queries[query_index])
            source.save(path, format="fast")
            restored.load(path)
            assert restored.source() == source.source()
            for query in queries:
                outcomes = []
                for space in (source, restored):
                    try:
                        outcomes.append(Counter(map(str, space.eval(query))))
                    except EngineError as error:
                        outcomes.append(str(error).replace(space.name, "&space"))
                assert outcomes[0] == outcomes[1]
