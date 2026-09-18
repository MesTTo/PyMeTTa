% Purpose: announce catalog limit changes across native transaction boundaries.
% Assumes: _binding/shim.pl imports metta_py_mirror_bounds/0.
% Guarantees: transaction helpers remain private to metta_python_bounds
% [tested: test_native_configuration_helpers_stay_out_of_the_host_namespace;
% commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
% Native watches preserve outer suspension and safe engine destruction
% [tested: test_bound_watches_transfer_until_outer_completion; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
% Owns resources: one process listener and per-engine live-frame markers; outer completion retires each marker
% [source: extensions/python/metta/_binding/bounds.pl:metta_py_bound_frame_finished/1; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
% Guarded by: nothing of its own; the process listener is installed through the
%   engine's metta_listen/2, whose once-only claim is atomic and which holds no
%   mutex while registering.

:- module(metta_python_bounds, [metta_py_mirror_bounds/0]).
:- use_module(library(janus), [py_call/2]).
:- use_module(library(error), [existence_error/2]).
:- include('provides_host_metta_python_bounds.pl').

%The seat MIRRORS the `(limit <name> <value>)` bounds it reads, because a
%cursor reads its chunk cap when it opens and asking the catalog per read
%cost 21 inferences and 3.2 microseconds of the 35 a one-answer match takes
%[measured 2026-09-08;
%command=python extensions/python/benchmarks/probes/bound_row_cost.py --read;
%fixture=a 50-atom space, 20,000 matches per arm, min of five]. A mirror is only
%correct if the write says so, and `!(add-atom &metta (limit chunk-cap 8))`
%is a write this side never sees, so the engine announces it. The
%seam:catalog_row_changed/2 clause in provides/event.pl and
%metta_py_mirror_bounds/0 below couple that event to metta._catalog.bounds,
%which holds the mirror and decides what a changed row means.

% A foreign mirror is not transactional storage. Suspend its shared fills
% only while a transaction has actually changed a bound, and invalidate it
% after its outer native frame commits or rolls back. Nested frames remain
% inside the suspension. SWI holds a channel's event-list lock while calling
% its listeners; a listener must not remove itself from that list, and nothing
% may hold a mutex while registering on it. One process listener is installed
% through the engine's door on the first transactional bound write, and each
% writer owns its non-backtrackable live-frame marker. Watch the nearest
% transaction and transfer to its remaining owner when it finishes. Walking
% above it marks the engine's outer query frame for an unsafe notification
% after PL_close_query has closed its foreign frame. A failure callback can
% start on the finishing frame, so exclude that ID while finding the next.
% This follows spaces:metta_receipt_watch_transaction/2 and
% spaces:metta_receipt_nearest_frame/3, and SWI's frame_finished:
% https://github.com/SWI-Prolog/swipl-devel/blob/fc7ef84b949378b729052c3ade79c90ce5416abb/src/pl-transaction.c
% https://github.com/SWI-Prolog/swipl-devel/blob/fc7ef84b949378b729052c3ade79c90ce5416abb/src/pl-event.c#L412-L467
% https://github.com/SWI-Prolog/swipl-devel/blob/V10.1.13/src/pl-wam.c#L902-L916
% [tested: test_bound_watches_transfer_until_outer_completion; commit=8358dfc233bf299bb23eceddd94593a62372fe4b].
metta_py_bound_transaction :-
    ( nb_current('$metta_bound_transaction', _) -> true
    ; metta_py_bound_watch_transaction(none),
      metta_py_bound_listener,
      py_call('metta._catalog.bounds':bound_transaction_started(), _) ).

% The mirror watches the nearest live transaction frame and transfers to the
% enclosing one when that frame finishes, so only the outermost completion
% retires it; a nearest-only watch would release the mirror at inner
% completion and admit a stale fill before an outer rollback.
metta_py_bound_watch_transaction(Finished) :-
    prolog_current_frame(Current),
    metta_py_bound_nearest_frame(Current, Finished, Frame),
    ( Frame == none -> existence_error(transaction_frame, Current) ; true ),
    nb_setval('$metta_bound_transaction', Frame).

metta_py_bound_listener :-
    metta_host_listeners:metta_listen(frame_finished,
                                      metta_python_bounds:metta_py_bound_frame_finished).

metta_py_bound_nearest_frame(Current, Finished, Nearest) :-
    prolog_frame_attribute(Current, predicate_indicator, Predicate),
    ( Current \== Finished,
      % policy-inventory-exempt: mechanism-internal; reason=SWI native transaction and snapshot frames watched for bounds rollback; evidence=extensions/python/metta/_binding/bounds.pl:metta_py_bound_nearest_frame/3
      memberchk(Predicate, [system:'$transaction'/2, system:'$transaction'/3,
                           system:'$snapshot'/1])
    -> Nearest = Current
    ; prolog_frame_attribute(Current, parent, Parent)
    -> metta_py_bound_nearest_frame(Parent, Finished, Nearest)
    ; Nearest = none ).

metta_py_bound_frame_finished(Frame) :-
    ( nb_current('$metta_bound_transaction', Frame)
    -> ( current_transaction(_)
       -> metta_py_bound_watch_transaction(Frame)
       ; nb_delete('$metta_bound_transaction'),
         py_call('metta._catalog.bounds':bound_transaction_finished(), _) )
    ; true ).

%Turn the announcement on. Called once per engine by the seat's own boot,
%beside the write that publishes the rows, so an engine whose host never
%loads this file is not announcing to anybody.
metta_py_mirror_bounds :-
    spaces:watch_catalog_rows(limit).
