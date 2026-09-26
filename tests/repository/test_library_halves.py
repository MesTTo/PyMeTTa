"""Purpose: prove a library's Prolog half compiles once in a child and loads from it after.

The half compiles beside itself through the boot's hermetic child on its first
import and loads from that artifact in every process after, in a copied tree
whose PATH finds a swipl that is not the build the process runs.

Guarantees: the first import compiles each claimed half exactly once, in one
child, and reads the artifact that child wrote, which also covers the half's
nested governed dependency; a later process starts no child and loads every
governed source from its artifact while an ungoverned nested source loads from
source and gains no artifact; and two later processes read the same inference
count, the second with SWI's file-search sweep last run at the epoch
[tested 2026-09-26T19:42:20+10:00: test_the_first_import_compiles_each_half_once_in_a_child,
test_a_later_process_loads_every_governed_source_from_its_artifact,
test_two_later_processes_read_the_same_inference_count].
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

Each probe fixes SWI's file_search_cache_time at its maximum before it boots,
the protocol every counted process follows
(docs/journal/2026-09-07-merged-tree-reconciliations.md: the twin launch
preamble fixes it outside the counted operation). At the default ten seconds a
cache miss sweeps the cache once half of that has passed since the last sweep
[source 2026-09-26T19:44:01+10:00:
https://github.com/SWI-Prolog/swipl-devel/blob/fc7ef84b949378b729052c3ade79c90ce5416abb/boot/init.pl#L1490-L1563],
and the sweep is Prolog work inside the window: with the third process's stamp
aged and the default lifetime, the import cost it 4 inferences more than the
second [measured 2026-09-26T19:41:58+10:00: 63,374 against 63,370, three runs
of three], the gap the pytest lane read between the two later processes at a
load of 122 [measured 2026-09-26T19:10:46+10:00: 63,374 against 63,370]. The
third process's sweep stamp is aged to the epoch, so the equality is asked of
an expired clock every run, not only when a process happens to run slowly.
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
#: loaded every file inside the window, and what the window cost. The fourth
#: argument, `aged`, sets the cache sweep's last run to the epoch first.
PROBE = r'''
import json, sys
seat, tree, library, clock = sys.argv[1:5]
sys.path.insert(0, seat)
import janus_swi as janus
# Engines inherit flags when created, so the lifetime is set before boot.
janus.cmd("system", "set_prolog_flag", "file_search_cache_time", 9223372036854775807)
from metta import MeTTa
m = MeTTa(metta_path=tree).self
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
if clock == "aged":
    janus.query_once("retractall(system:'$search_path_gc_time'(_)), "
                     "assertz(system:'$search_path_gc_time'(0))")
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

    def run(clock: str) -> dict:
        result = subprocess.run(
            [sys.executable, "-c", PROBE, str(seat()), str(tree), LIBRARY, clock],
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

    return {"tree": tree, "decoy": decoy, "first": run("fresh"), "later": run("fresh"),
            "again": run("aged")}


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
    """Neither pays a compile or a cache sweep, so the import costs both the same."""
    assert runs["later"]["inferences"] == runs["again"]["inferences"]
