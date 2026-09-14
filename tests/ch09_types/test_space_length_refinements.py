"""Purpose: apply length contracts to native and foreign space values.

Guarantees: live contents and owner metadata decide the contract; names and
enumeration do not substitute for a length [tested:
test_native_space_length_refinements_follow_live_contents,
test_foreign_space_length_refinements_use_the_owner,
test_foreign_space_length_failures_preserve_the_owner_error; commit=d336b911f0d727b50a5660eb86f5ed44b35303b5].
Owns resources: fixtures explicitly drop named spaces and unregister providers.
"""

from contextlib import contextmanager

import pytest

from metta import S, Space
from metta._declare import declarations
from metta._errors.errors import EngineError
from metta.foreign import SpaceProvider


@contextmanager
def _native_space(metta, parametric):
    home = Space(S["length-space"](1.0)) if parametric else metta._new_space()
    try:
        yield home
    finally:
        home.drop()


@pytest.mark.parametrize("parametric", [False, True])
def test_native_space_length_refinements_follow_live_contents(scratch_space, parametric):
    """Cached typed calls recheck each store after writes and removals."""
    scratch_space.run("""
        (: nonempty (-> (Annotated SpaceType (MinLen 1)) Number))
        (= (nonempty $space) 7)
        (: no-more-than-one (-> (Annotated SpaceType (MaxLen 1)) Number))
        (= (no-more-than-one $space) 9)
    """)
    with _native_space(scratch_space, parametric) as home:
        scratch_space.add(
            S[":"](S["current-store"], S["->"](S.Annotated(S.SpaceType, S.MinLen(1)))),
            S["="](S["current-store"](), home),
        )
        identity = scratch_space.eval(S.id(home))
        assert len(identity) == 1
        for count in range(4):
            if count:
                home.add(S.entry(count))
            lower = scratch_space.eval(S.nonempty(home))
            upper = scratch_space.eval(S["no-more-than-one"](home))
            assert lower == ([7] if count else [
                S.Error(S.nonempty(home), S.BadArgValue(1, S.MinLen(1), home))
            ])
            assert upper == ([9] if count <= 1 else [
                S.Error(S["no-more-than-one"](home), S.BadArgValue(1, S.MaxLen(1), home))
            ])
            returned = scratch_space.eval(S["current-store"]())
            assert returned == (identity if count else [
                S.Error(S["current-store"](), S.BadReturnValue(S.MinLen(1), home))
            ])
        home.clear()
        assert scratch_space.eval(S["no-more-than-one"](home)) == [9]
        assert scratch_space.eval(S.nonempty(home))[0].head == S.Error


class _LengthOwner(SpaceProvider):
    def __init__(self, size):
        self.size = size
        self.reads = 0

    def __len__(self):
        self.reads += 1
        return self.size

    def atoms(self):
        msg = "a length refinement must not enumerate"
        raise AssertionError(msg)


@pytest.mark.parametrize("size", [0, 1, 1_000_000])
def test_foreign_space_length_refinements_use_the_owner(scratch_space, size):
    """The Sized promise reaches a native length contract without reading atoms."""
    provider = _LengthOwner(size)
    name = "&python-sized-refinement"
    declarations._register_space(scratch_space, provider, name)
    try:
        scratch_space.run(
            f"(: exact-size (-> (Annotated SpaceType (Len {size} {size})) Number))"
            "(= (exact-size $space) 7)"
        )
        home = scratch_space._at(name)
        assert scratch_space.eval(S["exact-size"](home)) == [7]
        assert provider.reads >= 1
    finally:
        declarations._unregister_space(scratch_space, name)


@pytest.mark.parametrize("kind", ["unsized", "raising"])
def test_foreign_space_length_failures_preserve_the_owner_error(scratch_space, kind):
    """Missing and failed length queries retain their errors without a scan."""
    class Unsized(SpaceProvider):
        def atoms(self):
            msg = "a failed length query must not enumerate"
            raise AssertionError(msg)

    class Raising(Unsized):
        def __len__(self):
            msg = "provider length failed"
            raise RuntimeError(msg)

    provider = Unsized() if kind == "unsized" else Raising()
    name = "&python-refused-length"
    declarations._register_space(scratch_space, provider, name)
    try:
        scratch_space.run(
            "(: sized (-> (Annotated SpaceType (MinLen 1)) Number))"
            "(= (sized $space) 7)"
        )
        reason = "does not implement __len__" if kind == "unsized" else "provider length failed"
        with pytest.raises(EngineError, match=reason):
            scratch_space.eval(S.sized(scratch_space._at(name)))
    finally:
        declarations._unregister_space(scratch_space, name)


def test_foreign_space_length_does_not_choose_a_value_for_a_variable(scratch_space):
    """An owner recognizes a supplied value instead of enumerating its registry."""
    provider = _LengthOwner(1)
    name = "&python-length-variable"
    declarations._register_space(scratch_space, provider, name)
    try:
        answer = scratch_space.runtime.once(
            "(once(seam:grounded_length(_Value, _Length)) -> Claimed=true; Claimed=false),"
            "(var(_Value) -> Unbound=true; Unbound=false)"
        )
        assert answer["Claimed"] == "false"
        assert answer["Unbound"] == "true"
        assert provider.reads == 0
    finally:
        declarations._unregister_space(scratch_space, name)
