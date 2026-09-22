"""Purpose: the README's fences, executed: documentation that cannot quietly
stop being true, the Rust-doctest rule.

Each python block runs in a namespace of its own, so a reader can copy ANY block
and have it work rather than discovering it needed one further up; a block
needing an optional dependency (torch) skips exactly when the dependency is
absent. Each metta block runs on a fresh space, and the corpus style it is drawn
from asserts its own results through `!(test ...)`, so a drifted answer fails
here rather than in a reader's terminal.

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

import metta as metta_module
from metta._roots import workspace

README = workspace() / "README.md"
_TEXT = README.read_text()


_METTA = re.findall(r"```metta\n(.*?)```", _TEXT, re.DOTALL)
assert _METTA, "the README lost its metta blocks"

#: Languages whose component documents itself elsewhere, so a fence in one here
#: is a component's own page copied back onto the engine's.
_COMPONENT_LANGUAGES = ("c", "cpp", "js", "jsx", "python", "rust", "ts", "tsx", "typescript")


#: A fence runs on every machine that runs the suite, so it may not reach the
#: network. `git-import!` clones and then executes the repository's own build
#: script, which is remote code execution inside a documentation test; a bare
#: URL is the other spelling. The corpus settled this already, by building a
#: throwaway local repository in `_fixtures/git_fixture.pl` because "the suite
#: ran on every push and cloned github each time", and by refusing a website
#: fence over any example `tests/data/example_skips.txt` names.
_NOT_HERMETIC = ("git-import!", "https://", "http://")


@pytest.mark.parametrize("index", range(len(_METTA)), ids=lambda i: f"metta-{i + 1}")
def test_readme_metta_block_is_hermetic(index):
    """A metta fence reaches no network, because the suite below runs it.

    Caught after the fact: the first version of this file executed a fence
    holding `!(git-import! "https://github.com/patham9/faiss_ffi" "build.sh")`
    and left a clone in the battery tree.
    """
    source = _METTA[index]
    found = [mark for mark in _NOT_HERMETIC if mark in source]
    assert not found, (
        f"metta fence {index + 1} names {found}, so running it would reach the "
        f"network; show the feature with a local example and link the corpus "
        f"file for the network one, as the extending-the-engine section does"
    )


@pytest.mark.parametrize("index", range(len(_METTA)), ids=lambda i: f"metta-{i + 1}")
def test_readme_metta_block_runs(index, tmp_path, monkeypatch):
    """A metta fence runs on a fresh space, and its own `!(test ...)` judges it.

    A block of bare atoms with nothing to reduce is still run rather than
    skipped: it proves the text PARSES, which is the failure a hand-written
    fence actually has.

    In a directory of its own, because a fence WRITES. The catalog fence
    imports lib_package, which opens a catalog journal where the program runs,
    and running it here left `catalog/` in the checkout.
    """
    monkeypatch.chdir(tmp_path)
    source = _METTA[index]
    space = metta_module.space()
    space.run(source)


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
