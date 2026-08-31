"""Purpose: metta_module.boot assembles an app from a (boot ...) manifest: closed
vocabulary, whole-manifest validation before any effect, source-order
performance, and the deployment recorded as queryable atoms.
Guarantees:
  - covers every vocabulary entry (load, attach, bridge, serve), every
    refusal (unknown form, bad shape, definition, ! directive, empty
    manifest, connection mismatches), and the mid-way failure law
  - covers the three ways a form and its record can come apart: an attach
    the direct door would refuse, a record write that raises after its
    effect performed, and a cleanup that meets a server refusing to close
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
from metta import S, V
from metta.errors import SubscriberError


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class _StubServer:
    """A server handle that records its close and may refuse to close.

    Standing in for metta.remote.Server, whose own close() raises only from
    its own thread or on a stuck join, neither of which a test can ask for
    without wedging the run it is part of.
    """

    def __init__(self, *, refuse: bool = False) -> None:
        self.refuse = refuse
        self.closed = False

    def close(self) -> None:
        self.closed = True
        if self.refuse:
            msg = "this server refuses to close"
            raise RuntimeError(msg)


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
    (group,) = metta.run("!(collapse (match &metta (bridge &mdb $s $r) $s))")
    assert len(list(group[0])) == 1


def test_attach_registers_the_remote_space(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # Registration is lazy, so a dead URL attaches; only use would fail.
    (tmp_path / "app.metta").write_text('(boot (attach &mhq "http://127.0.0.1:9" &their))\n')
    with metta_module.boot(tmp_path / "app.metta", m=metta):
        assert "&mhq" in metta.space_names()
    metta._unregister_space("&mhq")


def test_a_manifest_cannot_attach_a_space_this_process_serves(metta, tmp_path):
    """The manifest's attach is the direct attach: one guard, called twice.

    Measured 2026-08-30, before the manifest called it: `metta.space(url)`
    refused this URL and the manifest attached it, after which the first
    match against the attached space stalled 30.0s, the transport's whole
    timeout, and failed with a message naming neither the cause nor the
    remedy while the serving thread died on a broken pipe.

    The refusal is compared against the guard's own words rather than
    matched loosely, because a manifest that grew a second copy of them
    would pass a loose match and then drift from the door it must agree
    with.
    """
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    served = metta_module.remote.serve(metta, port=port, spaces=["&self"])
    try:
        with pytest.raises(metta_module.MettaError) as guard:
            metta_module.remote._refuse_this_process(url, "&mself")
    finally:
        served.close()

    (tmp_path / "app.metta").write_text(
        f'(boot (serve (&self) {port}))\n(boot (attach &mself "{url}"))\n'
    )
    with pytest.raises(metta_module.MettaError, match=r"boot form 2 failed") as caught:
        metta_module.boot(tmp_path / "app.metta", m=metta)
    assert str(caught.value.__cause__) == str(guard.value)
    assert "&mself" not in metta.space_names()
    assert list(metta.match(f'(boot (attach &mself "{url}"))')) == []
    # the serve form that came first went with the failure
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(url + "/health", timeout=2)


def test_the_attach_guard_is_called_rather_than_copied(metta, tmp_path, monkeypatch):
    """The guard reached through its own name, with the form's own operands.

    The refusal text alone cannot tell a call from a verbatim copy, and a
    copy is the defect: it passes today and drifts from remote.py tomorrow.
    So this replaces the helper and watches the manifest reach for it, which
    also pins the argument order and that a refusal registers nothing.
    """
    asked = []

    def _record(url, name, pending):
        asked.append((url, name, tuple(pending)))
        msg = "the guard refused"
        raise metta_module.MettaError(msg)

    monkeypatch.setattr(metta_module.manifest._remote, "_refuse_this_process", _record)
    (tmp_path / "app.metta").write_text('(boot (attach &mguard "http://127.0.0.1:9" &their))\n')
    with pytest.raises(metta_module.MettaError, match=r"boot form 1 failed"):
        metta_module.boot(tmp_path / "app.metta", m=metta)
    # The addresses this run will serve travel with the URL and the name:
    # this manifest serves none, and the one below serves the very port it
    # attaches.
    assert asked == [("http://127.0.0.1:9", "&mguard", ())]
    assert "&mguard" not in metta.space_names()


def test_a_manifest_that_attaches_before_it_serves_is_refused(metta, tmp_path):
    """The guard reads the whole manifest, not the servers started so far.

    A manifest is validated whole before any of it runs, so an attach form
    standing above the serve form that binds its port names an address this
    same process is about to hold. Measured 2026-08-30: the same two forms
    were refused in one order and accepted in the other, and the accepted
    one had nothing left to fail on until its first match deadlocked.
    """
    port = _free_port()
    (tmp_path / "app.metta").write_text(
        f'(boot (attach &m-ahead "http://127.0.0.1:{port}"))\n'
        f"(boot (serve (&self) {port}))\n",
        encoding="utf-8",
    )
    with pytest.raises(metta_module.MettaError, match=r"boot form 1 failed") as refusal:
        metta_module.boot(tmp_path / "app.metta", m=metta)
    assert "same process" in str(refusal.value.__cause__)
    assert "&m-ahead" not in metta.space_names()


def test_a_failed_record_reports_the_effect_that_performed(metta, tmp_path):
    """A form performs in two halves, and the failure says which one failed.

    Measured 2026-08-30: a watcher raising on the `(boot ...)` record made
    boot say "boot form 1 failed ... The 0 forms before it performed and
    their writes stand", which reads as a form that did nothing, while its
    server was up and its record had committed. SubscriberError is the
    sharpest case of it, saying in as many words that the write stands.
    """
    port = _free_port()
    (tmp_path / "app.metta").write_text(f"(boot (serve (&self) {port}))\n")

    def explode(_event):
        msg = "the deployment watcher raised"
        raise RuntimeError(msg)

    watcher = metta.subscribe(S.boot(V.what), explode)
    try:
        with pytest.raises(metta_module.MettaError) as caught:
            metta_module.boot(tmp_path / "app.metta", m=metta)
    finally:
        watcher.cancel()
    assert "Its effect performed and the write that records it raised" in str(caught.value)
    assert isinstance(caught.value.__cause__, SubscriberError)
    # the effect that performed is also the effect the failure path closed
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)


def test_every_server_closes_even_when_one_refuses(metta):
    """One server that will not stop does not strand the servers after it.

    Measured 2026-08-30: with two servers and the first refusing, the second
    was never asked to close, so its socket, accept thread and engine worker
    stayed for the life of the process. One refusal still arrives on its
    own; several arrive together, the shape Server.close() already uses.
    """
    first, second = _StubServer(refuse=True), _StubServer()
    with pytest.raises(RuntimeError, match=r"refuses to close"):
        metta_module.manifest.Boot(metta, (first, second), ()).close()
    assert (first.closed, second.closed) == (True, True)

    both = (_StubServer(refuse=True), _StubServer(refuse=True))
    with pytest.raises(BaseExceptionGroup) as caught:
        metta_module.manifest.Boot(metta, both, ()).close()
    assert len(caught.value.exceptions) == 2


def test_a_cleanup_failure_travels_beside_the_boot_failure(metta, tmp_path, monkeypatch):
    """A close that fails while abandoning a boot loses neither failure.

    Measured 2026-08-30: the close raised out of the except block that was
    building the boot failure, so the reason the manifest failed never
    reached the caller and the server after the refusing one was never
    closed. They are independent failures, so neither is the other's cause.
    """
    started = []

    def _stub_serve(_m, **_policy):
        started.append(_StubServer(refuse=not started))
        return started[-1]

    monkeypatch.setattr(metta_module.manifest._remote, "serve", _stub_serve)
    (tmp_path / "app.metta").write_text(
        "(boot (serve (&self) 8701))\n"
        "(boot (serve (&self) 8702))\n"
        '(boot (load "missing.metta"))\n'
    )
    with pytest.raises(BaseExceptionGroup) as caught:
        metta_module.boot(tmp_path / "app.metta", m=metta)
    assert [stub.closed for stub in started] == [True, True]
    narrative, cause, refusal = caught.value.exceptions
    assert "boot form 3 failed" in str(narrative)
    assert "1 of the 2 servers it started did not close" in str(narrative)
    assert isinstance(refusal, RuntimeError)
    # the reason the manifest failed is in the group too, not replaced by the
    # close that failed while cleaning up after it
    assert "missing.metta" in str(cause)


def test_every_problem_is_reported_before_anything_performs(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "app.metta").write_text(
        "(boot (launch &x))\n"
        "(boot (load 42))\n"
        "(boot (serve () 8700))\n"
        "(boot (serve (&self) 70000))\n"
        "(not-a-boot-form)\n"
    )
    with pytest.raises(metta_module.MettaError) as caught:
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
    with pytest.raises(metta_module.MettaError, match=r"bridge &mconn names no connection"):
        metta_module.boot(tmp_path / "app.metta", m=metta)
    (tmp_path / "plain.metta").write_text("(boot (serve (&self) 0))\n")
    with pytest.raises(metta_module.MettaError, match=r"'&stray' is claimed by no bridge"):
        metta_module.boot(
            tmp_path / "plain.metta",
            m=metta,
            connections={"&stray": sqlite3.connect(":memory:")},
        )
    assert list(metta.match("(boot (bridge &mconn $s $r))")) == []


def test_a_manifest_neither_runs_nor_defines(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    (tmp_path / "bang.metta").write_text('!(boot (load "x.metta"))\n')
    with pytest.raises(metta_module.MettaError, match=r"does not run.*drop the !"):
        metta_module.boot(tmp_path / "bang.metta", m=metta)
    (tmp_path / "defn.metta").write_text("(= (manifest-smuggled) 1)\n")
    with pytest.raises(metta_module.MettaError, match=r"does not define"):
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
    with pytest.raises(metta_module.MettaError, match=r"declares nothing"):
        metta_module.boot(tmp_path / "app.metta", m=metta)


def test_a_mid_way_failure_names_the_form_and_closes_servers(metta, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    port = _free_port()
    (tmp_path / "app.metta").write_text(
        f'(boot (serve (&self) {port}))\n(boot (load "missing.metta"))\n'
    )
    with pytest.raises(metta_module.MettaError, match=r"boot form 2 failed") as caught:
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
