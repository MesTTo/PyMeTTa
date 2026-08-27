% This seat's control file: facts the engine READS and never consults, the
% PostgreSQL control-file model the runtime import scan already follows. The
% engine's loader (engine/metta.pl) checks every needs/1 and loads every
% entry(engine, _) only when all of them hold; an unmet need is recorded and
% queryable rather than a silent branch.
%
% library(janus) is SWI's own Python bridge, and its absence (the WASM build, a
% stripped install) means this host cannot exist rather than that anything is
% wrong: a tree without it loads nothing and says nothing, and a tree with it
% loads a bridge that raises if it is broken. Not present is not an error;
% half present is.

title('MeTTa in Python: the janus bridge and the metta library''s transport').
needs(prolog_library(janus)).

% The two directions under their own roles, which is what dissolves this seat's
% bridge/shim naming: entry(engine, ...) is the ENGINE reaching Python (py-atom
% resolves, py-call applies; consulted here at boot), and entry(host, ...) is
% Python reaching the ENGINE (the metta library's transport, consulted by
% _engine.py when the library boots -- the engine's loader records it and never
% loads it).
entry(engine, 'bridge.pl').
entry(host, 'metta/shim.pl').
