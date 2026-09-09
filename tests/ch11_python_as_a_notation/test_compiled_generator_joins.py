"""Purpose: prove generator joins preserve live bindings with linear emitted size."""

import importlib.util

import pytest

from metta import Expression, S, superpose
from metta._errors.errors import CompileError


def _atom_size(atom):
    return 1 + sum(map(_atom_size, atom)) if isinstance(atom, Expression) else 1


def _chain(tmp_path, count):
    name = f"chain_{count}"
    source = [f"def {name}(flag, value: int):"]
    for _ in range(count):
        source.extend([
            "    if flag:",
            "        value = value + 1",
            "        yield value",
            "    else:",
            "        value = value + 2",
        ])
    source.append("    yield value")
    path = tmp_path / f"{name}.py"
    path.write_text("\n".join(source) + "\n")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


def test_generator_join_size_is_linear_across_sequential_conditionals(scratch_space, tmp_path):
    """Count every stored helper too, so moving duplication cannot hide it."""
    m = scratch_space
    sizes = []
    for count in (1, 2, 4, 8):
        with m.stats() as measured:
            function = m.define(_chain(tmp_path, count))
        clauses = [
            atom for atom in m.atoms()
            if isinstance(atom, Expression) and atom.head == S["="]
            and isinstance(atom[1], Expression)
            and str(atom[1].head).startswith(function.name)
        ]
        size = sum(map(_atom_size, clauses))
        sizes.append(size)
        print(f"JOIN_SWEEP n={count} atoms={size} compile_inferences={measured.inferences}")
        assert list(function(flag=False, value=0)) == [2 * count]
        assert list(function(flag=True, value=0)) == [*range(1, count + 1), count]
    step = sizes[1] - sizes[0]
    assert [sizes[2] - sizes[1], sizes[3] - sizes[2]] == [2 * step, 4 * step]


def test_generator_join_reads_only_values_live_before_continuation_writes(scratch_space):
    """An overwritten input is not a helper argument, including writes in both arms."""
    @scratch_space.define
    def overwritten(flag):
        if flag:
            value = [1]
        value = 8
        yield value

    @scratch_space.define
    def overwritten_in_both_arms(flag):
        if flag:
            value = [1]
        if flag:
            value = 4
        else:
            value = 9
        yield value

    assert list(overwritten(flag=False)) == [8]
    assert list(overwritten(flag=True)) == [8]
    assert list(overwritten_in_both_arms(flag=False)) == [9]
    assert list(overwritten_in_both_arms(flag=True)) == [4]


def test_generator_join_refuses_a_possibly_unbound_live_value(scratch_space):
    """A read after a partial binding gets a precise remedy."""
    def missing(flag):
        if flag:
            value = 1
        yield value

    with pytest.raises(CompileError, match=r"value.*not bound.*bind.*every"):
        scratch_space.define(missing)


def test_generator_join_retains_same_species_and_native_number_proofs(scratch_space):
    """Every incoming edge contributes its container and numeric proofs."""
    @scratch_space.define
    def selected(flag):
        if flag:
            mapping = {1: 4}
            values = [1]
            number = 2
        else:
            mapping = {1: 9}
            values = [2]
            number = 3
        yield mapping[1]
        yield values + [number]  # noqa: RUF005 -- exercise list concatenation
        yield number + 1

    assert list(selected(flag=True)) == [4, Expression([1, 2]), 3]
    assert list(selected(flag=False)) == [9, Expression([2, 3]), 4]
    helpers = "\n".join(str(atom) for atom in scratch_space.atoms())
    assert "(get-value " in helpers
    assert "(+ " in helpers


def test_generator_join_intersects_numeric_proofs(scratch_space):
    """An unknown scalar arm prevents an unsafe native-number assumption."""
    @scratch_space.define
    def selected(flag, unknown):
        if flag:
            value = 2
        else:
            value = unknown
        yield value + value

    assert list(selected(flag=True, unknown="a")) == [4]
    assert list(selected(flag=False, unknown="a")) == ["aa"]


def test_generator_join_refuses_incompatible_live_container_images(scratch_space):
    """A representation disagreement refuses instead of changing container species."""
    def selected(flag):
        if flag:
            value = [1]
        else:
            value = (1,)
        yield value + value

    with pytest.raises(CompileError, match=r"value.*representation.*same.*arm"):
        scratch_space.define(selected)


def test_generator_join_lexical_reads_respect_comprehension_and_lambda_binders(scratch_space):
    """Nested binders do not demand a shadowed value from a previous arm."""
    @scratch_space.define
    def selected(flag):
        if flag:
            item = 8  # noqa: F841 -- the following nested binders shadow it
        values = [item + 1 for item in (1, 2)]
        yield values
        function = lambda item: item + 2  # noqa: E731
        yield function(3)

    assert list(selected(flag=False)) == [Expression([2, 3]), 5]
    assert list(selected(flag=True)) == [Expression([2, 3]), 5]


def test_generator_join_nested_match_empty_and_raise_paths(scratch_space):
    """Only falling-through nested branches call the shared continuation."""
    @scratch_space.define
    def selected(flag, subject):
        value = 0
        if flag:
            match subject:
                case (S.Item, captured):
                    value = captured
                case _:
                    yield 5
                    message = "closed"
                    raise ValueError(message)
        else:
            match superpose():
                case S.Empty:
                    value = 8
        yield value

    assert list(selected(flag=True, subject=S.Item(3))) == [3]
    assert list(selected(flag=False, subject=S.Other)) == [8]
    raised = list(selected(flag=True, subject=S.Other))
    assert raised[0] == 5
    assert len(raised) == 2
    assert raised[1].head == S.Error


def test_generator_join_live_reads_include_augmented_values_and_free_lambda_names(scratch_space):
    """Read-modify-write and lexical closures carry their input values."""
    @scratch_space.define
    def selected(flag):
        if flag:
            value = 2
        else:
            value = 8
        value += 1
        function = lambda item: item + value  # noqa: E731
        yield function(3)

    assert list(selected(flag=True)) == [6]
    assert list(selected(flag=False)) == [12]


def test_generator_join_empty_yield_stream_does_not_prune_the_continuation(scratch_space):
    """An answerless yield still falls through once with its updated bindings."""
    @scratch_space.define
    def selected(flag):
        if flag:
            value = 2
            yield superpose()
        else:
            value = 8
        yield value

    assert list(selected(flag=True)) == [2]
    assert list(selected(flag=False)) == [8]


def test_a_generator_walrus_refuses_as_an_unsupported_construct(scratch_space):
    """The liveness walk sees the walrus first, and must not blame liveness.

    A generator body cannot hoist a walrus, so every one refuses; the walk that
    gives the shared continuation its parameters runs BEFORE that refusal, and
    it treats the walrus target as a binding rather than a free read. Without
    that, `doubled` reads as unbound on the branch's other edge and the
    liveness check fires first with the wrong reason.
    """
    def hoisted(n):
        if n:
            yield 1
        total = (doubled := n * 2) + 1
        yield total
        yield doubled

    with pytest.raises(CompileError, match="NamedExpr has no MeTTa equivalent"):
        scratch_space.define(hoisted)
