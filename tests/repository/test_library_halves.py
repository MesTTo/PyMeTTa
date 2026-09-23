"""Purpose: prove a library's Prolog half compiles once in a child and loads from it after.

The half compiles beside itself through the boot's hermetic child on its first
import and loads from that artifact in every process after, in a copied tree
whose PATH finds a swipl that is not the build the process runs.

Guarantees: the first import compiles each claimed half exactly once, in one
child, and reads the artifact that child wrote, which also covers the half's
nested governed dependency; a later process starts no child and loads every
governed source from its artifact while an ungoverned nested source loads from
source and gains no artifact; and two later processes read the same inference
count [tested: test_the_first_import_compiles_each_half_once_in_a_child,
test_a_later_process_loads_every_governed_source_from_its_artifact,
test_two_later_processes_read_the_same_inference_count; commit=0a81c782fd6ba00984c36e58e228f73bca810dee].
Assumes: the copied engine/ and lib/ boot on the host running this suite, and a
`false` executable exists to stand in for a foreign swipl [assumed 2026-09-24].
Owns resources: pytest owns the copied tree and the decoy; every subprocess is
joined.

The tree is a copy because these tests delete and watch artifacts, and the
suites that run beside them load the same halves from the shared checkout,
where a deleted artifact races their loads. The decoy is an ELF binary named
swipl first on PATH, because that is what an embedded engine's executable flag
then names: the compile child used to be started from that flag, so on a host
whose PATH found the stock swipl the host check refused every child and no
artifact was ever written [measured 2026-09-24: 47 of 47 warm-up children
refused]. A script would not do, since SWI names a script's #! interpreter.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

import pytest

from metta._roots import seat, workspace

ROOT = workspace()

#: lib_uri's half reaches lib_encoding's through a nested use_module of a stem,
#: and lib_encoding's reaches lib_csv/support/csv_codec.pl, which sits outside
#: the stamped set; lib_import's half is claimed through consult_global.
LIBRARY = "lib_uri"
CLAIMED = ("lib/lib_import/lib_import.pl", "lib/lib_uri/lib_uri.pl")
NESTED = "lib/lib_encoding/lib_encoding.pl"
UNGOVERNED = "lib/lib_csv/support/csv_codec.pl"

#: One import in a fresh process: which children the claim started, how SWI
#: loaded every file inside the window, and what the window cost.
PROBE = r'''
import json, sys
seat, tree, library = sys.argv[1:4]
sys.path.insert(0, seat)
from metta import MeTTa
m = MeTTa(metta_path=tree).self
import janus_swi as janus
janus.consult("library_halves_probe", """
:- module(library_halves_probe, []).
:- use_module(library(prolog_wrap), [wrap_predicate/4]).
:- dynamic spawned/1, loaded/2, watching/0.
:- wrap_predicate(metta_qlf_boot:qlf_child(_, Arguments), library_halves, Wrapped,
                  ( forall(member(Argument, Arguments), assertz(spawned(Argument))),
                    Wrapped )).
:- multifile user:message_hook/3.
user:message_hook(load_file(done(_, file(_, Absolute), How, _, _, _)), _, _) :-
    watching, assertz(loaded(Absolute, How)), fail.
""")
janus.query_once("assertz(library_halves_probe:watching)")
before = janus.query_once("statistics(inferences, I)")["I"]
m.run(f"!(import! &self (library {library}))")
after = janus.query_once("statistics(inferences, I)")["I"]
janus.query_once("retractall(library_halves_probe:watching)")
print(json.dumps({
    "inferences": after - before,
    "spawned": [row["A"] for row in janus.query("library_halves_probe:spawned(A)")],
    "loaded": [[row["F"], row["H"]]
               for row in janus.query("library_halves_probe:loaded(F, H)")],
    "executable": janus.query_once("current_prolog_flag(executable, X)")["X"],
}))
'''


def governed(relative: PurePosixPath) -> bool:
    """engine/qlf_boot.pl's pattern table: a star matches one directory level."""
    return (relative.parts[0] in ("engine", "lib")
            and len(relative.parts) in (2, 3)
            and relative.suffix == ".pl")


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """Three processes importing one library into a fresh copy, in order."""
    tree = tmp_path_factory.mktemp("library-halves")
    for directory in ("engine", "lib"):
        shutil.copytree(ROOT / directory, tree / directory,
                        ignore=shutil.ignore_patterns("*.qlf", ".qlf-stamp", "__pycache__"))
    decoy = tree / "decoy"
    decoy.mkdir()
    false = shutil.which("false")
    assert false is not None, "the decoy swipl is a copy of the false executable"
    shutil.copy2(false, decoy / "swipl")
    environment = {**os.environ,
                   "PATH": os.pathsep.join((str(decoy), os.environ.get("PATH", "")))}

    def run() -> dict:
        result = subprocess.run(
            [sys.executable, "-c", PROBE, str(seat()), str(tree), LIBRARY],
            cwd=tree, env=environment, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout.strip().splitlines()[-1])
        report["loaded"] = {
            PurePosixPath(Path(path).relative_to(tree).with_suffix(".pl").as_posix()): how
            for path, how in report["loaded"]
            if Path(path).is_relative_to(tree)
        }
        report["spawned"] = [PurePosixPath(Path(path).relative_to(tree).as_posix())
                             for path in report["spawned"]]
        return report

    return {"tree": tree, "decoy": decoy, "first": run(), "later": run(), "again": run()}


def test_the_first_import_compiles_each_half_once_in_a_child(runs):
    """The claim's child writes each half, its nested dependency too, and the process reads it."""
    first, tree = runs["first"], runs["tree"]
    assert Path(first["executable"]) == runs["decoy"] / "swipl"
    assert sorted(map(str, first["spawned"])) == sorted(CLAIMED)
    for half in CLAIMED:
        assert first["loaded"][PurePosixPath(half)] == "loaded"
        assert (tree / half).with_suffix(".qlf").is_file()
    assert (tree / NESTED).with_suffix(".qlf").is_file()


def test_a_later_process_loads_every_governed_source_from_its_artifact(runs):
    """No child starts, and only an ungoverned source is compiled."""
    later, tree = runs["later"], runs["tree"]
    assert later["spawned"] == []
    governed_loads = {path: how for path, how in later["loaded"].items() if governed(path)}
    assert governed_loads, later["loaded"]
    assert all(how == "loaded" for how in governed_loads.values()), governed_loads
    assert governed_loads[PurePosixPath(NESTED)] == "loaded"
    assert later["loaded"][PurePosixPath(UNGOVERNED)] == "compiled"
    assert not (tree / UNGOVERNED).with_suffix(".qlf").exists()


def test_two_later_processes_read_the_same_inference_count(runs):
    """Neither pays a compile, so the import costs both the same."""
    assert runs["later"]["inferences"] == runs["again"]["inferences"]
