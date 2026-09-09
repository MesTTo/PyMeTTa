% Purpose: infer declarations from stored atoms and equations.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Inferred declarations %%%%%%%%%%
%
% What the atoms a space already holds say about the heads it never declared.
% One walk answers [Head, Arity, ArgumentKinds, Result] a row per (head,
% arity), with the kinds and the result as WIRE terms, so a declared result
% type that is itself an expression, `(List Number)`, crosses whole instead of
% flattened into a name.
%
% The rule is pandas.api.types.infer_dtype's, moved from a column's values to
% an argument position's children: name the NARROWEST kind that covers every
% child observed there [source:
% https://pandas.pydata.org/docs/reference/api/pandas.api.types.infer_dtype.html].
% A variable in a position is that function's skipna: it stands for anything,
% so it constrains nothing and is skipped rather than counted as a kind of its
% own. A position with nothing left to go on is '%Undefined%', the gradual
% unknown; a position whose children disagree is 'Atom', the top of the
% metatype lattice.
%
% Cost is one 'get-atoms'/2 walk plus one keysort, so theta(A log A + A*arity)
% in the atoms A the space holds, and one 'get-type-space'/3 lookup per
% DISTINCT head rather than per occurrence.
metta_py_infer_types(Space, Rows) :-
    findall(Atom, 'get-atoms'(Space, Atom), Atoms),
    metta_py_infer_scan(Atoms, Space, 0, Observations),
    keysort(Observations, Sorted),
    group_pairs_by_key(Sorted, Grouped),
    findall(Rank-Row,
            ( member(Key-Group, Grouped),
              metta_py_infer_row(Space, Key, Group, Rank, Row) ),
            Ranked),
    keysort(Ranked, ByFirstMention),
    pairs_values(ByFirstMention, Rows).

%One atom's contribution, keyed by the head and arity it mentions and carrying
%the position at which the space first mentioned that pair, which is the order
%the rows come back in. keysort/2 is stable, so a group's first element is its
%first mention.
metta_py_infer_scan([], _, _, []).
metta_py_infer_scan([Atom|Rest], Space, Index, Out) :-
    (   metta_py_infer_observation(Space, Atom, Name, Arity, Kinds, Result)
    ->  Out = [(Name-Arity)-seen(Index, Kinds, Result)|More]
    ;   Out = More
    ),
    Next is Index + 1,
    metta_py_infer_scan(Rest, Space, Next, More).

%An equation says what its head takes AND what it answers; a plain fact says
%only what it takes. A ':' or '@doc' row is the space's own catalogue rather
%than data about a head, which is the same three-row split
%extensions/python/metta/_catalog/declarations.py reads, so the two projections agree
%on what counts as a row.
metta_py_infer_observation(Space, ['=', Head, Body], Name, Arity, Kinds, Result) :-
    !,
    metta_py_infer_head(Head, Name, Arguments),
    length(Arguments, Arity),
    metta_py_infer_kinds(Arguments, Space, Kinds),
    metta_py_infer_body(Body, Space, Result).
metta_py_infer_observation(Space, [Name|Arguments], Name, Arity, Kinds, []) :-
    atom(Name),
    Name \== ':',
    Name \== '@doc',
    Arguments = [_|_],
    length(Arguments, Arity),
    metta_py_infer_kinds(Arguments, Space, Kinds).

%`(= (f $x) ...)` names f at arity one and `(= f 1)` names f at arity zero.
metta_py_infer_head([Name|Arguments], Name, Arguments) :- atom(Name), !.
metta_py_infer_head(Name, Name, []) :- atom(Name).

metta_py_infer_kinds([], _, []).
metta_py_infer_kinds([Child|Rest], Space, [Kind|Kinds]) :-
    metta_py_infer_kind(Child, Space, Kind),
    metta_py_infer_kinds(Rest, Space, Kinds).

%Zero or one kind per child, because a variable contributes NOTHING rather
%than a kind called Variable: it is the one child that already stands for
%every type, so counting it would make every parameter position disagree with
%itself and answer Atom.
metta_py_infer_kind(Child, _, [])           :- var(Child), !.
metta_py_infer_kind(Child, _, ['Number'])   :- number(Child), !.
metta_py_infer_kind(Child, _, ['String'])   :- string(Child), !.
metta_py_infer_kind(Child, _, ['Bool'])     :- (Child == true ; Child == false), !.
metta_py_infer_kind(Child, _, ['Grounded']) :- py_is_object(Child), !.
metta_py_infer_kind(Child, _, ['Symbol'])   :- atom(Child), !.
metta_py_infer_kind(Child, Space, [Kind])   :- is_list(Child), !,
    metta_py_infer_call_kind(Child, Space, 'Expression', Kind).
metta_py_infer_kind(_, _, ['Atom']).

%An expression's kind is the RESULT its head is declared to answer, when the
%head has an arrow, and the fallback otherwise: `(circle 2)` beside
%`(: circle (-> Number Shape))` observes a Shape at that position, where
%`(a b)` with nothing declared observes only that something structured is
%there.
metta_py_infer_call_kind([Head|_], Space, _Fallback, Kind) :-
    atom(Head),
    once('get-type-space'(Space, Head, Declared)),
    metta_py_infer_arrow_result(Declared, Result),
    !,
    Kind = Result.
metta_py_infer_call_kind(_, _, Fallback, Fallback).

metta_py_infer_arrow_result(['->'|Chain], Result) :-
    Chain = [_|_],
    last(Chain, Result).

%What one equation body says the head answers. A literal answers its own
%type, a call to a declared head answers that head's result, and everything
%else says nothing: a bare symbol's own type is '%Undefined%' here [measured
%2026-09-07: (get-type sym) answers %Undefined%], so reading it as a kind
%would claim more than the program does.
metta_py_infer_body(Body, _, [])          :- var(Body), !.
metta_py_infer_body(Body, _, ['Number'])  :- number(Body), !.
metta_py_infer_body(Body, _, ['String'])  :- string(Body), !.
metta_py_infer_body(Body, _, ['Bool'])    :- (Body == true ; Body == false), !.
metta_py_infer_body(Body, Space, Result)  :- is_list(Body), !,
    (   metta_py_infer_call_kind(Body, Space, '$none', Kind), Kind \== '$none'
    ->  Result = [Kind]
    ;   Result = []
    ).
