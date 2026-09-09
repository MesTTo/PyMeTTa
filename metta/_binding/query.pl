% Purpose: match patterns, project queries and explain their plans.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Query %%%%%%%%%%
%
% A query is a list of patterns run as one conjunction through the engine's own
% match/4, its native [','|Patterns] form, so joins are the matcher's joins.
% VarNames selects which variables come back, as one row per answer.

metta_py_query(Space, PatternsTagged, VarNames, Row) :-
    VarNames = [
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _ | _
    ],
    !,
    metta_py_decode_indexed(["e", PatternsTagged], Patterns, Bindings),
    metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments),
    metta_py_match_goal(Segments, Space, PlainPatterns, Goal),
    (   Modifiers == []
    ->  call(Goal)
    ;   call(Goal), metta_py_call_modifiers(Modifiers)
    ),
    metta_py_row(VarNames, Bindings, Row).

metta_py_query(Space, PatternsTagged, VarNames, Row) :-
    metta_py_query_match(Space, PatternsTagged, Bindings),
    metta_py_row(VarNames, Bindings, Row).

metta_py_query_match(Space, PatternsTagged, Bindings) :-
    metta_py_decode_shared(["e", PatternsTagged], Patterns, Bindings),
    metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments),
    metta_py_match_goal(Segments, Space, PlainPatterns, Goal),
    %Choose before the nondeterministic match. Calling the empty modifier
    %walker after Goal would call it once for every answer row.
    (   Modifiers == []
    ->  call(Goal)
    ;   call(Goal), metta_py_call_modifiers(Modifiers)
    ).

%A path marker occupies the root handle's position while Python builds the
%pattern. Before matching, it becomes one fresh variable and its structural
%work becomes a post-match goal. The engine therefore joins the opaque handle
%like any stored value and Python sees only the named segments, never an eager
%projection of the object graph.
:- multifile seam:pattern_modifier/3.
seam:pattern_modifier([PathAt, [SegmentsHead|Segments], Target], Root,
                 metta_py_path_guard(Root, Segments, Target)) :-
    %Both markers are read nonvar-then-==, the same reading colon_expression/1
    %uses, because a LITERAL in the head unifies with an unbound head instead
    %of rejecting it: an ordinary three-element pattern whose head is a
    %variable was compiled as a lazy path and raised `invalid lazy path
    %segment` out of paths.py [measured 2026-08-21, hypothesis
    %SpaceStateMachine].
    nonvar(PathAt), PathAt == 'path-at',
    nonvar(SegmentsHead), SegmentsHead == segments,
    !.

metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments) :-
    lift_pattern_modifiers(Patterns, PlainPatterns, Modifiers, Segments).

metta_py_call_modifiers([]).
metta_py_call_modifiers([Modifier|Modifiers]) :-
    call(Modifier),
    metta_py_call_modifiers(Modifiers).

metta_py_path_guard(Root, Segments, Target) :-
    nonvar(Root),
    py_call(metta_ops:path_begin(Root), Cursor),
    metta_py_path_steps(Cursor, Segments),
    py_call(metta_ops:path_value(Cursor), ValueWire),
    metta_py_decode_shared(ValueWire, Value, _),
    unify_with_occurs_check(Target, Value).

metta_py_path_steps(_, []).
metta_py_path_steps(Cursor, [Segment|Segments]) :-
    metta_py_encode(Segment, SegmentWire),
    py_call(metta_ops:path_step(Cursor, SegmentWire), Answer),
    Answer == @(true),
    metta_py_path_steps(Cursor, Segments).

%The gap-pattern decision arrives from the walk that already lifted the
%modifiers, so the question costs no inference of its own, and the answer sits
%in the FIRST argument, where SWI's clause index decides it: a query with no
%sequence variable resolves to the same one goal construction it always did
%[measured 2026-08-24: query-2k-rows unchanged at its pinned count]. A gap
%pattern is parsed and classified at the ask instead of at compile time,
%because a host built it rather than wrote it.
metta_py_match_goal(false, Space, [P], match(Space, P, answered, answered)) :- !.
metta_py_match_goal(false, Space, Ps,
                    match(Space, [','|Ps], answered, answered)).
