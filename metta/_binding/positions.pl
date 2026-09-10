% Purpose: project the engine's occurrence origins onto the Python wire.
% Guarantees: source identity and line resolution live in metta_head_origins/3
%   [tested: test_every_clause_of_a_multi_clause_head_answers_in_clause_order;
%   commit=90ba93eb8f6e98ebfefc55416859bf13de6a8427].

metta_py_origin(Space, Name0, Origins) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    metta_head_origins(Space, Name, Rows),
    findall([File, Line, -1], member([_, File, Line], Rows), Origins).
