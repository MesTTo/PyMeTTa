% Purpose: manage atom and committed-segment subscriptions.
% Assumes: loaded through _binding/shim.pl in its host module.
% Owns resources: subscription and segment hook references while consumers remain registered
% [source: extensions/python/metta/_binding/subscriptions.pl:60, metta_py_segments/1; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
% Guarded by: $metta_py_subscriptions serializes hook and consumer changes.

%%%%%%%%%% Subscriptions %%%%%%%%%%
%
% Standing queries: when Python has subscribers, every committed space write
% crosses to metta_ops for pattern matching and callbacks. An unscoped write
% crosses immediately; a transaction's segment crosses after commit, and a
% discarded segment never crosses. The hook clauses exist only while at least
% one space is watched.
% Their guard is one dynamic fact per subscribed space, first-arg indexed, so
% an unwatched space never crosses to Python while another space is watched.


:- dynamic metta_py_subscribed_space/1.
:- dynamic metta_py_subscription_hook_ref/2.

metta_py_notify_atom_added(Space, Term) :-
    atom(Space),
    metta_py_subscribed_space(Space),
    metta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    metta_py_future_answer_sequence(Space, Sequence),
    py_call(metta_ops:atom_added(SpaceStr, W, Sequence), _).

metta_py_future_answer_sequence(Space, Sequence) :-
    nb_current('$metta_future_answer_sequence', future(Space, Sequence)), !.
metta_py_future_answer_sequence(_, -1).

metta_py_notify_atom_removed(Space, Term) :-
    atom(Space),
    metta_py_subscribed_space(Space),
    metta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(metta_ops:atom_removed(SpaceStr, W), _).

metta_py_install_subscription_hook(Kind) :-
    metta_py_subscription_hook_ref(Kind, Ref),
    \+ clause_property(Ref, erased), !.
metta_py_install_subscription_hook(added) :-
    retractall(metta_py_subscription_hook_ref(added, _)),
    metta_py_provided_clause(atom_added, Clause),
    assertz(Clause, Ref),
    assertz(metta_py_subscription_hook_ref(added, Ref)).
metta_py_install_subscription_hook(removed) :-
    retractall(metta_py_subscription_hook_ref(removed, _)),
    metta_py_provided_clause(atom_removed, Clause),
    assertz(Clause, Ref),
    assertz(metta_py_subscription_hook_ref(removed, Ref)).

metta_py_remove_subscription_hooks :-
    forall(retract(metta_py_subscription_hook_ref(_, Ref)),
           ( clause_property(Ref, erased) -> true ; erase(Ref) )).


metta_py_subscriptions(Spaces) :-
    maplist(atom_string, SpaceAtoms, Spaces),
    with_mutex('$metta_py_subscriptions',
               metta_py_subscriptions_locked(SpaceAtoms)).

metta_py_subscriptions_locked(SpaceAtoms) :-
    retractall(metta_py_subscribed_space(_)),
    forall(member(Space, SpaceAtoms),
           assertz(metta_py_subscribed_space(Space))),
    ( SpaceAtoms == []
      -> metta_py_remove_subscription_hooks
    ; metta_py_install_subscription_hook(added),
      metta_py_install_subscription_hook(removed) ).

%%%%%%%%%% Committed-segment boundaries %%%%%%%%%%
%
% The boundary of one commit, crossed once after its atom events. A Python
% consumer that maintains a derived answer (metta.live.Live) re-answers
% here rather than per event, because the whole diff is already committed when
% the first event arrives. The clause exists only while some consumer asked for
% boundaries, so a program that uses subscriptions alone never crosses here,
% and the crossing itself is guarded on the segment having touched a WATCHED
% space, so writes into an unwatched one cost the guard and no crossing.


:- dynamic metta_py_segment_hook_ref/1.

metta_py_notify_segment_committed(Spaces) :-
    (   member(Space, Spaces),
        metta_py_subscribed_space(Space)
    ->  py_call(metta_ops:segment_committed(), _)
    ;   true
    ).

metta_py_install_segment_hook :-
    metta_py_segment_hook_ref(Ref),
    \+ clause_property(Ref, erased), !.
metta_py_install_segment_hook :-
    retractall(metta_py_segment_hook_ref(_)),
    metta_py_provided_clause(segment_committed, Clause),
    assertz(Clause, Ref),
    assertz(metta_py_segment_hook_ref(Ref)).

metta_py_remove_segment_hook :-
    forall(retract(metta_py_segment_hook_ref(Ref)),
           ( clause_property(Ref, erased) -> true ; erase(Ref) )).

%A Python bool crosses as @(true) / @(false), janus's own convention for the
%three values Prolog has no atom for [source: extensions/python/metta/_binding/json.pl:42,
%metta_py_json_options/1 and the capture flag at metta_py_run_options/2; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
metta_py_segments(Enabled) :-
    with_mutex('$metta_py_subscriptions',
               ( Enabled == @(true)
                 -> metta_py_install_segment_hook
                 ;  metta_py_remove_segment_hook )).