metta_py_infer_body(_, _, []).

%One (head, arity) group as the row that crosses, unless the head is already
%declared here: a declaration is the program's own answer and a proposal
%beside it would be noise. 'get-type-space'/3 is the space-scoped door the
%language itself answers get-type through, so a builtin and a locally
%declared head are both skipped by one question.
metta_py_infer_row(Space, Name-Arity, Group, Rank, [Text, Arity, Kinds, Result]) :-
    once('get-type-space'(Space, Name, Declared)),
    Declared == '%Undefined%',
    Group = [seen(Rank, _, _)|_],
    metta_py_infer_positions(Group, Arity, Positions),
    maplist(metta_py_infer_position_type, Positions, Types),
    maplist(metta_py_encode, Types, Kinds),
    findall(R, ( member(seen(_, _, Answers), Group), member(R, Answers) ), Results0),
    sort(Results0, Answered),
    metta_py_infer_result_type(Answered, ResultType),
    metta_py_encode(ResultType, Result),
    atom_string(Name, Text).

%The observed kinds at each position, as one sorted set per position.
metta_py_infer_positions(Group, Arity, Positions) :-
    length(Empty, Arity),
    maplist(=([]), Empty),
    foldl(metta_py_infer_merge, Group, Empty, Merged),
    maplist(sort, Merged, Positions).

metta_py_infer_merge(seen(_, Kinds, _), Into, Out) :-
    maplist(append, Into, Kinds, Out).

%Nothing observed is the gradual unknown; one kind is that kind; several is
%the top of the metatype lattice. Atom in an ARGUMENT position also stops the
%engine evaluating that argument [measured 2026-09-07: with
%(: shows (-> Atom Atom)), !(shows (+ 1 2)) answers (+ 1 2) where the same
%head undeclared answers 3], which is why the proposal is only ever added on
%request.
metta_py_infer_position_type([], '%Undefined%') :- !.
metta_py_infer_position_type([Kind], Kind) :- !.
metta_py_infer_position_type(_, 'Atom').

%Equations that disagree about what they answer say nothing together, which
%is the same '%Undefined%' a body with no readable kind answers. Atom is not
%used here: a result is a TYPE rather than a parameter's metatype, and the
%rule's own fallback is the gradual unknown.
metta_py_infer_result_type([Kind], Kind) :- !.
metta_py_infer_result_type(_, '%Undefined%').
