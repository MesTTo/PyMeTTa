"""Purpose: prove restricted execution modules expose only creation grants.
Guarantees:
  - file, process, and network operations name their missing capability before
    they run [tested:
    test_a_restricted_space_cannot_reach_what_its_base_does_not_publish;
    commit=6a08901f4125c2536f5b4032daac9937f793870f]
  - dropping an anonymous restricted space removes its policy before the name
    is reused [tested test_a_recycled_name_retains_no_restriction]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import asyncio

import pytest

from petta import S, SpaceCapabilityError, aio


def test_a_restricted_space_cannot_reach_what_its_base_does_not_publish(
    metta, tmp_path
):
    path = tmp_path / "visible.txt"
    path.write_text("visible")

    with metta.new_space(restricted=True) as locked:
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
            ) == (locked.space_name, operation, capability)

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

    with metta.new_space(restricted=True, grants=("file",)) as reader:
        assert reader.run(f'!(exists_file "{path}")') == [[True]]
        with pytest.raises(SpaceCapabilityError) as caught:
            reader.run("!(argv 0)")
        assert caught.value.capability == "process"


def test_a_restricted_space_cannot_evalc_or_write_into_self(metta):
    with metta.new_space() as victim:
        with metta.new_space(restricted=True) as locked:
            with pytest.raises(SpaceCapabilityError) as evalc_error:
                locked.run(f"!(evalc (+ 1 2) {victim.space_name})")
            assert evalc_error.value.operation == "evalc"

            with pytest.raises(SpaceCapabilityError) as write_error:
                locked.run(f"!(add-atom {victim.space_name} (escaped write))")
            assert write_error.value.operation == "add-atom"
            assert not victim.query(S.escaped(S.write))


def test_a_recycled_name_retains_no_restriction(metta):
    restricted = metta.new_space(restricted=True)
    name = restricted.space_name
    restricted.drop()

    metta.runtime.must("retract(petta_py_free_space(Name))", Name=name)
    recycled = metta.space(name)
    try:
        assert recycled.space_name == name
        assert recycled.run("!(argv 0)")
    finally:
        recycled.drop()


def test_restricted_constructor_validation_is_eager(metta):
    with pytest.raises(ValueError, match="grants require"):
        metta.new_space(grants=("file",))
    with pytest.raises(ValueError, match="unknown space capabilities"):
        metta.new_space(restricted=True, grants=("gpu",))
    with metta.new_space() as parent:
        with pytest.raises(ValueError, match="both inherited and restricted"):
            metta.new_space(inherits=parent, restricted=True)


def test_async_new_space_forwards_restriction_and_grants(metta, tmp_path):
    path = tmp_path / "async-visible.txt"
    path.write_text("visible")

    async def exercise():
        async with aio.AsyncMeTTa(metta=metta) as runtime:
            locked = await runtime.new_space(restricted=True)
            try:
                with pytest.raises(SpaceCapabilityError):
                    await locked.run(f'!(exists_file "{path}")')
            finally:
                await locked.drop()

            reader = await runtime.new_space(restricted=True, grants=("file",))
            try:
                assert await reader.run(f'!(exists_file "{path}")') == [[True]]
            finally:
                await reader.drop()

    asyncio.run(exercise())
