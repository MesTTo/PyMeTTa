% Purpose: announce catalog limit changes across native transaction boundaries.
% Assumes: _binding/shim.pl imports metta_py_mirror_bounds/0.
% Guarantees: transaction helpers remain private to metta_python_bounds
% [tested: test_native_configuration_helpers_stay_out_of_the_host_namespace;
% commit=WORKTREE].
% Owns resources: one process listener and per-thread outer-frame markers; frame completion retires each marker
% [source: extensions/python/metta/_binding/bounds.pl:66; commit=WORKTREE].
% Guarded by: $metta_bound_listener serializes process listener installation.

:- module(metta_python_bounds, [metta_py_mirror_bounds/0]).
:- use_module(library(janus), [py_call/2]).

%The seat MIRRORS the `(limit <name> <value>)` bounds it reads, because a
%cursor reads its chunk cap when it opens and asking the catalog per read
%cost 21 inferences and 3.2 microseconds of the 35 a one-answer match takes
%[measured 2026-09-08;
%command=python extensions/python/benchmarks/probes/bound_row_cost.py --read;
%fixture=a 50-atom space, 20,000 matches per arm, min of five]. A mirror is only
%correct if the write says so, and `!(add-atom &metta (limit chunk-cap 8))`
%is a write this side never sees, so the engine announces it. This clause and
%the door below are the whole of that coupling; metta._catalog.bounds holds the
%mirror and decides what a changed row means.
:- multifile seam:catalog_row_changed/2.
seam:catalog_row_changed(_Event, [limit, Name|_]) :-
    ( current_transaction(_) -> metta_py_bound_transaction ; true ),
    py_call('metta._catalog.bounds':bound_row_changed(Name), _).

% A foreign mirror is not transactional storage. Suspend its shared fills
% only while a transaction has actually changed a bound, and invalidate it
% after its outer native frame commits or rolls back. Nested frames remain
% inside the suspension. SWI holds its global event-list lock while calling
% listeners; a listener must not remove itself from that list. One process
% listener is installed on the first transactional bound write, and each
% writer owns only its non-backtrackable outer-frame marker.
% This follows spaces:metta_receipt_outer_frame/3 and SWI's frame_finished:
% https://github.com/SWI-Prolog/swipl-devel/blob/fc7ef84b949378b729052c3ade79c90ce5416abb/src/pl-transaction.c
% https://github.com/SWI-Prolog/swipl-devel/blob/fc7ef84b949378b729052c3ade79c90ce5416abb/src/pl-event.c#L412-L467
% [tested: test_configuration_rows_and_mirror_follow_outer_rollback;
% commit=WORKTREE].
metta_py_bound_transaction :-
    ( nb_current('$metta_bound_transaction', _) -> true
    ; prolog_current_frame(Current),
      metta_py_bound_outer_frame(Current, none, Frame),
      ( Frame == none -> existence_error(transaction_frame, Current) ; true ),
      nb_setval('$metta_bound_transaction', Frame),
      metta_py_bound_listener,
      py_call('metta._catalog.bounds':bound_transaction_started(), _) ).

metta_py_bound_listener :-
    with_mutex('$metta_bound_listener',
        ( flag('$metta_bound_listener_ready', Ready, Ready),
          ( Ready == 1 -> true
          ; prolog_listen(frame_finished, metta_python_bounds:metta_py_bound_frame_finished,
                          [name(metta_bound_transaction)]),
            flag('$metta_bound_listener_ready', _, 1) ) )).

metta_py_bound_outer_frame(Frame, Prior, Outer) :-
    prolog_frame_attribute(Frame, predicate_indicator, Predicate),
    % policy-inventory-exempt: mechanism-internal; reason=SWI native transaction frames in pl-transaction.c at the cited commit; evidence=metta_py_bound_outer_frame/3
    ( memberchk(Predicate, [system:'$transaction'/2, system:'$transaction'/3,
                           system:'$snapshot'/1]) -> Found = Frame ; Found = Prior ),
    ( prolog_frame_attribute(Frame, parent, Parent)
    -> metta_py_bound_outer_frame(Parent, Found, Outer)
    ; Outer = Found ).

metta_py_bound_frame_finished(Frame) :-
    ( nb_current('$metta_bound_transaction', Frame)
    -> nb_delete('$metta_bound_transaction'),
       py_call('metta._catalog.bounds':bound_transaction_finished(), _)
    ; true ).

%Turn the announcement on. Called once per engine by the seat's own boot,
%beside the write that publishes the rows, so an engine whose host never
%loads this file is not announcing to anybody.
metta_py_mirror_bounds :-
    spaces:watch_catalog_rows(limit).
