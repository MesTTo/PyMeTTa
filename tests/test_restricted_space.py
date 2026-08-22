"""Purpose: prove restricted execution modules expose only creation grants.

Guarantees:
  - file, process, and network operations name their missing capability before
    they run [tested:
    test_a_restricted_space_cannot_reach_what_its_base_does_not_publish;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - dropping an anonymous restricted space removes its policy before the name
    is reused [tested test_a_recycled_name_retains_no_restriction]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import asyncio

import pytest

from petta import S, aio
from petta.errors import SpaceCapabilityError


def test_a_restricted_space_cannot_reach_what_its_base_does_not_publish(
    metta, tmp_path
):
    """File, process, and network operations refuse by naming the missing capability."""
    path = tmp_path / "visible.txt"
    path.write_text("visible")

    with metta._new_space(restricted=True) as locked:
        assert locked.run("!(+ 20 22)") == [[42]]

        for source, operation, capability in [
            (f'!(exists_file "{path}")', "exists_file", "file"),
            ("!(argv 0)", "argv", "process"),
            (
                '!(git-import! "https://invalid.example/repo")',
                "git-import!",
                "network",
            ),
        ]:
            with pytest.raises(SpaceCapabilityError) as caught:
                locked.run(source)
            assert (
                caught.value.space,
                caught.value.operation,
                caught.value.capability,
            ) == (locked.name, operation, capability)

        with pytest.raises(SpaceCapabilityError) as computed:
            locked.run(f'!(let $operation exists_file ($operation "{path}"))')
        assert (computed.value.operation, computed.value.capability) == (
            "exists_file",
            "file",
        )

        with pytest.raises(SpaceCapabilityError) as raw:
            locked.run(f'!(translatePredicate (open "{path}" read $stream))')
        assert (raw.value.operation, raw.value.capability) == ("open", "file")

        assert locked.run("!(unknown-restricted-data 1)") == [
            [S["unknown-restricted-data"](1)]
        ]

    with metta._new_space(restricted=True, grants=("file",)) as reader:
        assert reader.run(f'!(exists_file "{path}")') == [[True]]
        with pytest.raises(SpaceCapabilityError) as caught:
            reader.run("!(argv 0)")
        assert caught.value.capability == "process"


def test_a_restricted_space_cannot_evalc_or_write_into_self(metta):
    """A restricted space cannot reach an unrestricted space through evalc or writes."""
    with metta._new_space() as victim:
        with metta._new_space(restricted=True) as locked:
            with pytest.raises(SpaceCapabilityError) as evalc_error:
                locked.run(f"!(evalc (+ 1 2) {victim.name})")
            assert evalc_error.value.operation == "evalc"

            with pytest.raises(SpaceCapabilityError) as write_error:
                locked.run(f"!(add-atom {victim.name} (escaped write))")
            assert write_error.value.operation == "add-atom"
            assert not victim.query(S.escaped(S.write))


def test_a_recycled_name_retains_no_restriction(metta):
    """Dropping a restricted space removes its policy before the name is reused."""
    restricted = metta._new_space(restricted=True)
    name = restricted.name
    restricted.drop()

    metta.runtime.must("retract(petta_py_free_space(Name))", Name=name)
    recycled = metta._at(name)
    try:
        assert recycled.name == name
        assert recycled.run("!(argv 0)")
    finally:
        recycled.drop()


def test_restricted_constructor_validation_is_eager(metta):
    """Malformed restriction and grant arguments refuse before any space exists."""
    with pytest.raises(ValueError, match="grants require"):
        metta._new_space(grants=("file",))
    with pytest.raises(ValueError, match="unknown space capabilities"):
        metta._new_space(restricted=True, grants=("gpu",))
    with metta._new_space() as parent:
        with pytest.raises(ValueError, match="both inherited and restricted"):
            metta._new_space(inherits=parent, restricted=True)


def test_async_space_forwards_restriction_and_grants(metta, tmp_path):
    """AsyncMeTTa.space forwards restricted= and grants= to the same policy."""
    path = tmp_path / "async-visible.txt"
    path.write_text("visible")

    async def exercise():
        async with aio.AsyncMeTTa(metta=metta) as runtime:
            locked = await runtime.space(restricted=True)
            try:
                with pytest.raises(SpaceCapabilityError):
                    await locked.run(f'!(exists_file "{path}")')
            finally:
                await locked.drop()

            reader = await runtime.space(restricted=True, grants=("file",))
            try:
                assert await reader.run(f'!(exists_file "{path}")') == [[True]]
            finally:
                await reader.drop()

    asyncio.run(exercise())
