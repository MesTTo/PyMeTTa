% Purpose: the reduction trace. metta_trace_source/3 runs MeTTa source
%   with every compiled MeTTa function wrapped by SWI's own
%   wrap_predicate, recording a call event with the input term and an
%   exit event with the answer per reduction, depth-nested through the
%   call tree, then unwraps whole, so tracing costs nothing when off. A
%   reduction that fails leaves its call without an exit, which is what
%   failing looks like. Events answer as tab-separated strings, depth,
%   kind, the term's text, and the answer's text, everything written by
%   the engine's own swrite so any reader parses it back.
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- dynamic metta_trace_event/2.

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

metta_trace_call(F, In, Head, Closure) :-
    Head =.. [_|Args],
    length(InArgs, In),
    append(InArgs, [Out], Args),
    b_getval(metta_trace_depth, D),
    metta_trace_record(D, call, [F|InArgs], ''),
    D1 is D + 1,
    b_setval(metta_trace_depth, D1),
    call(Closure),
    b_setval(metta_trace_depth, D),
    metta_trace_record(D, exit, [F|InArgs], Out).

metta_trace_record(Depth, Kind, Term, Answer) :-
    swrite(Term, TermText),
    ( Answer == '' -> AnswerText = ""
    ; swrite(Answer, AnswerText) ),
    format(string(Event), "~w\t~w\t~w\t~w",
           [Depth, Kind, TermText, AnswerText]),
    nb_getval(metta_trace_seq, N),
    N1 is N + 1,
    ( nb_getval(metta_trace_max, Max), N1 > Max
      -> throw(error(resource_error(petta_trace_events(Max)),
                     context(metta_trace_record/4,
                             'the trace hit its max_events bound')))
    ; true ),
    nb_setval(metta_trace_seq, N1),
    assertz(metta_trace_event(N, Event)).

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
    ( nb_current(metta_trace_active, true)
      -> throw(error(permission_error(trace, evaluation, nested),
                     context(metta_trace_source/3,
                             'a trace is already running')))
    ; true ),
    nb_setval(metta_trace_max, Max),
    findall(Target, metta_trace_target(Target), Targets0),
    sort(Targets0, Targets),
    retractall(metta_trace_event(_, _)),
    nb_setval(metta_trace_seq, 0),
    setup_call_cleanup(
        ( nb_setval(metta_trace_active, true),
          maplist(metta_trace_wrap, Targets) ),
        ( b_setval(metta_trace_depth, 0),
          process_metta_string(Source, _Results, Space) ),
        ( maplist(metta_trace_unwrap, Targets),
          nb_setval(metta_trace_active, false) )),
    findall(N-E, metta_trace_event(N, E), Pairs),
    msort(Pairs, Sorted),
    findall(E, member(_-E, Sorted), Events),
    retractall(metta_trace_event(_, _)).
