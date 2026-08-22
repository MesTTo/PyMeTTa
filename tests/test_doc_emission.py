"""Purpose: pin what a Python docstring becomes in the engine's doc vocabulary.
Assumes: a sectioned docstring is Google style, which is what this repository
  and sphinx.ext.napoleon both write.
Guarantees:
  - a docstring emits (@desc ...), one (@param ...) per SIGNATURE parameter in
    source order, and (@return ...), which is the shape engine/prelude.metta's
    own @doc atoms have; an unsectioned docstring stays one description.
  [tested: test_a_docstring_emits_the_whole_doc_vocabulary; commit=657ae9672c07b628f8a20c7fe39aa43e58b0014f]
Fails when: read as a claim that every docstring style parses. Only the Google
  section headers are read; anything else is one description, which is what it
  was before.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from petta import MeTTa


def _documentation(metta: MeTTa, name: str) -> str:
    """The one @doc atom the space holds for a name."""
    prefix = f"(@doc {name} "
    found = [str(atom) for atom in metta.atoms() if str(atom).startswith(prefix)]
    assert len(found) == 1, found
    return found[0]


def test_a_docstring_emits_the_whole_doc_vocabulary() -> None:
    """Description, parameters and return, the way the prelude writes them."""
    metta = MeTTa("&docemission")

    @metta.define
    def docemit_cube(n):
        """Answer n cubed.

        Args:
            n: the number to cube.

        Returns:
            n raised to the third power.
        """
        return n * n * n

    @metta.define
    def docemit_partly(a, b):  # noqa: D417  -- the missing description IS the fixture: a positional @param must hold its place when its parameter is undocumented
        """Two parameters, one documented.

        Args:
            b: only the second is described here.
        """
        return a + b

    @metta.define
    def docemit_plain(a, b):
        """One line and no sections."""
        return a + b

    assert _documentation(metta, "docemit_cube") == (
        '(@doc docemit_cube (@desc "Answer n cubed.") '
        '(@params ((@param "the number to cube."))) '
        '(@return "n raised to the third power."))'
    )
    # The SIGNATURE decides the list and its order, so an undocumented
    # parameter holds its place rather than shifting the next description onto
    # it. A @param is positional in the engine's shape.
    assert _documentation(metta, "docemit_partly") == (
        '(@doc docemit_partly (@desc "Two parameters, one documented.") '
        '(@params ((@param "") (@param "only the second is described here."))))'
    )
    # No sections is what it always was: one description, nothing invented.
    assert _documentation(metta, "docemit_plain") == (
        '(@doc docemit_plain (@desc "One line and no sections."))'
    )

    # The atoms are ordinary data the engine's own reader answers.
    (group,) = metta.run("!(get-doc docemit_cube)")
    assert str(group[0]) == _documentation(metta, "docemit_cube")

    # And the definitions still run.
    assert docemit_cube(3) == [27]
    assert docemit_partly(1, 2) == [3]
