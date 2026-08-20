% Purpose: tell the engine where the Python host lives and when it is usable.
%   This file is the whole of what the engine knows about Python, and it is
%   not in the engine.
% Assumes:
%   - library(janus) is SWI's own Python bridge, and its absence (the WASM
%     build, a stripped install) means this host cannot exist rather than
%     that anything is wrong.
% Guarantees:
%   - a tree without janus loads this file and nothing happens
%   - a tree with it loads the bridge.pl beside this file, which raises if the
%     bridge is broken, the split every host wants: not present is not an
%     error, half present is.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- prolog_load_context(directory, Dir),
   (   exists_source(library(janus))
   ->  directory_file_path(Dir, 'bridge.pl', Bridge),
       ensure_loaded(Bridge)
   ;   true
   ).
