"""Purpose: coordinate one deterministic Linda tuple through watch, peek, and take.

Guarantees:
  - watch observes the committed add, peek leaves the tuple present, and take
    returns and removes exactly that occurrence
    [tested: test_every_gallery_program_runs; commit=8bfe05c3850776543ece25a85038242f10b1d841]
Owns resources: one named tuple space and one watch iterator; close() and
  drop() release them on every normal path, while process exit releases them
  after an earlier failed claim.
"""

from _common import claim, doctest, done

from metta import MeTTa, S, V


def next_job(job_id: int) -> int:
    """Advance a monotonic job identifier.

    >>> !(next-job 7)
    [8]
    """
    return job_id + 1


engine = MeTTa()
owner = engine.self
mailbox = engine.space("&gallery-linda")
advance = owner.define(next_job)
doctest("job identifier doctest", advance)

changes = mailbox.watch(S.Job(V.job_id))
try:
    claim(
        "publish tuple",
        S.add_atom(mailbox, S.Job(7)),
        mailbox.eval,
    )
    # -> (add-atom &gallery-linda (Job 7))
    # => ()

    def watch_event(term):
        """Read the committed add event from the already-open watch."""
        event = next(changes)
        return [S.Event(S[event.action], event.bindings["job-id"], term.children[2])]

    claim(
        "watch committed add",
        S.watch(mailbox, S.Job(V.job_id)),
        watch_event,
    )
    # -> (watch &gallery-linda (Job $job-id))
    # => (Event add 7 (Job $job-id))

    def peek(term):
        """Peek the pattern carried by the checked structural operation."""
        return [mailbox.peek(term.children[2], deadline=1.0)]

    claim(
        "peek leaves tuple",
        S.peek_atom(mailbox, S.Job(V.job_id)),
        peek,
    )
    # -> (peek-atom &gallery-linda (Job $job-id))
    # => (Job 7)
    claim(
        "tuple remains after peek",
        S.match(mailbox, S.Job(V.job_id), S.Job(V.job_id)),
        owner.eval,
    )
    # -> (match &gallery-linda (Job $job-id) (Job $job-id))
    # => (Job 7)

    def take(term):
        """Take the pattern carried by the checked structural operation."""
        return [mailbox.take(term.children[2], deadline=1.0)]

    claim(
        "take consumes tuple",
        S.take_atom(mailbox, S.Job(V.job_id)),
        take,
    )
    # -> (take-atom &gallery-linda (Job $job-id))
    # => (Job 7)
    claim(
        "tuple absent after take",
        S.match(mailbox, S.Job(V.job_id), S.Job(V.job_id)),
        owner.eval,
    )
    # -> (match &gallery-linda (Job $job-id) (Job $job-id))
    # => <none>
finally:
    changes.close()
    mailbox.drop()

done("linda_coordination")
