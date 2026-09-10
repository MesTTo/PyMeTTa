% Purpose: compile the evaluation option policy into host-owned clauses.
% Assumes: options.pl supplies records and numeric presets from Door.Binding.
% Guarantees: presets and general records use the same collection and scope
% templates; expansion never evaluates program goals or traverses program data
% [tested: test_evaluation_presets_and_records_share_one_policy;
% commit=WORKTREE].
% Decides: only declared presets are specialized; dynamic collections retain
% indexed clauses rather than generating the product of all option values
% [source: extensions/python/metta/_binding/evaluation_policy.pl:binding_evaluation_expansion/2;
% commit=WORKTREE].

:- module(metta_python_evaluation, [binding_evaluation_expansion/2]).
:- use_module(library(lists), [append/3]).
:- use_module('options.pl', [binding_options_expansion/2, evaluation_preset/2]).

% SWI 10.1.13's program-transformation contract uses an imported sentinel to
% scope expansion. Each fresh clause owns its variables; no caller clause is
% unfolded or instantiated. The marker also gives reconsult one source owner.
% https://www.swi-prolog.org/pldoc/man?section=progtransform
binding_evaluation_expansion(binding_evaluation, Clauses) :-
    findall((metta_py_evaluate(Id, Space, Target, Result) :- !, Body),
            ( evaluation_preset(Id, Options),
              evaluation_clause(metta_py_evaluate(Options, Space, Target, Result), Raw),
              evaluation_fold(Raw, Body) ), Presets),
    findall((Head :- Body),
            ( evaluation_clause(Head, Raw), evaluation_fold(Raw, Body) ), General),
    append(Presets, General, Clauses).

:- multifile system:term_expansion/2.
system:term_expansion(binding_evaluation, Clauses) :-
    prolog_load_context(module, Module),
    Module \== metta_python_evaluation,
    predicate_property(Module:binding_evaluation_expansion(_, _),
                       imported_from(metta_python_evaluation)),
    binding_evaluation_expansion(binding_evaluation, Clauses).

evaluation_clause(metta_py_evaluate(Options, Space, Target, Result), Goal) :-
    metta_py_options(Options, [answers(Collection), seconds(Time), inferences(Inf)]),
    evaluation_clause(metta_py_evaluation_accounted(Options, Space, Target, Result), Accounted),
    Goal = ((Collection == cursor ; Time == none, Inf == none)
            -> Accounted
            ; metta_py_option_limits(Time, Inf, Seconds, Inferences),
              metta_py_guarded(Seconds, Inferences,
                  metta_py_evaluation_accounted(Options, Space, Target, Result))).

evaluation_clause(metta_py_evaluation_accounted(Options, Space, Target, Result), Goal) :-
    metta_py_options(Options, [answers(Collection), accounting(Accounting), under(Under)]),
    ( Accounting == false -> Values = Result ; true ),
    evaluation_work(Options, Space, Target, Values, Work),
    Scoped = ((Under == none ; Collection == cursor)
              -> Work
              ; Under = [Algebra, Limit, Direction],
                metta_with_evaluation_context(evaluation_context(Algebra, Limit, Direction), Work)),
    Goal = (Accounting == true
            -> metta_py_work(Before), Scoped, metta_py_work(After),
               Used is After - Before, Result = [Values, Used]
            ; Scoped, Result = Values).

evaluation_clause(metta_py_collect(one, Options, Space, Term, _, Encoded), Goal) :-
    metta_py_options(Options, [fuel(Fuel)]),
    Goal = metta_py_produce(wire, Fuel, Space, Term, Encoded).
evaluation_clause(metta_py_collect(all, Options, Space, Term, _, Encoded), Goal) :-
    metta_py_options(Options, [fuel(Fuel), unmatched(Unmatched)]),
    Goal = (findall(E, metta_py_produce(wire, Fuel, Space, Term, E), Answers),
            (Answers == [], Unmatched == true, metta_py_preserve_unmatched(Space, Term, Original)
             -> Encoded = [Original] ; Encoded = Answers)).
evaluation_clause(metta_py_collect(count, Options, Space, Term, _, Answer), Goal) :-
    metta_py_options(Options, [fuel(Fuel), repeatable(Repeatable)]),
    Goal = (Repeatable == true, \+ metta_py_repeatable(Space, Term)
            -> Answer = []
            ; aggregate_all(count, metta_py_produce(raw, Fuel, Space, Term, _), Count),
              (Repeatable == true -> Answer = [Count] ; Answer = Count)).
evaluation_clause(metta_py_collect(retained, Options, Space, Term, Bindings,
                                  [Count, prolog(Engine)]), Goal) :-
    metta_py_options(Options, [fuel(Fuel), columns(VarNames)]),
    Replay = (statistics(inferences, Before), member(Value-HeldRow, Bag),
              metta_py_retained_encoded(Value, Encoded),
              statistics(inferences, Now), Used is Now - Before),
    Goal = (findall(Held-Row, (metta_py_produce(raw, Fuel, Space, Term, Held),
                             metta_py_row(VarNames, Bindings, Row)), Bag),
            length(Bag, Count), metta_host_hold([Encoded, HeldRow, Used], Replay, Engine)).
