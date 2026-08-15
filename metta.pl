% Purpose: provide PeTTa's Prolog runtime, builtins, type system, evaluator,
%   imports, function registration, and named-space execution context.
% Guarantees:
%   - get-type/2 returns each derived type once, while has_type/2 uses one
%     witness for a fixed expected type [tested 2026-08-15:
%     metta_type_answers, translator_typed_checks].
%   - Import lifecycle state is separate from atom storage, so wildcard atom
%     removal cannot make a loaded source run twice [tested 2026-08-15:
%     filereader_import_lifecycle].
%   - Host failures from builtins retain their ISO error class and name the
%     written MeTTa operation [tested 2026-08-15:
%     metta_operation_errors, translator_evaluation_errors]. Integer
%     arithmetic pays nothing for this and float arithmetic pays one
%     inference per call, because only the integer pair takes the guarded
%     fast path [measured 2026-08-15: 300,000 and 400,000 inferences per
%     100,000 calls, against 300,000 unguarded]. Whole-corpus cost is
%     +2.1% instructions on examples/performance/scale.metta
%     [measured 2026-08-15].
%   - is-alpha-member/3 tests unifiability without retaining bindings in its
%     arguments [tested 2026-08-15: metta_alpha_membership].
%   - alpha-unique-atom/2 confirms identity inside each term-hash bucket, so a
%     hash collision cannot remove an inequivalent term [tested 2026-08-15:
%     metta_alpha_unique].
%   - get-metatype/2 classifies every Prolog term used as a MeTTa value
%     [tested 2026-08-14: metta_metatypes].
%   - Test assertions distinguish no answer from one empty-expression answer
%     [tested 2026-08-14: translator_test_answers].
%   - Runtime builtins reject prebound outputs that they would not produce
%     [tested 2026-08-14: metta_builtin_outputs].
%   - Function registration performed by a source load participates in that
%     load's rollback [tested 2026-08-14: filereader_source_rollback].
%   - Python source imports restore sibling modules and sys.path after setup
%     or execution errors [tested 2026-08-14:
%     metta_python_import_cleanup].
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

%%%%%%%%%% Dependencies %%%%%%%%%%
library(X, Path) :- standard_library_path(Base),
                    directory_file_path(Base, X, Path).
library(X, Y, Path) :- git_library_path(X, Base),
                       directory_file_path(Base, Y, Path).
:- prolog_load_context(directory, Source),
   directory_file_path(Source, '..', Parent),
   directory_file_path(Parent, 'lib', LibPath),
   asserta(standard_library_path(LibPath)).
:- autoload(library(uuid)).
:- use_module(library(crypto)).
:- use_module(library(random)).
:- use_module(library(janus)).
:- use_module(library(error)).
:- use_module(library(listing)).
:- use_module(library(aggregate)).
:- use_module(library(thread)).
:- use_module(library(lists)).
:- use_module(library(yall), except([(/)/3])).
:- use_module(library(apply)).
:- use_module(library(apply_macros)).
:- use_module(library(process)).
:- use_module(library(filesex)).
:- current_prolog_flag(argv, Argv),
   ( member(mork, Argv) -> ensure_loaded([ext_points, parser, translator, specializer, filereader, '../lib/lib_gitimport', '../mork_ffi/morkspaces', spaces, tracer])
                         ; ensure_loaded([ext_points, parser, translator, specializer, filereader, '../lib/lib_gitimport', spaces, tracer])).

%%%%%%%%%% Standard Library for MeTTa %%%%%%%%%%

%%% Representation and parsing conversions: %%%
id(X, X).
repr(Term, R) :- swrite(Term, Text), R = Text.
repra(Term, R) :- term_to_atom(Term, R).
parse(Str, R) :- sread(Str, R).

%%% Arithmetic & Comparison: %%%
%An arithmetic operand is a number. Everything else is refused here, before
%is/2 applies Prolog's own coercion rules to it.
%
%Two things came through that door. A MeTTa expression IS a Prolog list, and
%SWI reads a one-element list as a character code, so (+ 1 (g)) quietly
%answered 104, the code of g, and (* 2 (z)) answered 244: a symbol's SPELLING
%became a number, while the two-element case raised.
%
%Worse, Prolog's evaluable atoms silently outranked MeTTa. With (= pi 3.14)
%defined, (+ 1 pi) answered 4.141592653589793 from SWI's constant rather than
%4.14 from the user's own equation. A constant belongs in a MeTTa library as
%an ordinary rewrite, (= (my-pi) 3.14), which reduces before arithmetic sees
%it and now wins because nothing shadows it.
%
%Nobody chose either behaviour; both fall out of is/2. The whole corpus, 169
%programs including the ones passing inf and nan around, is unaffected
%[tested: metta_arithmetic_operands].
%An unbound operand is left to is/2, which raises instantiation_error for it,
%the answer Prolog and ISO both give; refusing it as a type error here would
%report a missing value as a wrong one.
%Both operands in one call: the inline type tests are free, the call is not,
%so checking them separately cost two inferences per operation instead of one
%[measured 2026-08-15: alpha-unique +200,010 against +100,005].
metta_arith_operands(Op, A, B) :-
    ( var(A) -> true ; number(A) -> true ; throw_metta_type_error(Op, number, A) ),
    ( var(B) -> true ; number(B) -> true ; throw_metta_type_error(Op, number, B) ).

'+'(A,B,R)  :- ( integer(A), integer(B) -> R is A + B
                ; metta_arith_operands('+', A, B),
                  catch(R is A + B, E, rethrow_metta_operation_error('+', E)) ).
'-'(A,B,R)  :- ( integer(A), integer(B) -> R is A - B
                ; metta_arith_operands('-', A, B),
                  catch(R is A - B, E, rethrow_metta_operation_error('-', E)) ).
'*'(A,B,R)  :- ( integer(A), integer(B) -> R is A * B
                ; metta_arith_operands('*', A, B),
                  catch(R is A * B, E, rethrow_metta_operation_error('*', E)) ).
'/'(A,B,R)  :- ( integer(A), integer(B), B =\= 0 -> R is A / B
                ; metta_arith_operands('/', A, B),
                  catch(R is A / B, E, rethrow_metta_operation_error('/', E)) ).
'%'(A,B,R)  :- ( integer(A), integer(B), B =\= 0 -> R is A mod B
                ; metta_arith_operands('%', A, B),
                  catch(R is A mod B, E, rethrow_metta_operation_error('%', E)) ).
'<'(A,B,R)  :- ( number(A), number(B) -> (A<B -> R=true ; R=false)
                ; metta_arith_operands('<', A, B),
                  catch((A<B -> R=true ; R=false), E,
                        rethrow_metta_operation_error('<', E)) ).
'>'(A,B,R)  :- ( number(A), number(B) -> (A>B -> R=true ; R=false)
                ; metta_arith_operands('>', A, B),
                  catch((A>B -> R=true ; R=false), E,
                        rethrow_metta_operation_error('>', E)) ).
'=='(A,B,R) :- (A==B -> R=true ; R=false).
'!='(A,B,R) :- (A==B -> R=false ; R=true).
'='(A,B,R) :-  (A=B -> R=true ; R=false).
'=?'(A,B,R) :- (\+ \+ A=B -> R=true ; R=false).
'=alpha'(A,B,R) :- (A =@= B -> R=true ; R=false).
'=@='(A,B,R) :- (A =@= B -> R=true ; R=false).
'<='(A,B,R) :- ( number(A), number(B) -> (A =< B -> R=true ; R=false)
                ; metta_arith_operands('<=', A, B),
                  catch((A =< B -> R=true ; R=false), E,
                        rethrow_metta_operation_error('<=', E)) ).
