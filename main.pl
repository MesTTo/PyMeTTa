:- ensure_loaded(metta).

prologfunc(X,Y) :- Y is X+1.

prolog_interop_example :- register_fun(prologfunc),
                          assert_function("(= (mettafunc $x) (prologfunc $x))"),
                          listing(mettafunc),
                          mettafunc(30, R),
                          format("mettafunc(30) = ~w~n", [R]).

main :- current_prolog_flag(argv, Args),
        ( Args = [] -> prolog_interop_example
                     ; Args = [File|_],
                       load_metta_file(File,default),
                       findall(R, run(default,R), Results),
                       format("~w~n", [Results]) ),
        halt.

crun(ARG,OUT) :-
  run(ARG,P),
  convert_term(P,OUT).

convert_term(Var, Str) :-
    var(Var),
    term_to_atom(Var, VAtom),
    atom_concat('$', VAtom, Str).

convert_term(Atom, Atom) :-
    atom(Atom).

convert_term(List, Str) :-
    is_list(List),
    List = [Head | Tail],
    convert_term(Head, HStr),
    maplist(convert_term, Tail, TStrs),
    atomic_list_concat([HStr | TStrs], ' ', Content),
    atomic_list_concat(['(', Content, ')'], Str).
