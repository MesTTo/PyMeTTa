"""Purpose: execute the shipped notebook in an isolated Python kernel and
require its rich Rows output to survive headless execution.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import json
import os
import sys

import pytest

MAGIC_SETUP = """%load_ext metta.ipython
from metta.ipython import use

use(m)"""

MAGIC_CELL = """%%metta
!(+ 1 2)
(Parent Zoe Lia)
!(match (context-space) (Parent $parent $child) ($parent $child))"""

TABLE_MARKER = "<table style='font-family: monospace; border-collapse: collapse;'>"


def _rendered_html(output) -> str:
    """One output's `text/html`, whichever shape it is stored in.

    nbformat writes a multiline string as a LIST of lines and joins it
    again on read, and this lane reads the stored notebook as plain JSON
    while the executed one arrives as nbformat nodes. The check passed
    only while the shipped notebook happened to be written by something
    other than nbformat, which kept it a single string; saving the tour
    once from Jupyter would have turned the lane red with nothing wrong.
    """
    html = output.get("data", {}).get("text/html", "")
    return "".join(html) if isinstance(html, list) else html


def _has_rows_table(notebook) -> bool:
    return any(
        TABLE_MARKER in _rendered_html(output)
        for cell in notebook["cells"]
        for output in cell.get("outputs", ())
    )


def test_tour_executes_and_renders_rows(repo_root, tmp_path, monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    notebook_path = repo_root / "extensions" / "python" / "notebooks" / "tour.ipynb"
    stored = json.loads(notebook_path.read_text(encoding="utf8"))
    assert _has_rows_table(stored)

    jupyter_data = tmp_path / "jupyter"
    kernel_dir = jupyter_data / "kernels" / "metta-test"
    kernel_dir.mkdir(parents=True)
    (kernel_dir / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [
                    sys.executable,
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": "MeTTa test kernel",
                "language": "python",
            }
        ),
        encoding="utf8",
    )
    jupyter_path = os.pathsep.join(
        filter(None, [str(jupyter_data), os.environ.get("JUPYTER_PATH")])
    )
    monkeypatch.setenv("JUPYTER_PATH", jupyter_path)

    nbclient = pytest.importorskip("nbclient")
    nbformat = pytest.importorskip("nbformat")
    pytest.importorskip("ipykernel")
    notebook = nbformat.read(notebook_path, as_version=4)
    sources = {cell.source for cell in notebook.cells if cell.cell_type == "code"}
    assert MAGIC_SETUP in sources
    assert MAGIC_CELL in sources

    python_path = str(repo_root / "extensions" / "python")
    env = {
        **os.environ,
        "METTA_PATH": str(repo_root),
        "PYTHONPATH": os.pathsep.join(
            filter(None, [python_path, os.environ.get("PYTHONPATH")])
        ),
    }
    client = nbclient.NotebookClient(
        notebook,
        timeout=300,
        kernel_name="metta-test",
        resources={"metadata": {"path": str(repo_root)}},
        allow_errors=False,
    )
    executed = client.execute(cwd=str(repo_root), env=env)

    assert _has_rows_table(executed)
