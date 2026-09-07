"""Purpose: use multi-argument pool work and nonblocking mailbox reads.

The pool and channel are context managers because each owns an attached Prolog
engine or an SWI message queue until it closes.
Owns resources: both handles close at their nested context-manager boundaries.
"""

from _common import check, done

from metta import MeTTa, S, channel

with MeTTa() as context:
    space = context.self
    with space.pool(workers=2) as pool:
        check(
            "starmap spreads each argument tuple in input order",
            list(
                pool.starmap(
                    lambda left, right: space.eval(S["+"](left, right))[0],
                    [(1, 2), (3, 4)],
                )
            ),
            [3, 7],
        )

    with space, channel(max=1) as mailbox:
        check("try_recv returns immediately when empty", mailbox.try_recv() is None)
        mailbox.send(S.job(7))
        check("try_recv takes a waiting term", mailbox.try_recv(), S.job(7))
        check("the take leaves the mailbox empty", mailbox.try_recv() is None)

done("concurrency_handles")
