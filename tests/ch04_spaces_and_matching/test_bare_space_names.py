"""Purpose: a space the engine registered without an ampersand crosses this seat's wire, so naming one does not take every later term on the engine down with it.

The engine registers a space under any symbol a program writes through:
`(= (space) my_space_name)` and one `add-atom` through it puts `my_space_name`
in the registry, which is what
`examples/ch04-spaces-and-matching/04-01-a-space-is-where-a-program-lives/07-add_atom_fun_space.metta`
relies on and what `space_names()` reports. The ampersand is how the engine
SPELLS the spaces it mints, not a rule about what a space name may be.

Three doors on this seat demanded it anyway, and a leaf that will not decode
fails the decode of every term containing it, so one bare name in the registry
made `(collapse (get-atoms my_space_name))` -- how a host photographs a space
-- undecodable for the rest of that engine's life. The Node seat met exactly
this against a downstream workspace and dropped its own demand on 2026-09-07;
these are the same claims on the Python seat.

Assumes:
  - the engine registry is process-wide, so each test writes through a name of
    its OWN and the walk runs the shared example once
Guarantees:
  - `space_names()` lists a bare registered name and `space(name)` opens THAT
    space, contents included
    [tested: test_a_bare_registered_name_opens_the_space_the_registry_named]
  - a handle for such a space crosses into a term and back, through `eval`,
    through `match` and through the text door
    [tested: test_a_bare_named_space_crosses_into_a_term_and_into_a_match]
  - the `p` wire round trips for a bare name exactly as for an ampersand one
    [tested: test_the_p_wire_round_trips_both_spellings]
  - a program naming one leaves every later program on the same engine
    answering what it answered before, which is the defect end to end
    [tested: test_a_bare_name_does_not_poison_a_later_program_on_one_engine]
  - a `$` name and the empty name are still refused, each for a reason the
    language gives [tested: test_a_dollar_name_is_still_refused]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import pytest

from metta import MeTTa, S, V

#: The program that registers a bare name, and the four a downstream workspace
#: measured drawing nothing once it had run before them.
POISONER = "04-01-a-space-is-where-a-program-lives/07-add_atom_fun_space.metta"
LATER = (
    "04-01-a-space-is-where-a-program-lives/08-spacefunction.metta",
    "04-01-a-space-is-where-a-program-lives/09-selfprog.metta",
    "04-01-a-space-is-where-a-program-lives/10-subtract_atom.metta",
    "04-02-patterns-and-bindings/01-matchsingle.metta",
)


@pytest.fixture()
def context():
    """A context of its own, so nothing this file stores outlives its test."""
    with MeTTa() as engine:
        yield engine


@pytest.fixture()
def registered(context, request):
    """A bare space name THIS test registered, the way the example does.

    The name carries the test's own, because the engine's registry is
    process-wide: two tests writing through one bare name would each see the
    other's atom and the count would depend on the shuffled order.
    """
    name = f"bare_{request.node.name}"
    context.self.run(f"(= (probe) {name})\n!(add-atom (probe) (my test atom))")
    return name


def test_a_bare_registered_name_opens_the_space_the_registry_named(
    context, registered
):
    """The listing door and the opening door agree.

    `space_names()` naming something `space()` refuses is this seat
    disagreeing with the engine about what a space is. A string names the
    space EXACTLY, which is the bracket door's rule everywhere else here; the
    Symbol door still supplies the ampersand, so the two are different spaces
    and say so.
    """
    assert registered in context.self.space_names()

    opened = context.space(registered)
    assert opened.name == registered
    assert [str(atom) for atom in opened] == ["(my test atom)"]

    # The convenience door is unchanged and reaches a DIFFERENT space, which
    # is what makes the exact door worth having. `name` is the ENGINE name
    # rather than str(), which answers the name ATOM where a handle carries
    # one and would print both of these the same.
    assert context.space(S[registered]).name == f"&{registered}"
    assert context.space(S[registered]) != opened


def test_a_bare_named_space_crosses_into_a_term_and_into_a_match(
    context, registered
):
    """The handle goes back IN, which is what the wire refused.

    `eval` builds a term holding the space and `match` sends it as the query's
    target; both cross a `p` payload the engine's own decoder used to reject,
    and a leaf that fails to decode fails the whole term rather than itself.
    """
    opened = context.space(registered)

    photographed = context.self.eval(S.collapse(S["get-atoms"](opened)))
    assert [str(answer) for answer in photographed] == ["((my test atom))"]

    assert [str(row[0]) for row in opened.match(S.my(V.what, S.atom))] == ["test"]

    # And through the text door on the same space, so the two rungs agree.
    (atoms,) = context.self.run(f"!(get-atoms {registered})")
    assert [str(atom) for atom in atoms] == ["(my test atom)"]


def test_the_p_wire_round_trips_both_spellings(context, registered):
    """One tag, two spellings, one decode.

    The payload is the engine name and nothing else, so a handle written out
    and read back is the same space whichever way the name is spelled.
    """
    for name in (registered, "&self"):
        opened = context.space(name)
        assert opened.to_wire() == ["p", name]
        assert context.space(name) == opened


def test_a_bare_name_does_not_poison_a_later_program_on_one_engine(repo_root):
    """The defect end to end, in the shape the consumer reported it.

    One engine, one space per program, and after each program a photograph of
    every registered space: that is what puts a bare name from the registry
    onto the wire. Two things are asked of it. Each program answers the same on
    an engine that has seen `07` as on one that has not, so the comparison is
    the engine's state rather than the program's; and every photograph
    ANSWERS, because `(collapse (get-atoms <space>))` has exactly one answer
    for every space there is.

    The second is what the wire decides here, and it is the Python seat's own
    shape of the damage. A wire term this seat cannot decode does not raise the
    way the Node seat's does: `metta_py_decode/2` simply fails, so the eval
    answers NOTHING and a host reads an empty photograph as an empty space.
    """
    chapter = repo_root / "examples" / "ch04-spaces-and-matching"
    with MeTTa() as engine:
        minted = []
        # The registry is process-WIDE, so it holds whatever every other test
        # in this worker has registered, including the deliberately broken
        # providers test_answer_protocol.py binds. The walk photographs what
        # ITS OWN programs put there, which is where the bare name comes from
        # and all this claim is about.
        already = set(engine.self.space_names())

        def walk(relative):
            scratch = engine.space()
            minted.append(scratch)
            answers = [
                [str(answer) for answer in group]
                for group in scratch.run((chapter / relative).read_text())
            ]
            # LIST, because eval answers a lazy view: a photograph nobody
            # pulls never crosses the wire, and the walk would then prove
            # nothing about the wire at all.
            for identity in sorted(set(engine.self.space_names()) - already):
                photographed = list(
                    engine.self.eval(
                        S.collapse(S["get-atoms"](engine.space(identity)))
                    )
                )
                # Every space photographs exactly one tuple, so an empty
                # answer means the term never reached the engine.
                assert len(photographed) == 1, (relative, identity)
            return answers

        try:
            before = [walk(relative) for relative in LATER]
            walk(POISONER)
            assert any(
                not identity.startswith("&")
                for identity in set(engine.self.space_names()) - already
            ), "the poisoning program registered no bare name, so nothing is proved"
            for relative, was in zip(LATER, before, strict=True):
                assert walk(relative) == was, relative
        finally:
            for scratch in minted:
                scratch.drop()


def test_a_dollar_name_is_still_refused(context):
    """The one refusal the old message named that is a rule of the language.

    A `$` name reads back as a VARIABLE, so a term mentioning such a space
    would stop being the term it crossed as. The empty name is refused beside
    it, for having no symbol to be.
    """
    with pytest.raises(ValueError, match=r"reads back as a variable"):
        context.space("$kb")
    with pytest.raises(ValueError, match=r"nonempty symbol"):
        context.space("")