'>='(A,B,R) :- ( number(A), number(B) -> (A >= B -> R=true ; R=false)
                ; metta_arith_operands('>=', A, B),
                  catch((A >= B -> R=true ; R=false), E,
                        rethrow_metta_operation_error('>=', E)) ).
min(A,B,R)  :- ( integer(A), integer(B) -> R is min(A,B)
                ; metta_arith_operands(min, A, B),
                  catch(R is min(A,B), E,
                        rethrow_metta_operation_error(min, E)) ).
max(A,B,R)  :- ( integer(A), integer(B) -> R is max(A,B)
                ; metta_arith_operands(max, A, B),
                  catch(R is max(A,B), E,
                        rethrow_metta_operation_error(max, E)) ).
exp(Arg,R) :- catch(R is exp(Arg), E,
                    rethrow_metta_operation_error(exp, E)).
:- use_module(library(clpfd)).
'#+'(A, B, R) :- catch(R #= A + B, E,
                       rethrow_metta_operation_error('#+', E)).
'#-'(A, B, R) :- catch(R #= A - B, E,
                       rethrow_metta_operation_error('#-', E)).
'#*'(A, B, R) :- catch(R #= A * B, E,
                       rethrow_metta_operation_error('#*', E)).
'#div'(A, B, R) :- catch(R #= A div B, E,
                         rethrow_metta_operation_error('#div', E)).
'#//'(A, B, R) :- catch(R #= A // B, E,
                        rethrow_metta_operation_error('#//', E)).
'#mod'(A, B, R) :- catch(R #= A mod B, E,
                         rethrow_metta_operation_error('#mod', E)).
'#min'(A, B, R) :- catch(R #= min(A,B), E,
                         rethrow_metta_operation_error('#min', E)).
'#max'(A, B, R) :- catch(R #= max(A,B), E,
                         rethrow_metta_operation_error('#max', E)).
'#<'(A, B, true)  :- catch(A #< B, E,
                           rethrow_metta_operation_error('#<', E)), !.
'#<'(A, B, false) :- catch(A #>= B, E,
                           rethrow_metta_operation_error('#<', E)).
'#>'(A, B, true)  :- catch(A #> B, E,
                           rethrow_metta_operation_error('#>', E)), !.
'#>'(A, B, false) :- catch(A #=< B, E,
                           rethrow_metta_operation_error('#>', E)).
'#='(A, B, true)  :- catch(A #= B, E,
                           rethrow_metta_operation_error('#=', E)), !.
'#='(A, B, false) :- catch(A #\= B, E,
                           rethrow_metta_operation_error('#=', E)).
'#\\='(A, B, true)  :- catch(A #\= B, E,
                              rethrow_metta_operation_error('#\\=', E)), !.
'#\\='(A, B, false) :- catch(A #= B, E,
                              rethrow_metta_operation_error('#\\=', E)).
'pow-math'(A, B, Out) :- catch(Out is A ** B, E,
                               rethrow_metta_operation_error('pow-math', E)).
'sqrt-math'(A, Out) :- catch(Out is sqrt(A), E,
                             rethrow_metta_operation_error('sqrt-math', E)).
'abs-math'(A, Out) :-
    ( integer(A) -> Out is abs(A)
    ; catch(Out is abs(A), E,
            rethrow_metta_operation_error('abs-math', E)) ).
'log-math'(Base, X, Out) :- catch(Out is log(X) / log(Base), E,
                                  rethrow_metta_operation_error('log-math', E)).
'exp-math'(A, Out) :- catch(Out is exp(A), E,
                            rethrow_metta_operation_error('exp-math', E)).
'trunc-math'(A, Out) :- catch(Out is truncate(A), E,
                              rethrow_metta_operation_error('trunc-math', E)).
'ceil-math'(A, Out) :- catch(Out is ceil(A), E,
                             rethrow_metta_operation_error('ceil-math', E)).
'floor-math'(A, Out) :- catch(Out is floor(A), E,
                              rethrow_metta_operation_error('floor-math', E)).
'round-math'(A, Out) :- catch(Out is round(A), E,
                              rethrow_metta_operation_error('round-math', E)).
'sin-math'(A, Out) :- catch(Out is sin(A), E,
                            rethrow_metta_operation_error('sin-math', E)).
'cos-math'(A, Out) :- catch(Out is cos(A), E,
                            rethrow_metta_operation_error('cos-math', E)).
'tan-math'(A, Out) :- catch(Out is tan(A), E,
                            rethrow_metta_operation_error('tan-math', E)).
'asin-math'(A, Out) :- catch(Out is asin(A), E,
                             rethrow_metta_operation_error('asin-math', E)).
'acos-math'(A, Out) :- catch(Out is acos(A), E,
                             rethrow_metta_operation_error('acos-math', E)).
'atan-math'(A, Out) :- catch(Out is atan(A), E,
                             rethrow_metta_operation_error('atan-math', E)).
'isnan-math'(A, Out) :-
    catch(( A =:= A -> Out = false ; Out = true ), E,
          rethrow_metta_operation_error('isnan-math', E)).
'isinf-math'(A, Out) :-
    catch(( ( A =:= 1.0Inf ; A =:= -1.0Inf )
            -> Out = true ; Out = false ), E,
          rethrow_metta_operation_error('isinf-math', E)).
%must_be/2 walks the list a second time with a type check per element, so a
%numeric list costs 3x what min_list alone does [measured 2026-08-15: 20 calls
%over 50,000 elements, 3,000,220 against 1,000,060 inferences]. That buys
%'min-atom': Type error: `number' expected, found `a' in place of a leaked
%lists:min_list/3, which is the trade this file makes everywhere.
'min-atom'(List, Out) :- non_list(List), !, Out = [].
'min-atom'(List, Out) :- catch(( must_be(list(number), List),
                                min_list(List, Out) ), E,
                              rethrow_metta_operation_error('min-atom', E)).
'max-atom'(List, Out) :- non_list(List), !, Out = [].
'max-atom'(List, Out) :- catch(( must_be(list(number), List),
                                max_list(List, Out) ), E,
                              rethrow_metta_operation_error('max-atom', E)).

%%% Random Generators: %%%
'random-int'(Min, Max, Result) :-
    ( integer(Min), integer(Max), Min =< Max
      -> random_between(Min, Max, Result)
       ; catch(random_between(Min, Max, Result), E,
               rethrow_metta_operation_error('random-int', E)) ).
'random-int'('&rng', Min, Max, Result) :-
    ( integer(Min), integer(Max), Min =< Max
      -> random_between(Min, Max, Result)
       ; catch(random_between(Min, Max, Result), E,
               rethrow_metta_operation_error('random-int', E)) ).
'random-float'(Min, Max, Result) :-
    catch(( random(R), Result is Min + R * (Max - Min) ), E,
          rethrow_metta_operation_error('random-float', E)).
'random-float'('&rng', Min, Max, Result) :-
    catch(( random(R), Result is Min + R * (Max - Min) ), E,
          rethrow_metta_operation_error('random-float', E)).

%%% Boolean Logic: %%%
bool(true).
bool(false).
boolean_argument(_, Value) :- var(Value), !, bool(Value).
boolean_argument(_, true) :- !.
boolean_argument(_, false) :- !.
boolean_argument(Operation, Culprit) :-
    throw_metta_type_error(Operation, boolean, Culprit).

and(A,B,C) :- boolean_argument(and, A), boolean_argument(and, B),
              ( A == true -> C = B ; A == false -> C = false ).
or(A,B,C) :- boolean_argument(or, A), boolean_argument(or, B),
             ( A == true -> C = true ; A == false -> C = B ).
not(A,B) :- boolean_argument(not, A),
            ( A == true -> B = false ; A == false -> B = true ).
