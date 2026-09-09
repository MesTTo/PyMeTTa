% Purpose: associate source positions with parsed and defined forms.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Source locations %%%%%%%%%%
%
% Where a head's clauses were written: one row per compiled clause, in clause
% order, arities ascending, as [File, Line, FormIndex]. An empty File means the
% engine knows no source for that clause; Line is -1 and FormIndex -1 when the
% respective half is unknown.
%
% Two routes, because the engine makes clauses two ways and only one of them
% leaves SWI a source location.
%
% A clause SWI loaded from a consulted Prolog file answers file and line off
% clause_property/2 directly. That is every builtin and every registered Prolog
% function, and engine/metta/interop.pl:113 already reads the file half of it
% to refuse a registration that would claim another file's name.
%
% A clause the translator built from a MeTTa equation is asserted at runtime,
% so SWI records nothing about it and clause_property(Ref, file(_)) simply
% fails [measured 2026-09-06: `car-atom` answers input_guards.pl lines 170-175
% while a head loaded from a .metta file and one defined through m.run both
% answer predicate/1 and nothing else; the MeTTa half is pinned since by
% test_a_head_defined_from_python_text_has_no_source]. Its file comes instead from the loader's ownership journal, which
% already records every reference a load asserted, and its line is left to
% extensions/python/metta/_binding/positions.py. Hence the FORM INDEX: it indexes
% the same parsed-form list metta_py_read_forms/2 hands that walk, so the two
% sides share one reader and neither reproduces the other's job -- Prolog owns
% which form defines a clause, Python owns where a form sits.
%
% The clause-to-form correspondence is the loader's own order. A file's
% equations for one predicate translate in source order and assert in that
% order, so the k-th clause of Name/Arity owned by a load is the k-th equation
% for Name/Arity in that load's source. The count is kept per LOAD rather than
% per predicate, which is what keeps a head defined across two files right.
metta_py_origin(Space, Name0, Origins) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %A deferred function has no clauses until its equations translate, and the
    %question is about clauses, so asking IS the demand, as .compiled is.
    spaces:metta_ensure_compiled(Name),
    space_module(Space, Module),
    findall(A, arity(Name, A), As0),
    sort(As0, As),
    metta_py_origin_arities(As, Module, Name, [], Nested),
    append(Nested, Origins).

metta_py_origin_arities([], _, _, _, []).
metta_py_origin_arities([A|As], Module, Name, Sources0, [Rows|Rest]) :-
    (   current_predicate(Module:Name/A),
        functor(Head, Name, A)
    ->  findall(Ref, nth_clause(Module:Head, _, Ref), Refs)
    ;   Refs = []
    ),
    %Clause numbering restarts with each predicate, so the per-load counter
    %does too; the parsed source cache is shared across arities.
    metta_py_origin_clauses(Refs, Name, A, [], _, Sources0, Sources1, Rows),
    metta_py_origin_arities(As, Module, Name, Sources1, Rest).

metta_py_origin_clauses([], _, _, Seen, Seen, Sources, Sources, []).
metta_py_origin_clauses([Ref|Refs], Name, Arity, Seen0, Seen,
                        Sources0, Sources, [Row|Rows]) :-
    metta_py_origin_clause(Ref, Name, Arity, Seen0, Seen1,
                           Sources0, Sources1, Row),
    metta_py_origin_clauses(Refs, Name, Arity, Seen1, Seen,
                            Sources1, Sources, Rows).

metta_py_origin_clause(Ref, _, _, Seen, Seen, Sources, Sources, [File, Line, -1]) :-
    clause_property(Ref, file(Path)),
    clause_property(Ref, line_count(Line)),
    !,
    atom_string(Path, File).
metta_py_origin_clause(Ref, Name, Arity, Seen0, Seen, Sources0, Sources,
                       [File, -1, Index]) :-
    metta_py_clause_load(Ref, Load, Path),
    !,
    atom_string(Path, File),
    metta_py_load_ordinal(Load, Seen0, Seen, K),
    metta_py_load_forms(Load, Path, Sources0, Sources, Parsed),
    (   metta_py_equation_indices(Parsed, Name, Arity, Indices),
        nth0(K, Indices, Found)
    ->  Index = Found
    ;   Index = -1
    ).
metta_py_origin_clause(_, _, _, Seen, Seen, Sources, Sources, ["", -1, -1]).

%The load that asserted this clause, and the file that load read. A clause
%asserted outside any load -- a definition made from Python text, a prelude
%clause built at boot -- matches nothing here and falls to the last clause
%above.
metta_py_clause_load(Ref, Load, Path) :-
    filereader:source_load_assertion(Load, artifact, Ref),
    filereader:metta_source_load(Path, _, Load, _),
    !.

metta_py_load_ordinal(Load, Seen0, Seen, K) :-
    (   selectchk(Load-K, Seen0, Rest)
    ->  Next is K + 1,
        Seen = [Load-Next|Rest]
    ;   K = 0,
        Seen = [Load-1|Seen0]
    ).

%One parse per source per call, and a source this cannot read or parse gives
%an empty form list rather than an error: a head still knows which FILE it came
%from when the file has since been deleted or edited into a syntax error, and
%saying so beats refusing the whole answer.
metta_py_load_forms(Load, _, Sources, Sources, Parsed) :-
    memberchk(Load-Parsed, Sources),
    !.
metta_py_load_forms(Load, Path, Sources, [Load-Parsed|Sources], Parsed) :-
    (   catch(filereader:read_source_text(Path, Text), _, fail),
        catch(filereader:metta_host_tagged_parse(Text, Read), _, fail)
    ->  Parsed = Read
    ;   Parsed = []
    ).

%Which top-level forms are equations for this head at this PREDICATE arity,
%by their position in the reader's own form list. The predicate carries the
%output slot the MeTTa call does not, so a form's argument count is one less.
metta_py_equation_indices(Parsed, Name, Arity, Indices) :-
    Args is Arity - 1,
    Args >= 0,
    findall(I,
            ( nth0(I, Parsed, Form),
              metta_py_form_equation(Form, Name, Args) ),
            Indices).

metta_py_form_equation(parsed(function, _, [=, [Name|Args], _]), Name, N) :-
    length(Args, N).
metta_py_form_equation(parsed(function, _, [=, [Name|Args], _], _), Name, N) :-
    length(Args, N).
