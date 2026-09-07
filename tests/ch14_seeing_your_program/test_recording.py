"""Purpose: recordings. A run kept as data walks backwards for free, saves and
loads unchanged, replays under its own seed into another engine, refuses when
the space or the program cannot support a replay, and hands back a live session
stopped where any of its events is.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import gzip
import json

import pytest

from metta import S
from metta import space as make_space
from metta._recording import Recording, RecordingVersionWarning
from metta.errors import MettaError
from metta.foreign import SpaceProvider
from metta.vocabularies import Limit

#: A doubly recursive definition, so the run has depth to walk and the
#: automatic memo takes it, which is the case a recording of a real program
#: is: `fib` is exactly the head whose trace was empty before the dispatcher
#: declared itself.
FIB = "(= (rec-fib $n) (if (< $n 2) $n (+ (rec-fib (- $n 1)) (rec-fib (- $n 2)))))"


@pytest.fixture()
def m(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    with metta._new_space() as space:
        space.run(FIB)
        yield space


@pytest.fixture()
def twin(metta):
    """A second space holding the same atoms, which is what a replay wants."""
    with metta._new_space() as space:
        space.run(FIB)
        yield space


def test_a_recording_holds_the_run_and_the_state_that_produced_it(m):
    """The header is what makes the events re-runnable rather than only readable."""
    recording = m.record(S["rec-fib"](6))
    assert recording.program == "!(rec-fib 6)"
    assert recording.space == m.name
    assert recording.digest == m.digest()
    assert recording.seed > 0
    assert recording.replayable is True
    assert recording.reason is None
    assert recording.engine["metta"]
    assert len(recording) == len(recording.events) > 4
    assert recording.events.stopped is None
    assert str(recording.at(0).term) == "(rec-fib 6)"


def test_a_named_seed_is_the_one_recorded_and_the_draws_replay(m, twin):
    """Record the nondeterministic input once and replay from it, rr's shape.

    The generator is the only such input a program has without a host call,
    and a recorded run always pins it, so the draws come back. The engine is
    left where it was, which is what makes the seed a scope rather than a
    setting.
    """
    m.run("(= (rec-roll) (random-int 1 1000000))")
    twin.run("(= (rec-roll) (random-int 1 1000000))")
    recording = m.record("!(rec-roll)", seed=7)
    assert recording.seed == 7
    drawn = [event.answer for event in recording.events if event.kind == "exit"]
    assert drawn

    replayed = recording.replay(twin)
    assert [event.answer for event in replayed if event.kind == "exit"] == drawn
    # And the space outside the recording still draws for itself.
    assert m.run("!(rec-roll)")


def test_a_recording_saves_and_loads_unchanged(m, tmp_path):
    """Round trip through the file: same header, same events, same answers."""
    recording = m.record(S["rec-fib"](8))
    path = tmp_path / "run.metta-rec.json"
    assert recording.save(path) == len(recording.events)

    loaded = Recording.load(path)
    assert loaded.document() == recording.document()
    assert loaded.events == recording.events
    assert loaded.seed == recording.seed
    assert loaded.digest == recording.digest
    # BYTE-identically, which is the strong reading: writing the recording
    # that came back out of the file produces the same file, so the terms
    # made the round trip through atoms and back with nothing lost or
    # reordered on the way.
    again = tmp_path / "again.metta-rec.json"
    loaded.save(again)
    assert again.read_bytes() == path.read_bytes()
    # A term crosses as the engine's WIRE and not as its text, which is what
    # keeps a value the reader would parse back differently: read from text,
    # a symbol whose spelling reads as something else came back as something
    # else, and the tracer's own note records the three that did.
    row = recording.document()["events"][0]
    assert row[4] == recording.events[0].term.to_wire()
    m.run('(= (rec-echo $x) $x)')
    odd = m.record('!(rec-echo "a;b\nc")')
    other = tmp_path / "odd.metta-rec.json"
    odd.save(other)
    reloaded = Recording.load(other)
    assert reloaded.events == odd.events
    assert str(reloaded.at(-1).answer) == str(odd.at(-1).answer)


def test_a_gzipped_recording_round_trips(m, tmp_path):
    """A name ending .gz is gzipped, the rule Space.save already follows."""
    recording = m.record(S["rec-fib"](8))
    path = tmp_path / "run.metta-rec.json.gz"
    recording.save(path)
    assert path.read_bytes()[:2] == b"\x1f\x8b"
    assert json.loads(gzip.decompress(path.read_bytes()))["format"] == "metta-recording"
    assert Recording.load(path).events == recording.events


def test_a_file_that_is_not_a_recording_refuses_by_name(m, tmp_path):
    """A KeyError halfway through decoding says nothing about the file."""
    path = tmp_path / "not-a-recording.json"
    path.write_text(json.dumps({"events": []}))
    with pytest.raises(ValueError, match="is not a MeTTa recording"):
        Recording.load(path)

    newer = tmp_path / "newer.metta-rec.json"
    document = m.record(S["rec-fib"](2)).document()
    document["version"] = 99
    newer.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="layout 99"):
        Recording.load(newer)


def test_a_recording_from_another_engine_version_warns_and_loads(m, tmp_path):
    """The events are data and stay readable; what may not hold is the replay."""
    path = tmp_path / "old.metta-rec.json"
    document = m.record(S["rec-fib"](4)).document()
    document["engine"]["metta"] = "0.0.1-from-elsewhere"
    path.write_text(json.dumps(document))
    with pytest.warns(RecordingVersionWarning, match="0.0.1-from-elsewhere"):
        loaded = Recording.load(path)
    assert len(loaded.events) == len(document["events"])


def test_navigation_walks_backwards_and_forwards(m):
    """The point of a recording: a step backwards is a lookup, not a re-run."""
    recording = m.record(S["rec-fib"](6))
    last = len(recording) - 1
    assert recording.position == 0
    assert recording.seek(4).index == 4
    assert recording.back().index == 3
    assert recording.forward().index == 4
    assert recording.at(-1).index == last
    # at() does not move the cursor; seek() does.
    assert recording.position == 4
    assert recording.at(0).index == 0
    assert recording.position == 4


def test_a_frame_outside_the_recording_refuses(m):
    """IndexError, which is what Python calls this, naming the range."""
    recording = m.record(S["rec-fib"](4))
    with pytest.raises(IndexError, match=f"outside a recording of {len(recording)}"):
        recording.at(len(recording))
    with pytest.raises(IndexError):
        recording.at(-len(recording) - 1)
    recording.seek(0)
    with pytest.raises(IndexError):
        recording.back()


def test_a_frames_stack_agrees_with_the_depths(m):
    """The chain of open calls, outermost first, ending with this event's term.

    It is computed from the depths in one pass, so it costs the event's own
    depth to read and nothing to hold.
    """
    recording = m.record(S["rec-fib"](6))
    for index in range(len(recording)):
        frame = recording.at(index)
        assert len(frame.stack) == frame.depth + 1
        assert frame.stack[-1] == frame.term
        assert frame.stack == recording.stack(index)
        if frame.depth:
            parent = frame.stack[-2]
            assert str(parent).startswith("(rec-fib")


def test_find_answers_the_frames_of_one_head(m):
    """A search becomes a position: find(...)[0].index feeds seek()."""
    m.run("(= (rec-twice $x) (+ (rec-fib $x) (rec-fib $x)))")
    recording = m.record(S["rec-twice"](4))
    found = recording.find(S["rec-twice"])
    assert [frame.kind for frame in found] == ["call", "exit"]
    assert recording.seek(found[0].index).term == S["rec-twice"](4)
    assert len(recording.find(S["rec-fib"])) > 2
    assert recording.find(S["rec-missing"]) == ()


def test_replay_reproduces_the_run_in_another_engine(m, twin):
    """Byte for byte, event for event, under the recorded seed."""
    recording = m.record(S["rec-fib"](12))
    replayed = recording.replay(twin)
    assert list(replayed) == list(recording.events)
    # And repeatedly, because the replay puts the target back to a first
    # run's state before it runs: a memo would answer the second one in
    # fewer steps and produce a shorter stream for the same answers.
    assert list(recording.replay(twin)) == list(recording.events)
    assert list(recording.replay()) == list(recording.events)


def test_replay_refuses_a_space_whose_content_differs(m, twin):
    """The digest is what says the program reduces against the same atoms."""
    recording = m.record(S["rec-fib"](6))
    twin.run("(= (rec-elsewhere) 1)")
    with pytest.raises(MettaError, match="needs the space the recording was made over"):
        recording.replay(twin)


def test_replay_refuses_a_program_that_reaches_the_host(m):
    """A host read is a new reading, not the recorded one.

    The verdict is taken at record time and kept, because the answer can
    change afterwards and the recording's is the one that matters.
    """
    recording = m.record('!(py-atom "len")')
    assert recording.replayable is False
    assert "py-atom" in recording.reason
    with pytest.raises(MettaError, match="not replayable"):
        recording.replay()
    with pytest.raises(MettaError, match="not replayable"):
        recording.debug(at=0)


def test_a_seeded_draw_stays_replayable(m):
    """A draw is oracleIO and replays anyway, because the seed captured it.

    Which oracleIO operations that is true of is the engine's declaration, so
    this reads it rather than holding a second list.
    """
    m.run("(= (rec-draw) (random-int 1 100))")
    recording = m.record("!(rec-draw)", seed=3)
    assert recording.replayable is True
    assert recording.reason is None


def test_replay_reports_the_first_divergent_event(m, twin):
    """"Something diverged" sends a reader through the whole log to find what."""
    recording = m.record(S["rec-fib"](6))
    twin.run("(= (rec-fib $n) 0)")
    twin.remove(twin.parse(FIB.strip()))
    object.__setattr__(recording, "digest", twin.digest())
    with pytest.raises(MettaError, match=r"diverged at event|replay stopped after"):
        recording.replay(twin)


def test_a_loaded_recording_needs_a_space_to_run_in(m, tmp_path):
    """A file has a space NAME, which is not a handle to anything."""
    path = tmp_path / "run.metta-rec.json"
    m.record(S["rec-fib"](4)).save(path)
    loaded = Recording.load(path)
    with pytest.raises(MettaError, match="no live space to replay in"):
        loaded.replay()
    assert list(loaded.replay(m)) == list(loaded.events)


def test_debug_at_stops_at_that_events_term(m):
    """The recording's other direction, from data back to a live execution.

    at(k) reads what happened at event k; debug(at=k) stands the program back
    up there with its bindings live.
    """
    recording = m.record(S["rec-fib"](6))
    for index in (0, 3, len(recording) - 1):
        frame = recording.at(index)
        with recording.debug(at=index) as session:
            assert session.stop is not None
            assert (session.stop.seq, session.stop.kind) == (frame.seq, frame.kind)
            assert session.stop.term == frame.term
    with pytest.raises(IndexError):
        recording.debug(at=len(recording))


def test_a_cut_recording_says_so_and_replays_to_the_same_length(m, twin):
    """A cut recording says so, and replays to the same length.

    max_events bounds the RECORDING, and a prefix that does not admit to being
    one is worse than the raise it replaced.
    """
    recording = m.record(S["rec-fib"](12), max_events=6)
    assert recording.events.stopped is Limit.events
    assert len(recording) == 6
    assert list(recording.replay(twin)) == list(recording.events)


def test_a_recording_reads_as_what_it_is(m):
    """The repr says the program, the size, the seed and any refusal."""
    recording = m.record(S["rec-fib"](4))
    text = repr(recording)
    assert "!(rec-fib 4)" in text
    assert f"{len(recording)} events" in text
    assert f"seed={recording.seed}" in text
    assert "not replayable" not in text
    assert str(recording.at(0)).startswith("[0] -> (rec-fib 4)")


def test_the_bound_host_values_ride_in_the_header(m):
    """What the run could see, recorded beside what it did.

    A number crosses on the wire and rides in the header; a live host object
    has no cross-process spelling, so a file claiming to carry it would replay
    against a different object, and the recording says so instead. The traced
    run does not read bound values yet, so the field records the scope rather
    than feeding it back; the handler layer is what will fill it.
    """
    with m.bind(n=5):
        numbered = m.record(S["rec-fib"](4))
    assert numbered.replayable is True
    assert numbered.bound == {"n": ["n", 5]}
    assert json.dumps(numbered.document())

    class Live:
        pass

    with m.bind(obj=Live()):
        opaque = m.record(S["rec-fib"](4))
    assert opaque.replayable is False
    assert "live host object" in opaque.reason
    assert opaque.bound == {}
    assert json.dumps(opaque.document())


def test_a_space_with_no_content_digest_records_and_says_why(metta):
    """A provider that will not be enumerated is a read from outside.

    The events are what they are and stay readable; what is lost is the check
    a replay makes before it re-runs, so the refusal becomes the reason rather
    than the answer. It is the other half of the question the effect plan
    asks.
    """
    del metta

    class Opaque(SpaceProvider):
        def can_run(self, capability, **request):
            del request
            return capability != "enumerate"

        def match(self, _pattern):
            return iter(())

    with make_space(backing=Opaque()) as target:
        target.run("(= (rec-opaque $x) $x)")
        recording = target.record("!(rec-opaque 1)")
    assert len(recording.events) == 2
    assert recording.digest == ""
    assert recording.replayable is False
    assert "no content digest" in recording.reason
    with pytest.raises(MettaError, match="not replayable"):
        recording.replay()
