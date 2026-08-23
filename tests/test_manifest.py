"""Purpose: metta_module.boot assembles an app from a (boot ...) manifest: closed
vocabulary, whole-manifest validation before any effect, source-order
performance, and the deployment recorded as queryable atoms.
Guarantees:
  - covers every vocabulary entry (load, attach, bridge, serve), every
    refusal (unknown form, bad shape, definition, ! directive, empty
    manifest, connection mismatches), and the mid-way failure law
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import json
import socket
import sqlite3
import urllib.error
import urllib.request

import pytest

import metta as metta_module


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_boot_is_reachable_lazily():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert "boot" in dir(metta_module)
    assert "Boot" not in dir(metta_module)
    assert metta_module.boot is metta_module.manifest.boot
    assert metta_module.manifest.Boot.__module__ == "metta.manifest"


def test_load_and_serve_assemble_and_record(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "rules.metta").write_text("(= (manifest-double $x) (* $x 2))\n")
    (tmp_path / "app.metta").write_text(
        ';; the app, declared\n(boot (load "rules.metta"))\n(boot (serve (&self) 0))\n'
    )
    booted = metta_module.boot(tmp_path / "app.metta", m=metta)
    try:
        assert list(metta.eval("(manifest-double 21)")) == [42]
        topology = {str(row[0]) for row in metta.match("(boot $what)")}
        assert '(load "rules.metta")' in topology
        assert "(serve (&self) 0)" in topology
        (server,) = booted.servers
        health = json.loads(urllib.request.urlopen(server.url + "/health").read())
        assert health["protocol"] == 3
        assert repr(booted) == "Boot(2 forms performed, 1 servers)"
    finally:
        booted.close()
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(server.url + "/health", timeout=2)


def test_boot_is_a_context_manager(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "app.metta").write_text("(boot (serve (&self) 0))\n")
    with metta_module.boot(tmp_path / "app.metta", m=metta) as booted:
        url = booted.servers[0].url
        urllib.request.urlopen(url + "/health")
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(url + "/health", timeout=2)


def test_load_resolves_against_the_manifest_directory(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    nested = tmp_path / "deploy"
    nested.mkdir()
    (nested / "facts.metta").write_text("(manifest-fact here)\n")
    (nested / "app.metta").write_text('(boot (load "facts.metta"))\n')
    # cwd is wherever pytest runs; only the manifest's directory may matter.
    with metta_module.boot(nested / "app.metta", m=metta):
        assert [str(row[0]) for row in metta.match("(manifest-fact $w)")] == ["here"]


def test_bridge_declares_materializes_and_registers(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE medges (a TEXT, b TEXT)")
    connection.executemany("INSERT INTO medges VALUES (?, ?)", [("x", "y"), ("y", "z")])
    (tmp_path / "app.metta").write_text(
        "(boot (bridge &mdb (medge $a $b) (row medges (a $a) (b $b))))\n"
    )
    booted = metta_module.boot(tmp_path / "app.metta", m=metta, connections={"&mdb": connection})
    assert [str(p) for p in booted.performed] == [
        "(boot (bridge &mdb (medge $a $b) (row medges (a $a) (b $b))))"
    ]
    (group,) = metta.run("!(collapse (match &mdb (medge x $to) $to))")
    assert [str(a) for a in group[0]] == ["y"]
    (group,) = metta.run("!(collapse (match &petta (bridge &mdb $s $r) $s))")
    assert len(list(group[0])) == 1


def test_attach_registers_the_remote_space(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Registration is lazy, so a dead URL attaches; only use would fail.
    (tmp_path / "app.metta").write_text('(boot (attach &mhq "http://127.0.0.1:9" &their))\n')
    with metta_module.boot(tmp_path / "app.metta", m=metta):
        assert "&mhq" in metta.space_names()
    metta._unregister_space("&mhq")


def test_every_problem_is_reported_before_anything_performs(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "app.metta").write_text(
        "(boot (launch &x))\n"
        "(boot (load 42))\n"
        "(boot (serve () 8700))\n"
        "(boot (serve (&self) 70000))\n"
        "(not-a-boot-form)\n"
    )
    with pytest.raises(metta_module.PettaError) as caught:
        metta_module.boot(tmp_path / "app.metta", m=metta)
    message = str(caught.value)
    assert "form 1: unknown boot form launch" in message
    assert "form 2: load takes one string path" in message
    assert "form 3: serve's first argument" in message
    assert "form 4: serve's second argument" in message
    assert "form 5: (not-a-boot-form) is not a (boot (...)) form" in message
    assert list(metta.match("(boot (launch $x))")) == []


def test_connections_must_match_bridges_exactly(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "app.metta").write_text("(boot (bridge &mconn (e $a) (row t (a $a))))\n")
    with pytest.raises(metta_module.PettaError, match=r"bridge &mconn names no connection"):
        metta_module.boot(tmp_path / "app.metta", m=metta)
    (tmp_path / "plain.metta").write_text("(boot (serve (&self) 0))\n")
    with pytest.raises(metta_module.PettaError, match=r"'&stray' is claimed by no bridge"):
        metta_module.boot(
            tmp_path / "plain.metta",
            m=metta,
            connections={"&stray": sqlite3.connect(":memory:")},
        )
    assert list(metta.match("(boot (bridge &mconn $s $r))")) == []


def test_a_manifest_neither_runs_nor_defines(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "bang.metta").write_text('!(boot (load "x.metta"))\n')
    with pytest.raises(metta_module.PettaError, match=r"does not run.*drop the !"):
        metta_module.boot(tmp_path / "bang.metta", m=metta)
    (tmp_path / "defn.metta").write_text("(= (manifest-smuggled) 1)\n")
    with pytest.raises(metta_module.PettaError, match=r"does not define"):
        metta_module.boot(tmp_path / "defn.metta", m=metta)
    # the refusal happened at the read: nothing was compiled
    assert list(metta.match("(= (manifest-smuggled) $b)")) == []
    # and nothing was REGISTERED either, which is the half a compiled-clause
    # query cannot see. run() and load() register a source's whole signature
    # set before processing its forms; a manifest read is the one door that
    # must not, because it neither compiles nor stores nor runs.
    metta.run("!(import! &self (library lib_reflect))")
    assert metta.run("!(engine-knows manifest-smuggled)") == [[False]]


def test_an_empty_manifest_refuses(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "app.metta").write_text(";; nothing but comments\n")
    with pytest.raises(metta_module.PettaError, match=r"declares nothing"):
        metta_module.boot(tmp_path / "app.metta", m=metta)


def test_a_mid_way_failure_names_the_form_and_closes_servers(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    port = _free_port()
    (tmp_path / "app.metta").write_text(
        f'(boot (serve (&self) {port}))\n(boot (load "missing.metta"))\n'
    )
    with pytest.raises(metta_module.PettaError, match=r"boot form 2 failed") as caught:
        metta_module.boot(tmp_path / "app.metta", m=metta)
    assert "1 forms before it performed" in str(caught.value)
    assert caught.value.__cause__ is not None
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
    # the performed prefix stands, the law the engine's own guards follow
    assert [str(r[0]) for r in metta.match(f"(boot (serve $s {port}))")] == ["(&self)"]


def test_bridge_declarations_gather_and_source_order_holds(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE mpeople (n TEXT)")
    connection.execute("CREATE TABLE mpets (n TEXT)")
    connection.execute("INSERT INTO mpeople VALUES ('ada')")
    connection.execute("INSERT INTO mpets VALUES ('rex')")
    (tmp_path / "app.metta").write_text(
        "(boot (bridge &mzoo (mperson $n) (row mpeople (n $n))))\n"
        "(boot (bridge &mzoo (mpet $n) (row mpets (n $n))))\n"
        "(boot (serve (&mzoo) 0))\n"
    )
    booted = metta_module.boot(
        tmp_path / "app.metta", m=metta, connections={"&mzoo": connection}
    )
    try:
        # the name materialized at its FIRST form carrying BOTH declarations,
        # which is what let the serve that follows name it
        (group,) = metta.run("!(collapse (match &mzoo (mperson $n) $n))")
        assert [str(a) for a in group[0]] == ["ada"]
        (group,) = metta.run("!(collapse (match &mzoo (mpet $n) $n))")
        assert [str(a) for a in group[0]] == ["rex"]
        # performed order is manifest order, the observable of "source order"
        assert [str(p)[6:16] for p in booted.performed] == [
            "(bridge &m",
            "(bridge &m",
            "(serve (&m",
        ]
    finally:
        booted.close()
