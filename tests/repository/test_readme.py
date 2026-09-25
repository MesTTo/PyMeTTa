"""Purpose: hold the engine README to its shape: every component named once in
the Architecture table, and no component's own page copied onto the engine's.

Its metta fences are executed elsewhere, by tests/checks/check_readme_fences.py,
each as a program in a process and a directory of its own, as rustdoc builds
every doctest into a program of its own. They ran here until 2026-09-25, on a
fresh space inside whichever pytest worker took this file, and a fresh space
does not isolate a program: the Concurrency fence writes `&Point`, a space name
every program in one engine shares, so a class named Point defined later in the
same worker was refused as a space already used [measured
2026-09-25T12:43:57+10:00: this file then
tests/ch09_types/test_type_inspection.py in one process fails
test_a_subtype_edge_waits_for_the_base_and_skips_an_undeclared_one that way].

This page is the ENGINE's, so the only fences it may carry are the language's
own and the engine's: `metta`, `prolog`, and the `bash` and `bibtex` that
install and cite it. A `c`, `ts` or `python` fence means a component's page has
been copied back in, and the copy then drifts from the original in silence --
which had already happened, with the root page and `lib/README.md` giving
`lib_crypto` two different descriptions. Each component documents itself in its
own repository and is named once in the Architecture table.

That replaces a mirrored-fence check. One `c` fence used to live here and was
held to the text of `extensions/cmetta/examples/lower.c` by identity, since no
compiler is available to this suite; when the CMeTTa section went, a check
parametrised over an empty table would have passed without running, so the slot
holds the rule that keeps the section from coming back instead. The same
guarantee cannot simply move to `extensions/cmetta/README.md`, whose C fences
are 8-line excerpts of an 82-line file rather than whole copies of it.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re

import pytest

from metta._roots import workspace

README = workspace() / "README.md"
_TEXT = README.read_text()


#: Languages whose component documents itself elsewhere, so a fence in one here
#: is a component's own page copied back onto the engine's.
_COMPONENT_LANGUAGES = ("c", "cpp", "js", "jsx", "python", "rust", "ts", "tsx", "typescript")


#: Every component this repository composes, read from .gitmodules rather than
#: listed, so a submodule added tomorrow is covered without an edit here.
_COMPONENTS = tuple(
    sorted(
        re.findall(r"url\s*=\s*\S+/([^/\s]+?)(?:\.git)?\s*$",
                   (workspace() / ".gitmodules").read_text(), re.MULTILINE)
    )
)


@pytest.mark.parametrize("component", _COMPONENTS)
def test_readme_names_every_component_once(component):
    """Each component has exactly one row, which is what makes it the index.

    The fence rule above says a component is documented in its own repository
    and named here; that is only true if naming here is total. Nothing checked
    it, and Python and TypeScript were in fact absent from the table while
    their own header sentence said they lived elsewhere -- a rule with a hole
    exactly where nobody looks, because a missing row reads like a row nobody
    wrote.
    """
    rows = [line for line in _TEXT.splitlines()
            if line.startswith("|") and f"/{component})" in line]
    assert len(rows) == 1, (
        f"{component} is a submodule of this repository and has {len(rows)} rows in "
        f"the Architecture table; every component is named there exactly once, so a "
        f"reader finds it without the page carrying its documentation"
    )


@pytest.mark.parametrize("language", _COMPONENT_LANGUAGES)
def test_readme_carries_no_component_language_fence(language):
    """A component's page is not copied onto the engine's.

    The whole content of a section written in one of these languages belongs to
    the repository that ships it, and a copy here is a second description that
    nothing reconciles with the first. Checked per language rather than by a
    whitelist of the four allowed ones, so the failure names the component that
    came back rather than saying a fence is unexpected.
    """
    fences = re.findall(rf"^```{language}$", _TEXT, re.MULTILINE)
    assert not fences, (
        f"the README carries {len(fences)} {language} fence(s); that component "
        f"documents itself in its own repository and is named once in the "
        f"Architecture table, so this page shows the engine and links to it"
    )
