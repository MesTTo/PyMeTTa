"""Purpose: distinguish Python twin families by their installed ownership.

Guarantees:
  - independent declarations, aliases and retained twins keep their own
    clauses while replacement follows the owning native head [tested:
    test_twin_families_follow_their_definition_space,
    test_same_python_name_can_have_distinct_native_twin_heads,
    test_twin_aliases_follow_exact_installed_functions,
    test_clear_starts_a_new_twin_family; commit=WORKTREE]
  - recursive clause selection stays within its owner and released source
    functions are collectible [tested:
    test_recursive_twin_clauses_keep_their_definition_space,
    test_released_twin_namespace_does_not_retain_source_functions;
    commit=WORKTREE]
  - compiling source alone cannot publish a twin or alter installed twins
    [tested: test_pure_compilation_does_not_publish_twin_bindings;
    commit=WORKTREE]
"""

import gc
import weakref

import pytest

from metta._declare.define import compile_function


def _offset_source(offset):
    def twin_value(value: int) -> int:
        return value + offset

    return twin_value


def _source_user(source):
    def twin_user(value: int) -> int:
        return source(value) * 2

    return twin_user


def _plain_helper(value: int) -> int:
    return value + 7


def _plain_user(value: int) -> int:
    return _plain_helper(value) * 2


def _recursive_family(space, offset):
    @space.define
    def twin_recurse(value=0):  # noqa: ARG001 -- the default is the clause head pattern
        return offset

    @space.define
    def twin_recurse(value):  # noqa: F811 -- stacked recursive clauses are the contract
        return twin_recurse(value - 1) + 1

    return twin_recurse


@pytest.mark.parametrize("offsets", [(10, 20), (0, -7), (-4, 0)])
def test_twin_families_follow_their_definition_space(metta, offsets):
    """Equal spellings in independent spaces retain different closures."""
    with metta._new_space() as left, metta._new_space() as right:
        functions = [
            space.define(_offset_source(offset))
            for space, offset in zip((left, right), offsets, strict=True)
        ]
        for function, offset in zip(functions, offsets, strict=True):
            assert function(1).one() == function.py(1) == offset + 1


def test_same_python_name_can_have_distinct_native_twin_heads(metta):
    """Explicit native heads remain independent within one owner."""
    with metta._new_space() as space:
        first = space.define(_offset_source(10), name="twin-left")
        second = space.define(_offset_source(20), name="twin-right")
        assert first(1).one() == first.py(1) == 11
        assert second(1).one() == second.py(1) == 21


@pytest.mark.parametrize("reference", ["source", "defined"])
def test_twin_aliases_follow_exact_installed_functions(metta, reference):
    """A captured function resolves its installed family through aliases."""
    with metta._new_space() as space:
        original = _offset_source(10)
        defined = space.define(original, name="twin-aliased-source")
        source = original if reference == "source" else defined
        user = space.define(_source_user(source), name="twin-alias-user")
        assert user(1).one() == user.py(1) == 22
        space.define(_offset_source(20), name="twin-aliased-source")
        assert user(1).one() == user.py(1) == 42


def test_clear_starts_a_new_twin_family(metta):
    """A retained twin keeps its clauses after the owner clears them."""
    with metta._new_space() as space:
        first = space.define(_offset_source(10))
        kept = first.py
        space.clear()
        second = space.define(_offset_source(20))
        assert second(1).one() == second.py(1) == 21
        assert kept(1) == 11


def test_pure_compilation_does_not_publish_twin_bindings(metta):
    """Reading a helper's source leaves an installed caller's twin intact."""
    with metta._new_space() as space:
        caller = space.define(_plain_user)
        assert caller.py(1) == 16
        compiled = compile_function(_plain_helper, known=lambda _name: False)
        assert compiled.twin(1) == 8
        assert caller.py(1) == 16


def test_recursive_twin_clauses_keep_their_definition_space(metta):
    """Recursive dispatch selects the literal clause from the same family."""
    with metta._new_space() as left, metta._new_space() as right:
        first = _recursive_family(left, 10)
        second = _recursive_family(right, 20)
        for count in range(7):
            assert first(count).one() == first.py(count) == 10 + count
            assert second(count).one() == second.py(count) == 20 + count


def test_released_twin_namespace_does_not_retain_source_functions(metta):
    """Dropping a space retires its source-function and twin references."""
    with metta._new_space() as space:
        source = _offset_source(10)
        observed = weakref.ref(source)
        defined = space.define(source)
        assert defined.py(1) == 11
    del source, defined
    gc.collect()
    assert observed() is None
