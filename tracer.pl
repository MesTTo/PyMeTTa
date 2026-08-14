% Purpose: the reduction trace. metta_trace_source/3 runs MeTTa source
%   with every compiled MeTTa function wrapped by SWI's own
%   wrap_predicate, recording a call event with the input term and an
%   exit event with the answer per reduction, depth-nested through the
%   call tree, then unwraps whole, so tracing costs nothing when off. A
%   reduction that fails leaves its call without an exit, which is what
%   failing looks like. Events answer as tab-separated strings, depth,
%   kind, the term's text, and the answer's text, everything written by
%   the engine's own swrite so any reader parses it back.
% Guarantees:
%   - Functions defined by the traced source and calls from hyperpose workers
%     produce events [tested 2026-08-14: tracer].
% Owns:
%   - metta_trace_source/4 removes every petta_tracer wrapper and state fact,
%     including after an event-limit error [tested 2026-08-14:
%     tracer:event_limit_error_removes_every_wrapper].
% Guarded by:
%   - '$petta_trace_state' serializes trace sessions and wrapper changes
%     [tested 2026-08-14: tracer:event_limit_error_removes_every_wrapper].
%   - '$petta_trace_events' assigns event sequence numbers and enforces the
%     event bound across hyperpose worker threads [tested 2026-08-14: tracer].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- dynamic metta_trace_event/2.
:- dynamic metta_trace_limit/1.
:- dynamic metta_trace_next_seq/1.
:- dynamic metta_trace_session/0.
:- dynamic metta_trace_wrapped/1.

%Every name the translator compiled from equations, in user and in each
%space module that registered it: exactly the predicates owning at least
%one translated_from-tracked clause. Builtins and imports never do,
%which keeps a trace about the program, not the engine, and keeps the
%wrap away from library predicates a weak import makes visible.
metta_trace_target(Module:F/A) :-
    arity(F, A),
    ( fun_in(Module, F) ; Module = user ),
    current_predicate(Module:F/A),
    functor(Head, F, A),
    \+ predicate_property(Module:Head, imported_from(_)),
    once(( clause(Module:Head, _, Ref),
           clause_property(Ref, module(Module)),
           translated_from(Ref, _) )).

metta_trace_wrap(Module:F/A) :-
    functor(Head, F, A),
    In is A - 1,
    wrap_predicate(Module:Head, petta_tracer, Closure,
                   metta_trace_call(F, In, Head, Closure)).

metta_trace_unwrap(Module:F/A) :-
    catch(unwrap_predicate(Module:F/A, petta_tracer), _, true).

metta_trace_wrap_once(Target) :-
    ( metta_trace_wrapped(Target) -> true
    ; metta_trace_wrap(Target),
      assertz(metta_trace_wrapped(Target)) ).

%A function compiled while a trace is active must be wrapped before the next
%form runs. process_form/3 fires this hook after installing every equation.
:- multifile metta_on_function_changed/1.
metta_on_function_changed(F) :-
    with_mutex('$petta_trace_state',
               ( metta_trace_session
                 -> findall(Target,
                            ( metta_trace_target(Target),
                              Target = _Module:F/_Arity ),
                            Targets0),
                    sort(Targets0, Targets),
                    maplist(metta_trace_wrap_once, Targets)
                 ; true )).

metta_trace_call(F, In, Head, Closure) :-
    Head =.. [_|Args],
    length(InArgs, In),
    append(InArgs, [Out], Args),
    ( nb_current('$petta_trace_depth', D) -> true ; D = 0 ),
    metta_trace_record(D, call, [F|InArgs], ''),
    D1 is D + 1,
    b_setval('$petta_trace_depth', D1),
    call(Closure),
    b_setval('$petta_trace_depth', D),
    metta_trace_record(D, exit, [F|InArgs], Out).

metta_trace_record(Depth, Kind, Term, Answer) :-
    swrite(Term, TermText),
    ( Answer == '' -> AnswerText = ""
    ; swrite(Answer, AnswerText) ),
    format(string(Event), "~w\t~w\t~w\t~w",
           [Depth, Kind, TermText, AnswerText]),
    with_mutex('$petta_trace_events',
               ( metta_trace_next_seq(N),
                 metta_trace_limit(Max),
                 N1 is N + 1,
                 ( N1 > Max
                   -> throw(error(resource_error(petta_trace_events(Max)),
                                  context(metta_trace_record/4,
                                          'the trace hit its max_events bound')))
                 ; retractall(metta_trace_next_seq(_)),
                   assertz(metta_trace_next_seq(N1)),
                   assertz(metta_trace_event(N, Event)) ) )).

metta_trace_begin(Max) :-
    with_mutex('$petta_trace_state', metta_trace_begin_unlocked(Max)).

metta_trace_begin_unlocked(Max) :-
    ( metta_trace_session
      -> throw(error(permission_error(trace, evaluation, nested),
                     context(metta_trace_source/3,
                             'a trace is already running')))
    ; retractall(metta_trace_event(_, _)),
      retractall(metta_trace_limit(_)),
      retractall(metta_trace_next_seq(_)),
      retractall(metta_trace_wrapped(_)),
      assertz(metta_trace_limit(Max)),
      assertz(metta_trace_next_seq(0)),
      assertz(metta_trace_session),
      catch(( findall(Target, metta_trace_target(Target), Targets0),
              sort(Targets0, Targets),
              maplist(metta_trace_wrap_once, Targets) ),
            Error,
            ( metta_trace_end_unlocked, throw(Error) )) ).

metta_trace_end :-
    with_mutex('$petta_trace_state', metta_trace_end_unlocked).

metta_trace_end_unlocked :-
    findall(Target, metta_trace_wrapped(Target), Targets),
    maplist(metta_trace_unwrap, Targets),
    retractall(metta_trace_wrapped(_)),
    retractall(metta_trace_session),
    retractall(metta_trace_limit(_)),
    retractall(metta_trace_next_seq(_)),
    retractall(metta_trace_event(_, _)).

%Run Source in Space with the trace armed; Events come back oldest
%first, at most Max of them: past the bound the trace throws instead of
%accumulating without limit, since a long run's trace is data too. The
%three-argument form carries the default bound.
metta_trace_source(Source, Space, Events) :-
    metta_trace_source(Source, Space, 1000000, Events).

metta_trace_source(Source, Space, Max, Events) :-
    ( integer(Max), Max > 0 -> true
    ; throw(error(domain_error(positive_integer, Max),
                  context(metta_trace_source/4, 'max_events bound')))),
    setup_call_cleanup(
        metta_trace_begin(Max),
        ( b_setval('$petta_trace_depth', 0),
          process_metta_string(Source, _Results, Space),
          with_mutex('$petta_trace_events',
                     findall(N-E, metta_trace_event(N, E), Pairs)),
          keysort(Pairs, Sorted),
          pairs_values(Sorted, Events) ),
        metta_trace_end).
