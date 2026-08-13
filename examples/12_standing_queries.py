"""Purpose: actors and pub-sub as spaces: the mailbox is a space, a
subscription is a standing query, and delivery is the engine's own write.
Two actors exchange messages by adding atoms; each reacts inside the write
that reached it, MeTTa programs and Python writes both delivering.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from petta import MeTTa, S, V

m = MeTTa().fresh_space()

# The ping actor: every (ping $n) mails back (pong $n), until three.
transcript = []


def ping_actor(event):
    n = event.bindings["n"].value
    transcript.append(("ping", n))
    if n < 3:
        m.add(S.pong(n))


def pong_actor(event):
    n = event.bindings["n"].value
    transcript.append(("pong", n))
    m.add(S.ping(n + 1))


ping = m.subscribe(S.ping(V.n), ping_actor)
pong = m.subscribe(S.pong(V.n), pong_actor)

# One message starts the exchange; delivery cascades inside the writes.
m.add(S.ping(1))
check("the exchange ran itself", transcript,
      [("ping", 1), ("pong", 1), ("ping", 2), ("pong", 2), ("ping", 3)])

# A MeTTa program's own add-atom delivers too: the funnel is the engine's.
seen = []
audit = m.subscribe(S.audit(V.what), lambda e: seen.append(str(e.bindings["what"])))
m.run("!(add-atom (context-space) (audit from-metta))")
check("engine-side writes deliver", seen, ["from-metta"])

# Queue mode is the mailbox reading: events wait until drained.
inbox = m.subscribe(S.letter(V.body), on="add")
m.add(S.letter(S.first), S.letter(S.second))
check("the mailbox drains in order",
      [str(e.bindings["body"]) for e in inbox.drain()], ["first", "second"])
check("and empties", inbox.drain(), [])

for subscription in (ping, pong, audit, inbox):
    subscription.cancel()
m.add(S.ping(99))
check("no delivery after cancel", len(transcript), 5)
done("12_standing_queries")
