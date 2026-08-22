"""Purpose: black-box acceptance for the P4.33 Scallop README witness.

Guarantees:
  - the five pinned README programs answer their printed outputs and the
    neighboring table maps every fixed Scallop feature to a general PeTTa seam
    or an explicit filed gap [tested:
    test_the_scallop_readme_examples_answer_identically_through_the_seams;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""


def test_the_scallop_readme_examples_answer_identically_through_the_seams(
    metta, repo_root
):
    """Run the pinned path, animal, negation, count, and argmax oracles."""
    example = repo_root / "examples" / "reasoning" / "scallop_readme.metta"
    mapping = example.with_suffix(".md")
    with metta._new_space() as program:
        program.declare_annotations(program.name, "set")
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
        "MeTTa.declare_algebra",
        "DLPack",
        "foldall",
        "not-provable",
        ":<",
        "MeTTa.add_table",
        "pettorch.MettaModule",
    ):
        assert seam in table
    assert "General cyclic least-fixed-point recursion" in table
