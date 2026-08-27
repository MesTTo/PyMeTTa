"""Purpose: the README's python blocks, executed: documentation that cannot
quietly stop being true, the Rust-doctest rule. Blocks run in order in one
namespace, since later ones build on earlier ones; a block needing an
optional dependency (torch) skips exactly when the dependency is absent.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re
from pathlib import Path

import pytest

import metta as metta_module

README = Path(__file__).resolve().parents[4] / "README.md"

_BLOCKS = re.findall(r"```python\n(.*?)```", README.read_text(), re.DOTALL)
assert _BLOCKS, "the README lost its python blocks"

_NAMESPACE: dict = {}


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
        exec(compile(source, str(path), "exec"), _NAMESPACE)
    finally:
        metta_module.config.configure(
            declaration_limit=settings["declaration_limit"],
            display_rows=settings["display_rows"],
        )
