crun(ARG,OUT) :-
  run(ARG,P),
  convert_term(P,OUT).

convert_term(Var, Str) :-
    var(Var), !,
    term_to_atom(Var, VAtom),
    atom_concat('$', VAtom, Str).

convert_term(Atom, Atom) :-
    atom(Atom), !.

convert_term(Number, Number) :-
    number(Number), !.

convert_term([],'()') :- !.

convert_term(List, Str) :-
    is_list(List), !,
    List = [Head | Tail],
    convert_term(Head, HStr),
    maplist(convert_term, Tail, TStrs),
    atomic_list_concat([HStr | TStrs], ' ', Content),
    atomic_list_concat(['(', Content, ')'], Str).
