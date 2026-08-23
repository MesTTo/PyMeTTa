"""Purpose: verify the Janus-readable function-catalogue generation seam.

Guarantees:
  - ``petta_py_function_generation/1`` is monotonic across a public function
    definition and stable across evaluation [tested:
    test_generation_tracks_definitions_but_not_evaluation; commit=4c9a794750103e0a3a2e9d883adde337ffb501f0]
"""


def test_generation_tracks_definitions_but_not_evaluation(metta):
    """Advance on a definition and remain stable across plain evaluation."""
    before = metta.runtime.once("petta_py_function_generation(G)")["G"]
    metta.run("(= (p14-python-generation $x) $x)")
    defined = metta.runtime.once("petta_py_function_generation(G)")["G"]
    metta.eval("(+ 1 2)")
    evaluated = metta.runtime.once("petta_py_function_generation(G)")["G"]

    assert defined > before
    assert evaluated == defined
