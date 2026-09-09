"""Purpose: preserve source-owned metadata through public lifecycle operations.

Guarantees:
  - projection rows retain exact source occurrence ownership through reload,
    rollback, inheritance, duplicate removal and fast restoration
    [tested: test_metadata_projections_follow_public_lifecycle,
    test_metadata_projections_follow_reload_and_failed_load,
    test_metadata_owners_follow_local_shadowing; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
"""

from collections import Counter

import pytest

from metta import MeTTa, S, V
from metta._errors.errors import EngineError


def _assert_projection(space):
    # There is no public clause-reference enumeration. Public answers alone
    # cannot detect an orphaned projection that a later module life could read.
    space.runtime.must(
        "space_module(Space, _M), "
        "findall(_Ref, clause(translator:fun_meta_clause(_M, _, _, _), true, _Ref), _Sources), "
        "findall(_Ref, translator:fun_meta_projection(_M, _, _Ref, _), _Projected), "
        "msort(_Sources, _Sorted), msort(_Projected, _Sorted), "
        "findall(_HeadRef, clause(translator:fun_meta_head(_M, _, _), true, _HeadRef), _Heads), "
        "findall(_HeadRef, translator:fun_meta_projection(_M, _, _, _HeadRef), _Linked), "
        "msort(_Heads, _SortedHeads), msort(_Linked, _SortedHeads), "
        "forall(translator:fun_meta_projection(_M, _F, _Ref, _HeadRef), "
        "(clause(translator:fun_meta_clause(_M, _F, _Args, _), true, _Ref), "
        "clause(translator:fun_meta_head(_M, _F, _Head), true, _HeadRef), _Args =@= _Head))",
        Space=space.name,
    )


@pytest.mark.parametrize("change", ["remove", "clear", "recompile"])
def test_metadata_projections_follow_public_lifecycle(tmp_path, change):
    """Rollback and fast restoration preserve every duplicate occurrence."""
    path = tmp_path / "metadata.fast"
    definition = S["="](S.metadata_lifecycle(V.x), S.metadata_payload(V.x))
    with MeTTa() as m, m.space() as source, m.space() as restored:
        source.run(f"{definition} {definition}")
        assert list(map(str, source.eval(S.metadata_lifecycle(S.a)))) == [
            "(metadata-payload a)", "(metadata-payload a)"
        ]
        _assert_projection(source)

        def failing_change():
            if change == "remove":
                source.remove(definition)
            elif change == "clear":
                source.clear()
            else:
                source.run("(= (metadata-payload $x) (changed $x))")
                assert list(map(str, source.eval(S.metadata_lifecycle(S.a)))) == [
                    "(changed a)", "(changed a)"
                ]
            _assert_projection(source)
            message = "discard metadata change"
            raise RuntimeError(message)

        with pytest.raises(RuntimeError, match="discard metadata change"):
            source.transaction(failing_change)
        _assert_projection(source)
        source.save(path, format="fast")
        restored.load(path)
        for space in (source, restored):
            assert Counter(map(str, space.eval(S.metadata_lifecycle(S.a)))) == {
                "(metadata-payload a)": 2
            }
            _assert_projection(space)
            assert space.remove(definition)
            assert list(map(str, space.eval(S.metadata_lifecycle(S.a)))) == [
                "(metadata-payload a)"
            ]
            _assert_projection(space)
            space.clear()
            _assert_projection(space)


def test_metadata_projections_follow_reload_and_failed_load(tmp_path):
    """A replacement and a failed first source load leave no stale index row."""
    program = tmp_path / "metadata.metta"
    program.write_text("(= (metadata-loaded) (+ 1 2))\n!(metadata-loaded)\n")
    with MeTTa() as m, m.space() as source:
        source.load(program)
        assert source.run("!(metadata-loaded)") == [[3]]
        _assert_projection(source)
        program.write_text(
            "(= (metadata-loaded) (+ 3 4))\n"
            "(= (metadata-loaded) (+ 3 4))\n!(metadata-loaded)\n"
        )
        source.load(program)
        assert source.run("!(metadata-loaded)") == [[7, 7]]
        _assert_projection(source)
        program.write_text("(= (metadata-loaded) 9)\n!(+ $a $b)\n")
        with pytest.raises(EngineError):
            source.load(program)
        assert source.run("!(metadata-loaded)") == [[7, 7]]
        _assert_projection(source)
        source.clear()
        _assert_projection(source)
        with pytest.raises(EngineError):
            source.load(program)
        assert source.source() == ""
        _assert_projection(source)


def test_metadata_owners_follow_local_shadowing():
    """A child reads its nearest source owner and regains the parent on removal."""
    with MeTTa() as m, m.space() as parent, m.space(inherits=parent) as child:
        parent.run("(= (metadata-owner $x) (parent $x))")
        assert list(map(str, child.eval(S.metadata_owner(S.a)))) == ["(parent a)"]
        _assert_projection(parent)
        _assert_projection(child)
        local = S["="](S.metadata_owner(V.x), S.local(V.x))
        child.run(f"{local} {local}")
        assert list(map(str, child.eval(S.metadata_owner(S.a)))) == [
            "(local a)", "(local a)"
        ]
        _assert_projection(child)
        assert child.remove(local)
        assert list(map(str, child.eval(S.metadata_owner(S.a)))) == ["(local a)"]
        assert child.remove(local)
        assert list(map(str, child.eval(S.metadata_owner(S.a)))) == ["(parent a)"]
        _assert_projection(parent)
        _assert_projection(child)
