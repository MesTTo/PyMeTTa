"""Purpose: pin the dict story a dict comprehension can lower to.
Assumes: `(import! &self (library lib_dict))`, which brings lib_json's
  dict-space, get-keys and get-value with it.
Guarantees:
  - a dict is a SPACE of (key value) atoms, a key holds one value, and the
    operations a comprehension needs are there: build from pairs, put,
    remove, size, membership, and the pair list back.
  [tested: test_a_dict_is_a_space_a_comprehension_can_build; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Fails when: read as a claim about key ORDER. get-keys answers in the space's
  own order, which is insertion order here, and lib_dict.metta says so rather
  than promising it; the arbiter carries no dict ruling to check it against.
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


def test_a_dict_is_a_space_a_comprehension_can_build() -> None:
    """The space IS the dict, and every operation is a space operation."""
    metta = MeTTa().space("&dictstory")
    metta.run("!(import! &self (library lib_dict))")
    metta.run("!(bind! dictstory-d (dict-space ((a 1) (b 2))))")

    assert _answers(metta, "!(dict-size dictstory-d)") == ["2"]
    assert _answers(metta, "!(get-value dictstory-d a)") == ["1"]
    assert _answers(metta, "!(dict-has dictstory-d a)") == ["True"]
    assert _answers(metta, "!(dict-has dictstory-d z)") == ["False"]

    # A key holds ONE value, which is what makes this a dict rather than a
    # relation: putting a key that is there replaces it and the size holds.
    metta.run("!(dict-put dictstory-d a 99)")
    assert _answers(metta, "!(collapse (get-value dictstory-d a))") == ["(99)"]
    assert _answers(metta, "!(dict-size dictstory-d)") == ["2"]

    # A new key inserts.
    metta.run("!(dict-put dictstory-d c 3)")
    assert _answers(metta, "!(dict-size dictstory-d)") == ["3"]

    # Removing is exact, and removing a key that is not there is an ordinary
    # answer rather than a failure, which is what lets put be a replacement.
    metta.run("!(dict-remove dictstory-d b)")
    assert _answers(metta, "!(dict-size dictstory-d)") == ["2"]
    assert _answers(metta, "!(dict-has dictstory-d b)") == ["False"]
    metta.run("!(dict-remove dictstory-d nosuchkey)")
    assert _answers(metta, "!(dict-size dictstory-d)") == ["2"]

    # The pairs come back in the shape dict-space reads, which is the whole
    # lowering target: a comprehension builds an expression of pairs and hands
    # it to dict-space.
    assert _answers(metta, "!(dict-pairs dictstory-d)") == ["((a 99) (c 3))"]
    metta.run(
        "!(bind! dictstory-rebuilt (dict-space (dict-pairs dictstory-d)))"
    )
    assert _answers(metta, "!(get-value dictstory-rebuilt c)") == ["3"]

    # And that is exactly what a dict comprehension lowers to: a generator
    # over pairs, collapsed, handed to dict-space. `{x: (* x x) for x in ...}`
    # is this expression with no string in it.
    metta.run(
        "!(bind! dictstory-squares"
        "  (dict-space (collapse (let $x (superpose (1 2 3)) ($x (* $x $x))))))"
    )
    assert _answers(metta, "!(dict-size dictstory-squares)") == ["3"]
    assert _answers(metta, "!(get-value dictstory-squares 3)") == ["9"]
    assert _answers(metta, "!(collapse (dict-values dictstory-squares))") == [
        "(1 4 9)"
    ]


def test_two_dicts_built_in_one_process_are_distinct() -> None:
    """A second space importing the library must not re-mint the first's name.

    lib_json minted `&json-N` from a dynamic fact, and `(import! &self (library
    lib_json))` in a second space CONSULTS the file again, which put the fact
    back to zero: the second dict was built on top of the first one's atoms and
    a two-entry dict answered a size of four. The counter is a flag now, which
    lives outside the source.
    """
    first = MeTTa().space("&dictdistinct-a")
    first.run("!(import! &self (library lib_dict))")
    first.run("!(bind! dictdistinct-1 (dict-space ((a 1) (b 2))))")
    assert _answers(first, "!(dict-size dictdistinct-1)") == ["2"]

    second = MeTTa().space("&dictdistinct-b")
    second.run("!(import! &self (library lib_dict))")
    second.run("!(bind! dictdistinct-2 (dict-space ((c 3) (d 4))))")
    assert _answers(second, "!(dict-size dictdistinct-2)") == ["2"]

    # And the first one is untouched, which is the half a shared name breaks
    # in the other direction.
    assert _answers(first, "!(dict-size dictdistinct-1)") == ["2"]
    assert _answers(first, "!(dict-has dictdistinct-1 c)") == ["False"]