metta_py_match_goal(true, Space, [P],
                    match(Space, Asked, answered, answered)) :- !,
    metta_seq_query_plan(P, Asked).
metta_py_match_goal(true, Space, Ps, match(Space, Asked, answered, answered)) :-
    metta_seq_query_plan([','|Ps], Asked).

metta_py_query_all(Space, PatternsTagged, VarNames, Rows) :-
    findall(Row, metta_py_query(Space, PatternsTagged, VarNames, Row), Rows).

%Count without constructing, encoding, or crossing caller rows. The count-only
%match cores retain shared pattern/guard bindings but skip metta_py_row/3, so
%answers whose terms grow with input depth stay linear instead of paying to
%walk every bound term again [tested:
%test_counting_inference_growth_is_linear_when_answers_grow_in_depth;
%commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa]. GuardTagged=[] selects the unguarded query, and Limit=0
%means unbounded, matching the eager query doors.
metta_py_query_count(Space, PatternsTagged, GuardTagged, _VarNames, Limit, Count) :-
    (   GuardTagged == [], Limit > 0,
        PatternsTagged = [PatternTagged], seam:foreign_space(Space)
    ->  Query = metta_py_bounded_match(Space, PatternTagged, Limit, _)
    ;   GuardTagged == []
    ->  Query = metta_py_query_match(Space, PatternsTagged, _)
    ;   Query = metta_py_query_guarded_match(Space, PatternsTagged,
                                             GuardTagged, _)
    ),
    (   Limit > 0
    ->  aggregate_all(count, limit(Limit, Query), Count)
    ;   aggregate_all(count, Query, Count)
    ).

%Answers may ask for a length hint before it opens its row cursor. Repeating a
%foreign provider, a path modifier, or an effect-bearing guard would make that
%hint observable, so the engine's shared effect walk admits only the ordinary
%native match with no modifier and a repeatable guard. [] tells Python to
%materialize its one existing cursor instead.
metta_py_query_count_if_repeatable(
        Space, PatternsTagged, GuardTagged, VarNames, Limit, Answer) :-
    (   metta_py_query_repeatable(Space, PatternsTagged, GuardTagged)
    ->  metta_py_query_count(
            Space, PatternsTagged, GuardTagged, VarNames, Limit, Count),
        Answer = [Count]
    ;   Answer = []
    ).

metta_py_query_repeatable(Space, PatternsTagged, GuardTagged) :-
    catch_recover(
        (   \+ seam:foreign_space(Space),
            (   GuardTagged == []
            ->  metta_py_decode_shared(
                    ["e", PatternsTagged], Patterns, _),
                Guard = true
            ;   metta_py_decode_shared(
                    ["e", [GuardTagged | PatternsTagged]],
                    [Guard | Patterns], _)
            ),
            metta_py_prepare_patterns(Patterns, _, Modifiers, _),
            Modifiers == [],
            (   GuardTagged == []
            ->  true
            ;   metta_py_module(Space, Module),
                metta_py_in_module(
                    Module,
                    ( translate_expr(Guard, Goals, _),
                      goals_list_to_conj(Goals, Body) )),
                metta_host_goal_repeatable(Module, Body)
            )
        ),
        fail).

metta_py_query_count_under(Space, PatternsTagged, GuardTagged, VarNames,
                           Limit, Algebra, Count) :-
    metta_with_under(
        Algebra,
        metta_py_query_count(Space, PatternsTagged, GuardTagged, VarNames,
                             Limit, Count)).

%The generic tagged facts and rules remain ordinary atoms. Counting is their
%semiring homomorphism that maps every source and rule coefficient to one, so
%the engine enumerates proof trees and aggregate_all/3 keeps the bag cardinality
%without returning any tree or row to Python [tested:
%test_tagged_derivations_flow_through_match_and_reinterpret_without_requery;
%commit=c7468b2789746bcf95c4bacc0e2d517ec4d972fa].
metta_py_has_tagged_program(Space, Target, Has) :-
    metta_py_eval_target(Space, Target, [], Query, _),
    (   once(( 'get-atoms'(Space, Atom),
               copy_term(Atom, Stored),
               metta_py_tagged_conclusion(Stored, Conclusion),
               unifiable(Query, Conclusion, _) ))
    ->  Has = true
    ;   Has = false
    ).

