"""Purpose: black-box acceptance for the P4.33 Scallop README witness.

Guarantees:
  - the five pinned README programs answer their printed outputs and the
    neighboring table maps every fixed Scallop feature to a general MeTTa seam
    or an explicit filed gap [tested:
    test_the_scallop_readme_examples_answer_identically_through_the_seams;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""


def test_the_scallop_readme_examples_answer_identically_through_the_seams(
    metta, repo_root
):
    """Run the pinned path, animal, negation, count, and argmax oracles."""
    example = repo_root / "examples" / "ch22-a-reasoner-you-can-serve" / "22-01-logic-programs" / "05-scallop_readme.metta"
    mapping = example.with_suffix(".md")
    with metta._new_space() as program:
        program.annotations(program.name, "set")
        results = program.load(example)
    assert [[str(answer) for answer in group] for group in results] == [
        ["True"],
        ["True"],
        ["True"],
        ["True"],
        ["True"],
    ]
    table = mapping.read_text(encoding="utf-8")
    for seam in (
        "Space.algebra",
        "DLPack",
        "foldall",
        "not-provable",
        ":<",
        "MeTTa.add_table",
        "pettorch.MettaModule",
    ):
        assert seam in table
    assert "General cyclic least-fixed-point recursion" in table
