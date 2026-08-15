% Purpose: the reduction trace. metta_trace_source/3 runs MeTTa source
%   with every compiled MeTTa function wrapped by SWI's own
%   wrap_predicate, recording a call event with the input term and an
%   exit event with the answer per reduction, depth-nested through the
%   call tree, then unwraps whole, so tracing costs nothing when off. A
%   reduction that fails leaves its call without an exit, which is what
%   failing looks like. Events answer as event/5 terms carrying the term
%   itself, depth, kind, term, answer, and the names of the term's
%   variables.
% Guarantees:
%   - Functions defined by the traced source and calls from hyperpose workers
%     produce events [tested 2026-08-14: tracer].
%   - A symbol whose spelling reads back as something else survives the
%     trip: the trace and run answer the same atom
%     [tested 2026-08-15: tracer:a_symbol_that_looks_like_a_variable_stays_a_symbol].
%   - Traced get-type extensions report their public function name
%     [tested 2026-08-15: tracer:type_extensions_keep_the_public_name].
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
    arity(LogicalF, A),
    ( fun_in(Module, LogicalF) ; Module = user ),
    compiled_function_name(LogicalF, F),
    current_predicate(Module:F/A),
    functor(Head, F, A),
    \+ predicate_property(Module:Head, imported_from(_)),
    once(( clause(Module:Head, _, Ref),
           clause_property(Ref, module(Module)),
           translated_from(Ref, _) )).

metta_trace_wrap(Module:F/A) :-
    functor(Head, F, A),
    compiled_function_name(LogicalF, F),
    In is A - 1,
    wrap_predicate(Module:Head, petta_tracer, Closure,
                   metta_trace_call(LogicalF, In, Head, Closure)).

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
                 -> compiled_function_name(F, Predicate),
                    findall(Target,
                            ( metta_trace_target(Target),
                              Target = _Module:Predicate/_Arity ),
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

%An event carries the term, not the term's text. Written with swrite and
%read back by the receiver, every symbol whose spelling reads as something
%else changed on the way: a stored (holds $notvar) traced as a variable
%while run answered the symbol, a semicolon truncated the rest of the term
%at the comment it starts, and a tab inside a symbol split the record into
%the wrong fields altogether. Variables are named by first occurrence,
%which is the one thing the text form did that a reader wants kept.
metta_trace_record(Depth, Kind, Term, Answer) :-
    copy_term(Term-Answer, TermCopy-AnswerCopy),
    term_variables(TermCopy-AnswerCopy, Variables),
    metta_trace_variable_names(Variables, 0, Names),
    Event = event(Depth, Kind, TermCopy, AnswerCopy, Names),
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

%_0, _1 and so on, by first occurrence, which is the naming swrite applied
%when an event crossed as text. The pairs travel with the term, so a
%receiver that encodes variables by name reads the same spelling; the
%leading $ belongs to the spelling of a variable, not to its name.
metta_trace_variable_names([], _, []).
metta_trace_variable_names([Variable|Rest], Index, [Name-Variable|Names]) :-
    atom_concat('_', Index, Name),
    Next is Index + 1,
    metta_trace_variable_names(Rest, Next, Names).

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
%three-argument form carries the default bound. Each event is
%event(Depth, Kind, Term, Answer, VariableNames), Answer being '' on a
%call, and VariableNames pairing $_0, $_1 with the term's variables.
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
