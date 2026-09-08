% Purpose: replace the Python door catalog as one rollback-safe snapshot.
% Assumes: metta_py_add/2 and metta_py_remove_many/3 are loaded by shim.pl.
% Guarantees: repeated publication is idempotent and a refused replacement
%   preserves the prior snapshot [tested:
%   test_door_catalog_publication_is_atomic_and_idempotent; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
% Owns resources: metta_py_door_snapshot/1 retains the last published wire
%   values until replacement or engine shutdown.
% Guarded by: '$metta_py_door_catalog' serializes publication. metta_transaction/1
%   rolls the stored atoms and snapshot back together [tested:
%   test_door_catalog_publication_is_atomic_and_idempotent; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].

:- dynamic metta_py_door_snapshot/1.

metta_py_publish_doors(Wires, Count) :-
    with_mutex('$metta_py_door_catalog',
        metta_transaction(metta_py_replace_doors(Wires, Count))).

metta_py_replace_doors(Wires, Count) :-
    (   metta_py_door_snapshot(Previous), Previous == Wires
    ->  Count = 0
    ;   ( retract(metta_py_door_snapshot(Old)) -> true ; Old = [] ),
        reverse(Old, Retired),
        metta_py_remove_many('&metta', Retired, Removed),
        % Vocabulary and kind rows have declaration-order dependencies.
        % One host crossing still carries every row; the ordinary add door
        % makes each declaration visible before checking its consumers.
        maplist(metta_py_add('&metta'), Wires),
        assertz(metta_py_door_snapshot(Wires)),
        length(Wires, Added),
        Count is Removed + Added
    ).
