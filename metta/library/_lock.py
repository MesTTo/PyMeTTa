"""Purpose: pin the knowledge a program loaded.

A lock says when the tree no longer matches what was pinned.
A `metta.lock` is to a MeTTa program what `uv.lock` is to a Python project:
one file, written by a tool and read by one, naming every artefact the program
depends on with the digest that identifies it, so a second machine either
loads exactly what the first did or is told precisely what differs. The shape
follows uv's and PEP 751's -- a `lock-version`, a `created-by`, an environment
table and one table per pinned artefact carrying its source and its hash
[source: https://docs.astral.sh/uv/concepts/projects/layout/ and
https://peps.python.org/pep-0751/].

The digests are the engine's own `metta_source_digest`, which is the identity
`import!` already compares to decide whether a source needs reloading, so a
lock check and a reload cannot disagree about whether a file changed
[source: engine/filereader/source_lifecycle.pl, metta_source_digest/2].

Assumes:
  - a relative path in a lock resolves against the LOCK's own directory, the
    rule uv uses for a project lock, so a checked-in lock travels with its
    program
  - `metta_py_source_loads/2` answers inside one transaction and refuses while
    a load is in flight [source: extensions/python/metta/_binding/library.pl:57; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e]
Guarantees:
  - a lock written and read back describes the same artefacts, and rewriting
    it beside itself reproduces its own bytes [tested:
    test_a_lock_round_trips_through_its_file,
    test_a_lock_is_readable_toml_with_the_documented_tables; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
  - editing one source flips exactly one Drift and leaves every other entry
    agreeing [tested: test_editing_one_source_flips_exactly_one_drift;
    commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
  - a lock taken while a load is in flight is refused rather than written half
    complete [tested: test_a_lock_refuses_while_a_load_is_in_flight;
    commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
  - a lock whose version this build does not know is refused by version rather
    than misread, and one that is not TOML is refused naming the file [tested:
    test_a_newer_lock_version_is_refused_by_number,
    test_a_malformed_lock_is_refused_by_name; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
  - `run --locked` gates the run BEFORE the program runs, refusing on drift
    with a nonzero exit [tested:
    test_a_locked_run_refuses_on_drift_and_runs_on_agreement; commit=ff4257005f562786e3ef7a5a37ce94b7d80e782d]
Fails when:
  - a program built its knowledge from text rather than from files: there is
    no source to digest, so nothing about it is pinned and the lock says so by
    having no row for it.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import functools
import hashlib
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from metta._errors.errors import LockDrift, MettaError
from metta._version import __version__

#: The lock format this build writes and is the newest it can read. It moves
#: when a reader of an older lock would misread a newer one, which is the rule
#: uv states for its own `version` field: a tool refuses a lock whose version
#: it does not know rather than guessing at the fields it has not seen
#: [source: https://docs.astral.sh/uv/concepts/projects/layout/].
LOCK_VERSION = 1

#: What a digest string carries in front of its hexadecimal, so a reader can
#: tell which function produced it if this ever grows a second one. PEP 751
#: spells the same idea as a `hashes` table keyed by algorithm name.
_PREFIX = "sha256:"

@dataclass(frozen=True)
class Drift:
    """One entry of a lock that no longer describes this tree.

    `kind` is which table the entry came from, `name` identifies it inside
    that table (an engine field, a library name, a source path, a repository
    URL), `expected` is what the lock recorded and `actual` is what is here
    now, which is None when the entry is not here at all.
    """

    kind: str
    name: str
    expected: str
    actual: str | None = None

    def __str__(self) -> str:
        """`library lib_memo: sha256:aa… locked, sha256:bb… here`."""
        here = "not present here" if self.actual is None else f"{self.actual} here"
        return f"{self.kind} {self.name}: {self.expected} locked, {here}"


@dataclass(frozen=True)
class LockedLibrary:
    """One shipped library the program imported, by its content digest."""

    name: str
    digest: str


@dataclass(frozen=True)
class LockedSource:
    """One file the program loaded, the space it loaded into, and its digest."""

    path: str
    space: str
    digest: str


@dataclass(frozen=True)
class LockedPin:
    """One repository the program pinned, at a full 40-character commit."""

    url: str
    commit: str


@dataclass(frozen=True)
class Lock:
    """The knowledge one program loaded, pinned by digest.

        lock = m.lock()
        lock.write("metta.lock")
        for drift in m.check(metta.Lock.read("metta.lock")):
            print(drift)

    `base` is the directory a relative source path resolves against: the
    working directory for a lock just taken, and the lock file's own directory
    for one read back. It is not written to the file, because it IS the file's
    location.
    """

    engine: _collections_abc.Mapping[str, str]
    libraries: tuple[LockedLibrary, ...] = ()
    sources: tuple[LockedSource, ...] = ()
    pins: tuple[LockedPin, ...] = ()
    version: int = LOCK_VERSION
    created_by: str = f"metta {__version__}"
    base: Path = field(default_factory=Path.cwd, compare=False)

    def text(self, *, base: Path | None = None) -> str:
        """The lock as TOML, with source paths relative to `base` where they can be.

        Written rather than serialised by a library because the shape is
        closed: three string tables and one integer, which is what keeps the
        file readable by a person and by `tomllib` without a dependency.
        """
        where = self.base if base is None else base
        lines = [
            f"lock-version = {self.version}",
            f"created-by = {_string(self.created_by)}",
            "",
            "[engine]",
        ]
        lines += [f"{key} = {_string(value)}" for key, value in self.engine.items()]
        for library in self.libraries:
            lines += [
                "",
                "[[library]]",
                f"name = {_string(library.name)}",
                f"digest = {_string(library.digest)}",
            ]
        for source in self.sources:
            lines += [
                "",
                "[[source]]",
                f"path = {_string(_relative(source.path, self.base, where))}",
                f"space = {_string(source.space)}",
                f"digest = {_string(source.digest)}",
            ]
        for pin in self.pins:
            lines += [
                "",
                "[[pin]]",
                f"url = {_string(pin.url)}",
                f"commit = {_string(pin.commit)}",
            ]
        return "\n".join(lines) + "\n"

    def write(self, path: str | os.PathLike[str]) -> Path:
        """Write the lock beside the program it pins, and answer where it went.

        Source paths are written relative to the lock's own directory when
        they sit under it, so a lock checked in beside its program travels
        with it; a path outside stays absolute, because there is nothing
        shorter that still names it.
        """
        target = Path(path)
        target.write_text(self.text(base=target.parent.resolve()), encoding="utf-8")
        return target

    @classmethod
    def read(cls, path: str | os.PathLike[str]) -> Lock:
        """Read a lock from its file, refusing one this build cannot read.

        A lock whose `lock-version` is newer is refused BY NUMBER rather than
        read for the fields this build happens to know, because a lock is a
        promise about everything it pins and a partial reading would pass a
        check it should have failed.
        """
        target = Path(path)
        try:
            with target.open("rb") as handle:
                document: dict[str, Any] = tomllib.load(handle)
        except OSError as error:
            msg = f"{target} cannot be read as a lock: {error}"
            raise MettaError(msg) from error
        except tomllib.TOMLDecodeError as error:
            msg = f"{target} is not readable as TOML: {error}"
            raise MettaError(msg) from error
        version = document.get("lock-version")
        if not isinstance(version, int) or version > LOCK_VERSION:
            msg = (
                f"{target} is lock-version {version!r} and this build reads "
                f"up to {LOCK_VERSION}: upgrade metta, or write a new lock "
                f"with `metta lock`"
            )
            raise MettaError(msg)
        return cls(
            engine={
                key: str(value) for key, value in (document.get("engine") or {}).items()
            },
            libraries=tuple(
                LockedLibrary(str(row.get("name")), str(row.get("digest")))
                for row in document.get("library") or ()
            ),
            sources=tuple(
                LockedSource(
                    str(row.get("path")), str(row.get("space")), str(row.get("digest"))
                )
                for row in document.get("source") or ()
            ),
            pins=tuple(
                LockedPin(str(row.get("url")), str(row.get("commit")))
                for row in document.get("pin") or ()
            ),
            version=version,
            created_by=str(document.get("created-by", "")),
            base=target.parent.resolve(),
        )

    def __str__(self) -> str:
        """The file's own text, so printing a lock shows what would be written."""
        return self.text()


