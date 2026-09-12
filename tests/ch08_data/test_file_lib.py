"""Purpose: compare the File library's paths, traversal and globbing with Python.

The four path functions translate CPython's `posixpath`, and the traversal and
glob answer what `os.walk` and `glob.glob` answer over the same tree, so the
oracle is the standard library rather than a table of expected strings. The
generated cases are Hypothesis-built path shapes; the tree cases are built in a
temporary directory and compared entry by entry.

Assumes: `lib_file` loads, which needs no native build.
Guarantees:
  - path-normalize, path-absolute, path-relative and path-resolve answer what
    posixpath answers over generated components, including `..` past the root,
    repeated separators, a doubled leading slash and symbolic links
    [tested: test_normalize_agrees_with_posixpath,
    test_absolute_agrees_with_posixpath, test_relative_agrees_with_posixpath,
    test_resolve_agrees_with_posixpath; commit=WORKTREE]
  - dir-glob answers what glob and pathlib answer for the same pattern under
    each one's link and dotfile policy, and dir-walk the paths os.walk yields,
    over a tree holding hidden names, links and a dangling link
    [tested: test_glob_follows_links_like_globs_own_recursion,
    test_glob_with_hidden_names_matches_pathlib,
    test_a_trailing_recursive_component_answers_directories,
    test_walk_agrees_with_os_walk, test_walk_following_links_visits_the_target_once;
    commit=WORKTREE]
  - every byte value survives a whole-file round trip and a handle round trip
    [tested: test_bytes_round_trip_through_python; commit=WORKTREE]
Owns resources: each test works inside a pytest `tmp_path` and closes every
handle it opens.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

# The ORACLES are os.path, os.walk and glob themselves: the library translates
# posixpath and declares its glob against the shell's grammar, so comparing it
# with pathlib's own rewrite of those modules would compare it with a second
# implementation instead of the one it follows. Ruff's pathlib preferences are
# answered here rather than per line.
import glob as globbing
import os
import os.path as posix
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import G, MeTTa, S, lib

#: The components a generated path is built from: ordinary names, the two dot
#: forms and the empty string, which is how a doubled or trailing separator
#: appears after a join.
COMPONENTS = st.sampled_from(["a", "b", "c", "..", ".", "", "x.y", ".hidden"])

#: A generated relative or absolute path, its shape left to the components.
PATHS = st.builds(
    lambda parts, absolute: ("/" if absolute else "") + "/".join(parts),
    st.lists(COMPONENTS, min_size=0, max_size=6),
    st.booleans(),
)


@pytest.fixture(scope="module")
def engine():
    """One engine with the File library imported, for the whole module."""
    with MeTTa() as metta:
        metta += lib.file
        yield metta


def test_bytes_round_trip_through_python(engine, tmp_path):
    """Every byte value survives both byte doors, and Python reads them back."""
    path = G(str(tmp_path / "all.bin"))
    every = tuple(range(256))
    assert engine.fn["write-bytes!"](path, every) == [True]
    assert (tmp_path / "all.bin").read_bytes() == bytes(every)
    assert tuple(engine.fn["read-bytes!"](path).one()) == every

    handle = engine.fn["file-open!"](path, G("rb")).one()
    try:
        head = tuple(engine.fn["file-read-bytes!"](handle, 8).one())
        assert head == every[:8]
        assert tuple(engine.fn["file-read-bytes!"](handle).one()) == every[8:]
    finally:
        engine.fn["file-close!"](handle).one()

    (tmp_path / "written.bin").write_bytes(bytes(reversed(every)))
    assert tuple(engine.fn["read-bytes!"](G(str(tmp_path / "written.bin"))).one()) == tuple(
        reversed(every)
    )


@given(path=PATHS)
def test_normalize_agrees_with_posixpath(path):
    """path-normalize is posixpath.normpath over generated component shapes."""
    with MeTTa() as metta:
        metta += lib.file
        assert metta.fn.path_normalize(G(path)) == [G(posix.normpath(path))]


@given(path=PATHS, start=PATHS)
def test_relative_agrees_with_posixpath(path, start):
    """path-relative is posixpath.relpath, and refuses the empty path it refuses."""
    with MeTTa() as metta:
        metta += lib.file
        if path == "":
            with pytest.raises(Exception, match="path"):
                metta.fn.path_relative(G(path), G(start or ".")).one()
            return
        expected = posix.relpath(path, start or ".")
        assert metta.fn.path_relative(G(path), G(start or ".")) == [G(expected)]


@given(path=PATHS)
def test_absolute_agrees_with_posixpath(path):
    """path-absolute is posixpath.abspath, anchored at the working directory."""
    with MeTTa() as metta:
        metta += lib.file
        assert metta.fn.path_absolute(G(path)) == [G(posix.abspath(path))]  # noqa: PTH100 -- abspath is the oracle


def test_resolve_agrees_with_posixpath(engine, tmp_path):
    """path-resolve is non-strict posixpath.realpath, links and loops included."""
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "leaf.txt").write_text("leaf", encoding="utf-8")
    (tmp_path / "link").symlink_to("real")
    (tmp_path / "dangling").symlink_to("nowhere")
    (tmp_path / "loop-a").symlink_to("loop-b")
    (tmp_path / "loop-b").symlink_to("loop-a")
    (tmp_path / "absolute").symlink_to("/")
    for relative in ("link/leaf.txt", "link/../real/leaf.txt", "dangling/x", "loop-a/tail",
                     "absolute/dev", "real/../link/leaf.txt", "missing/../real", "."):
        candidate = str(tmp_path / relative)
        assert engine.fn.path_resolve(G(candidate)) == [G(posix.realpath(candidate, strict=False))]


def plant(root: Path) -> None:
    """A tree with hidden names, nesting, a link to a directory and a dangling one."""
    (root / "sub" / "deep").mkdir(parents=True)
    (root / ".dotdir").mkdir()
    for name in ("t.txt", ".hidden.txt", "sub/y.md", "sub/deep/x.txt", ".dotdir/inside.txt"):
        (root / name).write_text("", encoding="utf-8")
    (root / "lnk").symlink_to("sub")
    (root / "dangling").symlink_to("nowhere")


#: The patterns both oracles and the library all answer the same way: every
#: component is a name or a wildcard, or a `**` followed by one, so the only
#: policies in play are the link and dotfile rules each comparison fixes.
PATTERNS = ["*", "*.txt", "**/*.txt", "sub/*", "sub/**/*.txt", "**/*.md", "t.txt",
            "sub/deep/x.txt", "missing/*", "[ts]*", "?.txt", "**/deep"]


@pytest.mark.parametrize("pattern", PATTERNS)
def test_glob_follows_links_like_globs_own_recursion(engine, tmp_path, pattern):
    """With links followed, dir-glob answers glob.glob's paths for the pattern.

    `glob.glob` recurses through a symbolic link under `**` and skips names
    beginning with a dot, which is the shell rule the library's default keeps;
    so the comparison asks the library to follow links and leaves hidden names
    out on both sides.
    """
    plant(tmp_path)
    answered = sorted(path.value for path in engine.fn.dir_glob(
        G(str(tmp_path)), G(pattern), ((S.follow_links, True),)
    ))
    expected = sorted(
        str(tmp_path / posix.normpath(found))
        for found in globbing.glob(pattern, root_dir=tmp_path, recursive=True)  # noqa: PTH207 -- glob is the oracle
    )
    assert answered == expected


@pytest.mark.parametrize("pattern", PATTERNS)
def test_glob_with_hidden_names_matches_pathlib(engine, tmp_path, pattern):
    """With hidden names included, dir-glob answers what pathlib answers.

    `Path.glob` has no dotfile rule and does not recurse through a link, so
    this comparison asks the library for hidden names and leaves its default
    link policy in place.
    """
    plant(tmp_path)
    answered = sorted(path.value for path in engine.fn.dir_glob(
        G(str(tmp_path)), G(pattern), ((S.hidden, True),)
    ))
    expected = sorted(str(found) for found in tmp_path.glob(pattern))
    assert answered == expected


def test_a_trailing_recursive_component_answers_directories(engine, tmp_path):
    """`**` alone answers the directories below the root, and the root itself.

    That is `Path.glob("**")` restricted to directories: the library's `**`
    matches directory LEVELS, so a pattern ending in one names places rather
    than entries.
    """
    plant(tmp_path)
    answered = sorted(path.value for path in engine.fn.dir_glob(
        G(str(tmp_path)), G("**"), ((S.hidden, True),)
    ))
    expected = sorted(
        str(found) for found in tmp_path.glob("**") if found.is_dir() and not found.is_symlink()
    )
    assert answered == expected


def test_walk_agrees_with_os_walk(engine, tmp_path):
    """dir-walk answers the paths os.walk yields, links reported not followed."""
    plant(tmp_path)
    expected = sorted(
        posix.join(parent, name)  # noqa: PTH118 -- os.walk answers text, and join keeps it text
        for parent, directories, files in os.walk(tmp_path, followlinks=False)
        for name in (*directories, *files)
    )
    # os.walk does not yield a dangling or file link among its directories, so
    # the two link entries are added the way the library reports them.
    expected = sorted({*expected, str(tmp_path / "lnk"), str(tmp_path / "dangling")})
    answered = sorted(path.value for path in engine.fn.dir_walk(G(str(tmp_path))))
    assert answered == expected


def test_walk_following_links_visits_the_target_once(engine, tmp_path):
    """Following links enters the target and refuses to re-enter an ancestor."""
    plant(tmp_path)
    (tmp_path / "sub" / "up").symlink_to("..")
    answered = [path.value for path in engine.fn.dir_walk(
        G(str(tmp_path)), ((S.follow_links, True),)
    )]
    assert len(answered) == len(set(answered))
    assert str(tmp_path / "lnk" / "y.md") in answered
    assert str(tmp_path / "sub" / "up") in answered
    assert not any(entry.count("/up/") for entry in answered)


def test_a_scope_closes_its_handle_even_when_the_caller_stops(engine, tmp_path):
    """One answer taken from a scope still closes the handle."""
    path = G(str(tmp_path / "data.txt"))
    (tmp_path / "data.txt").write_text("abcdef", encoding="utf-8")
    answers = engine.fn["with-file"](path, G("r"), S["file-get-size!"])
    handle_count = len(list(answers))
    assert handle_count == 1
    # Every handle the scope minted is gone, so reading through the last one
    # raises rather than answering.
    with pytest.raises(Exception, match=r"file_handle|file-handle"):
        engine.fn["file-read-to-string!"](3).one()
