"""Purpose: hold the Python bridge to its own patched-host requirement.

The engine requires only the patches to swipl-devel itself
(engine/host_patches.pl). The patches to janus are this bridge's to require,
because no other host loads janus, so the bridge checks them against the same
declaration through metta_host_check:metta_require_host_patches/2 once the
engine has booted. The rule under test is one sentence: a home is refused by
the bridge exactly when its declaration lacks one of the bridge's patches, and
the refusal names exactly those. The cases are generated from it, one per
subset of the bridge's patches planted beside every patch the engine needs.

Each case runs in a fresh interpreter, because an engine boots once per
process. The child plants its declaration in a scratch directory it puts ahead
of the home on the swi search path before the engine boots, which is the first
place the check looks, so no real home is touched.
Guarantees:
  - for every subset of the bridge's patches, the bridge refuses with
    EngineError naming exactly the ones left out, quoting itself, or the
    engine boots and answers when none are left out
    [tested: test_the_bridge_refuses_exactly_the_janus_patches_a_home_lacks]
"""

import itertools
import os
import subprocess
import sys

import pytest

import metta
from metta._roots import seat

_CHILD = """
import sys
from metta._binding.runtime import bridge
janus = bridge()
janus.query_once("asserta(user:file_search_path(swi, Dir))", {"Dir": sys.argv[1]})
import metta
try:
    answer = metta.space().run("!(+ 1 2)")
except metta.MettaError as error:
    print("refused", type(error).__name__)
    print(error)
    raise SystemExit(3)
print("booted", answer)
"""


def _requirements():
    """The build this binary is, and each requirement's File-Sha256 pairs."""
    metta.space().run("!(+ 1 1)")
    janus = sys.modules["janus_swi"]
    built = janus.query_once("current_prolog_flag(compiled_at, C)")["C"]

    def pairs(module):
        rows = janus.query_once(
            f"findall(_F-_S, {module}:host_patch(_F, _S), R)")["R"]
        return [tuple(row.args) if hasattr(row, "args") else tuple(row) for row in rows]

    return built, pairs("metta_host_patches"), pairs("metta_host_patches_packages_swipy")


_BUILT, _ENGINE, _BRIDGE = _requirements()


def _plant(directory, patches):
    lines = [f"host_build('{_BUILT}')."]
    lines += [f"host_patch('{name}', '{digest}')." for name, digest in patches]
    (directory / "metta-host.pl").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    "carried",
    [subset for size in range(len(_BRIDGE) + 1)
     for subset in itertools.combinations(_BRIDGE, size)],
    ids=lambda subset: "+".join(name for name, _ in subset) or "none",
)
def test_the_bridge_refuses_exactly_the_janus_patches_a_home_lacks(tmp_path, carried):
    """Plant the engine's patches and `carried`; the rest must be named, or none."""
    assert _BRIDGE, "the bridge requires no janus patch, so there is nothing to hold"
    _plant(tmp_path, _ENGINE + list(carried))
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = f"{seat()}{os.pathsep}{existing}" if existing else str(seat())
    done = subprocess.run(
        [sys.executable, "-c", _CHILD, str(tmp_path)],
        capture_output=True, text=True, env=environment, cwd=tmp_path, check=False,
    )
    lacking = [name for name, _ in _BRIDGE if (name, dict(_BRIDGE)[name]) not in carried]
    if not lacking:
        assert done.returncode == 0, done.stdout + done.stderr
        assert done.stdout.startswith("booted"), done.stdout
        return
    assert done.returncode == 3, done.stdout + done.stderr
    assert done.stdout.startswith("refused EngineError"), done.stdout
    assert "every patch PyMeTTa's janus bridge needs" in done.stdout, done.stdout
    for name, _ in _BRIDGE:
        assert (name in done.stdout) == (name in lacking), (name, done.stdout)
