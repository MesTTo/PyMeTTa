maybe_specialize_call(HV, AVs, Out, Goal) :- setup_call_cleanup( (catch(nb_getval(specsucess,Prev),_,Prev = []), nb_setval(specsucess,false) ),
                                                                 maybe_specialize_call_(HV, AVs, Out, Goal),
                                                                 (Prev == true ->  nb_setval(specsucess,Prev) ; true) ).

maybe_specialize_call_(HV, AVs, Out, Goal) :- \+ current_function(HV), %We are compiling HV don't try to specialize it
                                              catch(nb_getval(HV, MetaList0), _, fail), %Get all the info about HV
                                              copy_term(MetaList0, MetaList),           %Make a copy to specialize
                                              bind_specialized_args_meta_list(AVs,MetaList,BindSet),
                                              copy_term(BindSet,BindSetC), term_variables(BindSetC,Vars), %Create name
                                              maplist(=(var),Vars), maplist(term_to_atom,BindSetC,BindSetAtom),
                                              atomic_list_concat([HV, '_Spec_' | BindSetAtom], SpecName),
                                              maplist({HV,SpecName}/[fun_meta(Args,Body),fun_meta(Args,BodySubst)]>>substitute_nested(HV,Args,SpecName,Body,BodySubst),MetaList,MetaSubsts),
                                              ( ho_specialization(HV, SpecName)     %Previously specialzed function
                                                ; ( register_fun(SpecName), %Register Stuff
                                                    length(AVs, N),Arity is N + 1,assertz(arity(SpecName, Arity)),
                                                    ( compile_specialization(HV, MetaSubsts, SpecName) %Compile new Spec
                                                      -> true ; format("Fail unregister~n"), unregister_fun(SpecName/Arity),retractall(arity(SpecName,Arity)),fail ) ) ), !,
                                              append(AVs, [Out], CallArgs),
                                              Goal =.. [SpecName|CallArgs].

substitute_nested(_, _, _, Val, Out) :- (var(Val) -> Out = Val ; Val == [] -> Out = []), !.
substitute_nested(Old,Args, New, [H|T], [H2|T2]) :- maplist([Arg,ArgClean]>>( nonvar(Arg), Arg = partial(Base, Bound) -> ArgClean = [Base|Bound] ; ArgClean = Arg ), Args, ArgsClean),
                                                    ( is_list(H) -> substitute_nested(Old, Args, New, H, H2)
                                                                  ; ( H == Old , (\+ \+ Args = T ; \+ \+ ArgsClean = T) -> H2 = New ; H2 = H )),
                                                    substitute_nested(Old, Args, New, T, T2).
    
compile_specialization(HV, MetaList, SpecName) :- ( catch(match('&self', [':', HV, TypeChain], TypeChain, TypeChain), _, fail)
                                                    -> add_sexp('&self', [':', SpecName, TypeChain]) ; true ),
                                                  current_function(PrevCurrent),
                                                  call_cleanup( maplist(compile_meta_clauses(SpecName),MetaList,ClauseInfos),
                                                                restore_current(PrevCurrent) ),
                                                  nb_getval(specsucess,true),
                                                  maplist(assert_specialization_clause(SpecName), ClauseInfos),
                                                  assertz(ho_specialization(HV, SpecName)).

assert_specialization_clause(SpecName, clause_info(Input, Clause)) :- assertz(Clause),
                                                                      format(atom(Label), "metta specialization (~w)", [SpecName]),
                                                                      maybe_print_compiled_clause(Label, Input, Clause).

compile_meta_clauses(SpecName, fun_meta(ArgsNorm, BodyExpr), clause_info(Input, Clause)) :- Input = [=, [SpecName|ArgsNorm], BodyExpr],
                                                                                            translate_clause_(Input, Clause,false).

nb_addval(Key,Value) :- catch(nb_getval(Key,Prev), _, Prev =[]),
                        nb_setval(Key,[Value|Prev]).

current_function(Current) :- catch(nb_getval(current, Current), _, Current = none).

next_lambda_name(Name) :- ( catch(nb_getval(lambda_counter, Prev), _, Prev = 0) ),
                          N is Prev + 1,
                          nb_setval(lambda_counter, N),
                          format(atom(Name), 'lambda_~d', [N]).

restore_current(none) :- catch(nb_delete(current), _, true), !.
restore_current(Value) :- nb_setval(current, Value).

bind_specialized_args_meta_list(Values, MetaList, HoBindSet) :- setof(HoVar,
                                                                      ArgsNorm^BodyExpr^HoBinds^HoBindsPerArg^
                                                                      ( member(fun_meta(ArgsNorm, BodyExpr), MetaList),
                                                                        maplist(bind_specialized_args(BodyExpr), Values, ArgsNorm, HoBinds),
                                                                        member(HoBindsPerArg, HoBinds),
                                                                        member(HoVar, HoBindsPerArg),
                                                                        nonvar(HoVar) ),
                                                                      HoBindSet).

bind_specialized_args(_, Value, _, []) :- var(Value), !.
bind_specialized_args(BodyExpr, Value, Arg, HoVars) :- term_variables(Arg, Vars),
                                                       copy_term(Arg-Vars, Value-VarsCopy),
                                                       bind_specialized_args_(Vars, VarsCopy, BodyExpr, HoVars).

bind_specialized_args_([], [], _, []).
bind_specialized_args_([Var|Vars], [Copy|Copies], BodyExpr, HoVars) :- ( specializable_arg(Copy), (var_used_as_head(Var, BodyExpr) ; var_used_as_ho_arg(Var, BodyExpr))
                                                                         -> Var = Copy, HoVars = [Var|RestHoVars]
                                                                          ; HoVars = RestHoVars ),
                                                                       bind_specialized_args_(Vars, Copies, BodyExpr, RestHoVars).

var_used_as_head(Var, [Head|_]) :- Var == Head, nb_setval(specsucess,true), !.
var_used_as_head(Var, L) :- is_list(L), member(E,L), is_list(E), var_used_as_head(Var,E).

var_used_as_ho_arg(Var, [Head|Args]) :- specializable_arg(Head),
                                        member(Arg, Args),
                                        ( Var == Arg                     % directly as argument
                                          ; is_list(Arg),
                                            var_used_as_ho_arg(Var, Arg) ). % or deeper inside
var_used_as_ho_arg(Var, L) :- is_list(L),
                              member(E,L),
                              is_list(E),
                              var_used_as_ho_arg(Var,E).

specializable_arg(Arg) :- nonvar(Arg), 
                          ( atom(Arg), fun(Arg) ; Arg = partial(_, _)).
