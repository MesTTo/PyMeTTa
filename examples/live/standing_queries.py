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

from metta import MeTTa, S, V
from metta.live import Delta
from metta.vocabularies import LiveStrategy

m = MeTTa().space()

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

event_stream = m.events()
check("the event stream lists live folds", len(event_stream.folds(str(m.name))), 4)

for subscription in (ping, pong, audit, inbox):
    subscription.cancel()
check("cancelled folds leave the live roster", event_stream.folds(str(m.name)), ())
m.add(S.ping(99))
check("no delivery after cancel", len(transcript), 5)

# A subscription tells you what CHANGED. A live view keeps the ANSWER, so a
# program that keeps consulting "the current set of X" stops asking.
with m.live(S.alert(V.level)) as alerts:
    m.add(S.alert(S.red), S.alert(S.red), S.alert(S.amber))
    check("the view holds what the space holds", len(alerts), 3)
    check("multiplicity, because a space is a multiset",
          alerts.count(S.alert(S.red)), 2)
    check("membership without an engine call", S.alert(S.red) in alerts, True)
    m.remove(S.alert(S.red))
    check("and it follows a removal", alerts.count(S.alert(S.red)), 1)

# The query is one pattern, a conjunction spelled the way match spells one, or
# a call to a tabled head, and the maintenance follows that shape.
m.add(S.person(S.bob, 30), S.city(S.bob, S.nyc))
with m.live(S.person(V.n, V.a), S.city(V.n, V.c)) as joined:
    check("a join, materialised", len(joined), 1)
    check("watched by its heads", joined.strategy, LiveStrategy.heads)
    m.add(S.person(S.eve, 25), S.city(S.eve, S.la))
    check("and current when the write returns", len(joined), 2)

# The same view read as a stream: a signed delta per row, and a progress
# marker after each commit saying which generation you have seen everything up
# to. A commit is one boundary whatever it wrote.
with m.live(S.tick(V.n)) as ticks, ticks.changes(timeout=5) as deltas:
    m.transaction(lambda: m.add(S.tick(1), S.tick(2)))
    read = []
    for delta in deltas:
        match delta:
            case Delta("add", 1, row, _atom, _generation):
                read.append(f"add {row['n']}")
            case Delta("progress", _, None, None, _generation):
                read.append("progress")
                break
    check("two adds and one progress, because a commit is one boundary",
          read, ["add 1", "add 2", "progress"])
done("standing_queries")
