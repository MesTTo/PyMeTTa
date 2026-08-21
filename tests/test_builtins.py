"""Purpose: pin the public language-name enumeration to engine-owned data.

Guarantees:
  - MeTTa.builtins() equals the sorted set union of fun/1 and the translator's
    published special-form heads, with neither list copied into Python [tested:
    test_builtins_equals_the_union_of_functions_and_special_forms;
    commit=WORKTREE]
  - neither half of that union can go empty unnoticed, which is the way this
    test was previously able to pass while the answer was wrong [tested:
    test_builtins_equals_the_union_of_functions_and_special_forms;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

# The special forms every MeTTa program uses, named here so the equality below
# has something to be an equality ABOUT. The earlier version of this test asked
# the engine for clause(Engine:translate_special_dl(...), _), which is what
# shim.pl asked, so when the translator became a module of its own and that read
# stopped matching, both sides of the assertion fell from 268 names to 237
# together and the test stayed green over a real regression
# [measured 2026-08-22]. A floor cannot drift with the implementation.
ALWAYS_SPECIAL_FORMS = frozenset({"case", "collapse", "if", "let", "let*", "match"})


def test_builtins_equals_the_union_of_functions_and_special_forms(metta):
    """The host view is exactly both live engine registries, sorted once."""
    row = metta.runtime.must(
        "findall(_Function, fun(_Function), _Functions0), "
        "sort(_Functions0, Functions), "
        "findall(_Form, metta_special_form_head(_Form), _Forms0), "
        "sort(_Forms0, SpecialForms)"
    )
    functions = set(row["Functions"])
    special_forms = set(row["SpecialForms"])
    assert ALWAYS_SPECIAL_FORMS <= special_forms
    assert functions
    assert metta.builtins() == sorted(functions | special_forms)
