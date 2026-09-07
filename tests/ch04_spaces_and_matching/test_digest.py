"""Purpose: content digests. digest() answers one sha256 over the space's
canonicalized atoms: insertion order and stored-variable names cannot
change it, duplicates and any real content change do, the same content
answers the same digest in another process, and live host objects refuse
exactly like save.
Guarantees:
  - higher-order specializations mint symbols that survive text save, reload,
    and digest, including all eight formerly unwritable names in
    examples/ch05-equations-and-evaluation/05-02-changing-the-equations/04-specialize.metta [tested:
    test_a_specialized_program_saves_and_digests; commit=5d93a44cf4820717163bbf8dfaf667ae14e5e4ee]
  - the digest is pinned to the canonicalization it names, not merely to
    itself: tests/fixtures/space_digest_vector.json carries one program, the
    lines the engine writes for its atoms and their sha256, and this file
    rebuilds both from the stored atoms
    [tested: test_the_digest_is_sha256_over_the_lines_the_engine_writes;
    commit=8d67307403c1e41ccf058bd3c8d4c079dd7cf7d5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from metta import S, ground
from metta.atoms import Atom, Expression, Grounded, Symbol, Variable, _decode

#: The shared test vector every seat that answers digest() runs. Node's own
#: suite reads the same file, so the two seats cannot drift apart quietly.
VECTOR = json.loads(
    (Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "space_digest_vector.json").read_text(
        encoding="utf-8"
    )
)

#: The characters ISO gives their own token class, so a run of them is an atom
#: a Prolog writer leaves unquoted: `=`, `*`, `->` and their kin
#: [source: SWI-Prolog manual section 5, "Syntax Notes", symbol char set].
_SYMBOL_CHARACTERS = set("+-*/\\^<>=~:.?@#&$")

#: The atoms that are unquoted despite being neither of the two ordinary
#: shapes, which is SWI's solo-character set plus the empty list.
_SOLO_ATOMS = frozenset({"[]", "!", ";", "{}"})


def test_digest_ignores_order_and_variable_names(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as a, metta._new_space() as b:
        a.add(S.dg(1), S.dg(2))
        a.run("(= (dg-f $x) (+ $x 1))")
        b.run("(= (dg-f $renamed) (+ $renamed 1))")
        b.add(S.dg(2), S.dg(1))
        assert a.digest() == b.digest()
        assert len(a.digest()) == 64
        b.add(S.dg(3))
        assert a.digest() != b.digest()


def test_digest_counts_duplicates(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as a, metta._new_space() as b:
        a.add(S.dup(S.x))
        b.add(S.dup(S.x))
        b.add(S.dup(S.x))
        assert a.digest() != b.digest()


def test_digest_matches_across_processes(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as here:
        here.run("(dgx alpha) (dgx beta) (= (dgx-f $v) (* $v 2))")
        program = (
            "from metta import MeTTa\n"
            "m = MeTTa().space()\n"
            'm.run("(= (dgx-f $other) (* $other 2)) (dgx beta) (dgx alpha)")\n'
            "print(m.digest())\n"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(sys.path)
        done = subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        assert done.returncode == 0, done.stderr
        assert done.stdout.strip() == here.digest()


def test_digest_refuses_live_objects(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as m:
        m.add(S.holds(ground(object())))
        with pytest.raises(ValueError, match="cross-process identity"):
            m.digest()


@pytest.mark.parametrize(
    "name",
    [
        'bad"quote',
        "bad(paren",
        "bad)paren",
        "bad name",
        # Each of these reads back as something else, and each was accepted:
        # a variable, a comment, a number, and a boolean.
        "$notvar",
        "semi;colon",
        "42",
        "True",
    ],
)
def test_digest_refuses_symbols_without_round_trip_text(metta, name):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as m:
        m.add(S.container(S[name]))
        with pytest.raises(ValueError, match=r"cannot write symbol"):
            m.digest()


@pytest.mark.parametrize("number", [float("inf"), float("-inf"), float("nan")])
@pytest.mark.parametrize("operation", ["digest", "save-metta", "save-fast"])
def test_refuses_a_number_with_no_round_trip_text(metta, tmp_path, number, operation):
    """A value can lack a text form without being a name.

    A non-finite float prints as ``inf``, ``-inf`` or ``NaN`` and a rational
    as ``1r3``, and the MeTTa reader has a literal for none of the four, so
    each comes back a SYMBOL of that spelling. MeTTa arithmetic ANSWERS one
    now, ``(+ 1e400 1)`` saturating the way the reader's own literals do,
    and ``(py-atom "float('inf')")`` answers one as this constructor does,
    which is exactly why the seam must keep refusing to store them. Before
    it answered for numbers, a text save of this space wrote ``(holds
    inf)`` and loading it back gave ``Symbol('inf')``, with nothing reported
    [measured 2026-08-19].
    """
    with metta._new_space() as m:
        m.add(S.holds(ground(number)))
        with pytest.raises(ValueError, match=r"reads back as a symbol of that spelling"):
            if operation == "digest":
                m.digest()
            else:
                m.save(tmp_path / "n.metta", format=operation.split("-")[1])


@pytest.mark.parametrize("number", [0, -3, 2.5, -0.0, 1e10, 1.5e-10, 2**80])
def test_save_keeps_every_number_it_accepts(metta, tmp_path, number):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    path = tmp_path / "one.metta"
    with metta._new_space() as writer:
        writer.add(S.container(ground(number)))
        writer.save(path)
    with metta._new_space() as reader:
        reader.load(path)
        assert reader.atoms() == [S.container(ground(number))]


@pytest.mark.parametrize("name", ["plain", "a-b", "<=", "#+", "0x1f", ".5", "3x", "-abc"])
def test_save_keeps_every_symbol_it_accepts(metta, tmp_path, name):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The refusal has to guard the writer that actually runs: a saved file is
    # read back by the top-level form scanner, which tracks a string state
    # sread alone never sees.
    path = tmp_path / "one.metta"
    with metta._new_space() as writer:
        writer.add(S.container(S[name]))
        writer.save(path)
    with metta._new_space() as reader:
        reader.load(path)
        assert reader.atoms() == [S.container(S[name])]


def test_a_specialized_program_saves_and_digests(metta, repo_root, tmp_path):
    """The name minter, writer, parser, and digest agree on specializations."""
    exact = tmp_path / "map-flat.metta"
    with metta._new_space() as writer:
        writer.run("(= (map-flat $f $xs) (collapse ($f (superpose $xs))))")
        assert str(writer.run("!(map-flat (+ 1) (1 2 3))")) == "[[(2 3 4)]]"
        before = writer.digest()
        writer.save(exact)
    with metta._new_space() as reader:
        reader.load(exact)
        assert reader.digest() == before

    measured = tmp_path / "specialize.metta"
    with metta._new_space() as writer:
        writer.load(repo_root / "examples" / "ch05-equations-and-evaluation" / "05-02-changing-the-equations" / "04-specialize.metta")
        assert writer.run("!(trickyspec (+ 2))") == [[3]]
        names = {
            str(atom.children[1].children[0])
            for atom in writer.atoms()
            if str(atom).startswith("(= (") and "_Spec_" in str(atom)
        }
        assert len(names) == 11
        assert sum("_Spec_k" in name for name in names) == 8
        before = writer.digest()
        writer.save(measured)
    with metta._new_space() as reader:
        reader.load(measured)
        assert reader.digest() == before
        assert str(reader.run("!(map-flat (+ 1) (1 2 3))")) == "[[(2 3 4)]]"
        assert reader.run("!(trickyspec (+ 1))") == [[3]]
        loaded_names = {
            str(atom.children[1].children[0])
            for atom in reader.atoms()
            if str(atom).startswith("(= (") and "_Spec_" in str(atom)
        }
        assert names == loaded_names


def _prolog_atom(name: str) -> str:
    """One symbol as `write_term/2` with `quoted(true)` writes it."""
    if re.fullmatch(r"[a-z][a-zA-Z0-9_]*", name) or name in _SOLO_ATOMS:
        return name
    if name and set(name) <= _SYMBOL_CHARACTERS:
        return name
    return "'" + name.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _prolog_number(value: float) -> str:
    """One number as the writer writes it, refusing a shape this does not model.

    Python and SWI agree on every literal this vector uses and disagree on
    exponents (`1e+30` against `1.0e30`), so the mismatch is a refusal rather
    than a line that silently differs from the engine's.
    """
    written = repr(value)
    if "e" in written or "E" in written or written in ("inf", "-inf", "nan"):
        msg = f"this rebuild does not model the written form of {value!r}"
        raise AssertionError(msg)
    return written


def _canonical_line(atom: Atom, names: dict[str, str]) -> str:
    """One stored atom as engine/filereader/source_lifecycle.pl writes it.

    metta_host_digest_line/2 copies the atom, numbers its variables from zero
    and writes it quoted, and an expression is a Prolog list here, so
    `(user 1 ada)` is `[user,1,ada]`. This is the SECOND implementation of
    that rule: the point of the test below is that two of them agree, so a
    shape it does not model refuses instead of guessing.
    """
    if isinstance(atom, Expression):
        return "[" + ",".join(_canonical_line(child, names) for child in atom.children) + "]"
    if isinstance(atom, Variable):
        spelled = str(atom)
        if spelled not in names:
            # numbervars/3 numbers by term order, which is first appearance,
            # and '$VAR'(N) prints as the Nth letter with N//26 after it.
            index = len(names)
            names[spelled] = chr(ord("A") + index % 26) + ("" if index < 26 else str(index // 26))
        return names[spelled]
    if isinstance(atom, Grounded):
        value = _decode(atom)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return _prolog_number(value)
        if isinstance(value, str):
            return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        msg = f"this rebuild does not model a grounded {type(value).__name__}"
        raise AssertionError(msg)
    if isinstance(atom, Symbol):
        return _prolog_atom(str(atom))
    msg = f"this rebuild does not model {type(atom).__name__}"
    raise AssertionError(msg)


def test_the_digest_is_sha256_over_the_lines_the_engine_writes(metta):
    """Pin the digest to its canonicalization, both doors rebuilt here.

    digest() answering the same hex for the same atoms is what the tests
    above check; this one checks WHICH hex, by writing the lines the engine
    writes and hashing them the way it hashes them. A change to the
    canonicalization, the sort, the separator or the encoding moves the
    number and this goes red with the vector beside it.
    """
    with metta._new_space() as m:
        m.run(VECTOR["program"])
        rebuilt = sorted(_canonical_line(atom, {}) for atom in m.atoms())
        assert rebuilt == VECTOR["lines"]
        joined = "\n".join(VECTOR["lines"]).encode("utf-8")
        assert hashlib.sha256(joined).hexdigest() == VECTOR["digest"]
        assert m.digest() == VECTOR["digest"]


def test_the_digest_rebuild_refuses_a_shape_it_does_not_model():
    """The second implementation cannot pass by guessing.

    A rebuild that answered something for every atom would agree with the
    engine by construction on the shapes it got wrong, so the shapes it does
    not model are refusals; this is the assertion that keeps that true.
    """
    with pytest.raises(AssertionError, match="does not model"):
        _canonical_line(Grounded(object()), {})
    with pytest.raises(AssertionError, match="does not model"):
        _canonical_line(Grounded(1e30), {})
