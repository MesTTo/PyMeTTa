"""Purpose: prove lazy query paths project live opaque values without copies.
Guarantees:
  - path markers join stored facts to current object fields and stop at cycles
    [tested: test_a_path_reaches_into_a_handle_without_converting_it;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from petta import S, V, ground
from petta.paths import Key, path


def test_a_path_reaches_into_a_handle_without_converting_it(metta):
    """Prove a path marker joins stored facts to live object fields without converting the opaque handle."""

    class Profile:
        def __init__(self, age):
            self.age = age
            self.loop = self

        def __iter__(self):
            msg = "the opaque object was eagerly converted"
            raise AssertionError(msg)

    profile = Profile(31)
    with metta._new_space() as space:
        space.add(
            S.manager(S.ada, ground(profile)),
            S.band(31, S.senior),
            S.record(ground({"score": 7})),
        )

        rows = space.query(
            S.manager(V.who, path("age", to=V.age)),
            S.band(V.age, V.band),
        )
        assert rows.columns == ("who", "age", "band")
        assert rows.to_dicts() == [{"who": "ada", "age": 31, "band": "senior"}]

        profile.age = 32
        space.add(S.band(32, S.current))
        assert space.query(
            S.manager(S.ada, path("age", to=V.age)),
            S.band(V.age, V.band),
        ).to_dicts() == [{"age": 32, "band": "current"}]

        assert space.query(S.record(path(Key("score"), to=V.score))).to_dicts() == [
            {"score": 7}
        ]
        assert not space.query(S.manager(S.ada, path("loop", "age", to=V.age)))
