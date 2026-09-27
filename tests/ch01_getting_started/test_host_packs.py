"""Purpose: hold the seat's host-pack boot steps to their contract on the running engine.

A Linux wheel's host leaves out the SWI libraries whose plugins link LGPL code,
and metta-library-pack carries them as SWI packs, registered against the
host-pack seam point. The boot attaches every registered pack before the
engine loads, or, with none attached, tells the engine the command that
installs each library the home left out. Each case plants what a wheel would
hold in its own scratch tree and drives the two steps against the engine this
suite already booted, so the rule is exercised without a wheel.
Guarantees:
  - a host-pack row built for the running host attaches its packs, and a
    library in one then loads [tested 2026-09-27T22:15:47+10:00: test_a_row_for_this_host_attaches_its_packs]
  - a row built for another host refuses naming both builds and attaches
    nothing [tested 2026-09-27T22:15:47+10:00: test_a_row_for_another_host_is_refused]
  - with no pack attached, a library the home left for the pack is refused by
    SWI's own loader and by the census naming the install command, however a
    library in a directory is spelled, and a library nobody supplies keeps
    SWI's words
    [tested 2026-09-27T22:15:47+10:00: test_a_library_left_for_the_pack_names_the_command,
    test_a_library_in_a_directory_names_the_command_however_it_is_spelled,
    test_a_library_nobody_supplies_keeps_swis_words]
"""

from __future__ import annotations

import pytest

import metta
from metta import _host, seam
from metta._binding import runtime
from metta._binding.runtime import bridge
from metta._errors.errors import EngineError


@pytest.fixture
def janus():
    """The booted engine's bridge."""
    metta.space().run("!(+ 1 1)")
    return bridge()


def _running(janus) -> str:
    return str(janus.query_once("current_prolog_flag(compiled_at, C)")["C"])


def _plant_pack(root, pack, module):
    """One SWI pack as split-home.py lays it out: pack.pl and prolog/<module>.pl."""
    (root / pack / "prolog").mkdir(parents=True)
    (root / pack / "pack.pl").write_text(f"name({pack}).\nversion('1.0.0').\n", encoding="utf-8")
    (root / pack / "prolog" / f"{module}.pl").write_text(
        f":- module({module}, [planted/1]).\nplanted(from_the_pack).\n", encoding="utf-8")


def _refusal(janus, spec: str) -> str:
    """`loaded`, or the words SWI's message system gives the error loading Spec raised."""
    try:
        janus.query_once(f"use_module({spec})")
    except janus.PrologError as refused:
        return str(refused)
    return "loaded"


def test_a_row_for_this_host_attaches_its_packs(janus, tmp_path):
    """A row whose build is the running host's attaches, and its library loads."""
    _plant_pack(tmp_path, "hlpackplanted", "hl_pack_planted")
    seam.host_pack.register("planted", directory=tmp_path, build=_running(janus))
    try:
        assert runtime._attach_host_packs(janus) is True
        row = janus.query_once("use_module(library(hl_pack_planted)), hl_pack_planted:planted(X)")
        assert str(row["X"]) == "from_the_pack"
    finally:
        seam.host_pack.unregister("planted")
        janus.query_once("ignore('$pack_detach'(hlpackplanted, _))")
        janus.query_once("retractall(user:file_search_path(pack, D))", {"D": str(tmp_path)})


def test_a_row_for_another_host_is_refused(janus, tmp_path):
    """A pack linked against another libswipl is refused, naming both builds."""
    _plant_pack(tmp_path, "hlpackforeign", "hl_pack_foreign")
    seam.host_pack.register("foreign", directory=tmp_path, build="Jan  1 1970, 00:00:00")
    try:
        with pytest.raises(EngineError) as refused:
            runtime._attach_host_packs(janus)
        assert "Jan  1 1970, 00:00:00" in str(refused.value)
        assert _running(janus) in str(refused.value)
        assert "pip install --force-reinstall 'pymetta[pack]'" in str(refused.value)
        assert _refusal(janus, "library(hl_pack_foreign)") != "loaded"
    finally:
        seam.host_pack.unregister("foreign")


def test_a_library_left_for_the_pack_names_the_command(janus, monkeypatch):
    """With no pack attached, both refusals end in the extra that installs it."""
    monkeypatch.setattr(_host, "PACK_LIBRARIES", ("hl_left_for_the_pack",))
    monkeypatch.setattr(_host, "SUPPLIERS", {})
    runtime._declare_pack_suppliers()
    command = "`pip install 'pymetta[pack]'` installs it"
    assert command in _refusal(janus, "library(hl_left_for_the_pack)")
    census = janus.query_once("metta_engine:metta_platform_absence(library(hl_left_for_the_pack), T)")
    assert str(census["T"]) == f"library(hl_left_for_the_pack) is absent from this host, and {command}"


def test_a_library_in_a_directory_names_the_command_however_it_is_spelled(janus, monkeypatch):
    """library(cql/cql) and library('cql/cql') are one library, as pack-libraries.txt names it."""
    monkeypatch.setattr(_host, "PACK_LIBRARIES", ("hl_left_dir/hl_left_file",))
    monkeypatch.setattr(_host, "SUPPLIERS", {})
    runtime._declare_pack_suppliers()
    for spec in ("library(hl_left_dir/hl_left_file)", "library('hl_left_dir/hl_left_file')"):
        assert "`pip install 'pymetta[pack]'` installs it" in _refusal(janus, spec), spec


def test_a_library_nobody_supplies_keeps_swis_words(janus, monkeypatch):
    """A spec no host declared is refused in SWI's own words, with no command."""
    monkeypatch.setattr(_host, "SUPPLIERS", {})
    text = _refusal(janus, "library(hl_supplied_by_nobody)")
    assert "does not exist" in text
    assert "pip install" not in text
    census = janus.query_once("metta_engine:metta_platform_absence(library(hl_supplied_by_nobody), T)")
    assert str(census["T"]) == "library(hl_supplied_by_nobody) is absent"
