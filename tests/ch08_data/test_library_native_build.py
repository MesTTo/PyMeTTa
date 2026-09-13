"""Purpose: prove native library builds, cleanup and installed-wheel execution.

Guarantees: successful, failed, concurrent and cancelled builds preserve their
publication and cleanup contracts; a wheel carries source and builds on import
[tested: test_native_build_is_atomic_and_reused,
test_concurrent_processes_and_threads_publish_one_native_object,
test_cancelled_build_waits_for_its_compiler_and_discards_the_stage,
test_native_sources_build_after_wheel_install,
test_warm_native_build_needs_no_process_library; commit=WORKTREE].
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
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class NativeLibrary:
    """One real consumer's copied build inputs and executable probe."""

    path: Path
    name: str
    source: Path
    runtime_goal: str
    remedy: str

    @property
    def builder(self):
        """The owner's native build module follows its library name."""
        return f"lib_{self.name}_native_build"


PROVIDERS = {
    "database": ("support/lock.c", "support/native.pl",
                 "setup_call_cleanup(tmp_file_stream(binary,Probe,Stream),"
                 "lib_database_native:claim_stream(Stream,0),"
                 "call_cleanup(close(Stream),delete_file(Probe)))",
                 "SWI-Prolog development tools"),
    "regex": ("vendor/pcre4pl.c", "vendor/lib_regex_pcre.pl",
              "re_match('a', 'a')", "libpcre2-dev"),
    "crypto": ("support/crypto_native.c", "support/native.pl",
               "lib_crypto_native:digest(sha256,utf8(hello),none,B), length(B,32)", "libssl-dev"),
    "string": ("support/string_native.cpp", "support/native.pl",
               'lib_string_native:edit_distance("kitten","sitting",3)', "build-essential"),
    "compression": ("support/archive_locale.c", "support/native.pl",
                    'setup_call_cleanup(open_string("x",Input),'
                    'lib_compression_native:with_utf8('
                    'lib_compression_native:with_archive(stream(Input),[formats([raw])],Archive,'
                    'lib_compression_native:archive_next_header(Archive,data))),close(Input))',
                    "cmake"),
}


@pytest.fixture(params=PROVIDERS)
def native_library(tmp_path, request):
    """Copy each owner's inputs and the shared helper, excluding built objects."""
    name = request.param
    source, loader, probe, remedy = PROVIDERS[name]
    library = tmp_path / "lib" / f"lib_{name}"
    origin = ROOT / "lib" / library.name
    for directory in ("support", "vendor"):
        inputs = origin / directory
        if inputs.is_dir():
            shutil.copytree(inputs, library / directory, ignore=shutil.ignore_patterns("*.qlf"))
    shared = library.parent / "_support/native_build.pl"
    shared.parent.mkdir(parents=True)
    shutil.copy2(ROOT / "lib/_support/native_build.pl", shared)
    return NativeLibrary(library, name, library / source,
                         f"use_module('{loader}'), {probe}", remedy)


def native_command(goal, prelude=None):
    """Run the public build entry in an isolated SWI process."""
    prefix = ["swipl", "--on-error=status", "-q", "-f", "none"]
    if prelude is not None:
        prefix.extend(["-s", str(prelude)])
    return [*prefix, "-s", "support/native_build.pl", "-g", goal, "-t", "halt"]