xor(A,B,C) :- boolean_argument(xor, A), boolean_argument(xor, B),
              ( A == B -> C = false ; C = true ).
implies(A,B,C) :- boolean_argument(implies, A),
                  boolean_argument(implies, B),
                  ( A == true -> ( B == true  -> C = true
                                 ; B == false -> C = false )
                              ; A == false -> C = true ).

%%% Nondeterminism: %%%
superpose(L,X) :- member(X,L).
empty(_) :- fail.

%%% Lists / Tuples: %%%
'cons-atom'(H, T, [H|T]).
'decons-atom'([H|T], [H|[T]]).
'first-from-pair'([A, _], A).
first([A, _], A).
'second-from-pair'([_, A], A).
'unique-atom'(A, B) :- non_list(A), !, B = [].
'unique-atom'(A, B) :- list_to_set(A, B).

%%% Alpha-equivalence unique atom %%%
'alpha-unique-atom'(A, B) :- non_list(A), !, B = [].
'alpha-unique-atom'(A, B) :- alpha_list_to_set(A, B).

alpha_list_to_set(List, Set) :-
    empty_assoc(Seen0),
    alpha_list_to_set_assoc(List, Seen0, Set).

alpha_list_to_set_assoc([], _, []).
alpha_list_to_set_assoc([H|T], SeenIn, R) :-
    copy_term(H, HCopy),
    numbervars(HCopy, 0, _),
    term_hash(HCopy, Key),
    alpha_bucket_insert(Key, HCopy, SeenIn, SeenOut, IsNew),
    ( IsNew == false ->
        alpha_list_to_set_assoc(T, SeenIn, R)
    ;
        R = [H|RT],
        alpha_list_to_set_assoc(T, SeenOut, RT)
    ).

%A term hash selects a small bucket. Identity inside the bucket decides alpha
%equivalence, because canonical terms produced above are ground.
alpha_bucket_insert(Key, Term, SeenIn, SeenOut, IsNew) :-
    ( get_assoc(Key, SeenIn, Bucket) ->
        ( memberchk_eq(Term, Bucket) ->
            SeenOut = SeenIn,
            IsNew = false
        ;
            put_assoc(Key, SeenIn, [Term|Bucket], SeenOut),
            IsNew = true
        )
    ;
        put_assoc(Key, SeenIn, [Term], SeenOut),
        IsNew = true
    ).

%A term that can never become a list, no matter how it gets instantiated:
non_list(X) :- atomic(X), X \== [].
non_list(X) :- compound(X), X \= [_|_].

'sort-atom'(List, Sorted) :- non_list(List), !, Sorted = [].
'sort-atom'(List, Sorted) :- msort(List, Sorted).
'size-atom'(List, Size) :- non_list(List), !, Size = [].
'size-atom'(List, Size) :- length(List, Size).
'car-atom'([H|_], H) :- !.
'car-atom'(Term, []) :- \+ Term = [_|_].
'cdr-atom'([_|T], T) :- !.
'cdr-atom'(Term, []) :- \+ Term = [_|_].
decons([H|T], [H|[T]]).
cons(H, T, [H|T]).
'index-atom'(_, Index, Elem) :- nonvar(Index), \+ integer(Index), !,
                                Elem = [].
'index-atom'(List, Index, Elem) :- var(Index), !,
                                  nth0(Index, List, Elem).
'index-atom'(List, Index, Elem) :-
    ( nth0(Index, List, Value) -> Elem = Value ; Elem = [] ).
member(X, L, true) :- member(X, L).
'is-member'(X, List, true) :- member(X, List).
'is-member'(X, List, false) :- \+ member(X, List).

%"Alpha" is historical. This predicate tests unifiability, with a bare query
%variable matching only a variable list element. Double negation at the public
%boundary keeps that test's bindings private; it is deliberately not =@=/2.
member_alpha(X, [H|_]) :- (var(X) -> var(H) ; true), X = H, !.
member_alpha(X, [_|T]) :- member_alpha(X, T).

'is-alpha-member'(X, List, true) :- \+ \+ member_alpha(X, List), !.
'is-alpha-member'(X, List, false) :- \+ member_alpha(X, List).

'exclude-item'(A, L, R) :- exclude(==(A), L, R).

%Remove the first element identical to X, keeping the rest in order. select/3
%unifies instead, which both answers wrongly and binds the caller's variables:
%(subtraction-atom ($x) (a)) came back () with $x bound to a. PeTTa's own
%formalisation removes by equality, in leanPeTTa/StreamOps.lean:
%  removeFirstEq (x : Pattern) : List Pattern -> Option (List Pattern)
%    | y :: ys => if y == x then some ys else ...
select_eq(X, [Y|Ys], Ys) :- X == Y, !.
select_eq(X, [Y|Ys], [Y|Rest]) :- select_eq(X, Ys, Rest).

%Multisets. Keep the variable-headed non-list fallback last so list calls use
%the first argument index. Over 100,000 two-element calls this reduced each
%operation from 2,200,002 to 1,400,002 inferences [measured: 800,000 fewer
%inferences per operation, 2026-08-15]. The list clauses still handle a
%non-list right operand before recursing, preserving the empty-tuple result.
'subtraction-atom'([], _, []) :- !.
'subtraction-atom'([H|T], B, Out) :- !,
    ( non_list(B) -> Out = []
    ; select_eq(H, B, BRest) -> 'subtraction-atom'(T, BRest, Out)
    ; Out = [H|Rest],
      'subtraction-atom'(T, B, Rest) ).
'subtraction-atom'(A, B, Out) :- ( non_list(A) ; non_list(B) ), !, Out = [].
%The guard its two siblings already have, and it leads rather than trails
%because append/3 succeeds on a non-list right operand: (union-atom (a) b)
%built the improper list [a|b], printed as (cons a b), which is not a tuple
%and cannot be consumed by any tuple operation. A non-list left operand
%failed silently. The empty-tuple answer is this family's settled convention.
%
%non_list/1 is false for an unbound argument, which is load-bearing: lib_roman
%calls (union-atom $xs ($x)) with $xs unbound to SPLIT a list, so append/3
%must still be reached in its relational modes
%[tested: metta_set_operations, examples/libraries/roman_test.metta].
'union-atom'(A, B, Out) :- ( non_list(A) ; non_list(B) ), !, Out = [].
'union-atom'(A, B, Out) :- append(A, B, Out).
'intersection-atom'([], _, []) :- !.
'intersection-atom'([H|T], B, Out) :- !,
    ( non_list(B) -> Out = []
    ; select_eq(H, B, BRest) -> Out = [H|Rest],
                                'intersection-atom'(T, BRest, Rest)
    ; 'intersection-atom'(T, B, Out) ).
'intersection-atom'(A, B, Out) :- ( non_list(A) ; non_list(B) ), !, Out = [].

%%% Type system: %%%

%The space whose ':' declarations are in scope. A space's compiled clauses live
%in a module named after it, and space_module/2 is '&self' -> user and the
%identity otherwise, so inverting it recovers the space with no extra state to
%keep.
%
%Without this, get-type consulted '&self' literally, and a declaration made in
%any other space was invisible to it. That is not an edge case: every space
%PyPeTTa creates is a named one, so `(: a A)` written there answered
%'%Undefined%' no matter what.
current_metta_space(Space) :- current_metta_module(Module),
                              ( Module == user -> Space = '&self' ; Space = Module ).

%A ':' declaration in scope here: this space's, and &self's, since &self is the
%shared space. That is the rule fun_here/1 already applies to functions.
type_declaration(X, T) :- current_metta_module(Module),
                          type_declaration_in(Module, X, T).

type_declaration_in(user, X, T) :- !, match('&self', [':', X, T], T, _).
type_declaration_in(Module, X, T) :- (   match(Module, [':', X, T], T, _)
                                     ;   match('&self', [':', X, T], T, _) ).

