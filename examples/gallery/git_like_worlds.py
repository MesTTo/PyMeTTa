"""Purpose: branch, diff, and commit immutable worlds like local repository heads.

Guarantees:
  - two successor worlds leave their base untouched, expose an exact multiset
    diff, and only the selected world lands as one post-commit observed change
    [tested: test_a_gallery_program_runs; commit=4b6f6bf075e80f794ebcb46a5748dba46dcd3522]
  - branching declares the effect rank its branches are allowed to reach, so a
    world admits the writes it handles and refuses anything stronger [tested:
    test_a_gallery_program_runs; commit=173eeed021beb360b5e5f9f8461889e27190affc]
Owns resources: two named native spaces and one subscription; cancel() and
  drop() release them after the selected branch commits, while process exit
  releases them after an earlier failed claim.
"""

from _common import claim, doctest, done

from metta import MeTTa, S, V


def next_revision(revision: int) -> int:
    """Advance an immutable revision number.

    >>> !(next-revision 4)
    [5]
    """
    return revision + 1


engine = MeTTa()
owner = engine.self
parent = engine.space("&gallery-worlds")
audit = engine.space("&gallery-world-audit")
revision = owner.define(next_revision)
doctest("revision doctest", revision)

claim("create base revision", S.add_atom(parent, S.Base(1)), parent.eval)
# -> (add-atom &gallery-worlds (Base 1))
# => ()
# A reified world admits only the effect rank its origin declares it handles.
# Branching writes into each successor's own scratch state, so this repository
# covers writesState; anything stronger, an import or a clock read, still
# refuses and names the operation.
parent.covers("writesState")
base = parent.reify()
branches = {}


def observed(event) -> None:
    """Record both the committed event and the state visible during delivery."""
    audit.add(
        S.Observed(event.atom),
        S.Snapshot(S.Bag(*sorted(parent.atoms(), key=str))),
    )


subscription = parent.subscribe(S.Decision(V.choice), observed)


def branch(name):
    """Return an evaluator that records one immutable successor by name."""

    def evaluate(term):
        answers, successor = base.eval(term)
        branches[name] = successor
        return answers

    return evaluate


claim(
    "launch branch",
    S.add_atom(S["&self"], S.Decision(S.launch)),
    branch("launch"),
)
# -> (add-atom &self (Decision launch))
# => ()
claim(
    "abort branch",
    S.add_atom(S["&self"], S.Decision(S.abort)),
    branch("abort"),
)
# -> (add-atom &self (Decision abort))
# => ()
claim(
    "base remains untouched",
    S.match(parent, V.atom, V.atom),
    owner.eval,
)
# -> (match &gallery-worlds $atom $atom)
# => (Base 1)
claim(
    "speculation emits no parent event",
    S.match(audit, S.Observed(V.atom), V.atom),
    owner.eval,
)
# -> (match &gallery-world-audit (Observed $atom) $atom)
# => <none>


def compare_worlds(term):
    """Expose the exact two-sided multiset diff between the successors."""
    launch_only, abort_only = branches["launch"].diff(branches["abort"])
    return [S.Diff(S.Launch(*launch_only), S.Abort(*abort_only), term.children[1])]


claim(
    "branch multiset diff",
    S.compare_worlds(S.launch, S.abort),
    compare_worlds,
)
# -> (compare-worlds launch abort)
# => (Diff (Launch (Decision launch)) (Abort (Decision abort)) launch)
try:

    def commit_selected(term):
        """Commit the branch named by the checked structural term."""
        selected = str(term.children[1])
        parent.commit(branches[selected])
        return parent.atoms()

    claim(
        "commit selected world",
        S.commit_world(S.launch),
        commit_selected,
    )
    # -> (commit-world launch)
    # => (Base 1)
    # => (Decision launch)
    claim(
        "post-commit event",
        S.match(audit, S.Observed(V.atom), V.atom),
        owner.eval,
    )
    # -> (match &gallery-world-audit (Observed $atom) $atom)
    # => (Decision launch)
    claim(
        "observer sees complete commit",
        S.match(audit, S.Snapshot(V.state), V.state),
        owner.eval,
    )
    # -> (match &gallery-world-audit (Snapshot $state) $state)
    # => (Bag (Base 1) (Decision launch))
finally:
    subscription.cancel()
    audit.drop()
    parent.drop()

done("git_like_worlds")
