"""Purpose: pin the seeded scope over the engine's random surface.
Assumes: SWI's generator answers `random_property(state(S))` and takes
  `set_random(state(S))` back, which is what makes the scope restorable.
Guarantees:
  - a seeded scope repeats its draws exactly, different seeds give different
    ones, and the generator outside the scope is where it was.
  [tested: test_a_seed_scope_repeats_its_draws_and_leaves_the_outside_alone; commit=WORKTREE]
Fails when: read as a claim about cryptographic quality. It is reproducibility,
  the property a simulation and a test need; the generator is SWI's own.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from petta import MeTTa


def _answers(metta: MeTTa, source: str) -> list[str]:
    """Return one runnable's answers in their stable textual form."""
    groups = metta.run(source)
    assert len(groups) == 1
    return [str(atom) for atom in groups[0]]


def test_a_seed_scope_repeats_its_draws_and_leaves_the_outside_alone() -> None:
    """A seed is the scope's, not the process's."""
    metta = MeTTa().space("&seeded")

    # The same scope answers the same thing, however often it is run.
    first = _answers(metta, "!(with-seed 42 (random-int 1 1000000))")
    assert first == _answers(metta, "!(with-seed 42 (random-int 1 1000000))")
    assert first == _answers(metta, "!(with-seed 42 (random-int 1 1000000))")

    # A different seed is a different sequence.
    assert _answers(metta, "!(with-seed 7 (random-int 1 1000000))") != first

    # Draws WITHIN a scope advance the generator, and the whole sequence
    # repeats.
    many = "!(with-seed 42 (collapse (superpose ((random-int 1 1000000) (random-int 1 1000000) (random-float 0.0 1.0)))))"
    assert _answers(metta, many) == _answers(metta, many)

    # The scope is dynamic: what happens outside it is unaffected by the seed,
    # so a seeded scope in the middle of a program does not make the rest of it
    # deterministic. Two unseeded draws either side of a seeded one are drawn
    # from the generator the scope restored, not from the seed.
    unseeded = [
        _answers(metta, "!(random-int 1 1000000000)")[0] for _ in range(6)
    ]
    seeded_between = [
        _answers(metta, "!(with-seed 42 (random-int 1 1000000000))")[0]
        for _ in range(6)
    ]
    assert len(set(seeded_between)) == 1
    assert len(set(unseeded)) > 1

    # A seed that is not a number ANSWERS in the error vocabulary and the form
    # after it still runs, which is what every other rejected operand does.
    assert _answers(metta, '!(with-seed "bad" (random-int 1 6))') == [
        '(Error (with-seed "bad" (random-int 1 6)) (BadArgType 1 Number String))'
    ]
    assert _answers(
        metta, '!(if-error (with-seed "bad" (random-int 1 6)) caught missed)'
    ) == ["caught"]

    # The surface it composes with is unchanged: an unscoped draw is still in
    # range, which is what examples/basics/math_exp_random.metta asserts.
    metta.run("(= (seeded-in-range $lo $hi $x) (and (<= $lo $x) (<= $x $hi)))")
    assert _answers(
        metta, "!(with-seed 3 (seeded-in-range 1 6 (random-int 1 6)))"
    ) == ["True"]
