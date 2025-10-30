:- use_module(library(readutil)). % read_file_to_string/3

%Read Filename into string S and process it (S holds MeTTa code):
load_metta_file(Filename, Results) :- read_file_to_string(Filename, S, []),
                                      process_metta_string(S, Results).

%Process a MeTTa string and collect results from !-forms:
process_metta_string(S, Results) :- split_string(S, "\n", "", L0),
                                    findall(C, (member(L, L0), split_string(L, ";", "", [C|_])), L1),
                                    atomic_list_concat(L1, '\n', CodeWithoutComment),
                                    string_codes(CodeWithoutComment, Codes),
                                    phrase(top_entities(Entities,1), Codes),
                                    maplist(parse_entity, Entities, ParsedEntities),
                                    maplist(process_entity_with_error, ParsedEntities, ResultsList), !,
                                    append(ResultsList, Results).

%Helper for parsing error handling
sread_with_error(FormStr, Term) :- ( sread(FormStr, Term)
                                   -> true ; format('Parse error in form: ~w~n', [FormStr]), fail ).

%Classify parsed entities:
parse_entity(form(FormStr), parsed(Type, FormStr, Term)) :- sread_with_error(FormStr, Term),
                                                            ( Term = [=, [FAtom|_], _]
                                                             -> Type = function, !,
                                                                atom(FAtom), register_fun(FAtom) %Registers Fucntions before we compile their body
                                                             ; Type = expression ).
parse_entity(bang(FormStr), parsed(bang, FormStr, Term)) :- sread_with_error(FormStr, Term).

%Helper for pressing error handling
process_entity_with_error(In, Out) :- ( process_entity(In, Out)
                                      -> true ; format('Failed to process entity: ~w~n', [In]), halt(1) ).

%Run ! / add functions/atoms
process_entity(parsed(Type, FormStr, Term), []) :- ( Type = function
                                                   -> assert_function_form(FormStr, Term)
                                                   ; Type = expression
                                                   -> 'add-atom'('&self', Term, true) ).
process_entity(parsed(bang, _, Term), [Result]) :- eval([collapse, Term], Result).

%From a function string: parse, extract first atom as name, register, transform to relation, assert:
assert_function_form(FormStr, Term) :- add_sexp('&self', Term),
                                       translate_clause(Term, Clause),
                                       assertz(Clause, Ref),
                                       show_compiled_function(FormStr,Ref).

show_compiled_function(FormStr,Ref) :- ( current_prolog_flag(argv, Args) -> true ; Args = [] ),
                                       ( member(Flag, Args), ( Flag == silent ; Flag == '--silent'; Flag == '-s' )
                                       -> true
                                       ; format("\e[33m-->  metta S-exp  -->~n\e[36m~w~n\e[33m--> prolog clause -->~n\e[32m", [FormStr]),
                                         clause(Head, Body, Ref),
                                         ( Body == true -> Show = Head; Show = (Head :- Body) ),
                                         portray_clause(current_output, Show),
                                         format("\e[33m^^^^^^^^^^^^^^^^^^^^^~n\e[0m") ).

%Collect characters until all parentheses are balanced (depth 0), accumulating codes:
grab_until_balanced(D,Acc,Cs,LCI,LCO) --> [C], { ( C=0'( -> D1 is D+1 ; C=0') -> D1 is D-1 ; D1=D ), Acc1=[C|Acc] ,
                                                 ( C=10 -> LCI1 is LCI+1 ; LCI1 = LCI) },
                                          ( { D1=:=0 } -> { reverse(Acc1,Cs) , LCO = LCI1 } ; grab_until_balanced(D1,Acc1,Cs,LCI1,LCO) ).

%  Capture the rest of the current line
here_line(Str, S0, S0) :- ( append(LineCodes, [10|_], S0) ->  true ; LineCodes = S0 ),
                          string_codes(Str, LineCodes).

% like blanks but counts newlines
newlines(C0, C2) --> blanks_to_nl, !, {C1 is C0+1}, newlines(C1,C2).
newlines(C,C) --> blanks.

%Read balanced entities, distinguishing between regular forms and !-forms:
top_entities([],_) --> blanks, eos.
top_entities([Term|Fs],LC) --> newlines(LC,LC1), 
                            ( ( "!" -> { Tag = bang , E = "!" } ; { Tag = form , E = "" } ), "("
                              -> {true} ; here_line(Rest) , {format("Parse error: expected start of statment either '!(' or '(' found line ~w:~n~w~n", [LC1,Rest]), halt(1)} ),
                            (grab_until_balanced(1, [0'(], Cs, LC1, LC2)
                              -> {true} ; here_line(Rest) , {format("Parse error: missing ) starting at line ~w:~n~w(~w~n", [LC1,E,Rest]), halt(1)} ),
                            { string_codes(FormStr, Cs), Term =.. [Tag, FormStr] },
                            top_entities(Fs,LC2).