metta_py_tagged_conclusion([fact, _Tag, Proposition], Proposition).
metta_py_tagged_conclusion([rule, _Tag, Head, [premises|_]], Head).

metta_py_tagged_count(Space, Target, MaxDepth, Limit, Count) :-
    metta_py_eval_target(Space, Target, [], Query, _),
    findall(Atom, 'get-atoms'(Space, Atom), Atoms),
    Goal = metta_with_under(counting,
               metta_py_tagged_prove(Space, Atoms, Query, MaxDepth)),
    (   Limit > 0
    ->  aggregate_all(count, limit(Limit, Goal), Count)
    ;   aggregate_all(count, Goal, Count)
    ).

% Ordinary source rows enter through the same match door as direct queries.
% Capture k exactly as a direct query does. Python validates it against the
% selected declaration; metta_annotation/2 would instead reselect a same-name
% local carrier before the explicit declaration can check it.
% [tested: test_provider_conclusions_check_the_explicit_typed_carrier;
% commit=4f2d6c0f8eb293b73f8dde30a1c84e24834f7393]
metta_py_tagged_sources(Space, Target, Algebra, [Rows, Used]) :-
    metta_py_work(Before),
    metta_py_eval_target(Space, Target, [], Pattern, _),
    metta_with_under(Algebra,
        findall([ValueWire, KWire],
            ( metta_py_under_query(
                  Space, match(Space, Pattern, Pattern, Value), K),
              metta_py_encode(Value, ValueWire),
              metta_py_encode(K, KWire) ), Rows)),
    metta_py_work(After),
    Used is After - Before.

metta_py_tagged_prove(Space, _, Query, _) :-
    seam:foreign_space(Space),
    match(Space, Query, Query, _).
metta_py_tagged_prove(_, Atoms, Query, _) :-
    member(Stored, Atoms),
    copy_term(Stored, [fact, _Tag, Proposition]),
    unify_with_occurs_check(Query, Proposition).
metta_py_tagged_prove(Space, Atoms, Query, Depth) :-
    Depth > 0,
    member(Stored, Atoms),
    copy_term(Stored, [rule, _Tag, Head, [premises|Premises]]),
    unify_with_occurs_check(Query, Head),
    NextDepth is Depth - 1,
    metta_py_tagged_premises(Premises, Space, Atoms, NextDepth),
    ground(Head).

metta_py_tagged_premises([], _, _, _).
metta_py_tagged_premises([Premise|Premises], Space, Atoms, Depth) :-
    metta_py_tagged_prove(Space, Atoms, Premise, Depth),
    metta_py_tagged_premises(Premises, Space, Atoms, Depth).

%The seam's own decision for this query, shown without running it, is the
%engine's metta_host_explain_match/3; this renders its term report as the
%wire shape, classes to strings and origin terms to prose
%[tested test_explain_reflects_the_plan].
metta_py_explain(Space, PatternsTagged, Report) :-
    metta_py_decode_shared(["e", PatternsTagged], Patterns, _),
    metta_host_explain_match(Space, Patterns, Explained),
    metta_py_render_explain(Explained, Report).

metta_py_render_explain(explain(stored, _, _, _), ["stored", [], [], []]).
metta_py_render_explain(explain(refused, [Entry], _, _),
                        ["refused", [EText], [], []]) :-
    swrite(Entry, EText).
metta_py_render_explain(explain(foreign, Classes, ClaimedIdx, RestIdx),
                        ["foreign", Rendered, ClaimedIdx, RestIdx]) :-
    maplist(metta_py_render_class, Classes, Rendered).

metta_py_render_class(class(ClassAtom, Origin), [Class, OriginText]) :-
    atom_string(ClassAtom, Class),
    metta_py_render_origin(Origin, OriginText).

metta_py_render_origin(declared(Entry, Fidelity, Det), Text) :-
    swrite(Entry, EText),
    ( var(Det) -> DetText = unstated ; DetText = Det ),
    format(string(Text), "declared: (handles ~w ~w ~w)",
           [EText, Fidelity, DetText]).
metta_py_render_origin(provider, "the provider's own pushdown method").
metta_py_render_origin(unclaimed,
                       "unclaimed; silence is inexact and candidates re-unify").
