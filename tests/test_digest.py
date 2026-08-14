"""Purpose: content digests. digest() answers one sha256 over the space's
canonicalized atoms: insertion order and stored-variable names cannot
change it, duplicates and any real content change do, the same content
answers the same digest in another process, and live host objects refuse
exactly like save.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import subprocess
import sys

import pytest

from petta import S, val


def test_digest_ignores_order_and_variable_names(metta):
    with metta.fresh_space() as a, metta.fresh_space() as b:
        a.add(S.dg(1), S.dg(2))
        a.run("(= (dg-f $x) (+ $x 1))")
        b.run("(= (dg-f $renamed) (+ $renamed 1))")
        b.add(S.dg(2), S.dg(1))
        assert a.digest() == b.digest()
        assert len(a.digest()) == 64
        b.add(S.dg(3))
        assert a.digest() != b.digest()


def test_digest_counts_duplicates(metta):
    with metta.fresh_space() as a, metta.fresh_space() as b:
        a.add(S.dup(S.x))
        b.add(S.dup(S.x))
        b.add(S.dup(S.x))
        assert a.digest() != b.digest()


def test_digest_matches_across_processes(metta):
    with metta.fresh_space() as here:
        here.run("(dgx alpha) (dgx beta) (= (dgx-f $v) (* $v 2))")
        program = (
            "from petta import MeTTa\n"
            "m = MeTTa().fresh_space()\n"
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


def test_digest_refuses_live_objects(metta):
    with metta.fresh_space() as m:
        m.add(S.holds(val(object())))
        with pytest.raises(ValueError, match="cross-process identity"):
            m.digest()


@pytest.mark.parametrize("name", ['bad"quote', "bad(paren", "bad)paren", "bad name"])
def test_digest_refuses_symbols_without_round_trip_text(metta, name):
    with metta.fresh_space() as m:
        m.add(S.container(S[name]))
        with pytest.raises(ValueError, match=r"symbol.*round-trip text spelling"):
            m.digest()
