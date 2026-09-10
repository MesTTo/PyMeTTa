% Purpose: reflect host object protocol types.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Protocol types for host objects %%%%%%%%%%
%
% The engine asks seam:grounded_extra_type/2 for names beyond an object's own
% classes; the answer comes from the Python-side protocol registry, so a
% library teaches typing without touching Prolog.


metta_py_protocol_type(Candidate, Type) :-
    ( is_list(Candidate)
    -> metta_py_decode_shared(Candidate, Type, _)
    ; Type = Candidate ).

%(context-space) lives in the engine now (engine/metta.pl); the shim keeps
%nothing to add for it.

%%%%%%%%%% Retranslation on late definitions %%%%%%%%%%
%
% The engine decides call-against-data per equation at compile time, so a
% body mentioning a name that only becomes a function later stays data: the
% classic case is (= (f) (g)) in one run and (= (g) 5) in the next, and the
% Python case is an operation registered after equations that call it.
% The dependent-recompile that used to ride here as clauses of the
% seam:function_changed/1 and seam:function_removed/1 EVENTS is the
% engine's own now (announce_function_changed/2 and announce_function_removed/1 in
% engine/spaces.pl): an event observer must be optional, and an engine without
% this host in the process has to repair its own compiled code. The
% invalidation was already the engine's, threaded with the module each write
% goes to, which is the only place that knows it
%[tested: specializer_invalidation:writing_in_one_space_leaves_another_alone,
%test_adding_in_one_space_never_removes_atoms_from_another].