metta_py_render_origin(refused(Refusing), Text) :-
    swrite(Refusing, RText),
    format(string(Text), "the declared entry ~w answers Refuse", [RText]).

%A query with a guard and a bound: the guard decodes IN THE SAME variable
%scope as the patterns, so $age in both is one variable; after the match
%joins, the guard evaluates in the space's module and must answer true.
%Limit 0 means every answer.
%The guard translates ONCE, before the match enumerates: its variables are
%the same Prolog variables the patterns bind, so each answer runs the
%already-compiled goals against its own bindings, and backtracking retracts
%them. Translating inside the enumeration would recompile per candidate
%row, which measured at ~500ms per 2000-row guarded query.
metta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row) :-
    VarNames = [
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _ | _
    ],
    !,
    metta_py_decode_indexed(["e", [GuardTagged | PatternsTagged]],
                            [Guard | Patterns], Bindings),
    metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments),
    metta_py_match_goal(Segments, Space, PlainPatterns, Goal),
    metta_py_module(Space, Module),
    metta_py_in_module(Module, translate_expr(Guard, Goals, Out)),
    (   Modifiers == []
    ->  call(Goal)
    ;   call(Goal), metta_py_call_modifiers(Modifiers)
    ),
    metta_py_call_goals(Module, Goals),
    Out == true,
    metta_py_row(VarNames, Bindings, Row).

metta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row) :-
    metta_py_query_guarded_match(Space, PatternsTagged, GuardTagged, Bindings),
    metta_py_row(VarNames, Bindings, Row).

metta_py_query_guarded_match(Space, PatternsTagged, GuardTagged, Bindings) :-
    metta_py_decode_shared(["e", [GuardTagged | PatternsTagged]], [Guard | Patterns], Bindings),
    metta_py_prepare_patterns(Patterns, PlainPatterns, Modifiers, Segments),
    metta_py_match_goal(Segments, Space, PlainPatterns, Goal),
    metta_py_module(Space, Module),
    metta_py_in_module(Module, translate_expr(Guard, Goals, Out)),
    (   Modifiers == []
    ->  call(Goal)
    ;   call(Goal), metta_py_call_modifiers(Modifiers)
    ),
    metta_py_call_goals(Module, Goals),
    Out == true.

metta_py_query_guarded_all(Space, PatternsTagged, GuardTagged, VarNames, Limit, Rows) :-
    Query = metta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row),
    ( Limit > 0
      -> findall(Row, limit(Limit, Query), Rows)
    ; findall(Row, Query, Rows) ).

%The bound is applied here whatever happens below, so pushing it down cannot
%change an answer. It is pushed only for ONE pattern against a foreign space:
%across a join the bound belongs to the joined rows, and an outer match
%truncated at N would lose the rows its later candidates would have joined
%to. A guarded query keeps the bound here too, since the guard decides how
%many candidates become answers.
metta_py_query_limit_all(Space, PatternsTagged, VarNames, Limit, Rows) :-
    (   PatternsTagged = [PatternTagged],
        seam:foreign_space(Space)
    ->  findall(Row,
                limit(Limit,
                      metta_py_bounded_query(Space, PatternTagged, VarNames,
                                             Limit, Row)),
                Rows)
    ;   findall(Row,
                limit(Limit, metta_py_query(Space, PatternsTagged, VarNames, Row)),
                Rows)
    ).

metta_py_bounded_query(Space, PatternTagged, VarNames, Limit, Row) :-
    VarNames = [
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _,
        _, _, _, _, _, _, _, _ | _
    ],
    !,
    metta_py_decode_indexed(["e", [PatternTagged]], [Pattern], Bindings),
    metta_py_prepare_patterns([Pattern], [PlainPattern], Modifiers, Segments),
    (   Segments == true
    ->  metta_seq_query_plan(PlainPattern, Asked),
        match(Space, Asked, answered, answered),
        ( Modifiers == [] -> true ; metta_py_call_modifiers(Modifiers) )
    ;   Modifiers == []
    ->  match_foreign(Space, PlainPattern, [limit(Limit)], answered, answered)
    ;   match_foreign(Space, PlainPattern, [limit(Limit)], answered, answered),
        metta_py_call_modifiers(Modifiers)
    ),
    metta_py_row(VarNames, Bindings, Row).

