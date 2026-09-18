% Purpose: retain native values behind numeric host handles.
% Assumes: loaded through _binding/surface.pl, the engine audience, so the
%   grounded call's wire crossing can keep a blob alive without the host shim;
%   the shim includes it itself when it is loaded alone.
% Owns resources: metta_py_handle_store/2 references until metta_py_handle_release/1 retracts them
% [source: extensions/python/metta/_binding/handles.pl:21; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].

%%%%%%%%%% Native handles %%%%%%%%%%
%
%The registry that keeps a blob alive while Python holds its reference.
%A dynamic clause referencing the blob is what pins it: SWI's atom
%garbage collector respects clause references, so the blob lives exactly
%as long as its registry entry and release is one retract. Each crossing
%issues a fresh id (two crossings of one blob resolve to the same blob
%either way); flag/3 makes the counter atomic across threads.

:- dynamic metta_py_handle_store/2.

metta_py_handle_keep(Blob, Id) :-
    flag(metta_py_handle_counter, Id, Id + 1),
    assertz(metta_py_handle_store(Id, Blob)).

metta_py_handle_release(Id) :-
    retractall(metta_py_handle_store(Id, _)).