%&self is always the engine's native space. Its fixed private storage module
%keeps this recursive type probe on a compiled direct call, with no provider
%dispatch or exception handler.
get_function_type([F|Args], T) :- nonvar(F),
                                  '$petta_atoms:&self':'&self'(':', F, [->|Ts]),
                                  append(As,[T],Ts),
                                  maplist(has_type_in(user), Args, As).
get_function_type_in(Module, [F|Args], T) :- Module \== user,
                                             nonvar(F),
                                             type_declaration_in(Module, F, [->|Ts]),
                                             append(As,[T],Ts),
                                             maplist(has_type_in(Module), Args, As).

:- dynamic get_type_rule/2.
%get-type is the user-facing set boundary. Candidate derivations may overlap,
%for example an expression can be typed both element-wise and by an explicit
%declaration. Collecting candidates and retaining each first occurrence removes
%those duplicate answers without changing the declared type order.
%Internal checks call has_type/2 instead: a fixed expected type stops at its
%first witness, while an unbound shared type variable still enumerates the
%distinct choices needed to make later arguments consistent.
'get-type'(X, T) :- current_metta_module(Module),
                    type_answers(Module, X, Types),
                    member(T, Types).

has_type(X, T) :- current_metta_module(Module),
                  has_type_in(Module, X, T).

%The first-witness shortcut is only sound for a GROUND expected type. A
%parametric one such as (Pair $t) is nonvar but still carries a variable the
%later arguments must agree on, and once/1 commits to whichever witness came
%first: with (: p1 (Pair A)), (: p1 (Pair B)) and (: p2 (Pair B)) declared,
%(samepair p1 p2) answered nothing while (samepair p2 p1) answered True, from
%one symmetric definition [tested metta_shared_type_variables].
has_type_in(Module, X, T) :-
    ( ground(T)
      -> ( T == '%Undefined%'
           -> \+ once(type_candidate_in(Module, X, _))
            ; once(type_candidate_in(Module, X, T)) )
       ; type_answers(Module, X, Types),
         member(T, Types) ).

type_answers(Module, X, Types) :-
    findall(Type, type_candidate_in(Module, X, Type), Candidates),
    unique_type_answers(Candidates, Unique),
    ( Unique == [] -> Types = ['%Undefined%'] ; Types = Unique ).

%Canonical keys make alpha-equivalent polymorphic types equal. The two stable
%sorts remove repeats in O(n log n) work and then restore derivation order,
%which is observable through collapse.
unique_type_answers(Candidates, Unique) :-
    type_answer_pairs(Candidates, 0, Pairs),
    keysort(Pairs, ByType),
    first_type_per_key(ByType, Indexed),
    keysort(Indexed, ByIndex),
    pairs_values(ByIndex, Unique).

type_answer_pairs([], _, []).
type_answer_pairs([Type|Types], Index, [Key-(Index-Type)|Pairs]) :-
    copy_term(Type, Key),
    numbervars(Key, 0, _),
    Next is Index + 1,
    type_answer_pairs(Types, Next, Pairs).

first_type_per_key([], []).
first_type_per_key([Key-Indexed|Pairs], [Indexed|Unique]) :-
    skip_type_key(Pairs, Key, Rest),
    first_type_per_key(Rest, Unique).

skip_type_key([Other-_|Pairs], Key, Rest) :- Other == Key, !,
                                             skip_type_key(Pairs, Key, Rest).
skip_type_key(Pairs, _, Pairs).

type_candidate_in(user, X, T) :- get_type_candidate(X, T).
type_candidate_in(Module, X, T) :- Module \== user,
                                   get_type_candidate_in(Module, X, T).
type_candidate_in(Module, X, T) :- get_type_rule_in(Module, X, T).

get_type_rule_in(Module, X, T) :- Module \== user,
                                  fun_in(Module, 'get-type'),
                                  Module:get_type_rule(X, T).
get_type_rule_in(_, X, T) :- get_type_rule(X, T).

get_type_candidate(X, 'Number')   :- number(X), !.
get_type_candidate(X, _) :- var(X), !.
get_type_candidate(X, 'String')   :- string(X), !.
get_type_candidate(true, 'Bool')  :- !.
get_type_candidate(false, 'Bool') :- !.
%Only PyObject blobs can be Janus references. The blob guard avoids calling
%into Janus, and initializing Python, while typing ordinary MeTTa values;
%py_is_object/1 still validates a live reference and reports a freed one.
get_type_candidate(X, T) :- atomic(X), \+ atom(X),
                            blob(X, 'PyObject'), py_is_object(X), py_object_type(X, T).
get_type_candidate(X, T) :- get_function_type(X,T).
get_type_candidate(X, T) :- \+ get_function_type(X, _),
                            is_list(X),
                            maplist(has_type_in(user), X, T).
get_type_candidate(X, T) :- '$petta_atoms:&self':'&self'(':', X, T),
                            acyclic_term(T).

get_type_candidate_in(_, X, 'Number')   :- number(X), !.
get_type_candidate_in(_, X, _) :- var(X), !.
get_type_candidate_in(_, X, 'String')   :- string(X), !.
get_type_candidate_in(_, true, 'Bool')  :- !.
get_type_candidate_in(_, false, 'Bool') :- !.
get_type_candidate_in(_, X, T) :- atomic(X), \+ atom(X),
                                  blob(X, 'PyObject'), py_is_object(X), py_object_type(X, T).
get_type_candidate_in(Module, X, T) :- get_function_type_in(Module, X, T).
get_type_candidate_in(Module, X, T) :- \+ get_function_type_in(Module, X, _),
                                       is_list(X),
                                       maplist(has_type_in(Module), X, T).
get_type_candidate_in(Module, X, T) :- type_declaration_in(Module, X, T).
%A grounded Python object is Grounded, and its Python classes are its types:
%every class on the object's method resolution order short of object itself is
%a candidate, so a torch Linear is a Linear and a Module, in the same way
%MeTTa's own types are nondeterministic. This is what lets a declared
%(-> Tensor Tensor Tensor) hold for values the host created.
%A bridge that knows how to read the object answers with every type name at
%once, protocols included, as plain text the boundary cannot damage; without
%one, the class walk below runs, plus any engine-side extra types:
py_object_type(X, T) :- ( catch_recover(py_object_type_names(X, Names), fail)
                          -> member(N, Names),
                             ( atom(N) -> T = N ; atom_string(T, N) )
                        ; py_object_class_type(X, T) ).

py_object_class_type(X, T) :- py_call(builtins:type(X), Class),
                              py_call(builtins:getattr(Class, '__mro__'), MRO),
                              py_call(builtins:list(MRO), Classes),
                              member(C, Classes),
                              py_call(builtins:getattr(C, '__name__'), Name),
                              ( atom(Name) -> T = Name ; atom_string(T, Name) ),
                              T \== object.
%A protocol the object satisfies may name a type too, through the extension
%point, so (-> DLTensor ...) holds for every array library at once:
py_object_class_type(X, T) :- py_object_extra_type(X, T).

'get-metatype'(X, 'Variable') :- var(X), !.
'get-metatype'(X, 'Grounded') :- number(X), !.
'get-metatype'(X, 'Grounded') :- string(X), !.
'get-metatype'(true,  'Grounded') :- !.
'get-metatype'(false, 'Grounded') :- !.
'get-metatype'(X, 'Grounded') :- blob(X, 'PyObject'), py_is_object(X), !.
'get-metatype'(X, 'Grounded') :- atom(X), fun(X), !.  % e.g., '+' is a registered fun/1
'get-metatype'(X, 'Expression') :- is_list(X), !.     % e.g., (+ 1 2), (a b)
'get-metatype'(X, 'Symbol') :- atom(X), !.            % e.g., a
'get-metatype'(_, 'Grounded').                        % e.g., partial(f,[1]), f(1)