metta_py_bounded_query(Space, PatternTagged, VarNames, Limit, Row) :-
    metta_py_bounded_match(Space, PatternTagged, Limit, Bindings),
    metta_py_row(VarNames, Bindings, Row).

metta_py_bounded_match(Space, PatternTagged, Limit, Bindings) :-
    metta_py_decode_shared(["e", [PatternTagged]], [Pattern], Bindings),
    metta_py_prepare_patterns([Pattern], [PlainPattern], Modifiers, Segments),
    %A gap pattern is not a shape a provider was handed a bound for: its arity
    %is what the gap decides, so the engine enumerates candidates and the
    %caller's own limit/2 still cuts the stream. The test is == on an atom,
    %which SWI compiles inline, so the pushdown path keeps its per-row cost.
    (   Segments == true
    ->  metta_seq_query_plan(PlainPattern, Asked),
        match(Space, Asked, answered, answered),
        ( Modifiers == [] -> true ; metta_py_call_modifiers(Modifiers) )
    ;   Modifiers == []
    ->  match_foreign(Space, PlainPattern, [limit(Limit)], answered, answered)
    ;   match_foreign(Space, PlainPattern, [limit(Limit)], answered, answered),
        metta_py_call_modifiers(Modifiers)
    ).

%A row holds one encoded value per requested name; a variable the answer left
%unbound comes back as itself:
%The acyclicity guard is the engine's own semantics, not a transport
%limit: match_native guards every OUT template with acyclic_term/1, so a
%rational-tree instantiation is not an answer there, and the engine's
%matching is unify_with_occurs_check throughout (spaces.pl
%metta_match_atoms, the arbiter's variable cases). The query lanes keep
%their bindings OUTSIDE the out template, so without this guard a cyclic
%join sailed past match_native's check and the row encode walked it to a
%stack overflow. Same semantics as match/4: the cyclic candidate FAILS
%this row and enumeration continues. Guarded once per row, not per
%column.
%Loud, not a silent row drop: this gate used to FAIL a cyclic row, which
%made the engine-side len disagree with the rows a caller could read.
metta_py_row(Names, indexed(Bindings, Index), Row) :- !,
    ( acyclic_term(Bindings) -> true ; metta_py_wire_refuse ),
    metta_py_row_indexed(Names, Index, Row).
metta_py_row(Names, Bindings, Row) :-
    ( acyclic_term(Bindings) -> true ; metta_py_wire_refuse ),
    metta_py_row_columns(Names, Bindings, Row).

%A ROW IS ONE CROSSING, so its columns share one name map: a variable in two
%columns has to come back as one variable, and two variables must never come
%back as one. Encoding column by column restarted the numbering at each, which
%named the first variable of every column alike; (= $head $body) then answered
%a head and a body whose distinct variables had collided, and the equation read
%back with its head variable merged into a let* binder
%[tested: test_a_twin_stores_the_atoms_its_example_stores].
%
%The map is NOT seeded with the query's variable names. Seeding it reads
%well and is wrong: a column bound to a VARIABLE would then cross under the
%caller's spelling, which is the same spelling in every row, so two rows'
%distinct variables would arrive as one [measured 2026-08-31: two separately
%sealed rules both answered $x]. A caller's name says which column, not which
%cell. Only a column the match did not bind at all keeps it, below, and that
%names no cell to collide with.
metta_py_row_columns(Names, Bindings, Row) :-
    metta_py_row_columns(Names, Bindings, [], Row).

metta_py_row_columns([], _, _, []).
metta_py_row_columns([Name0|Names], Bindings, N0, [Value|Values]) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    ( memberchk(Name-V, Bindings) -> metta_py_encode(V, N0, N1, Value)
    ; Value = ["v", Name0], N1 = N0 ),
    metta_py_row_columns(Names, Bindings, N1, Values).

metta_py_row_indexed(Names, Index, Row) :-
    metta_py_row_indexed(Names, Index, [], Row).

metta_py_row_indexed([], _, _, []).
metta_py_row_indexed([Name0|Names], Index, N0, [Value|Values]) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    ( ht_get(Index, Name, V) -> metta_py_encode(V, N0, N1, Value)
    ; Value = ["v", Name0], N1 = N0 ),
    metta_py_row_indexed(Names, Index, N1, Values).
