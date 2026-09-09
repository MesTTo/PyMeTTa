% Purpose: run and load source programs with scoped substitutions.
% Assumes: loaded through _binding/shim.pl in its host module.

%%%%%%%%%% Run and load %%%%%%%%%%
%
% The grouping walk, the using-substitution, the load lifecycle and the
% status vocabulary live ENGINE-SIDE now, in engine/filereader.pl's host run
% and load surface, where every binding shares one copy; this side decodes
% the host values in, maps the codec over the term groups coming out, and
% nothing else. Reader failures arrive as the engine's reserved
% metta_control_signal envelope, which the Python side already classifies
% by shape. The grouping is one answer list per ! directive, in source
% order [tested test_run_status_reports_each_directive,
% test_both_doors_replace_a_files_definitions].

metta_py_run(Source, Space, Groups) :-
    metta_host_run_source(Source, Space, [], TermGroups),
    maplist(metta_py_encode_group, TermGroups, Groups).

metta_py_encode_group(Terms, Encoded) :-
    maplist(metta_py_encode_answer, Terms, Encoded).

%A binding may be a rational tree under the petta alignment, since
%unification binds raw, and the tagged-array wire has no finite form for
%one: the encoder's recursion would diverge (measured: 6.7 million frames
%to the stack limit). The ANSWER and ROW sites are the only places a
%cyclic term can reach the wire, so they test first and refuse loudly
%with the remedy named; stored atoms, events and parses are finite by
%construction and pay nothing
%[tested: test_a_rational_tree_binding_refuses_its_row_loudly].
%Inlined at the row clauses as ( acyclic_term(B) -> true ; refuse ), the
%exact shape and price the silent gate had (+2 inferences per row through
%a helper call measured on foreign-match and run-source); the cold branch
%alone is a predicate.
metta_py_wire_refuse :-
    throw(error(metta_rational_tree_wire,
                context(metta_py_encode/2,
                        'a rational-tree binding has no finite wire \c
                         form; match with the stored atom as the \c
                         template to read the atoms themselves'))).

metta_py_wire_acyclic(Term) :-
    (   acyclic_term(Term)
    ->  true
    ;   metta_py_wire_refuse
    ).

prolog:error_message(metta_rational_tree_wire) -->
    [ 'a rational-tree binding has no finite wire form; match with the \c
       stored atom as the template to read the atoms themselves' ].

metta_py_encode_answer('$metta_answer'(Term, NameState), Encoded) :- !,
    metta_py_wire_acyclic(Term),
    metta_name_pairs(NameState, Names),
    metta_py_encode_named(Term, Names, Encoded).
metta_py_encode_answer(Term, Encoded) :-
    metta_py_wire_acyclic(Term),
    metta_py_encode(Term, Encoded).

%Run with named host values: each Name-Value pair substitutes the bare
%symbol Name throughout the parsed forms before anything runs, the local-
%variable reading a dataframe gets in embedded SQL. Values arrive on the
%wire, objects boxed, so identity crosses whole; the decode is this side's
%half, the substitution walk is the engine's.
metta_py_run_using(Source, Space, Pairs, Groups) :-
    maplist(metta_py_using_pair, Pairs, Bindings),
    metta_host_run_source(Source, Space, Bindings, TermGroups),
    maplist(metta_py_encode_group, TermGroups, Groups).

metta_py_using_pair([Name0, Wire], Name-Value) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    metta_py_decode_shared(Wire, Value, _).

metta_py_run_status(Source, Space, Groups) :-
    metta_host_run_source_status(Source, Space, TermGroups),
    maplist(metta_py_status_group, TermGroups, Groups).

metta_py_status_group(Rows, Encoded) :-
    maplist(metta_py_status_row, Rows, Encoded).

metta_py_status_row([empty, none], [empty, none]) :- !.
metta_py_status_row([Status, Term], [Status, Encoded]) :-
    metta_py_encode_answer(Term, Encoded).

metta_py_load(File, Space, Groups) :-
    metta_host_load_file(File, Space, TermGroups),
    maplist(metta_py_encode_group, TermGroups, Groups).

%Ask every library to forget the answers it derived earlier, so a re-run takes
%the path a first run takes. A replay needs it: the recording's digest pins the
%space's atoms and its seed pins the draws, and this is the third piece of the
%state a recorded run started from.
metta_py_forget_derived :-
    metta_forget_derived.

%Every operation a pinned seed makes repeat, as the engine and its loaded
%libraries declare it. A recording reads this to tell an oracleIO operation
%whose draw its seed captured from one that reads something no seed can pin.
metta_py_seeded_operations(Names) :-
    findall(NameStr,
            ( seam:seeded_operation(Name), atom_string(Name, NameStr) ),
            Names0),
    sort(Names0, Names).

%Read every form in Source without processing any, the boot-manifest door
%[tested test_a_manifest_neither_runs_nor_defines].
metta_py_read_forms(Source, Forms) :-
    metta_host_read_forms(Source, Pairs),
    maplist(metta_py_form_pair, Pairs, Forms).

metta_py_form_pair([Kind, Text], [KindStr, TextStr]) :-
    atom_string(Kind, KindStr),
    ( string(Text) -> TextStr = Text ; atom_string(Text, TextStr) ).