'is-var'(A,R) :- var(A) -> R=true ; R=false.
'is-ground'(A,R) :- ground(A) -> R=true ; R=false.
'is-expr'(A,R) :- is_list(A) -> R=true ; R=false.
'is-space'(A,R) :- atom(A), atom_concat('&', _, A) -> R=true ; R=false.

%%% Diagnostics / Testing: %%%
:- multifile prolog:error_message//1.

prolog:error_message(petta_test_failed(Actual, Expected)) -->
    [ 'MeTTa test failed: ~p does not match ~p'-[Actual, Expected] ].
prolog:error_message(petta_assertion_failed(Goal)) -->
    [ 'MeTTa assertion failed: ~p'-[Goal] ].
prolog:error_message(petta_test_no_answer) -->
    [ 'MeTTa test expression produced no answer'-[] ].

'println!'(Arg, true) :- swrite(Arg, RArg),
                         format('~w~n', [RArg]).

'readln!'(Out) :- read_line_to_string(user_input, Str),
                  sread(Str, Out).

test(A,B,true) :- (A =@= B -> E = '✅' ; E = '❌'),
                  swrite(A, RA),
                  swrite(B, RB),
                  format("is ~w, should ~w. ~w ~n", [RA, RB, E]),
                  ( A =@= B -> true
                  ; throw(error(petta_test_failed(A, B),
                                context(test/3, 'MeTTa test values differ'))) ).

test_answer_value([], _) :-
    throw(error(petta_test_no_answer,
                context(test/3, 'expected a value but expression produced no answer'))).
test_answer_value([Actual], Actual) :- !.
test_answer_value(Results, Results).

'test-no-answer'(Results, Out) :-
    test(Results, [], Out).

assert(Goal, true) :- ( call(Goal) -> true
                                    ; swrite(Goal, RG),
                                      format("Assertion failed: ~w~n", [RG]),
                                      throw(error(petta_assertion_failed(Goal),
                                                  context(assert/2, 'MeTTa assertion failed'))) ).

%%% The running space: %%%
% (context-space) answers the space whose module the current goal runs in,
% so a program loaded into a named space reaches its own atoms the way a
% program in &self writes (match &self ...); outside any named space the
% answer is &self.
'context-space'(Space) :- ( current_metta_space(Space) -> true ; Space = '&self' ).

%%% Time Retrieval: %%%
'current-time'(Time) :- get_time(Time).
'format-time'(Format, TimeString) :- get_time(Time), format_time(atom(TimeString), Format, Time).

%%% Python bindings: %%%
% janus converts Python booleans to @(true)/@(false); normalize them to the
% language booleans, through lists too, so py-call results compose with if,
% and, or, == whether the boolean is the answer or sits inside one.
py_bool_norm('@'(true), true) :- !.
py_bool_norm('@'(false), false) :- !.
py_bool_norm(L, L1) :- is_list(L), !, maplist(py_bool_norm, L, L1).
py_bool_norm(R, R).
% The same conversion outward: the language booleans are the atoms true and
% false, which janus would pass as the strings 'true' and 'false'; map them
% (through lists too) to @(true)/@(false) so Python receives real booleans.
py_arg_norm(true, '@'(true)) :- !.
py_arg_norm(false, '@'(false)) :- !.
py_arg_norm(L, L1) :- is_list(L), !, maplist(py_arg_norm, L, L1).
py_arg_norm(X, X).

:- dynamic python_import_alias/2.
python_call_module(Name, ModuleKey) :- python_import_alias(Name, ModuleKey), !.
python_call_module(Name, Name).
%The rewrite below only ever changes a spec that python_import_alias/2 names,
%so with no alias registered it is the identity, and its whole effect is to
%rebuild the term through maplist/3. The loader runs it over every form it
%reads, which measured at 71 inferences per form on a program that never
%touches Python. Ask first.
bind_python_calls(Term, Bound) :-
    ( python_import_alias(_, _)
      -> bind_python_calls_(Term, Bound)
       ; Bound = Term ).

bind_python_calls_(Term, Term) :- var(Term), !.
bind_python_calls_(Term, Term) :- atomic(Term), !.
bind_python_calls_([Call, [Spec|Args]], ['py-call', [BoundSpec|BoundArgs]]) :-
    Call == 'py-call', !,
    bind_python_call_spec(Spec, BoundSpec),
    maplist(bind_python_calls_, Args, BoundArgs).
bind_python_calls_(Terms, BoundTerms) :-
    maplist(bind_python_calls_, Terms, BoundTerms).

bind_python_call_spec(Spec, BoundSpec) :-
    atom(Spec),
    atomic_list_concat([Module, Function], '.', Spec),
    Module \== '',
    python_import_alias(Module, ModuleKey), !,
    atomic_list_concat([ModuleKey, Function], '.', BoundSpec).
bind_python_call_spec(Spec, Spec).
'py-call'(SpecList, Result) :- 'py-call'(SpecList, Result, []).
'py-call'([Spec|Args0], Result, Opts) :- ( string(Spec) -> atom_string(A, Spec) ; A = Spec ),
                                        must_be(atom, A),
                                        maplist(py_arg_norm, Args0, Args),
                                        ( sub_atom(A, 0, 1, _, '.')         % ".method"
                                          -> sub_atom(A, 1, _, 0, Fun),
                                             Args = [Obj|Rest],
                                             ( py_is_object(Obj)            % on a Python object reference
                                               -> ( Rest == []
                                                    -> compound_name_arguments(Meth, Fun, [])
                                                     ; Meth =.. [Fun|Rest] ),
                                                  py_call(Obj:Meth, R0, Opts), py_bool_norm(R0, Result)
                                                ; py_call(builtins:type(Obj), Ty), % on a converted value (str, int, ...)
                                                  Call =.. [Fun, Obj|Rest],
                                                  py_call(Ty:Call, R0, Opts), py_bool_norm(R0, Result) )
                                           ; atomic_list_concat([M,F], '.', A) % "mod.fun"
                                             -> ( Args == []
                                                  -> compound_name_arguments(Call0, F, [])
                                                   ; Call0 =.. [F|Args] ),
                                                python_call_module(M, PyModule),
                                                py_call(PyModule:Call0, R0, Opts), py_bool_norm(R0, Result)
                                              ; ( Args == []                      % bare "fun"
                                                  -> compound_name_arguments(Call0, A, [])
                                                   ; Call0 =.. [A|Args] ),
                                                py_call(builtins:Call0, R0, Opts), py_bool_norm(R0, Result) ).

%%% States: %%%
'bind!'(Var, ['new-state', Value], true) :-
    ( atom(Var) -> nb_setval(Var, Value)
    ; catch(nb_setval(Var, Value), E,
            rethrow_metta_operation_error('bind!', E)) ).
'change-state!'(Var, Value, true) :-
    ( atom(Var) -> nb_setval(Var, Value)
    ; catch(nb_setval(Var, Value), E,
            rethrow_metta_operation_error('change-state!', E)) ).
'get-state'(Var, Value) :-
    catch(nb_getval(Var, Value), E,
          rethrow_metta_operation_error('get-state', E)).

