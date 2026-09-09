% Purpose: query space counts and retire definition reflections.
% Assumes: loaded through _binding/shim.pl in its host module.

%Bulk cleanup of the reflection facts describing one space: every
%(defined <Space> _) atom in &metta goes through the engine's own removal
%funnel (hooks fire per fact), but in ONE crossing from Python; the
%per-fact crossing measured 10,000 calls and 64ms for 10,000 defines.
metta_py_reflect_clear_defined(SpaceName) :-
    ( atom(SpaceName) -> S = SpaceName ; atom_string(S, SpaceName) ),
    metta_host_clear_defined(S).

metta_py_count(Space, Count) :-
    aggregate_all(count, 'get-atoms'(Space, _), Count).

metta_py_space_names(Names) :-
    metta_space_names(Names).
