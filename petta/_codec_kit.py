"""Purpose: run the shared golden corpus against one implementation of the
tagged wire codec, so "speaks the codec" is a checkable claim rather than a
compatibility rumor.

This is the codec's half of what `check_space_provider` is for a space
provider: it runs in process, calls the driver's four operations directly,
and asks whether that codec keeps the grammar's promises. The corpus itself
is language-neutral JSON and the grammar is CODEC.md, so a binding in a
language with no Python at all implements the same four operations against
the same file; this module is how the two codecs that ship here run it.

Assumes:
  - a driver refuses by raising, whatever its host's exception type
    [assumed 2026-08-20]
  - tests/codec/corpus.json ships beside the engine tree
    [tested test_the_packaging_map_carries_the_corpus]
    [measured 2026-08-20: the built wheel installed into a venv outside the
    checkout loads the corpus, which the checks.yml wheel job now asserts]
Guarantees:
  - wire terms compare up to a renaming of v payloads and byte-exactly
    everywhere else, so the two shipped variable-naming schemes both pass
    and a collapsed or aliased variable does not
    [tested test_alpha_comparison_refuses_a_collapsed_variable]
  - a case outside a driver's declared profile is REPORTED as out of
    profile rather than dropped, and a driver declaring less than the core
    profile is refused before any case runs
    [tested test_a_driver_declaring_less_than_the_core_profile_is_refused]
  - a driver that raises on everything fails every positive case rather
    than passing as one that refuses correctly
    [tested test_a_driver_that_refuses_everything_is_caught]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

__all__ = ["CodecDriver", "check_codec", "codec_corpus", "codec_plan"]


@runtime_checkable
class CodecDriver(Protocol):
    """One implementation of the codec, as the kit drives it.

    `tags` and `frames` declare what this encoding carries; a case using
    anything outside them is reported out of profile rather than failed.
    `printer` names which column of a case's `written` field applies.
    `exact_integers` and `non_finite` say what this concrete encoding can
    carry, which is what turns the two conditional refusals into
    obligations one way or the other. `resolves_anonymous` says whether
    decoding builds this host's own variables, which is what decides
    whether the reserved `_` payload comes back as itself.

    Not every codec is a whole binding. A storage provider validates and
    carries wire terms and neither reads MeTTa source nor prints an atom,
    so `reads_text` may be false and `printer` may be None; the kit runs
    the legs the driver has and `codec_plan` names the ones it does not.

    Every operation refuses by raising.
    """

    name: str
    tags: frozenset[str]
    frames: frozenset[str]
    printer: str | None
    reads_text: bool
    exact_integers: bool
    non_finite: bool
    resolves_anonymous: bool
    runs_programs: bool

    def read(self, text: str) -> Any:
        """MeTTa source text through the engine's reader and this encoder."""

    def roundtrip(self, wire: Any) -> Any:
        """Decode into this host's own atom, then encode it back."""

    def render(self, wire: Any) -> str:
        """Decode, then print with the printer this binding ships."""

    def transport(self, wire: Any) -> Any:
        """Serialise to the concrete encoding and parse it back."""

    def frame(self, wire: Any) -> dict:
        """Read one frame into its named parts."""

    def host_value(self) -> Any:
        """A value only this host can mint, for the o tag."""

    def transcript(self, program: str) -> list:
        """Run a MeTTa program, answering one wire group per ! directive."""
        # Spelled out rather than left a stub, the shape JanusBridge already
        # uses: a parameter no other line in this module names reads as dead
        # to vulture, and a bare docstring reads as a missing return to mypy.
        del program
        raise NotImplementedError


def _corpus_path() -> Path:
    """The corpus, in a checkout or beside an installed engine tree."""
    # Imported here rather than at module scope: the kit is data first, and
    # the engine is only where the file happens to live.
    from . import _engine  # noqa: PLC0415

    path = Path(_engine._resolve_petta_path()) / "tests" / "codec" / "corpus.json"
    if not path.is_file():
        msg = (
            f"the codec corpus is not at {path}; a checkout carries it at "
            f"tests/codec/corpus.json and a wheel carries it beside the "
            f"engine tree"
        )
        raise FileNotFoundError(
            msg
        )
    return path


def codec_corpus() -> dict:
    """The golden corpus as data, for a driver in any language to read."""
    return json.loads(_corpus_path().read_text(encoding="utf-8"))


# --------------------------------------------------------------- comparison


