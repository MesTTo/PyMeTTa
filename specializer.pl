:- dynamic ho_specialization/2.

%Maybe specializes HV(AVs) if not already ongoing, and if specialization fails, nothing changes and specneeded is restored:
maybe_specialize_call(HV, _, _, _) :- catch(nb_getval(stack, S), _, S = []),
                                      memberchk(HV, S), !, fail.
maybe_specialize_call(HV, AVs, Out, Goal) :- catch(nb_getval(stack, S0), _, S0 = []),
                                             S = [HV|S0],
                                             nb_setval(stack, S),
                                             setup_call_cleanup( (catch(nb_getval(specneeded,Prev),_,Prev = []), nb_setval(specneeded,false)),
                                                                 specialize_call(HV, AVs, Out, Goal),
                                                                 (catch(nb_getval(stack, [_|S1]), _, S1 = []), nb_setval(stack, S1), (Prev == true -> nb_setval(specneeded,Prev))) ).

%Specialize a call by creating and translating a specialized version of the MeTTa code:
specialize_call(HV, AVs, Out, Goal) :- %1.  Skip specialization when HV is the function currently being compile:
                                       \+ catch(nb_getval(HV, HV), _, HV = none),
                                       %2. Retrieve a copy of all meta-clauses stored for HV:
                                       catch(nb_getval(HV, MetaList0), _, fail),
                                       copy_term(MetaList0, MetaList),
                                       %3. Copy all clause variables eligible for specialization across all meta-clauses:
                                       setof(HoVar, ArgsNorm^BodyExpr^HoBinds^HoBindsPerArg^
                                                    ( member(fun_meta(ArgsNorm, BodyExpr), MetaList),
                                                      maplist(specializable_vars(BodyExpr), AVs, ArgsNorm, HoBinds),
                                                      member(HoBindsPerArg, HoBinds),
                                                      member(HoVar, HoBindsPerArg),
                                                      nonvar(HoVar) ), BindSet),
                                       copy_term(BindSet,BindSetC),
                                       %4. Build the specialization name from the concrete higher-order bind set:
                                       term_variables(BindSetC,Vars),
                                       maplist(=(var),Vars),
                                       maplist(term_to_atom,BindSetC,BindSetAtom),
                                       atomic_list_concat([HV, '_Spec_' | BindSetAtom], SpecName),
                                       %5. Replace calls to HV with SpecName inside each clause body:
                                       maplist({HV,SpecName}/[fun_meta(Args,Body),fun_meta(Args,BodySubst)]>>substitute_nested(HV,Args,SpecName,Body,BodySubst), MetaList, MetaSubsts),
                                       %6. Specialize, but only if not already specialized:
                                       ( ho_specialization(HV, SpecName)
                                         ; ( %6.1. Otherwise register the specialization:
                                             register_fun(SpecName),
                                             length(AVs, N),
                                             Arity is N + 1,
                                             assertz(arity(SpecName, Arity)),
                                             ( %6.2. Re-use the type definition of the parent function for the specialization:
                                               ( catch(match('&self', [':', HV, TypeChain], TypeChain, TypeChain), _, fail)
                                                 -> add_sexp('&self', [':', SpecName, TypeChain]) ; true ),
                                               %6.3 Translate specialized MeTTa clauseses to Prolog, keeping track of the function we are compiling through recursion:
                                               catch(nb_getval(PrevCurrent, PrevCurrent), _, PrevCurrent = none),
                                               call_cleanup( maplist({SpecName}/[fun_meta(ArgsNorm,BodyExpr),clause_info(Input,Clause)]>>
                                                                     ( Input = [=,[SpecName|ArgsNorm],BodyExpr], translate_clause_(Input,Clause,false) ), MetaSubsts, ClauseInfos),
                                                             ( PrevCurrent == none -> catch(nb_delete(current), _, true) ; nb_setval(current, PrevCurrent) )),
                                               %6.4 Only proceeed specializing if any recursive call profited from specialization with the specialized function at head position:
                                               nb_getval(specneeded, true),
                                               %6.5 Assert and print each of the created specializations:
                                               forall(member(clause_info(Input, Clause), ClauseInfos),
                                               ( assertz(Clause),
                                                 format(atom(Label), "metta specialization (~w)", [SpecName]),
                                                 maybe_print_compiled_clause(Label, Input, Clause) )),
                                               assertz(ho_specialization(HV, SpecName))
                                               %6.6 Ok specialized, but if we did not succeed ensure the specialization is retracted:
                                               -> true ; format("Not specialized ~w~n", [SpecName/Arity]),
                                                         unregister_fun(SpecName/Arity),
                                                         retractall(arity(SpecName,Arity)), fail ))), !,
                                       %7. Generate call to the specialized function:
                                       append(AVs, [Out], CallArgs),
                                       Goal =.. [SpecName|CallArgs].

%Recursively replaces occurrences of the old function name with the specialized name inside nested expressions:
substitute_nested(_, _, _, Val, Out) :- (var(Val) -> Out = Val ; Val == [] -> Out = []), !.
substitute_nested(Old,Args, New, [H|T], [H2|T2]) :- maplist([Arg,ArgClean]>>( nonvar(Arg), Arg = partial(Base, Bound) -> ArgClean = [Base|Bound] ; ArgClean = Arg ), Args, ArgsClean),
                                                    ( is_list(H) -> substitute_nested(Old, Args, New, H, H2)
                                                                  ; ( H == Old , (\+ \+ Args = T ; \+ \+ ArgsClean = T) -> H2 = New ; H2 = H )),
                                                    substitute_nested(Old, Args, New, T, T2).

%Extracts clause-head variables and their call-site copies, producing eligible Var–Copy pairs for specialization:
specializable_vars(_, Value, _, []) :- var(Value), !.
specializable_vars(BodyExpr, Value, Arg, HoVars) :- term_variables(Arg, Vars),
                                                    copy_term(Arg-Vars, Value-VarsCopy),
                                                    eligible_var_pairs(Vars, VarsCopy, BodyExpr, HoVars).

%Selects and unifies variable–argument pairs that act as higher-order or head operands in the body:
eligible_var_pairs([], [], _, []).
eligible_var_pairs([Var|Vars], [Copy|Copies], BodyExpr, HoVars) :- ( specializable_arg(Copy), (var_use_check(head, Var, BodyExpr) ; var_use_check(ho, Var, BodyExpr))
                                                                     -> Var = Copy,
                                                                        HoVars = [Var|RestHoVars]
                                                                      ; HoVars = RestHoVars ),
                                                                   eligible_var_pairs(Vars, Copies, BodyExpr, RestHoVars).

%If Var appears at list head it means function call, meaning specialization is needed, and detect when used as HOL arg
var_use_check(head, Var, [Head|_]) :- Var == Head,
                                      nb_setval(specneeded, true).
var_use_check(ho, Var, [Head|Args]) :- specializable_arg(Head),
                                       member(Arg, Args),
                                       ( Var == Arg
                                       ; is_list(Arg),
                                         var_use_check(ho, Var, Arg) ).
var_use_check(Mode, Var, L) :- is_list(L),
                               member(E, L),
                               is_list(E),
                               var_use_check(Mode, Var, E).

%Tests whether an argument represents a specializable function or partial application:
specializable_arg(Arg) :- nonvar(Arg), 
                          ( fun(Arg) ; Arg = partial(_, _) ).
