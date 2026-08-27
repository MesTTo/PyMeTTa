% Purpose: adapt the legacy Python class to the runtime's file and string
% entry points while keeping verbosity scoped to one call.
% Assumes: the engine is consulted, so its metta_host_set_silent/1 is the
%   writer here. This file used to spell the retract-then-assert itself, which
%   was one of the copies that door was published to end.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

helper_silent_value(true, false) :- !.
helper_silent_value(false, true).

helper_previous_silent(some(Value)) :- once(silent(Value)), !.
helper_previous_silent(none).

helper_set_silent(Verbose, Previous) :-
    helper_previous_silent(Previous),
    helper_silent_value(Verbose, Value),
    metta_host_set_silent(Value).

%The `none` branch is the one thing the door does not offer, leaving silent/1
%with no clause at all. It is reachable only before the load-time directive in
%engine/filereader.pl has run, which is why the door has no spelling for it.
helper_restore_silent(none) :- !, retractall(silent(_)).
helper_restore_silent(some(Value)) :- metta_host_set_silent(Value).

run_metta_helper(Verbose, Predicate, Arg, ResultsR) :-
    with_mutex(petta_helper_state,
        setup_call_cleanup(
            helper_set_silent(Verbose, Previous),
            ( call(Predicate, Arg, Results),
              maplist(swrite, Results, ResultsR) ),
            helper_restore_silent(Previous))).