def _is_variable(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 2 and value[0] == "v"


def alpha_equal(left: Any, right: Any) -> bool:
    """Wire equality up to a renaming of v payloads.

    A v payload is an identity within its own term and never a display name,
    and two encoders ship here that spell it differently: one writes the
    source name and one writes a process-local machine name. Both are
    correct, so the comparison is a BIJECTION between the two terms'
    payloads, which still separates (f $x $x) from (f $x $y).

    Everything else compares by type and value, so ["n", 1] and ["n", 1.0]
    are different terms, as an integer and a float are different atoms.
    """
    forward: dict[Any, Any] = {}
    backward: dict[Any, Any] = {}
    stack = [(left, right)]
    while stack:
        a, b = stack.pop()
        if _is_variable(a) or _is_variable(b):
            if not (_is_variable(a) and _is_variable(b)):
                return False
            x, y = a[1], b[1]
            if forward.setdefault(x, y) != y or backward.setdefault(y, x) != x:
                return False
            continue
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            if len(a) != len(b):
                return False
            stack.extend(zip(a, b, strict=True))
            continue
        if a is b:
            continue
        if type(a) is not type(b):
            return False
        if a != b:
            # The one value not equal to itself. The wire carries THE NaN,
            # so two decodings of it are the same term even though IEEE-754
            # says the values differ.
            if isinstance(a, float) and math.isnan(a) and math.isnan(b):
                continue
            return False
    return True


# ------------------------------------------------------------- materialising

_FLOATS = {"inf": float("inf"), "-inf": float("-inf"), "nan": float("nan")}


def _materialise(value: Any, driver: CodecDriver) -> Any:
    """Resolve the corpus's two escapes into values JSON cannot write."""
    if isinstance(value, dict):
        if "$float" in value:
            return _FLOATS[value["$float"]]
        if "$host" in value:
            return driver.host_value()
        return value
    if isinstance(value, list):
        return [_materialise(item, driver) for item in value]
    return value


def _generated(spec: dict) -> Any:
    """A wire term too large to write out, built from its description."""
    if spec["kind"] != "nest":
        msg = f"the corpus asks for an unknown generator {spec['kind']!r}"
        raise ValueError(msg)
    wire = spec["leaf"]
    for _ in range(spec["depth"]):
        wire = ["e", [["s", "down"], wire]]
    return wire


def _case_wire(case: dict, driver: CodecDriver) -> Any:
    if "generate" in case:
        return _generated(case["generate"])
    return _materialise(case["wire"], driver)


# -------------------------------------------------------------------- plan


def codec_plan(driver: CodecDriver, *, corpus: dict | None = None) -> dict:
    """Which cases this driver's declaration puts in and out of scope, and
    which of the four legs it runs at all.

    Reported rather than silently applied: a profile is how an encoding says
    what it carries, and a case dropping out of a run without saying so is
    how a kit passes while testing less.
    """
    corpus = corpus or codec_corpus()
    legs = ["roundtrip", "transport"]
    if driver.reads_text:
        legs.insert(0, "read")
    if driver.printer is not None:
        legs.append("render")
    plan: dict[str, list] = {"run": [], "out_of_profile": [], "legs": sorted(legs)}
    for case in corpus["cases"]:
        outside = set(case.get("tags", ())) - set(driver.tags)
        required = case.get("requires")
        if outside:
            plan["out_of_profile"].append((case["id"], f"tags {sorted(outside)}"))
        elif required and not getattr(driver, required):
            plan["out_of_profile"].append((case["id"], f"needs {required}"))
        else:
            plan["run"].append(case["id"])
    for case in corpus["refusals"]:
        plan["run"].append(case["id"])
    for case in corpus["frames"]:
        if case["frame"] in driver.frames:
            plan["run"].append(case["id"])
        else:
            plan["out_of_profile"].append((case["id"], f"frame {case['frame']}"))
    for case in corpus["transcripts"]:
        if driver.runs_programs:
            plan["run"].append(case["id"])
        else:
            plan["out_of_profile"].append((case["id"], "runs no programs"))
    return plan


# ------------------------------------------------------------------- checks


def _refused(operation, *arguments) -> str | None:
    """The refusal an operation raised, or None when it accepted."""
    try:
        operation(*arguments)
    except Exception as exc:  # noqa: BLE001  a driver refuses in its host's own way
        return f"{type(exc).__name__}: {exc}"
    return None


def _check_term(case: dict, driver: CodecDriver) -> list[str]:
    complaints: list[str] = []
    wire = _case_wire(case, driver)
    here = f"{driver.name}/{case['id']}"

    if "text" in case and driver.reads_text:
        try:
            read = driver.read(case["text"])
            if not alpha_equal(read, wire):
                complaints.append(f"{here}: read({case['text']!r}) gave {read!r}, not {wire!r}")
        except Exception as exc:  # noqa: BLE001
            complaints.append(f"{here}: read({case['text']!r}) refused: {exc}")

    # A roundtrip is identity except where the wire is not an identity: the
    # anonymous payload means "fresh here", so what comes back depends on
    # whether this codec resolves it or carries it.
    expected = case.get("roundtrip", wire)
    if isinstance(expected, dict):
        branch = "then" if getattr(driver, expected["when"]) else "otherwise"
        expected = _materialise(expected[branch], driver)
    try:
        back = driver.roundtrip(wire)
        if not alpha_equal(back, expected):
            complaints.append(f"{here}: roundtrip gave {back!r}, not {expected!r}")
    except Exception as exc:  # noqa: BLE001
        complaints.append(f"{here}: roundtrip refused: {exc}")

    if "written" in case and driver.printer is not None:
        written = case["written"]
        expected = written if isinstance(written, str) else written.get(driver.printer)
        if expected is None:
            complaints.append(
                f"{here}: the corpus pins no {driver.printer} spelling for this case"
            )
        else:
            try:
                actual = driver.render(wire)
                if actual != expected:
                    complaints.append(f"{here}: render gave {actual!r}, not {expected!r}")
            except Exception as exc:  # noqa: BLE001
                complaints.append(f"{here}: render refused: {exc}")

    try:
        carried = driver.transport(wire)
        if not alpha_equal(carried, wire):
            complaints.append(f"{here}: transport gave {carried!r}, not {wire!r}")
    except Exception as exc:  # noqa: BLE001
        complaints.append(f"{here}: transport refused: {exc}")

    if case.get("reads_back") is False and "written" in case and driver.reads_text:
        written = case["written"]
        text = written if isinstance(written, str) else written[driver.printer]
        if _refused(driver.read, text) is None and alpha_equal(driver.read(text), wire):
            complaints.append(
                f"{here}: {text!r} reads back as this term, so the corpus is "
                f"wrong to say the text form loses it"
            )
    return complaints


def _check_refusal(case: dict, driver: CodecDriver) -> list[str]:
    wire = _materialise(case["wire"], driver)
    here = f"{driver.name}/{case['id']}"
    operation = getattr(driver, case["refuse"])
    licensed = case.get("unless")
    if licensed and getattr(driver, licensed):
        try:
            carried = operation(wire)
        except Exception as exc:  # noqa: BLE001
            return [f"{here}: declares {licensed} and still refused {wire!r}: {exc}"]
        if not alpha_equal(carried, wire):
            return [f"{here}: declares {licensed} and changed {wire!r} into {carried!r}"]
        return []
    if _refused(operation, wire) is None:
        return [f"{here}: {case['refuse']} accepted {wire!r}; {case['because']}"]
    return []


def _check_frame(case: dict, driver: CodecDriver) -> list[str]:
    here = f"{driver.name}/{case['id']}"
    try:
        parts = driver.frame(_materialise(case["wire"], driver))
    except Exception as exc:  # noqa: BLE001
        return [f"{here}: frame refused: {exc}"]
    complaints = []
    expected = {name: _materialise(value, driver) for name, value in case["parts"].items()}
    if set(parts) != set(expected):
        complaints.append(f"{here}: frame named {sorted(parts)}, not {sorted(expected)}")
        return complaints
    for name, want in expected.items():
        if not alpha_equal(parts[name], want):
            complaints.append(f"{here}: frame part {name} was {parts[name]!r}, not {want!r}")
    return complaints


def _check_transcript(case: dict, driver: CodecDriver) -> list[str]:
    here = f"{driver.name}/{case['id']}"
    try:
        groups = driver.transcript(case["program"])
    except Exception as exc:  # noqa: BLE001
        return [f"{here}: the program refused: {exc}"]
    want = _materialise(case["groups"], driver)
    if not alpha_equal(groups, want):
        return [f"{here}: answered {groups!r}, not {want!r}"]
    return []


def check_codec(driver: CodecDriver, *, corpus: dict | None = None) -> list[str]:
    """Run the golden corpus against one codec, answering its complaints.

    An empty list is conformance for everything the driver's profile puts in
    scope; `codec_plan` says what that scope was, and a driver declaring less
    than the core profile is refused here rather than passing on a small one.

        def test_my_codec_conforms():
            assert petta.testing.check_codec(MyDriver()) == []
    """
    corpus = corpus or codec_corpus()
    core = set(corpus["profiles"]["core"]["tags"])
    missing = core - set(driver.tags)
    if missing:
        msg = (
            f"{driver.name} declares {sorted(driver.tags)}, which is short of "
            f"the core profile by {sorted(missing)}. Every codec carries the "
            f"core five; an encoding that cannot is not a codec for this "
            f"grammar."
        )
        raise ValueError(
            msg
        )
    plan = set(codec_plan(driver, corpus=corpus)["run"])
    complaints: list[str] = []
    for case in corpus["cases"]:
        if case["id"] in plan:
            complaints.extend(_check_term(case, driver))
    for case in corpus["refusals"]:
        complaints.extend(_check_refusal(case, driver))
    for case in corpus["frames"]:
        if case["id"] in plan:
            complaints.extend(_check_frame(case, driver))
    for case in corpus["transcripts"]:
        if case["id"] in plan:
            complaints.extend(_check_transcript(case, driver))
    return complaints
