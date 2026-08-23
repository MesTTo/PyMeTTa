"""Purpose: verify the Janus-readable function-catalogue generation seam.

Guarantees:
  - ``petta_py_function_generation/1`` is monotonic across a public function
    definition and stable across evaluation [tested:
    test_generation_tracks_definitions_but_not_evaluation; commit=WORKTREE]
"""


def test_generation_tracks_definitions_but_not_evaluation(metta):
    before = metta.runtime.once("petta_py_function_generation(G)")["G"]
    metta.run("(= (p14-python-generation $x) $x)")
    defined = metta.runtime.once("petta_py_function_generation(G)")["G"]
    metta.eval("(+ 1 2)")
    evaluated = metta.runtime.once("petta_py_function_generation(G)")["G"]

    assert defined > before
    assert evaluated == defined
