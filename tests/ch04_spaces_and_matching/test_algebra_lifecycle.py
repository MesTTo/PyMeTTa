"""Purpose: keep algebra declarations inside their named or pooled space life.

Guarantees:
  - dropping a space removes its algebra before the name can be reused
    [tested: test_drop_retires_algebra_before_redeclaration; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
  - transaction rollback restores the exact algebra mirror preimage, including
    nested declarations [tested: test_rollback_releases_an_algebra_mirror,
    test_rollback_restores_a_replaced_algebra_mirror; commit=074dc0a88b1605c54824de677d586b6f60998bcf]
"""
import importlib
from contextlib import ExitStack

import pytest

from metta import S


@pytest.mark.parametrize("named", [True, False])
def test_drop_retires_algebra_before_redeclaration(metta, named):
    """Named and pooled space names begin their next algebra life empty."""
    algebra = importlib.import_module("metta.algebra")
    with ExitStack() as cleanup:
        first = metta._at("&algebra-lifecycle") if named else metta._new_space()
        cleanup.callback(first.drop)
        name = first.name
        first.algebra("local-product", combine="+", extend="*", zero=0, one=1)
        first.annotations("local-product")
        assert algebra.require(first, "local-product").combine == "+"
        first.drop()
        # metta_py_pool_space appends behind names released by earlier tests.
        attempts = 1 if named else metta.runtime.must(
            "aggregate_all(count, metta_py_free_space(_), N)"
        )["N"]
        second = None
        for _ in range(attempts):
            candidate = metta._at(name) if named else metta._new_space()
            cleanup.callback(candidate.drop)
            if candidate.name == name:
                second = candidate
                break
        assert second is not None
        with pytest.raises(algebra.AlgebraDeclarationError, match="algebra_not_declared"):
            algebra.require(second, "local-product")
        assert not second.runtime.once(
            "metta_catalog_row([annotations, Ctx|_])", Ctx=second.name
        )
        second.algebra("local-product", combine="max", extend="*", zero=0, one=1)
        second.add_tagged_fact(2, S.input(S.a))
        second.add_tagged_rule(3, S.output(S.a), S.input(S.a))
        assert second.match(S.output(S.a), under="local-product").one().annotation == 6
        assert algebra.require(second, "local-product").combine == "max"


@pytest.mark.parametrize("nested", [False, True])
def test_rollback_releases_an_algebra_mirror(metta, nested):
    """An aborted transaction retains neither catalog row nor Python mirror."""
    algebra = importlib.import_module("metta.algebra")
    with metta._new_space() as space:
        key = algebra._key(space, str(space.name), "rolled-back-carrier")

        def declare():
            space.algebra("rolled-back-carrier", combine="max", extend="*",
                          zero=0, one=1, type=int)

        def abort():
            if nested:
                space.transaction(declare)
            else:
                declare()
            msg = "abort algebra declaration"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="abort algebra declaration"):
            space.transaction(abort)
        assert not space.runtime.once(
            "metta_catalog_row([algebra,'rolled-back-carrier',_,_,_,_,_,_,_,Ctx])",
            Ctx=space.name,
        )
        assert key not in algebra._REGISTRY


def test_rollback_restores_a_replaced_algebra_mirror(metta):
    """A replacement rollback restores the original declaration object."""
    algebra = importlib.import_module("metta.algebra")
    with metta._new_space() as space:
        original_row = space.algebra("replaced-carrier", combine="max", extend="*",
                                     zero=0, one=1, type=int)
        original = algebra.require(space, "replaced-carrier")
        key = algebra._key(space, str(space.name), "replaced-carrier")

        def replace_and_abort():
            space._at("&metta").remove(original_row)
            space.algebra("replaced-carrier", combine="+", extend="*",
                          zero=0.0, one=1.0, type=float)
            msg = "abort algebra replacement"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="abort algebra replacement"):
            space.transaction(replace_and_abort)
        assert algebra._REGISTRY[key][1] is original
        assert algebra.require(space, "replaced-carrier") is original
        assert original.type is int
