"""Purpose: the MORK space through the python surface. &mork is
trueagi-io/MORK behind mork_ffi, hooked into the engine's own space
predicates, so adds, removes, queries, joins, subscriptions, count,
digest, and MM2 exec all run the ordinary petta surface with MORK as
the store. Writes queue inside MORK and every read flushes first, so
read-your-writes holds without an explicit flush. Skips whole when the
native library is not built.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os

import pytest

from petta import S, V

_MORKLIB = os.path.join(
    os.path.dirname(__file__), "..", "..", "mork_ffi", "target", "release",
    "libmork_ffi.so",
)
pytestmark = pytest.mark.skipif(
    not os.path.isfile(_MORKLIB),
    reason="mork_ffi is not built; run sh build.sh at the repo root",
)


@pytest.fixture()
def mork(metta):
    space = metta.space("&mork")
    yield space
    for atom in space.atoms():
        space.remove(atom)


def test_writes_queue_and_reads_see_them(mork):
    mork.add(S.friend(S.sam, S.tim), S.friend(S.sam, S.joe))
    rows = mork.query(S.friend(S.sam, V.x))
    assert sorted(str(row.x) for row in rows) == ["joe", "tim"]
    assert mork.count() == 2


def test_joins_are_the_engines_joins_over_mork_conjuncts(mork):
    mork.add(S.friend(S.sam, S.tim), S.friend(S.sam, S.joe), S.age(S.tim, 30))
    join = mork.query(S.friend(S.sam, V.x), S.age(V.x, V.n))
    assert [(row.x, row.n) for row in join] == [(S.tim, 30)]


def test_remove_and_atoms_enumeration(mork):
    mork.add(S.mk(S.a), S.mk(S.b))
    assert mork.remove(S.mk(S.a)) is True
    assert [str(atom) for atom in mork.atoms()] == ["(mk b)"]


def test_subscriptions_see_mork_writes(mork):
    seen = []
    sub = mork.subscribe(S.watched(V.x), lambda e: seen.append(e))
    try:
        mork.add(S.watched(S.one), S.other(S.two))
        assert len(seen) == 1
        assert seen[0].bindings["x"] == S.one
    finally:
        sub.cancel()


def test_digest_names_mork_content_too(mork, metta):
    mork.add(S.dgm(1), S.dgm(2))
    first = mork.digest()
    assert len(first) == 64
    with metta.fresh_space() as native:
        native.add(S.dgm(2), S.dgm(1))
        assert native.digest() == first


def test_mm2_exec_transforms_inside_mork(mork, metta):
    metta.run("!(import! &self (library lib_mm2))")
    mork.add(S.friend(S.sam, S.tim))
    metta.run(
        "!(~> (, (friend sam $x)) (O (- (friend sam $x)) (+ (enemy sam $x))))"
    )
    rows = mork.query(S.enemy(S.sam, V.x))
    assert [row.x for row in rows] == [S.tim]
    assert not mork.query(S.friend(S.sam, V.x))


@pytest.fixture()
def named_pair(metta):
    alpha = metta.space("&mork:iso-alpha")
    beta = metta.space("&mork:iso-beta")
    yield alpha, beta
    for space in (alpha, beta):
        for atom in space.atoms():
            space.remove(atom)


def test_named_mork_spaces_are_isolated(named_pair, mork):
    alpha, beta = named_pair
    alpha.add(S.only(S.alpha))
    beta.add(S.only(S.beta))
    assert [str(a) for a in alpha.atoms()] == ["(only alpha)"]
    assert [str(a) for a in beta.atoms()] == ["(only beta)"]
    assert not mork.query(S.only(V.x))  # the default space saw nothing


def test_bulk_add_lands_in_one_crossing(metta, named_pair):
    alpha, _ = named_pair
    stored = metta.runtime.once(
        "findall(_A, (between(1, 500, _I), _A = [bulked, _I]), _L),"
        " 'mork-add-atoms'('&mork:iso-alpha', _L, true),"
        " aggregate_all(count,"
        "   ('get-atoms'('&mork:iso-alpha', _P), _P = [bulked, _]), N)"
    )["N"]
    assert stored == 500
    assert len(alpha.query(S.bulked(V.i))) == 500


try:
    from hypothesis import HealthCheck, given, settings
except ModuleNotFoundError:
    pass
else:
    from petta.testing import expressions

    @settings(
        max_examples=25,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(expressions(max_leaves=6, ground=True))
    def test_generated_expressions_round_trip_through_mork(metta, atom):
        """MORK's own parser and printer agree with the engine's on
        whatever the strategy generates: what goes in comes back."""
        space = metta.space("&mork:fuzz")
        try:
            space.add(atom)
            assert atom in [a for a in space.atoms()]
        finally:
            for stored in space.atoms():
                space.remove(stored)
