"""Purpose: pin the public language-name enumeration to engine-owned data.
Guarantees:
  - MeTTa.builtins() equals the sorted set union of fun/1 and the heads of
    translate_special_dl/5, with neither list copied into Python [tested:
    test_builtins_equals_the_union_of_functions_and_special_forms;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose


def test_builtins_equals_the_union_of_functions_and_special_forms(metta):
    """The host view is exactly both live engine registries, sorted once."""
    row = metta.runtime.must(
        "petta_engine_module(_Engine), "
        "findall(_Function, fun(_Function), _Functions0), "
        "sort(_Functions0, Functions), "
        "findall(_Form, "
        "        (clause(_Engine:translate_special_dl(_Form, _, _, _, _), _), "
        "         atom(_Form)), "
        "        _Forms0), "
        "sort(_Forms0, SpecialForms)"
    )
    expected = sorted(set(row["Functions"]) | set(row["SpecialForms"]))
    assert metta.builtins() == expected
