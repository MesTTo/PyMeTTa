"""Purpose: prove private regex builds, cleanup and installed-wheel execution.

Guarantees: successful, failed, concurrent and cancelled builds preserve their
publication and cleanup contracts; a wheel carries source and builds on import
[tested: test_native_build_is_atomic_and_reused,
test_concurrent_processes_and_threads_publish_one_native_object,
test_cancelled_build_waits_for_its_compiler_and_discards_the_stage,
test_regex_source_builds_after_wheel_install; commit=WORKTREE].
Owns resources: pytest owns the copied libraries and installations. Every child
process is joined, and the cancellation fixture releases its compiler barrier.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from contextlib import ExitStack
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
NATIVE = ROOT / "lib/lib_regex"


@pytest.fixture
def native_library(tmp_path):
    """Copy the three build inputs, excluding existing objects and test data."""
    library = tmp_path / "library"
    for name in ("support/native_build.pl", "vendor/pcre4pl.c", "vendor/lib_regex_pcre.pl"):
        target = library / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(NATIVE / name, target)
    return library


def native_command(goal):
    """Run the public build entry in an isolated SWI process."""
    return ["swipl", "--on-error=status", "-q", "-f", "none",
            "-s", "support/native_build.pl", "-g", goal, "-t", "halt"]


def run_native(library):
    """Build, load and execute the resulting object before returning its path."""
    return subprocess.run(
        native_command("lib_regex_native_build:native_object(P), "
                       "use_module('vendor/lib_regex_pcre.pl'), "
                       "re_match('a', 'a'), writeln(P)"),
        cwd=library, capture_output=True, text=True, check=False,
    )


def test_native_build_is_atomic_and_reused(native_library):
    """A warm build is reused; a failed rebuild preserves the old executable."""
    first = run_native(native_library)
    assert first.returncode == 0, first.stdout + first.stderr
    binary = Path(first.stdout.strip()).resolve()
    original = binary.read_bytes()
    built = binary.stat().st_mtime_ns
    second = run_native(native_library)
    assert second.returncode == 0, second.stdout + second.stderr
    assert Path(second.stdout.strip()).resolve() == binary
    assert binary.stat().st_mtime_ns == built

    source = native_library / "vendor/pcre4pl.c"
    source.write_text(source.read_text(encoding="utf-8") + "\n#error regex_build_refusal_probe\n", encoding="utf-8")
    newer = built + 2_000_000_000
    os.utime(source, ns=(newer, newer))
    failed = run_native(native_library)
    assert failed.returncode != 0
    assert "regex_native_build" in failed.stderr
    assert "regex_build_refusal_probe" in failed.stderr
    assert "libpcre2-dev" in failed.stderr
    assert binary.read_bytes() == original
    assert sorted(path.name for path in binary.parent.iterdir()) == ["build.lock", binary.name]


def test_concurrent_processes_and_threads_publish_one_native_object(native_library):
    """Independent processes and their threads all load one complete object."""
    source = native_library / "vendor/pcre4pl.c"
    source.write_text(source.read_text(encoding="utf-8") + '\n#pragma message("regex_build_once")\n', encoding="utf-8")
    goal = (
        "findall(T, (between(1,4,_), "
        "thread_create(lib_regex_native_build:native_object(_),T,[])), Threads), "
        "maplist(thread_join,Threads,Statuses), maplist(=(true),Statuses), "
        "lib_regex_native_build:native_object(P), "
        "use_module('vendor/lib_regex_pcre.pl'), re_match('a','a'), writeln(P)"
    )
    with ExitStack() as resources:
        children = []
        for _ in range(6):
            out = resources.enter_context(tempfile.TemporaryFile(mode="w+", dir=native_library))
            err = resources.enter_context(tempfile.TemporaryFile(mode="w+", dir=native_library))
            child = resources.enter_context(subprocess.Popen(
                native_command(goal), cwd=native_library, stdout=out, stderr=err, text=True,
            ))
            children.append((child, out, err))
        results = []
        for child, out, err in children:
            status = child.wait()
            out.seek(0)
            err.seek(0)
            results.append((status, out.read(), err.read()))
    assert all(status == 0 for status, _, _ in results), results
    paths = {Path(out.strip()).resolve() for _, out, _ in results}
    assert len(paths) == 1
    diagnostics = [line for _, _, err in results for line in err.splitlines()
                   if "regex_build_once" in line and ("note:" in line or "warning:" in line)]
    assert len(diagnostics) == 1, results
    [binary] = paths
    assert sorted(path.name for path in binary.parent.iterdir()) == ["build.lock", binary.name]


@pytest.mark.skipif(os.name != "posix", reason="the compiler-barrier fixture uses a POSIX FIFO")
def test_cancelled_build_waits_for_its_compiler_and_discards_the_stage(native_library):
    """Cancellation joins the compiler before removing its unpublished output."""
    before = run_native(native_library)
    assert before.returncode == 0, before.stdout + before.stderr
    binary = Path(before.stdout.strip()).resolve()
    original = binary.read_bytes()
    barrier = native_library / "build-barrier.h"
    os.mkfifo(barrier)
    source = native_library / "vendor/pcre4pl.c"
    source.write_text(f"#include {json.dumps(str(barrier))}\n" + source.read_text(encoding="utf-8"), encoding="utf-8")
    newer = binary.stat().st_mtime_ns + 2_000_000_000
    os.utime(source, ns=(newer, newer))
    goal = (
        "thread_create(catch(lib_regex_native_build:native_object(_),"
        "error(regex_native_build(build_cancelled),_),thread_exit(cancelled)), Worker, []),"
        "get_char(_), thread_signal(Worker,throw(build_cancelled)),"
        "writeln(cancel_requested), flush_output,"
        "thread_join(Worker,exited(cancelled)),writeln(cancelled)"
    )
    with tempfile.TemporaryFile(mode="w+", dir=native_library) as errors:
        with subprocess.Popen(native_command(goal), cwd=native_library,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=errors, text=True) as child:
            assert child.stdin is not None and child.stdout is not None
            # Opening a FIFO writer waits until the compiler opens its include.
            with barrier.open("w", encoding="utf-8") as unblock:
                try:
                    child.stdin.write("C\n")
                    child.stdin.flush()
                    acknowledgement = child.stdout.readline()
                finally:
                    unblock.write("\n")
                    unblock.flush()
            output, _ = child.communicate()
            status = child.returncode
        errors.seek(0)
        diagnostic = errors.read()
    assert acknowledgement == "cancel_requested\n", diagnostic
    assert status == 0 and output == "cancelled\n", output + diagnostic
    assert binary.read_bytes() == original
    assert sorted(path.name for path in binary.parent.iterdir()) == ["build.lock", binary.name]


def test_regex_source_builds_after_wheel_install(tmp_path):
    """Build a wheel from its source archive, install it and call its regex face."""
    dist = tmp_path / "dist"
    built_source = subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(dist), str(ROOT)],
        capture_output=True, text=True, check=False,
    )
    assert built_source.returncode == 0, built_source.stdout + built_source.stderr
    [sdist] = dist.glob("pymetta-*.tar.gz")
    with tarfile.open(sdist) as archive:
        source_names = archive.getnames()
    assert any(name.endswith("/lib/lib_regex/vendor/pcre4pl.c") for name in source_names)
    assert not any("/.native/" in name for name in source_names)

    built_wheel = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist), str(sdist)],
        capture_output=True, text=True, check=False,
    )
    assert built_wheel.returncode == 0, built_wheel.stdout + built_wheel.stderr
    [wheel] = dist.glob("pymetta-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    assert "metta/_runtime/lib/lib_regex/vendor/pcre4pl.c" in names
    assert "metta/_runtime/lib/lib_regex/support/native_build.pl" in names
    assert not any("/.native/" in name for name in names)

    installed = tmp_path / "installed"
    install = subprocess.run(
        ["uv", "pip", "install", "--python", sys.executable, "--no-deps",
         "--target", str(installed), str(wheel)],
        capture_output=True, text=True, check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    environment = os.environ | {"PYTHONPATH": str(installed)}
    environment.pop("METTA_PATH", None)
    probe = subprocess.run(
        [sys.executable, "-c", """
from pathlib import Path
import metta
from metta import G, MeTTa, lib
package = Path(metta.__file__).parent
assert package.parent == Path.cwd() / "installed", package
runtime = package / "_runtime"
assert not (runtime / "lib/lib_regex/.native").exists()
with MeTTa() as engine:
    engine += lib.regex
    [pattern] = engine.fn.re_compile(G("a*?"))
    try:
        assert engine.fn.re_find(pattern, G("aa")) == ["", "a", "", "a", ""]
        assert engine.fn.re_replace_all(pattern, G("X"), G("aa")) == ["XXXXX"]
        assert "_NativeHandle(" in repr([pattern])
    finally:
        pattern.release()
assert list((runtime / "lib/lib_regex/.native").glob("pcre-*"))
print("installed regex source built and executed")
"""],
        cwd=tmp_path, env=environment, capture_output=True, text=True, check=False,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr
    assert probe.stdout.strip() == "installed regex source built and executed"
