"""Purpose: a `.metta` file imported as a Python module.

`metta.importing.install()` puts a `sys.meta_path` finder in place; after it,
`import rules` finds `rules.metta` on the search path, loads it into a space
with the engine's own `import!`, and answers a module whose attributes are
that file's heads. `importlib.reload` is the digest reload under Python's
word. Every test here drives the public surface, writes real files, and
leaves `sys.meta_path`, `sys.modules` and `sys.path` exactly as it found
them, because all three are process-wide and the suite shuffles its order.

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import gzip
import importlib
import importlib.util
import sys
import types
import uuid
from pathlib import Path

import pytest

import metta as metta_module
from metta import __main__ as command_line
from metta import importing
from metta.errors import MettaError


def fresh(stem):
    """A module name no other test in the session shares.

    `sys.modules`, the engine's per-source load records and the process's own
    head registry are all process-wide, so two tests sharing a name would be
    one test.
    """
    return f"{stem}_{uuid.uuid4().hex[:12]}"


@pytest.fixture()
def space():
    """A context of its own per test, closed on every exit path."""
    with metta_module.MeTTa() as context:
        yield context


def test_a_metta_file_imports_as_a_module_of_its_own_heads(space, tmp_path):
    """The module contract, whole: what a file becomes and what it does not.

    The file declares four things and the module carries three of them. The
    fourth, `(: promised ...)` with no equation, is a promise the space cannot
    answer, so it is not an attribute and asking for it gets the namespace's
    refusal rather than a name that raises when called.
    """
    name = fresh("rules")
    source = tmp_path / f"{name}.metta"
    source.write_text(
        "; The rules this test writes.\n"
        "; A second line of them.\n"
        "\n"
        "(: answer (-> Number))\n"
        "(= (answer) 1)\n"
        "(= (double-it $x) (* 2 $x))\n"
        "(: promised (-> Number))\n",
        encoding="utf-8",
    )

    with importing.install(space, path=tmp_path) as finder:
        module = importlib.import_module(name)

        assert module.__name__ == name
        assert module.__file__ == str(source)
        assert module.__spec__.origin == str(source)
        assert module.__all__ == ["answer", "double_it"]
        assert module.__doc__ == "The rules this test writes.\nA second line of them."
        assert module.__metta_space__.name == space.self.name
        assert not hasattr(module, "__path__"), "a .metta file is a module, never a package"
        assert [entry for entry in dir(module) if not entry.startswith("_")] == [
            "answer",
            "double_it",
        ]

        # The attributes are heads, called the way any engine function is
        # called, and Python's snake_case reaches MeTTa's hyphens.
        assert space.eval(module.answer()) == [metta_module.ground(1)]
        assert space.eval(module.double_it(21)) == [metta_module.ground(42)]
        assert module.double_it.__name__ == "double-it"

        with pytest.raises(AttributeError, match="has no 'promised'"):
            module.promised  # noqa: B018  -- reading the attribute IS the refusal under test

        assert list(finder.modules) == [name]
        assert importing.installed() == (finder,)

    assert importing.installed() == ()
    assert name not in sys.modules


def test_a_module_attribute_and_the_namespace_build_one_term(space, tmp_path):
    """`rules.answer` and `m.fn.answer` are the same function, so a call
    through either builds the same term and the space answers it once.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("same")
    (tmp_path / f"{name}.metta").write_text("(= (twice $x) (* 2 $x))\n", encoding="utf-8")

    with importing.install(space, path=tmp_path):
        module = importlib.import_module(name)
        assert module.twice(4) == space.self.fn.twice(4)
        assert space.eval(module.twice(4)) == space.eval(space.self.fn.twice(4))


def test_the_import_statement_reaches_a_metta_file(space, tmp_path):
    """The statement form itself, which is the whole point of a finder.

    `importlib.import_module` is the same machinery with the name as data;
    this is the spelling a program writes, and nothing else in the suite
    proves the compiler's `IMPORT_NAME` reaches the hook.
    """
    (tmp_path / "lib_list.metta").write_text(
        "(= (list-tail $xs) (cdr-atom $xs))\n", encoding="utf-8"
    )
    with importing.install(space, path=tmp_path):
        import lib_list  # the statement under test, and its own name is the assertion

        assert lib_list.__file__ == str(tmp_path / "lib_list.metta")
        assert space.eval(lib_list.list_tail(metta_module.Expression([1, 2]))) == [
            metta_module.Expression([2])
        ]
    assert "lib_list" not in sys.modules


