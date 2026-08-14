% Purpose: adapt the legacy Python class to the runtime's file and string
% entry points while keeping verbosity scoped to one call.
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
    retractall(silent(_)),
    assertz(silent(Value)).

helper_restore_silent(none) :- !, retractall(silent(_)).
helper_restore_silent(some(Value)) :-
    retractall(silent(_)),
    assertz(silent(Value)).

run_metta_helper(Verbose, Predicate, Arg, ResultsR) :-
    with_mutex(petta_helper_state,
        setup_call_cleanup(
            helper_set_silent(Verbose, Previous),
            ( call(Predicate, Arg, Results),
              maplist(swrite, Results, ResultsR) ),
            helper_restore_silent(Previous))).