def _string(value: str) -> str:
    r"""One TOML basic string, escaped the way the specification requires.

    The six named escapes, the backslash and the delimiter itself, and
    `\\uXXXX` for every other control character; nothing else may appear
    unescaped inside a basic string
    [source: https://toml.io/en/v1.0.0#string].
    """
    out = ['"']
    for character in value:
        if character in _ESCAPES:
            out.append(_ESCAPES[character])
        elif character < " " or character == "\x7f":
            out.append(f"\\u{ord(character):04X}")
        else:
            out.append(character)
    out.append('"')
    return "".join(out)


# closed-set: decides; policy=which characters a lock's TOML string escapes, which is TOML's own basic-string grammar; reads=none, it is the source
_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def _relative(path: str, source: Path, target: Path) -> str:
    """A path rewritten relative to `target`, resolving it against `source` first.

    Both halves are needed: the path in hand is either absolute or relative to
    the lock it came from, and the path written out is relative to the lock
    being written. Reading a lock and writing it back beside itself therefore
    reproduces its own text, which is what makes the file a fixed point.
    """
    absolute = _resolve(path, source).resolve()
    try:
        return absolute.relative_to(target).as_posix()
    except ValueError:
        return str(absolute)


def _resolve(path: str, base: Path) -> Path:
    """A locked path read back, against the lock's own directory."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else (base / candidate)


@functools.cache
def engine_digest(root: str) -> str:
    """One digest over the engine's own sources, cached for the process.

        metta.library._lock.engine_digest(metta.engine().runtime.metta_path)

    Every `engine/**/*.pl`, the vocabulary tier engine/prelude.pl among them
    since the prelude is Prolog, each hashed on its own
    and listed under its path relative to the tree, then the listing hashed as
    one document: two checkouts agree exactly when every engine source agrees,
    and a file added or removed changes the answer as surely as an edit does.

    The bytes are hashed here rather than through the engine's own text digest
    because this is a digest OF digests and never of a source, so it needs no
    encoding decision; the two answer identically for the same text
    [measured 2026-09-07: `metta_source_digest` of lib_he.metta and
    `hashlib.sha256` of its decoded text are the same 64 characters].

    Cost: O(the engine's source bytes) once per process, which is why it is
    cached; the tree is 50,297 lines.
    """
    tree = Path(root)
    sources = sorted(tree.joinpath("engine").rglob("*.pl"))
    listing = "\n".join(
        f"{path.relative_to(tree).as_posix()}\t"
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}"
        for path in sorted(sources)
    )
    return _PREFIX + hashlib.sha256(listing.encode("utf-8")).hexdigest()


def _loaded(rt: Any) -> tuple[str, list[tuple[str, str, str]]]:
    """Every source this process loaded, inside one transaction snapshot."""
    row = rt.must("metta_py_source_loads(Status, Rows)")
    return str(row["Status"]), [
        (str(path), str(space), str(digest)) for path, space, digest in row["Rows"]
    ]


def take(rt: Any) -> Lock:
    """Build a lock from what this engine has loaded.

    The library rows are the shipped libraries the program imported, by the
    digest of ALL their files rather than only the half that was read, because
    importing a library is importing both halves. Everything else it loaded is
    a source row with the space it landed in.

    The scope is the PROCESS. `metta_source_load/4` is the engine's own table
    and the engine is process-wide, so a second context takes the same lock;
    that is the unit a lock has to pin, because a program that loads into one
    space and reads from another is still one program to reproduce.
    """
    from metta.library import roster  # noqa: PLC0415  -- a satellite, deferred like the rest

    status, loads = _loaded(rt)
    if status != "settled":
        msg = (
            "a source is loading right now, so a lock taken here would record "
            "a program that is only half loaded: take it after the load "
            "finishes"
        )
        raise MettaError(msg)
    known = roster(rt.metta_path)
    owner = {
        str(path.resolve()): name for name, files in known.items() for path in files
    }
    base = Path.cwd()
    libraries: dict[str, str] = {}
    sources: list[LockedSource] = []
    for path, space, digest in loads:
        name = owner.get(str(Path(path).resolve()))
        if name is None:
            sources.append(
                LockedSource(_relative(path, base, base), space, _PREFIX + digest)
            )
        elif name not in libraries:
            libraries[name] = _library_digest(rt, known[name])
    return Lock(
        engine=_engine_table(rt),
        libraries=tuple(
            LockedLibrary(name, digest) for name, digest in sorted(libraries.items())
        ),
        sources=tuple(sorted(sources, key=lambda row: row.path)),
        pins=tuple(
            sorted(
                (
                    LockedPin(str(url), str(commit))
                    for url, commit in rt.apply_must("metta_py_git_pins")
                ),
                key=lambda row: row.url,
            )
        ),
        base=base,
    )


def _engine_table(rt: Any) -> dict[str, str]:
    """The engine this program ran on: its version, SWI's, and its sources.

    The two versions come from the same places `MeTTa.info()` reads them, so a
    lock and the context's own report cannot name different builds.
    """
    from metta._binding.runtime import (  # noqa: PLC0415 -- engine discovery is needed only when writing the lock
        _resolve_metta_path,
        bridge,
    )

    row = rt.must("current_prolog_flag(version, Version)")
    return {
        "metta": __version__,
        "swi-prolog": bridge().version_str(row["Version"]),
        "sources": engine_digest(rt.metta_path or _resolve_metta_path()),
    }


def _library_digest(rt: Any, files: _collections_abc.Iterable[Path]) -> str:
    """One library's digest, the derivation `metta.library.digest` states."""
    listing = sorted(
        f"{path}\t{rt.apply_must('metta_py_source_digest', str(path.resolve()))}"
        for path in files
    )
    return _PREFIX + hashlib.sha256("\n".join(listing).encode("utf-8")).hexdigest()


def check(rt: Any, lock: Lock) -> list[Drift]:
    """Every entry of a lock this tree no longer matches, in the lock's order.

    Nothing is loaded to answer it: each entry names something on disk, so the
    check reads the tree the way a fresh process would find it rather than the
    way this process happens to have it.
    """
    from metta.library import roster  # noqa: PLC0415  -- a satellite, deferred like the rest

    drifts: list[Drift] = []
    here = _engine_table(rt)
    for key, expected in lock.engine.items():
        actual = here.get(key)
        if actual != expected:
            drifts.append(Drift("engine", key, expected, actual))
    known = roster(rt.metta_path)
    for library in lock.libraries:
        files = known.get(library.name)
        actual = None if files is None else _library_digest(rt, files)
        if actual != library.digest:
            drifts.append(Drift("library", library.name, library.digest, actual))
    for source in lock.sources:
        path = _resolve(source.path, lock.base)
        actual = (
            _PREFIX + str(rt.apply_must("metta_py_source_digest", str(path)))
            if path.is_file()
            else None
        )
        if actual != source.digest:
            drifts.append(Drift("source", source.path, source.digest, actual))
    pinned = {str(url): str(commit) for url, commit in rt.apply_must("metta_py_git_pins")}
    for pin in lock.pins:
        actual = pinned.get(pin.url)
        if actual != pin.commit:
            drifts.append(Drift("pin", pin.url, pin.commit, actual))
    return drifts


def require(rt: Any, lock: Lock, source: str | os.PathLike[str] | None = None) -> None:
    """Refuse unless the tree matches the lock, naming every entry that differs.

    This is `metta run --locked`'s gate and it runs BEFORE the program does,
    which is uv's own rule for `--locked`: a lock that no longer describes the
    project stops the command rather than being quietly brought up to date
    [source: https://docs.astral.sh/uv/reference/cli/#uv-run--locked].
    """
    drifts = check(rt, lock)
    if drifts:
        raise LockDrift(drifts, source=source)

# Resolve annotations after definitions so peer imports can finish.
import collections.abc as _collections_abc  # noqa: E402 -- deferred annotation bindings