%%% Eval: %%%
%eval runs its goals in the current space's module, for the same reason
%call_goals_in/2 and current_metta_space/1 exist: call/1 resolves a goal in the
%module its clause was compiled in, so a module-blind call/1 reaches only user.
%Without this, `!(eval (f 1))` on a function defined in any space other than
%&self raised `call_goals/1: Unknown procedure: f/2` while the same `!(f 1)`
%answered normally, and every named space PyPeTTa creates hit it. lib_he's
%`unify` and the ToResult asserts route their branches through eval, so they
%failed there too [tested: test_per_space.py::test_eval_uses_the_spaces_own_equations].
%The unset case is `user`, which is what a bare call/1 already resolves to, so
%it keeps the original path and costs nothing on the default space; only a
%named space pays for the qualification.
eval(C, Out) :- translate_runnable_expr(C, Goals, Out),
                ( nb_current('$petta_module', Module)
                  -> call_goals_in_(Module, Goals)
                  ;  call_goals(Goals) ).

%evalc is eval in a space you name, the counterpart to context-space, which
%reports the space eval is already running in. Naming the space is the only
%way to reach another space's equations from MeTTa: import! loads a file into
%one, and everything else runs where it was written.
%
%The space argument selects the module the goals resolve in and nothing else.
%PeTTa's eval is a full evaluation of compiled goals rather than the single
%rewriting step of minimal MeTTa, and evalc keeps that, so the two agree
%everywhere except which space's equations answer
%[source: /home/user/Dev/LeaTTa/stdlib.md, evalc's SpaceType is the "Space to
%evaluate atom in its context"] [tested: metta_evalc].
%
%A space is an atom beginning with &, which is what is-space/2 tests, so an
%argument that is not one is a type error rather than a silently empty space.
evalc(C, Space, Out) :- ( 'is-space'(Space, true)
                          -> true
                          ;  throw_metta_type_error(evalc, 'SpaceType', Space) ),
                        space_module(Space, Module),
                        with_metta_module(Module, eval(C, Out)).

call_goals([]).
call_goals([G|Gs]) :- call(G), 
                      call_goals(Gs).

%As call_goals/1, but in a named module, so a form run against a space reaches
%that space's own equations. call/1 resolves in the module its clause was
%compiled in, which is why the module has to be named rather than inherited.
%The space's module is in force while the goals run, not only while they were
%compiled. Anything consulting the current space at call time needs it: get-type
%does, so without this a `(: a A)` written in a named space was invisible to
%`!(get-type a)` even though the two ran in the same space.
call_goals_in(Module, Goals) :- with_metta_module(Module, call_goals_in_(Module, Goals)).

call_goals_in_(_, []).
call_goals_in_(Module, [G|Gs]) :- call(Module:G),
                                  call_goals_in_(Module, Gs).

%%% Higher-Order Functions: %%%
'foldl-atom'([], Acc, _Func, Acc).
'foldl-atom'([H|T], Acc0, Func, Out) :- reduce([Func,Acc0,H], Acc1, _),
                                        'foldl-atom'(T, Acc1, Func, Out).

'map-atom'([], _Func, []).
'map-atom'([H|T], Func, [R|RT]) :- reduce([Func,H], R, _),
                                   'map-atom'(T, Func, RT).

'filter-atom'([], _Func, []).
'filter-atom'([H|T], Func, Out) :- ( reduce([Func,H], true, _) -> Out = [H|RT]
                                                             ; Out = RT ),
                                   'filter-atom'(T, Func, RT).

%%% Prolog interop: %%%
argv(K, Arg) :- current_prolog_flag(argv, Argv), nth0(K, Argv, A), ( atom_number(A, N) -> Arg = N ; Arg = A ).
import_prolog_function(N, true) :- register_fun(N).

%A Prolog library loaded from MeTTa belongs to the process, not to a space. Its
%predicates are builtins once loaded, register_fun/1 reads their arity out of
%user, and every space has to be able to call them. SWI loads a file into the
%module the load runs in, and under per-space equations a runnable form runs in
%its space's module, so a library imported inside a named space would define
%itself where register_fun/1 cannot see it: the arities never register and every
%call to it compiles to a partial application instead. In &self the load module
%already is user, so this states that behaviour rather than adding a rule.
consult_global(File) :- user:consult(File).
use_module_global(File) :- user:use_module(File).
%A predicate term headed by a space is a provider query, not a raw Prolog
%call into the module where native atoms happen to be stored. Other heads keep
%the Prolog interop constructor's original meaning.
metta_predicate_goal([Space|Pattern],
                     match(Space, Pattern, matched, matched)) :-
    atom(Space), atom_concat('&', _, Space), !.
metta_predicate_goal([F|Args], Term) :- Term =.. [F|Args].

'Predicate'(Parts, Term) :- metta_predicate_goal(Parts, Term).
callPredicate(G, true) :- call(G).
assertzPredicate(G, true) :- assertz(G).
assertaPredicate(G, true) :- asserta(G).
retractPredicate(G, true) :- retract(G), !.
retractPredicate(_, false).

%%% Library / Import: %%%
ensure_metta_ext(Path, Path) :- file_name_extension(_, gz, Path), !.
ensure_metta_ext(Path, Path) :- file_name_extension(_, metta, Path), !.
ensure_metta_ext(Path, PathWithExt) :- file_name_extension(Path, metta, PathWithExt).

current_working_dir(Base) :- working_dir(Base), !.
current_working_dir(Base) :- absolute_file_name('.', Base, [file_type(directory)]).

import_file_string(File, SFile) :- string(File), !, SFile = File.
import_file_string(File, SFile) :- atom_string(File, SFile).

python_import_file(File) :- import_file_string(File, SFile),
                            file_name_extension(_, py, SFile).

resolve_existing_import_path(Base, RequestedPath, CanonPath) :-
    ( is_absolute_file_name(RequestedPath)
      -> absolute_file_name(RequestedPath, CanonPath,
                            [access(read), file_errors(fail)])
       ; absolute_file_name(RequestedPath, CanonPath,
                            [relative_to(Base), access(read), file_errors(fail)]) ),
    !.

throw_missing_import(File) :-
    throw(error(existence_error(source_sink, File), context('import!', File))).

resolve_metta_import_path(File, CanonPath) :-
    import_file_string(File, SFile),
    \+ python_import_file(SFile),
    current_working_dir(Base),
    ensure_metta_ext(SFile, RequestedPath),
    ( resolve_existing_import_path(Base, RequestedPath, CanonPath)
      -> true
       ; throw_missing_import(File) ).

resolve_python_import_path(File, CanonPath) :-
    import_file_string(File, SFile),
    python_import_file(SFile),
    current_working_dir(Base),
    ( resolve_existing_import_path(Base, SFile, CanonPath)
      -> true
       ; throw_missing_import(File) ).

:- dynamic imported_metta_source/2.
:- dynamic import_life/3.

%Import state cannot live as a clause of the space predicate: wildcard
%remove-atom retracts every unifying clause, including rules. Loading is
%visible while recursive imports run so cycles terminate; success changes the
%state to loaded. A full space clear owns removal of both states.
import_life_current(Space, CanonPath) :-
    atom(Space), !,
    import_life(Space, CanonPath, _).
import_life_current(_, _).

assert_import_life_marker(Space, CanonPath, Ref) :-
    atom(Space), !,
    assertz(import_life(Space, CanonPath, loading), Ref).
assert_import_life_marker(_, _, none).

erase_import_life_marker(none) :- !.
erase_import_life_marker(Ref) :-
    ( clause_property(Ref, erased) -> true ; erase(Ref) ).

finish_import_life(_, _, none, _) :- !.
finish_import_life(Space, CanonPath, Ref, exit) :- !,
    erase_import_life_marker(Ref),
    assertz(import_life(Space, CanonPath, loaded)).
finish_import_life(_, _, Ref, _) :-
    erase_import_life_marker(Ref).

run_with_import_life_marker(Space, CanonPath, Goal) :-
    setup_call_catcher_cleanup(
        assert_import_life_marker(Space, CanonPath, Ref),
        once(Goal),
        Catcher,
        finish_import_life(Space, CanonPath, Ref, Catcher)).

clear_import_life(Space, CanonPath) :-
    ( atom(Space) -> retractall(import_life(Space, CanonPath, _)) ; true ).

% Assert both markers before loading to break cycles. Retain them on success
% and retract them on failure. The recursive mutex serializes the loader graph.
import_once(Space, CanonPath, Goal) :-
    ( imported_metta_source(Space, CanonPath),
      import_life_current(Space, CanonPath)
      -> true
       ; retractall(imported_metta_source(Space, CanonPath)),
         clear_import_life(Space, CanonPath),
         run_with_loading_marker(
             imported_metta_source(Space, CanonPath),
             run_with_import_life_marker(Space, CanonPath, Goal)) ).

python_module_names(CanonPath, ModuleKey, ModuleName) :-
    crypto_data_hash(CanonPath, Hash, [algorithm(sha256)]),
    atom_concat('_petta_import_', Hash, ModuleKey),
    file_base_name(CanonPath, BaseName),
    file_name_extension(ModuleName, _, BaseName).

python_sibling_module_names(ParentDir, ModuleNames) :-
    directory_files(ParentDir, Entries),
    findall(ModuleName,
            ( member(Entry, Entries),
              file_name_extension(ModuleName, py, Entry) ),
            Names),
    sort(Names, ModuleNames).

save_python_module(Name, module_state(Name, true, Module)) :-
    py_call(sys:modules:'__contains__'(Name), @(true)), !,
    py_call(sys:modules:pop(Name), Module, [py_object(true)]).
save_python_module(Name, module_state(Name, false, @(none))).

restore_python_module(module_state(Name, true, Module)) :- !,
    py_call(sys:modules:'__setitem__'(Name, Module), _).
restore_python_module(module_state(Name, false, _)) :-
    clear_python_module(Name).

clear_python_module(Name) :-
    ( py_call(sys:modules:'__contains__'(Name), @(true))
      -> py_call(sys:modules:pop(Name), _)
       ; true ).

with_saved_python_modules([], Goal) :-
    call(Goal).
with_saved_python_modules([Name|Names], Goal) :-
    setup_call_cleanup(
        save_python_module(Name, State),
        with_saved_python_modules(Names, Goal),
        restore_python_module(State)).

load_python_source(CanonPath) :-
    python_module_names(CanonPath, ModuleKey, ModuleName),
    py_call(sys:path:copy(), PreviousPath),
    file_directory_name(CanonPath, ParentDir),
    python_sibling_module_names(ParentDir, SiblingNames),
    with_saved_python_modules(
        SiblingNames,
        load_python_source_in_context(CanonPath, ModuleKey, ModuleName,
                                      ParentDir, PreviousPath)),
    retractall(python_import_alias(ModuleName, _)),
    assertz(python_import_alias(ModuleName, ModuleKey)).

load_python_source_in_context(CanonPath, ModuleKey, ModuleName, ParentDir,
                              PreviousPath) :-
    catch(load_python_module(CanonPath, ModuleKey, ModuleName, ParentDir,
                             PreviousPath),
          Error,
          ( clear_python_module(ModuleKey),
            throw(Error) )).

load_python_module(CanonPath, ModuleKey, ModuleName, ParentDir,
                   PreviousPath) :-
    py_call(importlib:util:spec_from_file_location(ModuleKey, CanonPath), Spec),
    py_call(importlib:util:module_from_spec(Spec), Module),
    py_call(sys:modules:'__setitem__'(ModuleKey, Module), _),
    py_call(sys:modules:'__setitem__'(ModuleName, Module), _),
    setup_call_cleanup(
        py_call(sys:path:insert(0, ParentDir), _),
        py_call(Spec:loader:exec_module(Module), _),
        restore_python_path(PreviousPath)).

restore_python_path(PreviousPath) :-
    py_call(sys:path:clear(), _),
    py_call(sys:path:extend(PreviousPath), _).

'import!'(Space, File, true) :- importer_helper(Space, File).
importer_helper(Space, File) :-
    with_mutex(metta_loader, importer_helper_impl(Space, File)).
importer_helper_impl(Space, File) :-
    ( python_import_file(File)
      -> resolve_python_import_path(File, CanonPath),
         import_once('$python', CanonPath, load_python_source(CanonPath))
       ; resolve_metta_import_path(File, CanonPath),
         import_once(Space, CanonPath,
                     load_imported_metta_file(CanonPath, _, Space)) ).

:- dynamic translator_rule/1.
'add-translator-rule!'(HV, true) :- ( translator_rule(HV)
                                      -> true ; assertz(translator_rule(HV)) ).

'remove-translator-rule!'(HV, true) :-
    must_be(nonvar, HV),
    retractall(translator_rule(HV)).

%%% Registration: %%%
:- dynamic fun/1, arity/2.
register_fun(N) :- must_be(atom, N),
                   ( fun(N) -> true
                   ; assertz(fun(N), Ref),
                     record_source_assertion(Ref),
                     forall((current_predicate(N/Arity), \+ (current_op(_, _, N), Arity =< 2)),
                            register_arity(N, Arity)),
                     repair_after_late_registration(N) ).

%Record each callable arity once, even when a function has many equations.
register_arity(N, Arity) :- ( arity(N, Arity) -> true
                            ; assertz(arity(N, Arity), Ref),
                              record_source_assertion(Ref) ).

%The module whose equations are in scope while a term is compiled or run. The
%default is user, so nothing changes for a program that only ever uses &self.
current_metta_module(Module) :-
    ( nb_current('$petta_module', M) -> Module = M ; Module = user ).

with_metta_module(Module, Goal) :-
    current_metta_module(Previous),
    setup_call_cleanup(b_setval('$petta_module', Module),
                       Goal,
                       b_setval('$petta_module', Previous)).

%Control signals pass through every recovery catch: a caught abort, limit,
%alarm, or interrupt is a stopped program pretending it succeeded. This is
%the KeyboardInterrupt-outside-Exception design; a swallowed limit signal
%also DISARMS call_with_inference_limit for the rest of the call, measured
%as six million inferences spent under a thousand-inference budget when a
%recovery catch ate the signal mid-translation.
control_exception(time_limit_exceeded).
control_exception(inference_limit_exceeded).
control_exception(petta_py_interrupted).
control_exception('$aborted').
control_exception(error(petta_py_time_limit(_), _)).
control_exception(error(petta_py_inference_limit(_), _)).
control_exception(error(resource_error(_), _)).

%Keep the ISO Formal term because callers and the MeTTa catch form inspect it.
%Only the host context is replaced, so lists:min_list/3, is/2, and nb_setval/2
%cannot leak into a language-level diagnostic. Integer fast paths avoid the
%catch cost on valid arithmetic without letting float overflow escape. Over
%100,000 calls the guarded form used
%300,002 inferences against 300,003 directly, while an unconditional catch used
%400,002 [measured: guarded -1 and caught +99,999 inferences, 2026-08-15].
rethrow_metta_operation_error(_, Error) :- control_exception(Error), !,
                                            throw(Error).
rethrow_metta_operation_error(Operation, error(Formal, _)) :- !,
    throw(error(Formal,
                context(Operation, 'while evaluating MeTTa operation'))).
rethrow_metta_operation_error(_, Error) :- throw(Error).

throw_metta_type_error(Operation, Expected, Culprit) :-
    throw(error(type_error(Expected, Culprit),
                context(Operation, 'invalid MeTTa operation argument'))).

%These builtins validate their own runtime inputs and provide their own error
%context. The translator may therefore bypass reflective input filtering when
%the builtin has not been overridden. Keep this list aligned with those guards.
runtime_type_guarded('+').
runtime_type_guarded('-').
runtime_type_guarded('*').
runtime_type_guarded('/').
runtime_type_guarded('%').
runtime_type_guarded('<').
runtime_type_guarded('>').
runtime_type_guarded('<=').
runtime_type_guarded('>=').
runtime_type_guarded(min).
runtime_type_guarded(max).
runtime_type_guarded(exp).
runtime_type_guarded('#+').
runtime_type_guarded('#-').
runtime_type_guarded('#*').
runtime_type_guarded('#div').
runtime_type_guarded('#//').
runtime_type_guarded('#mod').
runtime_type_guarded('#min').
runtime_type_guarded('#max').
runtime_type_guarded('#<').
runtime_type_guarded('#>').
runtime_type_guarded('#=').
runtime_type_guarded('#\\=').
runtime_type_guarded('pow-math').
runtime_type_guarded('sqrt-math').
runtime_type_guarded('abs-math').
runtime_type_guarded('log-math').
runtime_type_guarded('exp-math').
runtime_type_guarded('trunc-math').
runtime_type_guarded('ceil-math').
runtime_type_guarded('floor-math').
runtime_type_guarded('round-math').
runtime_type_guarded('sin-math').
runtime_type_guarded('cos-math').
runtime_type_guarded('tan-math').
runtime_type_guarded('asin-math').
runtime_type_guarded('acos-math').
runtime_type_guarded('atan-math').
runtime_type_guarded('isnan-math').
runtime_type_guarded('isinf-math').
runtime_type_guarded('min-atom').
runtime_type_guarded('max-atom').
runtime_type_guarded('random-int').
runtime_type_guarded('random-float').
runtime_type_guarded(and).
runtime_type_guarded(or).
runtime_type_guarded(not).
runtime_type_guarded(xor).
runtime_type_guarded(implies).

%The evaluator's catch-all: real errors take the recovery, control
%signals keep flying.
:- meta_predicate catch_recover(0, 0).
catch_recover(Goal, Recovery) :-
    catch(Goal, E, ( control_exception(E) -> throw(E) ; call(Recovery) )).

%The hot recovery case needs no meta-call or compound handler term. Real
%errors fail the candidate; control signals retain catch_recover/2 semantics.
recover_failure(E) :- ( control_exception(E) -> throw(E) ; fail ).

%Whether a symbol is callable from where we are: a process-wide function that
%no named equation module claims, a function this module defines, or one &self
%defines, since &self is shared. fun_scoped/1 summarizes non-user fun_in/2
%claims. A builtin or user-only function is therefore unambiguous in every
%space and avoids a current-module read in higher-order loops.
%fun_in/2 is only ever asserted by register_fun_in/2, which registers fun/1
%first, so fun_in implies fun. A name that is not a function therefore cannot
%be one here either, and one indexed lookup settles it: the old second clause
%went on to read current_metta_module/1 and two fun_in/2 facts before failing,
%for every non-function head the translator resolves
%[measured 2026-08-15: alpha-unique 4,050,778 to 3,750,772 inferences].
fun_here(F) :- fun(F),
               ( \+ fun_scoped(F) -> true
               ; current_metta_module(Module), fun_here_in(Module, F) ).

%The builtin fallback is what keeps (+ 1 2) working in &self after some other
%named space defines (= (+ $a $b) ...). fun_scoped(N) stops fun_here/1's first
%clause applying process-wide, and without this the name resolved nowhere: one
%named space turned + into inert data in every other space and in engines
%built afterwards [tested: metta_builtin_scoping].
fun_here_in(Module, F) :- (   fun_in(Module, F) -> true
                          ;   Module \== user, fun_in(user, F) -> true
                          ;   builtin_fun(F) ).

%Register a function and record which module its clauses live in. fun/1 stays
%global because the translator consults it at compile time to decide whether a
%head is a call or data, and that decision has to hold wherever the term is
%compiled; fun_in/2 says where the clauses actually are, so a caller can ask
%whether *this* space defines a symbol rather than whether any space does.
:- dynamic fun_in/2, fun_scoped/1.
%A builtin is visible from every space, and stays visible when a named space
%defines its name. fun_in/2 cannot carry that: it means "an equation or a
%registered operation defines this here", which is exactly the test
%runtime_guarded_builtin_call/1 uses to decide a builtin was overridden. One
%fact for each meaning, so neither reading breaks the other.
:- dynamic builtin_fun/1.
register_builtin_fun(N) :- register_fun(N),
                           ( builtin_fun(N) -> true ; assertz(builtin_fun(N)) ).

register_fun_in(Module, N) :- register_fun(N),
                              ( fun_in(Module, N) -> true
                              ; assertz(fun_in(Module, N), FunInRef),
                                record_source_assertion(FunInRef) ),
                              ( Module == user -> true
                              ; fun_scoped(N) -> true
                              ; assertz(fun_scoped(N), ScopedRef),
                                record_source_assertion(ScopedRef) ).

unregister_fun_in(Module, N) :- retractall(fun_in(Module, N)),
                                ( fun_in(Other, N), Other \== user
                                  -> true ; retractall(fun_scoped(N)) ).

unregister_fun_everywhere(N) :- retractall(fun_in(_, N)),
                                retractall(fun_scoped(N)).
:- maplist(register_builtin_fun, [superpose, empty, let, 'let*', '+','-','*','/', '%', min, max, 'change-state!', 'get-state', 'bind!',
                          '<','>','==', '!=', '=', '=?', '<=', '>=', and, or, xor, implies, not, exp,
                          'first-from-pair', 'second-from-pair', 'car-atom', 'cdr-atom', 'unique-atom', 'alpha-unique-atom',
                          repr, repra, parse, 'println!', 'readln!', test, 'test-no-answer', assert, atom_concat, atom_chars, copy_term, term_hash,
                          foldl, first, last, append, length, 'size-atom', sort, msort, member, 'is-member', 'is-alpha-member', 'exclude-item', list_to_set, maplist, eval, evalc, reduce, 'import!',
                          'git-import!',
                          'add-atom', 'remove-atom', 'get-atoms', match, 'is-var', 'is-ground', 'is-expr', 'is-space',
                          decons, 'decons-atom', 'py-call', 'get-type', 'get-metatype', '=alpha', sread, cons, reverse,
                          '#+','#-','#*','#div','#//','#mod','#min','#max','#<','#>','#=','#\\=',
                          'union-atom', 'cons-atom', 'intersection-atom', 'subtraction-atom', 'index-atom', id,
                          'pow-math', 'sqrt-math', 'sort-atom','abs-math', 'log-math', 'exp-math', 'trunc-math', 'ceil-math',
                          'floor-math', 'round-math', 'sin-math', 'cos-math', 'tan-math', 'asin-math','random-int','random-float',
                          'acos-math', 'atan-math', 'isnan-math', 'isinf-math', 'min-atom', 'max-atom',
                          'foldl-atom', 'map-atom', 'filter-atom','current-time','format-time', 'context-space', library, exists_file,
                          import_prolog_function, 'Predicate', callPredicate, assertaPredicate, assertzPredicate, retractPredicate,
                          'add-translator-rule!', 'remove-translator-rule!', argv]).

%The mork bridge's builtins come with morkspaces, which loads only in mork
%mode, so their registration is gated the same way. Registering a name whose
%predicate is absent records no arity, and incomplete_application_kind/3 reads
%"no arity" as "not applied far enough": every call to it then compiled to a
%partial application, so (mm2-exec &mork 1) answered (partial mm2-exec (&mork
%1)) instead of running or failing.
:- current_prolog_flag(argv, Argv),
   ( member(mork, Argv)
     -> maplist(register_builtin_fun, ['mm2-exec', 'mork-add-atoms', 'mork-flush'])
      ; true ).