def run_native(library, prelude=None):
    """Build, load and execute the resulting object before returning its path."""
    return subprocess.run(
        native_command(f"{library.builder}:native_object(P), "
                       f"{library.runtime_goal}, writeln(P)", prelude),
        cwd=library.path, capture_output=True, text=True, check=False,
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

    source = native_library.source
    source.write_text(source.read_text(encoding="utf-8") + "\n#error native_build_refusal_probe\n", encoding="utf-8")
    newer = built + 2_000_000_000
    os.utime(source, ns=(newer, newer))
    failed = run_native(native_library)
    assert failed.returncode != 0
    assert f"{native_library.name}_native_build" in failed.stderr
    assert "native_build_refusal_probe" in failed.stderr
    assert native_library.remedy in failed.stderr
    assert binary.read_bytes() == original
    assert {path.name for path in binary.parent.iterdir()} == {"build.lock", binary.name}


def test_concurrent_processes_and_threads_publish_one_native_object(native_library):
    """Independent processes and their threads all load one complete object."""
    source = native_library.source
    source.write_text(source.read_text(encoding="utf-8") + '\n#pragma message("native_build_once")\n', encoding="utf-8")
    goal = (
        "findall(T, (between(1,4,_), "
        f"thread_create({native_library.builder}:native_object(_),T,[])), Threads), "
        "maplist(thread_join,Threads,Statuses), maplist(=(true),Statuses), "
        f"{native_library.builder}:native_object(P), "
        f"{native_library.runtime_goal}, writeln(P)"
    )
    with ExitStack() as resources:
        children = []
        for _ in range(6):
            out = resources.enter_context(tempfile.TemporaryFile(mode="w+", dir=native_library.path))
            err = resources.enter_context(tempfile.TemporaryFile(mode="w+", dir=native_library.path))
            child = resources.enter_context(subprocess.Popen(
                native_command(goal), cwd=native_library.path, stdout=out, stderr=err, text=True,
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
                   if "native_build_once" in line and ("note:" in line or "warning:" in line)]
    assert len(diagnostics) == 1, results
    [binary] = paths
    assert {path.name for path in binary.parent.iterdir()} == {"build.lock", binary.name}


@pytest.mark.skipif(os.name != "posix", reason="the compiler-barrier fixture uses a POSIX FIFO")
def test_cancelled_build_waits_for_its_compiler_and_discards_the_stage(native_library):
    """Cancellation joins the compiler before removing its unpublished output."""
    before = run_native(native_library)
    assert before.returncode == 0, before.stdout + before.stderr
    binary = Path(before.stdout.strip()).resolve()
    original = binary.read_bytes()
    barrier = native_library.path / "build-barrier.h"
    os.mkfifo(barrier)
    source = native_library.source
    source.write_text(f"#include {json.dumps(str(barrier))}\n" + source.read_text(encoding="utf-8"), encoding="utf-8")
    newer = binary.stat().st_mtime_ns + 2_000_000_000
    os.utime(source, ns=(newer, newer))
    goal = (
        f"thread_create(catch({native_library.builder}:native_object(_),"
        f"error({native_library.name}_native_build(build_cancelled),_),thread_exit(cancelled)), Worker, []),"
        "get_char(_), thread_signal(Worker,throw(build_cancelled)),"
        "writeln(cancel_requested), flush_output,"
        "thread_join(Worker,exited(cancelled)),writeln(cancelled)"
    )
    with tempfile.TemporaryFile(mode="w+", dir=native_library.path) as errors:
        with subprocess.Popen(native_command(goal), cwd=native_library.path,
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
    assert {path.name for path in binary.parent.iterdir()} == {"build.lock", binary.name}


def test_warm_native_build_needs_no_process_library(native_library):
    """A real missing process.pl permits a warm import and names a cold refusal."""
    first = run_native(native_library)
    assert first.returncode == 0, first.stdout + first.stderr
    binary = Path(first.stdout.strip()).resolve()
    locate = subprocess.run(
        ["swipl", "-q", "-f", "none", "-g",
         "absolute_file_name(library(process),P,[file_type(prolog),access(read)]),"
         "file_directory_name(P,D),write(D),halt"],
        capture_output=True, text=True, check=False,
    )
    assert locate.returncode == 0, locate.stderr
    origin = Path(locate.stdout)
    farm = native_library.path / "reduced-process"
    farm.mkdir()
    for entry in origin.iterdir():
        if entry.name == "process.pl" or entry.suffix == ".qlf":
            continue
        target = farm / entry.name
        if entry.name == "INDEX.pl":
            shutil.copy2(entry, target)
        else:
            target.symlink_to(entry, target_is_directory=entry.is_dir())
    prelude = native_library.path / "without-process.pl"
    prelude.write_text(f"""
:- use_module(library(lists), [member/2]).
:- forall(member(Alias,[library,autoload]),
          ( Spec =.. [Alias,'.'],
            findall(D,absolute_file_name(Spec,D,[file_type(directory),access(read),solutions(all)]),Dirs),
            retractall(user:file_search_path(Alias,_)),
            forall(member(Dir,Dirs),
                   ( (same_file(Dir,{json.dumps(str(origin))})
                      -> Path={json.dumps(str(farm))} ; Path=Dir),
                     assertz(user:file_search_path(Alias,Path)) )) )).
:- retractall('$autoload':library_index(_,_,_)),
   retractall('$autoload':autoload_directories(_)),
   retractall('$autoload':index_checked_at(_)).
:- \\+ absolute_file_name(library(process),_,[file_type(prolog),access(read),file_errors(fail)]),
   \\+ current_predicate(process:process_create/3).
""", encoding="utf-8")
    warm = run_native(native_library, prelude)
    assert warm.returncode == 0 and not warm.stderr, warm.stdout + warm.stderr
    assert Path(warm.stdout.strip()).resolve() == binary
    binary.unlink()
    cold = run_native(native_library, prelude)
    assert cold.returncode != 0
    assert f"{native_library.name}_native_build" in cold.stderr
    assert "Prebuild" in cold.stderr and "same SWI ABI" in cold.stderr
    assert not list(binary.parent.glob("*.tmp.*"))


@pytest.mark.parametrize(("native_library", "header_path"),
                         [("string", "vendor/isub.hpp"),
                          ("compression", "vendor/archive_read_support_format_zip.c")],
                         indirect=["native_library"])
def test_native_header_change_rebuilds_the_object(native_library, header_path):
    """An included header cannot change or disappear behind a warm object."""
    before = run_native(native_library)
    assert before.returncode == 0, before.stdout + before.stderr
    binary = Path(before.stdout.strip()).resolve()
    original = binary.read_bytes()
    header = native_library.path / header_path
    source = header.read_text(encoding="utf-8")
    header.write_text(source + "\n#error native_header_refusal_probe\n", encoding="utf-8")
    newer = binary.stat().st_mtime_ns + 2_000_000_000
    os.utime(header, ns=(newer, newer))
    failed = run_native(native_library)
    assert failed.returncode != 0 and "native_header_refusal_probe" in failed.stderr, failed
    assert binary.read_bytes() == original
    header.write_text(source, encoding="utf-8")
    rebuilt = run_native(native_library)
    assert rebuilt.returncode == 0, rebuilt.stdout + rebuilt.stderr
    header.unlink()
    missing = run_native(native_library)
    assert missing.returncode != 0, missing
    assert header.name in missing.stderr and f"{native_library.name}_native_build" in missing.stderr


def test_native_sources_build_after_wheel_install(tmp_path):
    """Build from the source archive, install, then call native and codec libraries."""
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
    assert any(name.endswith("/lib/lib_crypto/support/crypto_native.c") for name in source_names)
    assert any(name.endswith("/lib/_support/native_build.pl") for name in source_names)
    assert any(name.endswith("/lib/lib_csv/support/csv_codec.pl") for name in source_names)
    assert any(name.endswith("/lib/_support/owned_resources.pl") for name in source_names)
    provider_files = ["lib/lib_string/support/string_native.cpp", "lib/lib_string/vendor/SHA256SUMS",
                      "lib/lib_vector/lib_vector.pl", "lib/lib_vector/lib_vector.metta",
                      "lib/lib_vector/README.md", "lib/lib_vector/vendor/README.md",
                      "lib/lib_vector/vendor/PYTHON-LICENSE",
                      "lib/lib_database/lib_database.pl", "lib/lib_database/lib_database.metta"]
    provider_files.extend("lib/lib_string/vendor/" + line.split("  ", 1)[1]
                        for line in (ROOT / "lib/lib_string/vendor/SHA256SUMS").read_text(encoding="utf-8").splitlines())
    provider_files.extend(str(path.relative_to(ROOT))
                          for library in ("lib_compression", "lib_database")
                          for directory in ("support", "vendor")
                          for path in (ROOT / "lib" / library / directory).rglob("*")
                          if path.is_file() and path.suffix != ".qlf")
    for name in provider_files:
        assert any(entry.endswith("/" + name) for entry in source_names), name
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
    assert "metta/_runtime/lib/lib_crypto/support/crypto_native.c" in names
    assert "metta/_runtime/lib/_support/native_build.pl" in names
    assert "metta/_runtime/lib/lib_csv/support/csv_codec.pl" in names
    assert "metta/_runtime/lib/_support/owned_resources.pl" in names
    for name in provider_files:
        assert "metta/_runtime/" + name in names, name
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
        [sys.executable, "-c", r"""
from pathlib import Path
import struct
import zipfile
import zlib
import metta
from metta import G, S, V, MeTTa, lib
package = Path(metta.__file__).parent
assert package.parent == Path.cwd() / "installed", package
runtime = package / "_runtime"
assert not (runtime / "lib/lib_regex/.native").exists()
assert not (runtime / "lib/lib_crypto/.native").exists()
assert not (runtime / "lib/lib_string/.native").exists()
assert not (runtime / "lib/lib_compression/.native").exists()
assert not (runtime / "lib/lib_database/.native").exists()
with MeTTa() as engine:
    engine += lib.regex
    [pattern] = engine.fn.re_compile(G("a*?"))
    try:
        assert engine.fn.re_find(pattern, G("aa")) == ["", "a", "", "a", ""]
        assert engine.fn.re_replace_all(pattern, G("X"), G("aa")) == ["XXXXX"]
        assert "_NativeHandle(" in repr([pattern])
    finally:
        pattern.release()
    engine += lib.crypto
    assert engine.fn.crypto_hash(G("sha256"), G("hello")).one() == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    record = engine.fn.crypto_password_hash(G("fixture"), 0).one()
    assert engine.fn.crypto_password_verify(G("fixture"), G(record)).one() is True
    engine += lib.csv
    options = S.quote(((S.separator, G("🦊")), (S.quote, G("λ"))))
    rows = ((G("a🦊b"), G("λquotedλ")),)
    text = engine.fn.csv_encode(rows, options).one()
    assert engine.fn.csv_parse(G(text), options).one() == rows
    engine += lib.string
    assert engine.fn.string_edit_distance(G("a\0🦊"), G("a")).one() == 2
    assert engine.fn.string_replace(G("a\0🦊"), G("\0"), G("-")).one() == "a-🦊"
    assert engine.fn.string_dedent(G("  a\0\n  b\n")).one() == "a\0\nb\n"
    engine += lib.vector
    ratios = engine.fn.vector_divide((1, 2), (3, 3)).one()
    assert ratios[0].to_wire()[0] == "n"
    assert engine.fn.vector_scale(ratios, 3).one() == (1, 2)
    assert engine.fn.dot((2.0**54, 1.0, -(2.0**54)), (1, 1, 1)).one() == 1.0
    assert engine.fn.cosine((2.0**1000,), (2.0**1000,)).one() == 1.0
    engine += lib.compression
    encoded = engine.fn.compress_bytes(S.gzip, 6, (0, 128, 255)).one()
    assert list(engine.fn.decompress_bytes(S.gzip, encoded).one()) == [0, 128, 255]
    fixture = Path("archive.zip")
    info = zipfile.ZipInfo("caf_")
    payload = b"\x01" + struct.pack("<I", zlib.crc32(b"caf\x82")) + "café/π🙂".encode()
    info.extra = struct.pack("<HH", 0x7075, len(payload)) + payload
    with zipfile.ZipFile(fixture, "w") as archive:
        archive.writestr(info, b"bytes")
    fixture.write_bytes(fixture.read_bytes().replace(b"caf_", b"caf\x82"))
    entries = engine.fn["archive-entries!"](G(str(fixture))).one()
    assert entries[0][2] == G("café/π🙂")
    assert bytes(engine.fn["archive-read!"](G(str(fixture)), 0).one()) == b"bytes"
    engine += lib.database
    for opening in (0, 1):
        handle = engine.fn["database-open!"](G("store"), S.close)[0]
        try:
            if opening == 0:
                assert engine.fn["database-add!"](handle, S.row(G("a\0π🙂"))).one() is True
            else:
                assert engine.fn.database_atoms(handle) == [(S.row(G("a\0π🙂")),)]
        finally:
            engine.fn["database-close!"](handle).one()
assert list((runtime / "lib/lib_regex/.native").glob("pcre-*"))
assert list((runtime / "lib/lib_crypto/.native").glob("crypto-*"))
assert list((runtime / "lib/lib_string/.native").glob("string-*"))
assert list((runtime / "lib/lib_compression/.native").glob("archive_locale-*"))
assert list((runtime / "lib/lib_database/.native").glob("database-*"))
print("installed native sources built and executed")
"""],
        cwd=tmp_path, env=environment, capture_output=True, text=True, check=False,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr
    assert probe.stdout.strip() == "installed native sources built and executed"
