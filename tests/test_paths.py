"""Purpose: prove lazy query paths project live opaque values without copies.
Guarantees:
  - path markers join stored facts to current object fields and stop at cycles
    [tested: test_a_path_reaches_into_a_handle_without_converting_it;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from petta import Key, S, V, path, val


def test_a_path_reaches_into_a_handle_without_converting_it(metta):
    class Profile:
        def __init__(self, age):
            self.age = age
            self.loop = self

        def __iter__(self):
            raise AssertionError("the opaque object was eagerly converted")

    profile = Profile(31)
    with metta.new_space() as space:
        space.add(
            S.manager(S.ada, val(profile)),
            S.band(31, S.senior),
            S.record(val({"score": 7})),
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
