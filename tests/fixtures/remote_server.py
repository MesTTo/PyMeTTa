"""Purpose: the other context: a separate engine process serving one space
for the remote-space tests. Prints its URL and served space name as one
JSON line, then serves until terminated.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import json
import time

from metta import MeTTa, S, remote

m = MeTTa().space()
m.add(S.users(1, "Ada"), S.users(2, "Bob"))
server = remote.serve(m, spaces=[m.name])
print(json.dumps({"url": server.url, "space": m.name}), flush=True)
while True:
    time.sleep(3600)