def test_reload_is_the_digest_reload_under_pythons_word(space, tmp_path):
    """Edit the file, reload the module: the same module object answers the
    new bodies, a head the edit removed leaves both the module and the space,
    and a head it added arrives. This is `import!`'s own lifecycle, which
    withdraws what the file put in every space holding it and replaces it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("edited")
    source = tmp_path / f"{name}.metta"
    source.write_text("(= (answer) 1)\n(= (withdrawn) 7)\n", encoding="utf-8")

    with importing.install(space, path=tmp_path):
        module = importlib.import_module(name)
        assert module.__all__ == ["answer", "withdrawn"]
        assert space.eval(module.answer()) == [metta_module.ground(1)]

        source.write_text("(= (answer) 2)\n(= (arrived $x) (+ $x 1))\n", encoding="utf-8")
        reloaded = importlib.reload(module)

        assert reloaded is module, "reload answers the module it was given"
        assert module.__all__ == ["answer", "arrived"]
        assert space.eval(module.answer()) == [metta_module.ground(2)]
        assert space.eval(module.arrived(4)) == [metta_module.ground(5)]
        assert "withdrawn" not in vars(module)
        # The space forgot it too, which is why the module can: the withdrawal
        # un-compiles the equation and forgets its name.
        assert not space.self.is_function_here("withdrawn")
        with pytest.raises(AttributeError, match="has no 'withdrawn'"):
            module.withdrawn  # noqa: B018  -- reading the attribute IS the refusal under test


def test_a_module_reads_the_space_and_not_a_snapshot(space, tmp_path):
    """A head defined after the import is reachable through the module.

    `__all__` stays the file's own heads, because that is what `import *`
    should take; attribute lookup falls through to the space's own namespace,
    so the module is a view of a live space rather than a copy of one moment.
    """
    name = fresh("live")
    (tmp_path / f"{name}.metta").write_text("(= (first) 1)\n", encoding="utf-8")

    with importing.install(space, path=tmp_path):
        module = importlib.import_module(name)
        later = fresh("later").replace("_", "-")
        space.run(f"(= ({later}) 9)")
        assert module.__all__ == ["first"]
        assert space.eval(getattr(module, later)()) == [metta_module.ground(9)]


def test_a_python_module_of_the_same_name_wins(space, tmp_path, monkeypatch):
    """The finder is appended, never prepended, so Python's own finders answer
    first and a name with both a `.py` and a `.metta` on one search path is
    Python's. The deferral is by ORDER: the finder still resolves the file.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("both")
    (tmp_path / f"{name}.py").write_text("VALUE = 'python'\n", encoding="utf-8")
    (tmp_path / f"{name}.metta").write_text("(= (value) metta)\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    with importing.install(space) as finder:
        try:
            module = importlib.import_module(name)
            assert module.VALUE == "python"
            assert module.__file__.endswith(".py")
        finally:
            sys.modules.pop(name, None)
        assert finder.find_spec(name) is not None, "the file is found, and deferred to Python"
        assert finder.find_spec(name).origin == str(tmp_path / f"{name}.metta")


def test_a_file_that_cannot_load_raises_import_error(space, tmp_path):
    """A load that fails is an import that fails, with the engine's own error
    as the cause, and it leaves no half-made module in `sys.modules`.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("broken")
    (tmp_path / f"{name}.metta").write_text("(= (unclosed)\n", encoding="utf-8")

    with importing.install(space, path=tmp_path):
        with pytest.raises(ImportError, match="could not load") as raised:
            importlib.import_module(name)
        assert isinstance(raised.value.__cause__, MettaError)
        assert raised.value.name == name
        assert raised.value.path == str(tmp_path / f"{name}.metta")
        assert name not in sys.modules


def test_reload_of_a_module_the_hook_did_not_load_is_pythons_own_refusal(space, tmp_path):
    """There is no `reload` verb here. `importlib.reload` is the only door, so
    a module this hook never loaded gets Python's own answer and nothing of
    ours: the machinery decides, and the finder is not consulted at all.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    with importing.install(space, path=tmp_path):
        with pytest.raises(ImportError, match=r"not in sys\.modules"):
            importlib.reload(types.ModuleType(fresh("handmade")))
        with pytest.raises(TypeError, match="must be a module"):
            importlib.reload(object())


def test_a_package_declared_library_imports_by_its_declared_name(space, tmp_path, monkeypatch):
    """A pip-installed package advertises a MeTTa library under the
    `metta.libraries` entry-point group, the way a pytest plugin advertises
    itself, and the declared NAME becomes importable. The target answers the
    directory the sources live in, which is the group's existing contract, and
    the file is found there under the engine's own library layout.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("shipped")
    package = f"wheel_{uuid.uuid4().hex[:12]}"
    site = tmp_path / "site-packages"
    (site / package).mkdir(parents=True)
    (site / package / "__init__.py").write_text(
        "from pathlib import Path\n\n\ndef sources():\n    return Path(__file__).parent / 'metta'\n",
        encoding="utf-8",
    )
    metadata = site / f"{package}-0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {package}\nVersion: 0\n", encoding="utf-8"
    )
    (metadata / "entry_points.txt").write_text(
        f"[metta.libraries]\n{name} = {package}:sources\n", encoding="utf-8"
    )
    shipped = site / package / "metta" / name
    shipped.mkdir(parents=True)
    (shipped / f"{name}.metta").write_text(
        f'(@doc {name} (@desc "rules a package ships"))\n(= (shipped) 42)\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(site))
    importlib.invalidate_caches()

    with importing.install(space, path=[]):
        try:
            module = importlib.import_module(name)
            assert module.__file__ == str(shipped / f"{name}.metta")
            assert module.__doc__ == f"{name}: rules a package ships"
            assert space.eval(module.shipped()) == [metta_module.ground(42)]
        finally:
            for loaded in [key for key in sys.modules if key.startswith(package)]:
                del sys.modules[loaded]


def test_a_declared_library_is_consulted_after_the_search_path(space, tmp_path, monkeypatch):
    """Order, stated as a test: a file on the path wins over a package's
    advertisement of the same name, and the advertisement is read only for a
    name that matches, so an unrelated import loads nobody's entry point.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("contested")
    site = tmp_path / "site-packages"
    metadata = site / "claimant-0.dist-info"
    metadata.mkdir(parents=True)
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: claimant\nVersion: 0\n", encoding="utf-8"
    )
    # A target that would raise if it were ever loaded: nothing may consult it
    # while the search path answers, and nothing may consult it for a name it
    # does not claim.
    (metadata / "entry_points.txt").write_text(
        f"[metta.libraries]\n{name} = no_such_package_at_all:sources\n", encoding="utf-8"
    )
    beside = tmp_path / "beside"
    beside.mkdir()
    (beside / f"{name}.metta").write_text("(= (from-the-path) 1)\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(site))
    importlib.invalidate_caches()

    with importing.install(space, path=beside):
        module = importlib.import_module(name)
        assert module.__file__ == str(beside / f"{name}.metta")
        assert space.eval(module.from_the_path()) == [metta_module.ground(1)]
        # And a name nobody advertises simply misses, without loading anything.
        assert importlib.util.find_spec(fresh("unclaimed")) is None


def test_a_compressed_source_and_a_library_directory_are_both_found(space, tmp_path):
    """The finder recognises what the engine loads: `.metta`, the `.metta.gz`
    the CLI and `import!` already read under the same name, and the library
    layout where a directory named for the library holds its surface.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    zipped = fresh("zipped")
    with gzip.open(tmp_path / f"{zipped}.metta.gz", "wt", encoding="utf-8") as handle:
        handle.write("(= (compressed) 1)\n")
    nested = fresh("nested")
    (tmp_path / nested).mkdir()
    (tmp_path / nested / f"{nested}.metta").write_text("(= (inside) 2)\n", encoding="utf-8")

    with importing.install(space, path=tmp_path):
        compressed = importlib.import_module(zipped)
        assert compressed.__file__.endswith(".metta.gz")
        assert space.eval(compressed.compressed()) == [metta_module.ground(1)]

        directory = importlib.import_module(nested)
        assert directory.__file__ == str(tmp_path / nested / f"{nested}.metta")
        assert space.eval(directory.inside()) == [metta_module.ground(2)]


def test_a_submodule_comes_from_its_python_packages_own_directory(space, tmp_path, monkeypatch):
    """A `.metta` file has no `__path__`, so it is never a package; a DOTTED
    name reaches one only when a Python package ships the file, and then the
    search is that package's `__path__` and never the wider path.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    package = f"carrier_{uuid.uuid4().hex[:12]}"
    (tmp_path / package).mkdir()
    (tmp_path / package / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / package / "rules.metta").write_text("(= (inner) 3)\n", encoding="utf-8")
    # The same name outside the package, which the submodule import must NOT see.
    (tmp_path / "rules.metta").write_text("(= (outer) 4)\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    with importing.install(space):
        try:
            module = importlib.import_module(f"{package}.rules")
            assert module.__file__ == str(tmp_path / package / "rules.metta")
            assert space.eval(module.inner()) == [metta_module.ground(3)]
        finally:
            for loaded in [key for key in sys.modules if key.startswith(package)]:
                del sys.modules[loaded]


def test_a_head_python_cannot_spell_keeps_its_exact_name(space, tmp_path):
    """`__all__` holds identifiers, because that is what `import *` binds. A
    head Python cannot spell stays reachable by its exact name, through the
    same `getattr` door every other attribute uses.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("spelling")
    (tmp_path / f"{name}.metta").write_text(
        "(= (prime? $x) True)\n(= (plain) 1)\n", encoding="utf-8"
    )

    with importing.install(space, path=tmp_path):
        module = importlib.import_module(name)
        assert module.__all__ == ["plain"]
        assert getattr(module, "prime?").__name__ == "prime?"
        assert space.eval(getattr(module, "prime?")(2)) == [metta_module.TRUE]


def test_a_finder_is_a_value_installed_and_uninstalled(space, tmp_path):
    """Two installs are two finders, asked in order, each removable on its
    own; `installed()` reads `sys.meta_path` rather than a registry beside it,
    and `uninstall()` takes this finder's modules with it so a later import
    cannot answer from a hook that is gone.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("owned")
    (tmp_path / f"{name}.metta").write_text("(= (owned) 1)\n", encoding="utf-8")

    first = importing.install(space, path=tmp_path)
    second = importing.install(space, path=tmp_path)
    try:
        assert importing.installed() == (first, second)
        assert sys.meta_path[-2:] == [first, second]
        module = importlib.import_module(name)
        assert list(first.modules) == [name], "the first finder asked answers"
        assert second.modules == {}

        second.uninstall()
        assert importing.installed() == (first,)
        assert name in sys.modules, "the module belongs to the finder that loaded it"

        first.uninstall()
        assert importing.installed() == ()
        assert name not in sys.modules
        # The module a caller already holds goes on working: its heads read a
        # space, and the space is still there.
        assert space.eval(module.owned()) == [metta_module.ground(1)]
    finally:
        first.uninstall()
        second.uninstall()


def test_the_given_directories_are_searched_before_sys_path(space, tmp_path, monkeypatch):
    """`path` is what `python script.py` does with the script's directory: it
    goes in front, and `sys.path` itself is untouched and still read live.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("ordered")
    front = tmp_path / "front"
    back = tmp_path / "back"
    front.mkdir()
    back.mkdir()
    (front / f"{name}.metta").write_text("(= (which) front)\n", encoding="utf-8")
    (back / f"{name}.metta").write_text("(= (which) back)\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(back))
    importlib.invalidate_caches()

    with importing.install(space, path=front):
        module = importlib.import_module(name)
        assert module.__file__ == str(front / f"{name}.metta")
        assert space.eval(module.which()) == [metta_module.S.front]
    assert str(back) in sys.path, "the finder searches sys.path without changing it"


def test_a_stub_beside_the_file_is_reached_from_the_modules_origin(space, tmp_path):
    """`__spec__.origin` is the file, so a checker finds `rules.pyi` beside it
    the way it finds one beside a `.py`, and `metta stubs` is what writes it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("typed")
    source = tmp_path / f"{name}.metta"
    source.write_text(
        "(: area (-> Number Number))\n(= (area $r) (* $r $r))\n", encoding="utf-8"
    )
    stub = source.with_suffix(".pyi")
    assert command_line.main(["stubs", str(source), "-o", str(stub)]) == 0

    with importing.install(space, path=tmp_path):
        module = importlib.import_module(name)
        assert Path(module.__spec__.origin).with_suffix(".pyi") == stub
        assert "def area(x1: int | float, /) -> int | float:" in stub.read_text(encoding="utf-8")


def test_a_file_that_declares_nothing_still_imports(space, tmp_path):
    """A file of plain data declares no head, so the module carries none and
    says so, rather than failing or inventing one.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    name = fresh("data")
    (tmp_path / f"{name}.metta").write_text("(fact one)\n(fact two)\n", encoding="utf-8")

    with importing.install(space, path=tmp_path):
        module = importlib.import_module(name)
        assert module.__all__ == []
        assert module.__doc__ is None
        assert len(space.self[metta_module.S.fact(metta_module.V.x)]) == 2
