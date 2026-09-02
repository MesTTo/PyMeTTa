"""Purpose: prove restricted execution modules expose only creation grants.

Guarantees:
  - file, process, and network operations name their missing capability before
    they run [tested:
    test_a_restricted_space_cannot_reach_what_its_base_does_not_publish;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - dropping an anonymous restricted space removes its policy before the name
    is reused [tested test_a_recycled_name_retains_no_restriction]
  - a NAMED space takes every model an anonymous one takes, on both the
    synchronous and the async door, because the engine's declarations take any
    valid space name [tested:
    test_a_named_space_takes_every_model_an_anonymous_one_takes,
    test_an_async_named_space_takes_a_model; commit=e3787593132a7ece2d300397045f7415709847c9]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import asyncio

import pytest

from metta import MeTTa, S, V, aio
from metta.errors import MettaError, SpaceCapabilityError


def test_a_restricted_space_cannot_reach_what_its_base_does_not_publish(metta, tmp_path):
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

        assert locked.run("!(unknown-restricted-data 1)") == [[S["unknown-restricted-data"](1)]]

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
            assert not victim.match(S.escaped(S.write))


def test_a_recycled_name_retains_no_restriction(metta):
    """Dropping a restricted space removes its policy before the name is reused."""
    restricted = metta._new_space(restricted=True)
    name = restricted.name
    restricted.drop()

    metta.runtime.must("retract(metta_py_free_space(Name))", Name=name)
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


def test_a_named_space_takes_every_model_an_anonymous_one_takes():
    """`!(new-space &locked (restricted))` has a Python spelling.

    A name and a MODEL are independent. The mint and the declaration used to be
    one engine predicate per model, so there was nowhere to put a caller's name
    and the door refused the pair; the engine itself never required anonymity,
    since metta_declare_restricted_space/2 and metta_declare_space_parent/2
    validate with metta_require_space_name/2 and accept any space name.
    """
    world = MeTTa()
    locked = world.space(S.namedlocked, restricted=True)
    assert str(locked.name) == "&namedlocked"

    @locked.define
    def namedlocked_double(x: int) -> int:
        return x * 2

    # A restricted space keeps ordinary computation and its own equations.
    assert locked.eval(S.namedlocked_double(21)) == [42]
    with pytest.raises(SpaceCapabilityError):
        locked.eval(S["exists_file"]("/etc/hostname"))

    # A grant reaches the named space exactly as it reaches an anonymous one.
    reader = world.space(S.namedreader, restricted=True, grants=("file",))
    # S["exists_file"] and not S.exists_file: the attribute door applies the
    # underscore-to-hyphen map, and this operation's name really does carry an
    # underscore, so the bracket door is the exact-spelling rung.
    assert reader.eval(S["exists_file"]("/etc/hostname")) == [True]

    # An inheriting child reads through its parent and writes only into itself.
    parent = world.space(S.namedparent)
    parent += S.rung(S.parent)
    child = world.space(S.namedchild, inherits=parent)
    child += S.rung(S.child)
    assert [row.x for row in child[S.rung(V.x)]] == [S.child, S.parent]
    assert [row.x for row in parent[S.rung(V.x)]] == [S.parent]


def test_redeclaring_a_named_model_agrees_or_says_so():
    """A space has ONE model, so a second declaration must agree."""
    world = MeTTa()
    first = world.space(S.twicelocked, restricted=True)
    again = world.space(S.twicelocked, restricted=True)
    assert str(first.name) == str(again.name)
    with pytest.raises(MettaError, match="already restricted"):
        world.space(S.twicelocked, restricted=True, grants=("file",))


def test_an_async_named_space_takes_a_model(metta):
    """The async door drops the same refusal, through the same declaration."""

    async def exercise():
        async with aio.AsyncMeTTa(metta=metta) as runtime:
            locked = await runtime.space("&asyncnamedlocked", restricted=True)
            assert str(locked.name) == "&asyncnamedlocked"
            with pytest.raises(SpaceCapabilityError):
                await locked.eval(S["exists_file"]("/etc/hostname"))

    asyncio.run(exercise())