evaluation_clause(metta_py_collect(status, Options, Space, Term, _, Results), Goal) :-
    metta_py_options(Options, [fuel(Fuel)]),
    Goal = (metta_py_module(Space, Module), metta_py_classify(Module, Term, Status),
            findall([Status, E], metta_py_produce(wire, Fuel, Space, Term, E), Answers),
            (Answers == []
             -> (Status == 'not-reducible', metta_py_preserve_unmatched(Space, Term, Original)
                 -> Results = [[Status, Original]] ; Results = [[empty, none]])
             ; Results = Answers)).
evaluation_clause(metta_py_collect(cursor, Options, Space, Term, Bindings, prolog(Engine)), Goal) :-
    metta_py_options(Options,
        [fuel(Fuel), columns(VarNames), seconds(Time), inferences(Quota),
         under(Under), policy(Policy)]),
    Values = (metta_py_produce(wire, Fuel, Space, Term, Encoded),
              metta_py_row(VarNames, Bindings, Row)),
    Goal = (metta_py_option_limits(Time, Quota, TimeS, Inf),
            (Under == none
             -> Held = (statistics(inferences, Before), Values,
                        statistics(inferences, Now), Used is Now - Before),
                Template = [Encoded, Row, Used]
             ; Under = [Algebra, Limit, Direction],
               (Direction == none
                -> Core = (statistics(inferences, Before), metta_py_under_query(Space, Values, K),
                           statistics(inferences, Now), Used is Now - Before)
                ; Core = (statistics(inferences, Before),
                          metta_py_ordered_within_time(TimeS, Direction, K0-[Encoded, Row],
                              metta_py_under_query(Space, Values, K0), Ordered),
                          statistics(inferences, Now), Used is Now - Before,
                          member(K-[Encoded, Row], Ordered))),
               Held = (metta_with_evaluation_context(evaluation_context(Algebra, Limit, Direction), Core),
                       metta_py_encode(K, KWire)),
               Template = [Encoded, Row, KWire, Used]),
            metta_host_time_budget(Held, TimeS, Timed), metta_host_inference_budget(Timed, Inf, Bounded),
            metta_py_open_controlled_cursor(Policy, Template, Bounded, Engine)).

evaluation_work(Options, Space, Target, Values, Goal) :-
    metta_py_options(Options, [batch(Batch), answers(Collection)]),
    ( Batch == false -> Item = Target, Values = Group ; true ),
    evaluation_prepare(Options, Space, Item, Term, Bindings, Prepare),
    Head = metta_py_collect(Collection, Options, Space, Term, Bindings, Group),
    ( nonvar(Collection)
    -> evaluation_clause(Head, CollectionBody), evaluation_fold(CollectionBody, Collect)
    ; Collect = Head ),
    Raw = (Batch == true
           -> findall(Group, (member(Item, Target), Prepare, Collect), Values)
           ; Item = Target, Prepare, Collect, Values = Group),
    evaluation_fold(Raw, Goal).

evaluation_prepare(Options, Space, Target, Term, Bindings, Goal) :-
    metta_py_options(Options, [form(Form), using(Pairs)]),
    ( Pairs == [] -> Term0 = Term ; true ),
    Raw = ((Form == term -> Term0 = Target, Bindings = []
            ; metta_py_target_term_bindings(Space, Target, Term0, Bindings)),
           (Pairs == [] -> Term = Term0
            ; maplist(metta_py_using_pair, Pairs, Substitutions),
              metta_host_substitute(Substitutions, Term0, Term))),
    evaluation_fold(Raw, Goal).

% Fold only executable control syntax. In particular, arguments to ordinary
% goals and data inside unifications are never walked or called.
evaluation_fold(In, Out) :-
    ( nonvar(In), In = (If -> Then ; Else)
    -> evaluation_condition(If, Condition),
       ( Condition == true -> evaluation_fold(Then, Out)
       ; Condition == fail -> evaluation_fold(Else, Out)
       ; evaluation_fold(Then, T), evaluation_fold(Else, E), Out = (Condition -> T ; E) )
    ; nonvar(In), In = (A, B)
    -> evaluation_fold(A, X), evaluation_fold(B, Y),
       ( X == true -> Out = Y ; Y == true -> Out = X ; Out = (X, Y) )
    ; Out = In ).

evaluation_condition(In, Out) :-
    ( nonvar(In), In = (A == B), ground(A-B)
    -> ( A == B -> Out = true ; Out = fail )
    ; nonvar(In), In = (A, B)
    -> evaluation_condition(A, X), evaluation_condition(B, Y),
       ( X == fail -> Out = fail ; X == true -> Out = Y
       ; Y == true -> Out = X ; Out = (X, Y) )
    ; nonvar(In), In = (A ; B)
    -> evaluation_condition(A, X), evaluation_condition(B, Y),
       ( X == true -> Out = true ; X == fail -> Out = Y
       ; Y == fail -> Out = X ; Out = (X ; Y) )
    ; Out = In ).
