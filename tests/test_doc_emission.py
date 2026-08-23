"""Purpose: pin the complete documentation family emitted from Python source.
Assumes: sectioned docstrings use Google style and doctest prompts carry MeTTa
  calls whose following expectation is a Python list of answers.
Guarantees:
  - define and op emit kind, summary, typed parameters, typed return, and one
    example atom per doctest pair [tested:
    test_a_docstring_emits_the_whole_doc_vocabulary; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - a record field's attribute docstring becomes that constructor parameter's
    description [tested: test_record_attribute_docstrings_describe_parameters;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - generated fn mentions carry offline runtime and stub documentation [tested:
    test_generated_fn_help_is_offline; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

import os
import subprocess
import sys
from pathlib import Path

from petta import MeTTa, S


def _documentation(metta: MeTTa, name: str) -> str:
    """The one @doc atom the space holds for a name."""
    prefix = f"(@doc {name} "
    found = [str(atom) for atom in metta.atoms() if str(atom).startswith(prefix)]
    assert len(found) == 1, found
    return found[0]


def test_a_docstring_emits_the_whole_doc_vocabulary() -> None:
    """Description, parameters and return, the way the prelude writes them."""
    metta = MeTTa().space("&docemission")

    @metta.define
    def docemit_cube(n: int) -> int:
        """Answer n cubed.

        Args:
            n: the number to cube.

        Returns:
            n raised to the third power.

        >>> !(docemit-cube 2)
        [8]
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

    @metta.op
    def docemit_double(n: int) -> int:
        """Double a number.

        Args:
            n: the input number.

        Returns:
            twice the input.
        """
        return n * 2

    assert _documentation(metta, "docemit-cube") == (
        '(@doc docemit-cube (@kind function) (@desc "Answer n cubed.") '
        '(@params ((@param (@type Number) (@desc "the number to cube.")))) '
        '(@return (@type Number) (@desc "n raised to the third power.")) '
        '(@example (docemit-cube 2) (8)))'
    )
    # The SIGNATURE decides the list and its order, so an undocumented
    # parameter holds its place rather than shifting the next description onto
    # it. A @param is positional in the engine's shape.
    assert _documentation(metta, "docemit-partly") == (
        '(@doc docemit-partly (@kind function) '
        '(@desc "Two parameters, one documented.") '
        '(@params ((@param (@type %Undefined%) (@desc "")) '
        '(@param (@type %Undefined%) '
        '(@desc "only the second is described here.")))))'
    )
    # No sections is what it always was: one description, nothing invented.
    assert _documentation(metta, "docemit-plain") == (
        '(@doc docemit-plain (@kind function) '
        '(@desc "One line and no sections.") '
        '(@params ((@param (@type %Undefined%) (@desc "")) '
        '(@param (@type %Undefined%) (@desc "")))))'
    )
    assert _documentation(metta, "docemit-double") == (
        '(@doc docemit-double (@kind operation) (@desc "Double a number.") '
        '(@params ((@param (@type Number) (@desc "the input number.")))) '
        '(@return (@type Number) (@desc "twice the input.")))'
    )

    # The atoms are ordinary data the engine's own reader answers.
    assert str(metta.fn.get_doc(S.docemit_cube).one()) == _documentation(
        metta, "docemit-cube"
    )

    # And the definitions still run.
    assert docemit_cube(3) == [27]
    assert docemit_partly(1, 2) == [3]
    metta.unregister_op("docemit-double")


def test_record_attribute_docstrings_describe_parameters() -> None:
    """Adjacent field prose stays attached to that field."""
    metta = MeTTa().space("&docrecord")

    @metta.define
    class DocemitRecord:
        """One documented record."""

        code: str
        """The external code."""

        count: int
        """How many are held."""

    assert _documentation(metta, "DocemitRecord") == (
        '(@doc DocemitRecord (@kind record) (@desc "One documented record.") '
        '(@params ((@param (@type String) (@desc "The external code.")) '
        '(@param (@type Number) (@desc "How many are held.")))))'
    )


def test_generated_fn_help_is_offline() -> None:
    """Generated mentions and stubs carry inert catalog documentation."""
    source = (
        "import json\n"
        "from petta import _engine, fn\n"
        "print(json.dumps([_engine.started(), fn.car_atom.__doc__, "
        "_engine.started()]))\n"
    )
    root = Path(__file__).parents[3]
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=root,
        env=os.environ | {"PYTHONPATH": str(root / "bindings" / "python")},
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.startswith('[false, "')
    assert "head" in completed.stdout.lower()
    assert completed.stdout.rstrip().endswith("false]")

    stub = Path(__file__).parents[1] / "petta" / "_fn.pyi"
    text = stub.read_text(encoding="utf-8")
    marker = "    car_atom: Symbol\n"
    assert marker in text
    assert text[text.index(marker) + len(marker) :].startswith('    "')
