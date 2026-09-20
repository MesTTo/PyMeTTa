"""Purpose: the README's fences, executed: documentation that cannot quietly
stop being true, the Rust-doctest rule.

Each python block runs in a namespace of its own, so a reader can copy ANY block
and have it work rather than discovering it needed one further up; a block
needing an optional dependency (torch) skips exactly when the dependency is
absent. Each metta block runs on a fresh space, and the corpus style it is drawn
from asserts its own results through `!(test ...)`, so a drifted answer fails
here rather than in a reader's terminal.

The ts and c fences cannot run from this suite: one needs node and a WebAssembly
boot, the other a compiler and libcmetta. They are checked the other way round,
against the file their OWN gate builds and runs, which is the rule
`test_every_run_fence_runs_the_corpus_file_it_names` already applies to the
website. One rewrite is declared rather than tolerated: the TypeScript example
imports `../src/index.ts` so the gate can run it in-tree, and a reader must
import the published package instead.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re

import pytest

import metta as metta_module
from metta._roots import workspace

README = workspace() / "README.md"
_TEXT = README.read_text()

_BLOCKS = re.findall(r"```python\n(.*?)```", _TEXT, re.DOTALL)
assert _BLOCKS, "the README lost its python blocks"

_METTA = re.findall(r"```metta\n(.*?)```", _TEXT, re.DOTALL)
assert _METTA, "the README lost its metta blocks"

#: A fence that cannot run here, and the gate-run file whose text it must be.
#: The value is that file plus the rewrites a reader needs, applied in order.
_MIRRORED = {
    "ts": (
        "extensions/node/examples/readme-snippet.ts",
        (('"../src/index.ts"', '"tsmetta"'),),
    ),
    "c": ("extensions/cmetta/examples/lower.c", ()),
}


@pytest.mark.parametrize("index", range(len(_BLOCKS)), ids=lambda i: f"block-{i + 1}")
def test_readme_block_executes(index, metta, tmp_path):  # noqa: ARG001, D103  -- pytest injects this fixture to establish engine state for the scenario; pytest discovers or injects this callable; its descriptive name states the contract
    source = _BLOCKS[index]
    if "torch" in source or "pettorch" in source:
        pytest.importorskip("torch")
    if "pettaprove" in source:
        # The soft layer lives in its own repository beside this one.
        pytest.importorskip("pettaprove")
    # A real file, so inspect.getsource sees @m.define bodies, exactly as
    # the compiler asks of a REPL.
    path = tmp_path / f"readme_block_{index + 1}.py"
    path.write_text(source)
    settings = metta_module.config.as_dict()
    try:
        # A namespace per block: every example stands alone.
        exec(compile(source, str(path), "exec"), {"__name__": "__main__"})
    finally:
        metta_module.config.configure(
            declaration_limit=settings["declaration_limit"],
            display_rows=settings["display_rows"],
        )


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


@pytest.mark.parametrize("language", sorted(_MIRRORED), ids=sorted(_MIRRORED))
def test_readme_mirrored_fence_is_the_file_its_gate_runs(language):
    """The fence is that file's text, or the page has drifted from what runs.

    Checked by identity rather than by execution because neither toolchain is
    available to this suite, and an unrun fence is exactly the thing the python
    blocks above exist to refuse. The node gate runs the TypeScript file through
    `extensions/node/test/gallery.test.ts`; the C file is one of the Makefile's
    EXAMPLES, which `make test` builds and runs.
    """
    path, rewrites = _MIRRORED[language]
    fences = re.findall(rf"```{language}\n(.*?)```", _TEXT, re.DOTALL)
    assert len(fences) == 1, (
        f"the README holds {len(fences)} {language} fences; this check pairs "
        f"exactly one with {path}"
    )
    wanted = (workspace() / path).read_text()
    # The obligation header explains the file to a maintainer and would only be
    # noise to a reader, so the fence starts after it.
    if wanted.startswith("/*"):
        wanted = wanted.split("*/\n", 1)[1].lstrip("\n")
    for before, after in rewrites:
        wanted = wanted.replace(before, after)
    assert fences[0].strip() == wanted.strip(), (
        f"the README's {language} fence is not the text of {path}, which is the "
        f"copy its own gate builds and runs; paste that file back into the fence"
    )
