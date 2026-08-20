% Purpose: Prolog side of the petta Python library. Adds tagged term encoding,
%   per-directive structured runs, space operations, Python-backed MeTTa
%   functions (deterministic and nondeterministic), evaluation, and proof-tree
%   derivations on top of an unmodified PeTTa engine. Consulted after
%   engine/main.pl; only adds predicates, never redefines engine ones.
% Guarantees:
%   - Python's non-direct eval paths use translate_cached_expr/3, so repeated
%     forms reuse the engine's invalidated translation templates
%     [tested: translation_cache, test_the_host_service_scoreboard_matches_the_tree; commit=d90a3c9620e56e42d3a2f5982b4353da8423e873]
%   - petta_py_declare_handles/3 writes the declaration and checks the
%     context's critical pairs in one transaction, so a conflicting entry
%     rolls back and never becomes queryable
%     [tested test_declare_handles_rejects_a_conflict_eagerly]
%   - petta_py_raise/2 reserves one exact exception shape for Python-side
%     classification [tested test_reserved_exception_shape_maps_by_kind]
%   - petta_py_load/3 loads under the engine's own source-load lifecycle, so
%     the library's door and import! replace each other's loads of a file and
%     not only their own [tested 2026-08-19:
%     test_both_doors_replace_a_files_definitions,
%     test_loading_the_same_file_twice_leaves_one_copy]
%   - Engine atom hooks exist only while a Python space subscription exists
%     [tested test_subscription_hooks_follow_the_active_space_set]
%   - metta_control_signal_info/3 returns the tagged reader detail without
%     parsing Janus's rendered exception [tested test_run_syntax_error_is_loud]
%   - petta_py_eval_status_all/3 and petta_py_run_status/3 report which of
%     PeTTa's evaluation paths produced each answer, leaving the ordinary
%     entry points' output unchanged [tested
%     test_eval_status_reports_the_four_outcomes]
%   - petta_py_operation_error/5 reports a builtin refusal as its written
%     operation, formal functor, expected type and culprit, and every value it
%     yields is one Janus can carry [tested
%     test_operation_error_carries_its_parts]
%   - Every wire tag decodes to its term in both the atom and the string
%     spelling Janus may deliver, sharing a variable by name and never
%     sharing an anonymous one, and a malformed wire term fails rather than
%     decoding to something [tested 2026-08-16: shim_wire_decoding,
%     shim_wire_variable_sharing in tests/prolog/shim.plt]
%   - A payload outside the class its tag names fails as a malformed shape
%     does, so a tag is a claim about its payload rather than a label
%     [tested 2026-08-20:
%     shim_wire_decoding:a_payload_outside_its_tags_class_fails]
%   - the n tag carries signed-i64 Number integers and wider BigInt integers
%     through Janus without changing their exact value
%     [tested 2026-08-20: test_janus_carries_bigint_losslessly]
%   - petta_py_run/3, petta_py_run_using/4 and petta_py_run_status/3 register a
%     source's whole signature set before processing any of its forms, through
%     the engine's own prepare_parsed_forms/1, so a ! may NAME a function the
%     same source defines lower down and run() and load() answer what the
%     engine's file reader answers. What is registered is the signature, not
%     the clauses, so a ! that CALLS one still cannot answer, in either
%     configuration [tested 2026-08-18:
%     test_a_source_registers_every_signature_before_any_form_runs,
%     test_run_using_registers_signatures_over_the_forms_that_will_run,
%     test_run_status_registers_signatures_before_any_form_runs,
%     test_load_memoizes_a_function_the_same_file_defines_lower_down,
%     test_a_declaration_that_cannot_type_what_the_source_defines_is_refused]
%   - petta_py_read_forms/2 is the exception and stays one: it neither compiles
%     nor stores nor runs, so it parses without preparing
%     [tested test_a_manifest_neither_runs_nor_defines]
%   - grouped runnable answers use their carried reader map when encoding free
%     variables, so the public run surface retains source names
%     [tested: test_variable_names_survive_to_the_printer; commit=916def0562c211143bb91cd0bd8b2c9dac7ab4fa]
%   - petta_py_symbol_writable/2 exposes the engine grammar's single symbol
%     decision to Python consumers without reproducing delimiters there
%     [tested: test_every_delimiter_check_derives_from_one_grammar_rule;
%     commit=3ae4e6b08bc82d8b9cbdf934afc92ada7cf7a19e]
%   - petta_py_symbol_refusal/2 derives both its refusal and its character
%     witness from metta_symbol_writable/1, so register_op rejects unreadable
%     names before any registry state changes [tested:
%     test_register_op_refuses_a_name_metta_cannot_read;
%     commit=WORKTREE]
%   - petta_py_builtins/1 answers the sorted union of every fun/1 name and
%     every translate_special_dl/5 head, so host tooling sees the language
%     rather than only its callable registry [tested:
%     test_builtins_equals_the_union_of_functions_and_special_forms;
%     commit=bcf80e727923cce0e034f716d7eef01f9395c490]
% Open Obligations:
%   To Do: None
%   Hacks: None
%   Future Enhancements: None

:- use_module(library(janus)).
:- use_module(library(lists)).
:- use_module(library(apply)).
:- use_module(library(time)).
:- use_module(library(prolog_profile)).
:- use_module(library(wfs)).

%The engine asserts translated_from/2 without declaring it, so a read before
%the first equation would raise existence rather than finding nothing:
:- dynamic translated_from/2.

%%%%%%%%%% Wire encoding %%%%%%%%%%
%
% janus maps both a Prolog atom and a Prolog string to a Python str, and maps
% the booleans to strings too, so a bare term crossing the boundary loses its
% metatype. Every term crosses tagged instead: ["s",Name] symbol, ["g",Text]
% string, ["n",N] Number or BigInt, ["b",true|false] boolean,
% ["v",Name] variable, ["e",[...]] expression, ["o",Ref] Python object
% reference. The tag list itself is nested lists, which janus converts
% natively in both directions.

%Encode a Prolog term as a tagged wire term:
%The clauses are mutually exclusive and every one of them cuts, so their order
%is a pure COST decision, and py_is_object/1 was in the wrong place: it is a
%foreign call into janus and it ran on every argument, and on every ELEMENT of
%every list, before anything asked whether the value was a number. It costs 915
%instructions where number/1 and string/1 are VM instructions costing nothing
%measurable [measured 2026-08-17, 3,000,000 iterations, min of 3: 1,765,021,710
%for the bare loop, 4,510,067,594 with py_is_object/1, 2,914,057,131 with
%blob/2]. Moving it behind the free tests is worth most on exactly the argument
%shape the encoded path is worst at, since a 64-item list paid it 64 times.
%
%Sound because a janus reference satisfies NONE of the tests now in front of
%it: it is atomic and not atom, number, string, is_list, compound or callable
%[measured 2026-08-17 against py_call(builtins:object(), Obj), blob type py].
%That is the same fact get_type_candidate/2 relies on where it writes
%`atomic(X), \+ atom(X), python_object_blob(X)` to keep ordinary values out of
%janus. Nothing else about the encoding moves; the relative order of every
%other clause is unchanged.
%The wire name is an IDENTITY, never a display name: the same cell must
%encode the same on every crossing, and two different cells must never
%collide, so the source-name attribute (petta_var_name) deliberately does
%NOT reach here. Sending it was measured breaking round-trip identity
%(a variable through a registered op stopped unifying home) and aliasing
%distinct answer variables that shared a spelling.
petta_py_encode(T, ["v", Name]) :- var(T), !, term_to_atom(T, A), atom_string(A, Name).
petta_py_encode(T, ["n", T])    :- number(T), !.
petta_py_encode(T, ["g", T])    :- string(T), !.
petta_py_encode(T, ["b", T])    :- ( T == true ; T == false ), !.
petta_py_encode(T, ["s", S])    :- atom(T), !, atom_string(T, S).
petta_py_encode(T, ["o", T])    :- py_is_object(T), !.
petta_py_encode(T, ["e", Es])   :- is_list(T), !, maplist(petta_py_encode, T, Es).
petta_py_encode([H|T], ["e", [["s", "cons"], EH, ET]]) :- !,
    petta_py_encode(H, EH),
    petta_py_encode(T, ET).
%A non-list compound encodes as (f a b). compound_name_arguments/3 rather
%than =../2, because =.. RAISES on a ZERO-ARITY compound and janus hands us
%one for every empty Python tuple: py_call(builtins:tuple(), X) binds X to
%-() [measured 2026-08-18]. That reached here as
%`Domain error: compound_non_zero_arity expected, found -()` out of an
%ordinary Python return value, ''.split() of an empty string among them,
%and only through the LIBRARY: the engine has its own writer and never ran
%this clause, so no lane saw it [source: ai-audit-md-review.md section 4].
%
%Known disagreement, deliberately left visible rather than papered over.
%janus renders a Python tuple as a `-` compound (`(1,2)` is `1-2`), so this
%clause encodes one as `(- 1 2)` while the engine's swrite prints `(1, 2)`,
%Python's own syntax, which sread cannot read back: it answers the two-item
%expression `('1,' 2)` [measured 2026-08-18]. Both configurations are
%self-consistent and they do not agree with each other. What a Python tuple
%IS at this seam is a boundary decision, not an encoder detail, and it is
%tracked as its own item; encoding every arity the same way here is what
%stops the empty one being a crash while the rest are silent.
petta_py_encode(T, ["e", [["s", FS] | Es]]) :-
    compound(T),
    compound_name_arguments(T, F, Args),
    atom(F), !,
    atom_string(F, FS),
    maplist(petta_py_encode, Args, Es).
%Anything else (a blob, a dict) is carried as text, the printer's last resort:
%A native handle (a C blob) crosses as a registry reference plus its own
%printed text, so Python holds it opaquely and can hand back the very
%same blob: identity, not a serialisation. It used to fall through to
%the term_string clause below, which silently stringified it and made
%the round trip impossible: 'vector-length' on what came back saw a
%string [measured 2026-08-17]. The clause sits HERE, at the tail, so
%only a term every other clause refused pays the blob/2 probe: placed
%before the list clauses it taxed every encoded list node, and SWI's []
%is itself a reserved non-text blob, so it also registered every () as
%a handle, caught by the wire round-trip property over Expr('()'). A
%blob is atomic, so nothing above claims one: atom/1 is false for
%non-text blobs, and the compound clause needs compound/1.
petta_py_encode(T, ["h", Id, S]) :- blob(T, Type), Type \== text, T \== [], !,
    petta_py_handle_keep(T, Id),
    term_string(T, S).
petta_py_encode(T, ["g", S]) :- term_string(T, S).

%Encode with an explicit Name-Var list, so parsed variables keep their names:
petta_py_encode_named(T, Pairs, ["v", Name]) :-
    var(T), !,
    ( petta_py_var_name(Pairs, T, N) -> atom_string(N, Name)
    ; term_to_atom(T, A), atom_string(A, Name) ).
petta_py_encode_named(T, Pairs, ["e", Es]) :-
    is_list(T), !,
    petta_py_encode_named_list(T, Pairs, Es).
petta_py_encode_named(T, _, W) :- petta_py_encode(T, W).

petta_py_encode_named_list([], _, []).
petta_py_encode_named_list([T|Ts], Pairs, [E|Es]) :-
    petta_py_encode_named(T, Pairs, E),
    petta_py_encode_named_list(Ts, Pairs, Es).

petta_py_var_name([N-V|_], T, N) :- V == T, !.
petta_py_var_name([_|Pairs], T, N) :- petta_py_var_name(Pairs, T, N).

%A tag arrives back as an atom or a string depending on the sender; accept both:
petta_py_tag(T, T) :- atom(T), !.
petta_py_tag(T, A) :- string(T), atom_string(A, T).

%A HOST ANSWER read as a boolean: a Python predicate answers whatever it
%answers and everything that is not one of the true spellings is false, the
%truthiness reading. This is for a RETURN VALUE, not for a wire payload; the
%b tag has its own strict reader below, because a payload the grammar does
%not admit is a malformed term and turning it into `false` would answer a
%question nobody asked.
petta_py_bool(B, true)  :- B == true, !.
petta_py_bool(B, false) :- B == false, !.
petta_py_bool(B, true)  :- B == '@'(true), !.
petta_py_bool(B, false) :- B == '@'(false), !.
petta_py_bool(B, true)  :- B == "true", !.
petta_py_bool(_, false).

%The b tag's payload, and nothing else. Facts rather than a chain of ==/2
%with cuts, so first-argument indexing decides in one step and an
%inadmissible payload has no clause to fall into.
petta_py_wire_bool(true,       true).
petta_py_wire_bool(false,      false).
petta_py_wire_bool('@'(true),  true).
petta_py_wire_bool('@'(false), false).
petta_py_wire_bool("true",     true).
petta_py_wire_bool("false",    false).

%Decode a tagged wire term; every v tag becomes its own fresh variable.
%
%The tag decides the clause, so it is normalised once and dispatched on.
%Asking petta_py_tag/2 whether the tag is o, then s, then g, then n, walks
%that list of alternatives and re-runs atom/1 and string/1 at every step,
%which is how deciding that ['n',1] holds a number came to cost nine
%inferences. Every Python term crossing into the engine is decoded this way,
%so the walk was on the query path, the run path and the eval path alike
%[measured 2026-08-16: (m6f 1) evaluated from Python, 72.00 inferences to
%63.00 and 5.45us to 4.98us, of which the wire term's own decode fell 22.00
%to 13.00 and a single number leaf 9.00 to 4.00].
petta_py_decode([T0|Rest], Term) :-
    ( atom(T0) -> T = T0 ; string(T0) -> atom_string(T, T0) ),
    petta_py_decode_(T, Rest, Term).

petta_py_decode_(o, [Obj], Obj).
%A handle reference resolves to the registered blob itself. A stale id
%is an existence error naming it, never a fresh or empty value: the
%handle's release is explicit on the Python side, so reaching a released
%one is the caller's bug and silence would turn it into a wrong answer.
petta_py_decode_(h, [Id|_], Blob) :-
    (   petta_py_handle_store(Id, Blob)
    ->  true
    ;   throw(error(existence_error(petta_native_handle, Id),
                    context(petta_py_decode_/3,
                            'the handle was released or never issued')))
    ).
%Each payload is checked against the class its tag names, and a payload of
%another class has no decoding: the term is malformed and the decode fails,
%which is what every malformed shape above already did. Without the checks
%the tag was a label rather than a claim, and six payloads decoded to
%something instead: ["s",1] to the symbol '1', ["g",1] to "1", ["n","1/3"]
%to a string wearing the number tag, ["v",1] to a fresh variable, and
%["b",<anything>] to FALSE, which is the one that answers rather than fails
%[measured 2026-08-20, both spellings, against bindings/python/petta/_atom_wire.py,
%which refuses all six]. A wire term is written by an encoder, so nothing
%conforming loses a shape here; what changes is that a boundary bug now
%reports as one [tested: shim_wire_decoding:a_payload_outside_its_tags_class_fails].
%Every check is a TYPE TEST WRITTEN OUT, never a call to a shared one, and
%that is a measurement rather than a preference: number/1, atom/1 and
%string/1 compile to VM instructions costing no inference, while a call to
%a predicate wrapping them costs one on a path that runs per leaf of every
%answer. Per-leaf inferences, before against after, as the atom payload /
%as the string payload, both being spellings janus delivers
%[measured 2026-08-20, 10,000 decodes each, three runs identical]:
%
%  s        4.00/5.00  ->  3.00/5.00     g   4.00/4.00  ->  4.00/4.00
%  v        3.00/4.00  ->  3.00/4.00     n   4.00       ->  4.00
%  v shared 8.00/10.00 ->  8.00/10.00    b   4.00/8.00  ->  4.00/5.00
%
%Faster or equal on every tag and every spelling: the boolean payload
%replaced a chain of ==/2 with indexed facts, and the symbol payload stopped
%calling atom_string/2 on an atom that already is the symbol.
%
%A shared petta_py_wire_text/1 helper was written first and cost +1.00 on s
%and on v, which the alpha-unique benchmark saw as +1.54% and the counter
%gate refused. The A/B behind it had measured zero and was wrong: its
%synthetic term held 1000 s, 500 v and 500 b leaves, whose +1000 +500 -1500
%cancels exactly. A per-tag change needs a per-tag measurement.
petta_py_decode_(s, [S], A)     :- ( atom(S) -> A = S ; string(S), atom_string(A, S) ).
petta_py_decode_(g, [S], Str)   :- ( string(S) -> Str = S ; atom(S), atom_string(S, Str) ).
petta_py_decode_(n, [N], N)     :- number(N).
petta_py_decode_(b, [B], A)     :- petta_py_wire_bool(B, A).
petta_py_decode_(v, [Name], _)  :- ( atom(Name) -> true ; string(Name) ).
petta_py_decode_(e, [Es], Term) :- maplist(petta_py_decode, Es, Term).

%Decode sharing variables by name, so the $x in a head and in a body unify.
%Bindings comes back as Name-Var pairs for reading answers off a query:
petta_py_decode_shared(Tagged, Term, Bindings) :-
    petta_py_decode_shared_(Tagged, Term, [], Bindings).

petta_py_decode_shared_([T0|Rest], Term, B0, B) :-
    ( atom(T0) -> T = T0 ; string(T0) -> atom_string(T, T0) ),
    petta_py_decode_shared_tagged(T, Rest, Term, B0, B).

%Only v and e differ from the plain decode: one shares a variable by name and
%the other has to thread the bindings through its elements. Every leaf below
%them carries no bindings, so it is the plain decode with B unchanged.
petta_py_decode_shared_tagged(v, [Name0], Var, B0, B) :- !,
    petta_py_shared_table(B0, Table),
    %The atom branch carries the payload check with it: a name arriving as
    %anything but text has no identity to share by, and testing it here
    %rather than ahead of the table keeps the check on a branch that was
    %already being taken.
    ( string(Name0) -> atom_string(Name, Name0) ; atom(Name0), Name = Name0 ),
    %The anonymous variable is fresh at every occurrence and never binds,
    %exactly as the reader treats $_ in source; recording it would make two
    %underscores constrain each other.
    ( Name == '_' -> Var = _, B = Table
    ; memberchk(Name-Var, Table) -> B = Table
    ; B = [Name-Var|Table] ).
petta_py_decode_shared_tagged(e, [Es], Term, B0, B) :- !,
    foldl_decode(Es, Term, B0, B).
petta_py_decode_shared_tagged(T, Rest, Term, B, B) :-
    petta_py_decode_(T, Rest, Term).

foldl_decode([], [], B, B).
foldl_decode([E|Es], [T|Ts], B0, B) :-
    petta_py_decode_shared_(E, T, B0, B1),
    foldl_decode(Es, Ts, B1, B).

%A seed table is built on FIRST USE, and only this clause ever uses one. An
%operation dispatch seeds the decode with variables_of(Args) so a returned
%variable resolves to the argument variable it came from, and nearly every
%call has ground arguments and a result with no variable in it. Building the
%table eagerly put a ground/1 walk on all of them, one inference on a
%thirteen-inference call, for a table nothing was going to read
%[measured 2026-08-17: the encoded operation went 13.01 to 14.01 eager, and
%back to 13.01 this way]. A result with no variable never reaches here.
petta_py_shared_table(variables_of(Args), Table) :- !,
    term_variables(Args, Variables),
    maplist(petta_py_named_variable, Variables, Table).
petta_py_shared_table(Table, Table).

%%%%%%%%%% The explicit answer form %%%%%%%%%%
%
%["a", Theta, Residue, K] and ["a", Theta, Residue, K, Value]: bindings
%for the query's variables, crossing beside plain atom wires in one
%stream. Theta pairs are [Name, ValueWire]; the names are the ones
%petta_py_encode/2 wrote for the query's variables, so binding by name is
%binding the caller's own variable. This is Hyperon's execute_bindings,
%LeaTTa's ReduceResult.okBind: an answer atom together with the bindings
%it is returned under, each set merged into the current frame. The wire
%is transport-agnostic; janus is one carrier of it, and a Prolog-side
%provider needs none of it because unification already binds.
%
%The head asks for four elements before it looks at the tag, so every
%plain two-element wire falls through on the list spine without reaching
%the comparison; the explicit form stays off the hot path's price.
petta_py_answer_form([Tag, Theta, Residue, K], Theta, Residue, K, none) :-
    ( Tag == "a" -> true ; Tag == a ).
petta_py_answer_form([Tag, Theta, Residue, K, Value], Theta, Residue, K,
                     value(Value)) :-
    ( Tag == "a" -> true ; Tag == a ).

%The annotation slot: the degenerate point is semiring 1 and costs
%nothing; a real k is admitted exactly when its context declared a
%non-Boolean semiring, and rides '$petta_answer_k' backtrackably for the
%collapse-point consumers (top). An undeclared k is refused loudly
%naming the declaration to add, because silently dropping it would
%misweigh the answer and silently keeping it would smuggle an order the
%context never declared.
petta_py_answer_kappa('@'(none), _) :- !.
petta_py_answer_kappa(K0, Ctx) :-
    (   petta_annotations(Ctx, Semiring),
        Semiring \== bool
    ->  (   K0 = [_|_]
        ->  petta_py_decode_shared(K0, K, _)
        ;   K = K0
        ),
        b_setval('$petta_answer_k', K)
    ;   throw(error(petta_answer_annotation_undeclared(Ctx, K0), none))
    ).

%Close an answer's residue: the part of the query the provider did not
%discharge, evaluated by the engine under the bindings already made. The
%residue decodes against the same name table, so its variables ARE the
%query's, and each evaluation result that is not false contributes one
%closure, composing bindings by ordinary sharing; false contributes
%nothing. That rule is the language's own: a condition like (> $y 3)
%reduces to a boolean and false drops the answer, a match form inside the
%residue contributes one closure per solution, and a term with no
%equation answers itself, exactly as !(edge a b) does at the top level.
%This is one notion worn three ways already: 'residual-goals'/2 carries
%dif/2 constraints an answer holds under, Undefined's residual carries
%the delayed goals a WFS answer is conditional on, and a Planner's rest
%is the part of a conjunction the provider left; the answer form carries
%the same R across the wire.
petta_py_answer_close('@'(true), _) :- !.
petta_py_answer_close(ResidueW, Table) :-
    petta_py_decode_shared_(ResidueW, Residue, Table, _),
    eval(Residue, Out),
    Out \== false.

%A conditional answer under a pushed bound under-answers: the provider
%truncated at the caller's k, and a residue can still drop answers after
%that, so fewer than k arrive while more existed. Exact licensed the
%bound; a residue is exactly what Exact rules out.
petta_py_answer_bounded('@'(true), _, _) :- !.
petta_py_answer_bounded(_, '@'(none), _) :- !.
petta_py_answer_bounded(Residue, _, Pattern) :-
    throw(error(petta_answer_conditional_under_bound(Pattern, Residue),
                none)).

%Merge Theta into the query frame: seed the name table with the query's
%own variables, decode each bound value against it, so values may
%reference the query's variables and each other while unknown names stay
%fresh, and unify. A failing unification drops the ANSWER, exactly as a
%candidate that does not unify is dropped, and is equally sound.
petta_py_answer_theta(Pairs, Seed, Table) :-
    term_variables(Seed, Variables),
    maplist(petta_py_named_variable, Variables, Table0),
    foldl(petta_py_answer_binding, Pairs, Table0, Table).

petta_py_answer_binding([NameW, ValueW], Table0, Table) :-
    ( atom(NameW) -> Name = NameW ; atom_string(Name, NameW) ),
    petta_py_decode_shared_(ValueW, Value, Table0, Table1),
    ( memberchk(Name-Variable, Table1) -> Table = Table1
    ; Table = [Name-Variable|Table1] ),
    Variable = Value.

%One item of a provider's match stream against the query pattern. The
%explicit form applies theta to the pattern's variables; its value, when
%present, is the candidate-with-bindings reading and unifies under them,
%and its residue closes through the engine, one answer per closure.
petta_py_answer_match(Item, Pattern, Ctx) :-
    petta_py_answer_match(Item, Pattern, '@'(none), Ctx).
petta_py_answer_match(Item, Pattern, Limit, Ctx) :-
    (   petta_py_answer_form(Item, Theta, Residue, K, ValueW)
    ->  petta_py_answer_kappa(K, Ctx),
        petta_py_answer_bounded(Residue, Limit, Pattern),
        petta_py_answer_theta(Theta, Pattern, Table),
        (   ValueW = value(VW)
        ->  petta_py_decode_shared_(VW, Value, Table, _),
            Pattern = Value
        ;   true
        ),
        petta_py_answer_close(Residue, Table)
    ;   petta_py_decode_shared(Item, Candidate, _),
        Pattern = Candidate
    ).

%One result of an operation dispatch: the explicit form binds the CALL's
%variables and reduces to its value, () when none, the relational
%reading; a plain wire is the value itself, decoded with the lazy seed.
petta_py_answer_result(Item, Name, Args, Result) :-
    (   petta_py_answer_form(Item, Theta, Residue, K, ValueW)
    ->  petta_py_answer_kappa(K, Name),
        petta_py_answer_theta(Theta, Args, Table),
        (   ValueW = value(VW)
        ->  petta_py_decode_shared_(VW, Result, Table, _)
        ;   Result = []
        ),
        petta_py_answer_close(Residue, Table)
    ;   petta_py_decode_shared_(Item, Result, variables_of(Args), _)
    ).

:- multifile prolog:error_message//1.
prolog:error_message(petta_answer_conditional_under_bound(Pattern, Residue)) -->
    [ 'an answer for ~q carries a residue (~q) while the caller\'s bound \c
       was pushed to the provider. A conditional answer can still drop \c
       after the provider truncated, which under-answers; a residue is \c
       exactly what an Exact claim rules out, so declare this shape \c
       Sound instead'-[Pattern, Residue] ].
prolog:error_message(petta_answer_annotation_undeclared(Ctx, K)) -->
    [ 'this answer carries an annotation (~q) and ~w declares no \c
       semiring for it. Declare (annotations ~w ranked) to admit ordered \c
       annotations there; silently dropping k would misweigh the answer \c
       and silently keeping it would smuggle an order the context never \c
       declared'-[K, Ctx, Ctx] ].

%%%%%%%%%% Errors %%%%%%%%%%
%
% Some exceptions are control signals rather than errors; converting one into a
% value would swallow the very signal its thrower waits for.
petta_py_raise(Kind, Detail) :-
    throw(error(metta_control_signal(Kind, Detail), context(petta, Kind))).

metta_control_signal_info(
    error(metta_control_signal(Kind, Detail), context(petta, _)), Kind, Detail) :-
    memberchk(Kind, [syntax, time_limit, inference_limit, interrupted,
                     value, type]).

metta_control_signal_kind(Error, Kind) :-
    metta_control_signal_info(Error, Kind, _).

%The classification is the engine's metta_host_operation_error/5; this side
%maps its neutral absence, an unbound part, onto janus's None.
petta_py_operation_error(Error, Operation, Kind, Expected, Culprit) :-
    metta_host_operation_error(Error, Operation, Kind, Expected0, Culprit0),
    petta_py_operation_part(Expected0, Expected),
    petta_py_operation_part(Culprit0, Culprit).

petta_py_operation_part(Part, @none) :- var(Part), !.
petta_py_operation_part(Part, Part).

%The Python side's contributions to the engine's control-signal seam. There
%was a petta_py_control_exception/1 here holding a SECOND copy of the list,
%and nothing ever called it: it had drifted from the engine's, missing
%metta_host_interrupted and both petta_py limit errors, so anyone who found it
%and used it would have swallowed exactly the signals this side raises.
:- multifile control_exception/1.
control_exception(error(metta_control_signal(_, _), context(petta, _))).

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

petta_py_run(Source, Space, Groups) :-
    metta_host_run_source(Source, Space, [], TermGroups),
    maplist(petta_py_encode_group, TermGroups, Groups).

petta_py_encode_group(Terms, Encoded) :-
    maplist(petta_py_encode_answer, Terms, Encoded).

petta_py_encode_answer('$petta_answer'(Term, NameState), Encoded) :- !,
    petta_name_pairs(NameState, Names),
    petta_py_encode_named(Term, Names, Encoded).
petta_py_encode_answer(Term, Encoded) :-
    petta_py_encode(Term, Encoded).

%Run with named host values: each Name-Value pair substitutes the bare
%symbol Name throughout the parsed forms before anything runs, the local-
%variable reading a dataframe gets in embedded SQL. Values arrive on the
%wire, objects boxed, so identity crosses whole; the decode is this side's
%half, the substitution walk is the engine's.
petta_py_run_using(Source, Space, Pairs, Groups) :-
    maplist(petta_py_using_pair, Pairs, Bindings),
    metta_host_run_source(Source, Space, Bindings, TermGroups),
    maplist(petta_py_encode_group, TermGroups, Groups).

petta_py_using_pair([Name0, Wire], Name-Value) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    petta_py_decode_shared(Wire, Value, _).

petta_py_run_status(Source, Space, Groups) :-
    metta_host_run_source_status(Source, Space, TermGroups),
    maplist(petta_py_status_group, TermGroups, Groups).

petta_py_status_group(Rows, Encoded) :-
    maplist(petta_py_status_row, Rows, Encoded).

petta_py_status_row([empty, none], [empty, none]) :- !.
petta_py_status_row([Status, Term], [Status, Encoded]) :-
    petta_py_encode_answer(Term, Encoded).

petta_py_load(File, Space, Groups) :-
    metta_host_load_file(File, Space, TermGroups),
    maplist(petta_py_encode_group, TermGroups, Groups).

%Read every form in Source without processing any, the boot-manifest door
%[tested test_a_manifest_neither_runs_nor_defines].
petta_py_read_forms(Source, Forms) :-
    metta_host_read_forms(Source, Pairs),
    maplist(petta_py_form_pair, Pairs, Forms).

petta_py_form_pair([Kind, Text], [KindStr, TextStr]) :-
    atom_string(Kind, KindStr),
    ( string(Text) -> TextStr = Text ; atom_string(Text, TextStr) ).

%%%%%%%%%% Guarded and captured calls %%%%%%%%%%
%
% Two meta entry points wrap the run, query and eval entry points without
% changing them. petta_py_limited applies the engine's own per-call guards,
% call_with_time_limit (seconds) and call_with_inference_limit (steps);
% petta_py_captured collects everything the wrapped goal prints to the
% current output. Both name their target as data, a listed entry point plus
% its input list and one output, so they compose by listing
% petta_py_captured as itself wrappable: limited over captured is a capture
% inside a limit. Exceeding a guard throws the reserved exception envelope;
% the Python side classifies its exact shape, never its rendered text.
% A guard that stops a goal stops it mid-way, so writes it already made
% stand, the honest semantics of every timeout.

petta_py_wrappable(petta_py_run).
petta_py_wrappable(petta_py_run_using).
petta_py_wrappable(petta_py_query_all).
petta_py_wrappable(petta_py_query_guarded_all).
petta_py_wrappable(petta_py_query_limit_all).
petta_py_wrappable(petta_py_eval_all).
petta_py_wrappable(petta_py_eval_using_all).
petta_py_wrappable(petta_py_eval_res_all).
petta_py_wrappable(petta_py_eval_status_all).
petta_py_wrappable(petta_py_run_status).
petta_py_wrappable(petta_py_captured).
petta_py_wrappable(petta_py_atomic).
petta_py_wrappable(petta_py_speculative).
petta_py_wrappable(petta_py_profiled).
petta_py_wrappable(petta_py_cursor_next).
petta_py_wrappable(petta_py_derivation).

petta_py_wrapped_goal(Pred0, Ins, Out, Goal) :-
    ( atom(Pred0) -> Pred = Pred0 ; atom_string(Pred, Pred0) ),
    ( petta_py_wrappable(Pred) -> true
    ; throw(error(domain_error(petta_py_wrappable, Pred), none)) ),
    append(Ins, [Out], Args),
    Goal =.. [Pred | Args].

%TimeS and Inf use -1 for "no bound"; both bounds may apply at once, the
%inference wrapper outermost so a time signal thrown inside it passes out.
petta_py_limited(TimeS, Inf, Pred, Ins, Out) :-
    petta_py_wrapped_goal(Pred, Ins, Out, Goal),
    petta_py_guarded(TimeS, Inf, Goal).

petta_py_guarded(TimeS, Inf, Goal) :-
    ( TimeS < 0 -> Timed = Goal
    ; Timed = catch(call_with_time_limit(TimeS, Goal),
                    time_limit_exceeded,
                    petta_py_raise(time_limit, TimeS)) ),
    ( Inf < 0 -> call(Timed)
    ; call_with_inference_limit(Timed, Inf, Result),
      ( Result == inference_limit_exceeded
        -> petta_py_raise(inference_limit, Inf)
      ; true ) ).

petta_py_captured(Pred, Ins, [Out, Text]) :-
    petta_py_wrapped_goal(Pred, Ins, Out, Goal),
    with_output_to(string(Text), call(Goal)).

%One crossing for the engine's own counters: statistics/2 inferences and
%cputime, the garbage_collection triple (collections, bytes freed,
%milliseconds spent), and the thread's answer-table bytes, which the
%tabling review found reachable only through the lower-level runtime.
%The Python side reads deltas around a with-block.
petta_py_stats([Inferences, CpuTime, GcCount, GcFreed, GcTimeMs, TableBytes]) :-
    statistics(inferences, Inferences),
    statistics(cputime, CpuTime),
    statistics(garbage_collection, [GcCount, GcFreed, GcTimeMs|_]),
    statistics(table_space_used, TableBytes).

%Run the wrapped call inside the engine's own transaction/1: its dynamic
%writes, facts and equations alike, commit whole or roll back whole when
%the goal fails or throws. This is the engine's inline (transaction ...)
%form lifted over a whole entry point. Subscription callbacks fire when a
%write happens and are not unfired by a rollback, and the Python-side
%effects of operations are equally the caller's own.
petta_py_atomic(Pred, Ins, Out) :-
    petta_py_wrapped_goal(Pred, Ins, Out, Goal),
    transaction(Goal).

%Run against a frozen view and discard every change: snapshot/1, the
%what-if reading. The answers return; the space stays as it was.
petta_py_speculative(Pred, Ins, Out) :-
    petta_py_wrapped_goal(Pred, Ins, Out, Goal),
    snapshot(Goal).

%%%%%%%%%% Lazy cursors %%%%%%%%%%
%
% A query held open as an SWI engine: engine_next pulls one answer per
% call, the goal's join state stays alive inside the engine between
% pulls, and unrelated calls interleave freely, which a raw janus cursor
% forbids (its frames nest LIFO and it dies crossing threads; probed).
% The handle crosses to Python opaquely inside prolog/1, and both
% stepping and destroying work from any thread (probed). The engine runs
% under the logical update view: a fact added after the first pull is not
% seen by this cursor, the snapshot-like enumeration contract.

%Inf bounds the cursor's WHOLE engine work, installed inside the engine:
%an engine counts its own inferences, so an outer call_with_inference_limit
%around one pull sees almost none of the work (measured: a 100M-step guard
%ran to completion under a 1000-inference outer bound). The limiter's
%dynamic extent lives on the engine's own stack, so it spans every resume,
%the cumulative-budget reading. Wall bounds stay outside, per pull, where
%idle time between pulls cannot count.
petta_py_cursor_open(Space, PatternsTagged, GuardTagged, VarNames, Inf, prolog(Engine)) :-
    ( GuardTagged == [] ->
        Goal = petta_py_query(Space, PatternsTagged, VarNames, Row)
    ; Goal = petta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row)
    ),
    ( Inf < 0 -> Bounded = Goal
    ; Bounded = ( call_with_inference_limit(Goal, Inf, Result),
                  ( Result == inference_limit_exceeded
                    -> petta_py_raise(inference_limit, Inf)
                  ; true ) )
    ),
    engine_create(Row, Bounded, Engine).

%[] is exhaustion, [Row] one answer, so Python needs no sentinel value.
petta_py_cursor_next(Engine, Answer) :-
    ( engine_next(Engine, Row) -> Answer = [Row] ; Answer = [] ).

%Idempotent close: a second destroy finds no engine and is at peace.
petta_py_cursor_close(Engine) :-
    catch(engine_destroy(Engine), error(existence_error(_, _), _), true).

%%%%%%%%%% Profiling %%%%%%%%%%
%
% The statistical profiler around one wrapped call, its terminal report
% swallowed and its data projected to plain values: the summary counters
% and one row per predicate, self-ticks-descending. Sampling is
% statistical, so a short program may carry few samples.
petta_py_profiled(Pred, Ins, [Out, Samples, Ticks, Nodes]) :-
    petta_py_wrapped_goal(Pred, Ins, Out, Goal),
    with_output_to(string(_), profile(Goal, [top(0)])),
    profile_data(Data),
    get_dict(summary, Data, Summary),
    get_dict(samples, Summary, Samples),
    get_dict(ticks, Summary, Ticks),
    get_dict(nodes, Data, NodeDicts),
    %sort/4 keys index compounds, not lists, so the self-ticks ride in
    %front as the key of a pair and are stripped after the sort.
    findall(Self-[PredName, Calls, Redos, Self, Siblings],
            ( member(Node, NodeDicts),
              get_dict(predicate, Node, P), term_string(P, PredName),
              get_dict(call, Node, Calls), get_dict(redo, Node, Redos),
              get_dict(ticks_self, Node, Self),
              get_dict(ticks_siblings, Node, Siblings) ),
            Keyed),
    sort(1, @>=, Keyed, SortedKeyed),
    findall(Row, member(_-Row, SortedKeyed), Nodes).

%What the profiler cannot say about a registered function: which tier put it
%there, and whether the clause index its callers rely on actually exists.
%
%Index quality is read from predicate_property/2 rather than
%library(prolog_jiti)'s jiti_list/1, which prints its table instead of
%answering it. `speedup` is the ratio SWI itself computes for the index it
%chose, so 1.0 means the argument does not discriminate and every call walks
%the clause list. `realised` matters as much: SWI builds an index on first
%need, so an unrealised index is one no call has asked for yet rather than a
%bad one.
%The tier comes from the two engine facts lib_reflect.pl's 'engine-origin'/2
%reads, not from that predicate, which lives in a library the profiler cannot
%require to be loaded. Its builtin and special-form branches are absent here
%on purpose: a profiled name is one an extension registered, and neither of
%those can be.
petta_py_function_shape(Name0, [Tier, Detail, Arities, Determinism]) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    (   catch(metta_function_determinism(Name, Mode), _, fail)
    ->  atom_string(Mode, Determinism)
    ;   Determinism = ""
    ),
    (   metta_function_origin(Name, Tier0, Detail0)
    ->  atom_string(Tier0, Tier), petta_py_origin_part(Detail0, Detail)
    ;   fun(Name)
    ->  Tier = "equation",
        ( fun_in(Module, Name) -> atom_string(Module, Detail) ; Detail = "" )
    ;   Tier = "absent", Detail = ""
    ),
    ( fun_in(Home, Name) -> true ; petta_py_module('&self', Home) ),
    findall([Arity, Speedup, Realised],
            ( arity(Name, Arity),
              petta_py_index_quality(Home, Name, Arity, Speedup, Realised) ),
            Arities).

petta_py_origin_part(Part, String) :-
    ( atom(Part) -> atom_string(Part, String)
    ; string(Part) -> String = Part
    ; term_string(Part, String) ).

%The best index SWI has for this predicate, or 1.0 for none, which is the
%same number a useless index scores and reads the same way: no discrimination.
petta_py_index_quality(Module, Name, Arity, Speedup, Realised) :-
    functor(Head, Name, Arity),
    (   predicate_property(Module:Head, indexed(Indexes)),
        Indexes \== []
    ->  findall(S-R, ( member(Index, Indexes),
                       get_dict(speedup, Index, S),
                       get_dict(realised, Index, R0),
                       ( R0 == true -> R = @(true) ; R = @(false) ) ), Pairs),
        sort(1, @>=, Pairs, [Speedup-Realised|_])
    ;   Speedup = 1.0, Realised = @(false)
    ).

%%%%%%%%%% Native handles %%%%%%%%%%
%
%The registry that keeps a blob alive while Python holds its reference.
%A dynamic clause referencing the blob is what pins it: SWI's atom
%garbage collector respects clause references, so the blob lives exactly
%as long as its registry entry and release is one retract. Each crossing
%issues a fresh id (two crossings of one blob resolve to the same blob
%either way); flag/3 makes the counter atomic across threads.

:- dynamic petta_py_handle_store/2.

petta_py_handle_keep(Blob, Id) :-
    flag(petta_py_handle_counter, Id, Id + 1),
    assertz(petta_py_handle_store(Id, Blob)).

petta_py_handle_release(Id) :-
    retractall(petta_py_handle_store(Id, _)).

%%%%%%%%%% JSON %%%%%%%%%%
%
%The JSON codec is the engine's own reader and writer, library(json),
%under the janus value conventions: @(true), @(false) and @(none) are
%what janus makes of Python True, False and None, and the option list
%teaches the reader and writer that exact vocabulary, so a Python value
%crosses, serializes and comes back with no Python-side JSON
%implementation existing anywhere. SWI integers are unbounded, which is
%what makes wide integers exact in both directions without any guard.

:- use_module(library(json), [json_read_dict/3, json_write_dict/3]).

petta_py_json_options([true(@(true)), false(@(false)), null(@(none))]).

%Encode one janus-shaped value to JSON text. Non-finite floats are
%refused before writing, because json_write_dict serializes NaN and the
%infinities in SWI's own float syntax, which no JSON reader accepts
%back. Errors leave through the reserved envelope so the Python side
%raises ValueError and TypeError by kind rather than by message text.
petta_py_json_encode(Value, Text) :-
    catch(petta_py_json_encode_(Value, Text), Error,
          petta_py_json_rethrow(Error)).

petta_py_json_encode_(Value, Text) :-
    petta_py_json_finite(Value),
    petta_py_json_options(Options),
    with_output_to(string(Text),
                   json_write_dict(current_output, Value,
                                   [width(0)|Options])).

petta_py_json_finite(Value) :-
    (   is_dict(Value)
    ->  dict_pairs(Value, _, Pairs),
        petta_py_json_finite_pairs(Pairs)
    ;   is_list(Value)
    ->  maplist(petta_py_json_finite, Value)
    ;   float(Value)
    ->  (   float_class(Value, Class),
            ( Class == nan ; Class == infinite )
        ->  throw(error(domain_error(finite_number, Value),
                        context(petta_py_json_encode/2, _)))
        ;   true
        )
    ;   true
    ).

petta_py_json_finite_pairs([]).
petta_py_json_finite_pairs([_-Value|Pairs]) :-
    petta_py_json_finite(Value),
    petta_py_json_finite_pairs(Pairs).

%Decode JSON text to a janus-shaped value. The reader stops after one
%value, so the remainder must hold nothing but layout: a second value
%in the same text is refused here, not silently dropped. The tag makes
%read dicts cross janus exactly as written dicts arrive.
petta_py_json_decode(Text, Value) :-
    catch(petta_py_json_decode_(Text, Value), Error,
          petta_py_json_rethrow(Error)).

petta_py_json_decode_(Text, Value) :-
    petta_py_json_options(Options),
    open_string(Text, Stream),
    call_cleanup(petta_py_json_read(Stream, Value, Options),
                 close(Stream)).

petta_py_json_read(Stream, Value, Options) :-
    json_read_dict(Stream, Value, [tag(py)|Options]),
    (   petta_py_json_rest_layout(Stream)
    ->  true
    ;   throw(error(syntax_error(json(trailing_content)),
                    context(petta_py_json_decode/2, _)))
    ).

petta_py_json_rest_layout(Stream) :-
    get_char(Stream, Char),
    (   Char == end_of_file
    ->  true
    ;   char_type(Char, space),
        petta_py_json_rest_layout(Stream)
    ).

%Each error class keeps its own clause, so Python raises by kind: a
%value that JSON cannot carry is a ValueError, a term that is not JSON
%data at all is a TypeError, and anything unrecognized stays a raw
%engine error rather than being dressed as one of those.
petta_py_json_rethrow(error(domain_error(finite_number, Culprit), _)) :-
    format(string(Message),
           "JSON cannot carry the non-finite number ~w", [Culprit]),
    petta_py_raise(value, Message).
petta_py_json_rethrow(error(type_error(Type, Culprit), _)) :-
    format(string(Message),
           "JSON cannot carry ~p, which is not a ~w", [Culprit, Type]),
    petta_py_raise(type, Message).
petta_py_json_rethrow(error(domain_error(Domain, Culprit), _)) :-
    format(string(Message),
           "JSON cannot carry ~p, which is not a ~w", [Culprit, Domain]),
    petta_py_raise(type, Message).
petta_py_json_rethrow(error(syntax_error(What), _)) :-
    format(string(Message), "not valid JSON: ~w", [What]),
    petta_py_raise(value, Message).
petta_py_json_rethrow(error(duplicate_key(Key), _)) :-
    format(string(Message), "JSON object repeats the key ~w", [Key]),
    petta_py_raise(value, Message).
petta_py_json_rethrow(Error) :-
    throw(Error).

%%%%%%%%%% Parse and print %%%%%%%%%%

%Read one form into a tagged term, keeping variable names. sread/2 discards the
%name map its own DCG builds; calling sexpr//3 directly keeps it:
petta_py_parse(Source, Tagged) :-
    petta_py_read_form(Source, Term, VarMap),
    petta_py_encode_named(Term, VarMap, Tagged).

%The reader half of petta_py_parse/2, on its own. An evaluation handed source
%text needs the TERM, and reaching it through the wire form costs an encode
%and a decode of a term that never left the engine, on top of the second janus
%crossing Python makes to parse before it evaluates [measured 2026-08-16:
%(structured (pair a b)) cost 516.00 inferences as parse-then-evaluate and
%449.00 read straight to a term].
petta_py_read_form(Source, Term, VarMap) :-
    ( string(Source) -> S = Source ; atom_string(Source, S) ),
    ( sread_with_names(S, Term, VarMap)
      -> true
    ; format(atom(Msg), 'Parse error in form: ~w', [S]),
      petta_py_raise(syntax, Msg) ).

%An evaluation target arrives either as a wire term or, when the caller passed
%source text, as that text. The test is whether it is a wire term, not what
%type the text has: Janus hands a Python str over as an ATOM, so asking
%string/1 sent every source evaluation down the decoder, where it failed and
%findall/3 turned that into an empty answer list indistinguishable from a
%query that truly answered nothing. Reading it here also keeps the variables
%the reader shared by name, which is what the wire round trip was rebuilding.
%Every wire term is exactly two elements, so the shape is decided here in O(1)
%and the decode below is NOT wrapped in the test. Wrapping it, as an earlier
%version did to turn a failed decode into a refusal, left a choice point over
%the whole recursive walk and cost 11% of alpha-unique, whose operation
%decodes one large term: 3,699,768,516 instructions became 4,106,476,179
%[measured 2026-08-16]. That is the same last-call optimisation the plunit
%gate's own choicepoint check exists to catch.
%&self resolves where text is read, exactly as in loaded source: the text
%branch substitutes the hosting space's name, gated by a C substring probe
%so text that never says &self pays two inferences, not a term walk. A wire
%term was built programmatically, so it keeps its atoms as written, the
%same boundary stored data has; petta_py_parse/2 has no space and reads
%unpinned, the reader LeaTTa gives include. An unconditional walk here
%cost alpha-unique +400k inferences on its one large decoded term
%[measured 2026-08-17].
petta_py_target_term(Space, Target, Term) :-
    (   Target = [_, _]
    ->  petta_py_decode_shared(Target, Term, _)
    ;   \+ is_list(Target)
    ->  petta_py_read_form(Target, Term0, _),
        (   Space == '&self'
        ->  Term = Term0
        ;   atom(Target), sub_atom(Target, _, _, _, '&self')
        ->  metta_substitute_self(Space, Term0, Term)
        ;   string(Target), sub_string(Target, _, _, _, "&self")
        ->  metta_substitute_self(Space, Term0, Term)
        ;   Term = Term0
        )
    ;   throw(error(domain_error(petta_py_wire_term, Target), none))
    ).

%Print a tagged term the way PeTTa prints it:
petta_py_swrite(Tagged, String) :-
    petta_py_decode_shared(Tagged, Term, _),
    swrite(Term, String).

%%%%%%%%%% Space operations %%%%%%%%%%
%
% Writes go through PeTTa's own 'add-atom'/3 and 'remove-atom'/3, so an
% equation takes the engine's function path (register_fun, arity,
% translate_clause, invalidation) exactly as one read from a file does, and
% removal keeps the engine's own semantics (a plain atom removal is retractall).

petta_py_add(Space, Tagged) :-
    petta_py_decode_shared(Tagged, Term, _),
    'add-atom'(Space, Term, _).

petta_py_decode_for_add(Tagged, Term) :-
    petta_py_decode_shared(Tagged, Term, _).

%The engine decides how a batch crosses. This chose for MORK itself and so
%bypassed metta_add_atoms/2 entirely, which is where the rule that a batch may
%not skip per-atom work lives: an equation added to a MORK space alongside any
%other atom was stored inert [measured 2026-08-16].
petta_py_add_many(Space, TaggedList) :-
    maplist(petta_py_decode_for_add, TaggedList, Terms),
    metta_add_atoms(Space, Terms).

%The verdict dance and its index-directed existence probe are the engine's
%metta_host_remove_reported/3 now; this is decode, one call, encode.
petta_py_remove(Space, Tagged, Removed) :-
    petta_py_decode_shared(Tagged, Term, _),
    metta_host_remove_reported(Space, Term, Verdict),
    petta_py_encode(Verdict, Removed).

petta_py_atoms(Space, Encoded) :-
    findall(E, ('get-atoms'(Space, P), petta_py_encode(P, E)), Encoded).

%The tracer answers terms; putting them on the wire is the shim's job, as
%it is for every other atom leaving the engine. A call event has no answer
%field at all, rather than a value standing in for its absence.
petta_py_trace(Source, Space, Max, Encoded) :-
    metta_trace_source(Source, Space, Max, Events),
    maplist(petta_py_trace_event, Events, Encoded).

petta_py_trace_event(event(Depth, call, Term, _, Names),
                     [Depth, "call", EncodedTerm]) :- !,
    petta_py_encode_named(Term, Names, EncodedTerm).
petta_py_trace_event(event(Depth, exit, Term, Answer, Names),
                     [Depth, "exit", EncodedTerm, EncodedAnswer]) :-
    petta_py_encode_named(Term, Names, EncodedTerm),
    petta_py_encode_named(Answer, Names, EncodedAnswer).

%Bulk cleanup of the reflection facts describing one space: every
%(defined <Space> _) atom in &petta goes through the engine's own removal
%funnel (hooks fire per fact), but in ONE crossing from Python; the
%per-fact crossing measured 10,000 calls and 64ms for 10,000 defines.
petta_py_reflect_clear_defined(SpaceName) :-
    ( atom(SpaceName) -> S = SpaceName ; atom_string(S, SpaceName) ),
    metta_host_clear_defined(S).

petta_py_count(Space, Count) :-
    aggregate_all(count, 'get-atoms'(Space, _), Count).

petta_py_space_names(Names) :-
    metta_space_names(Names).

%The live Python exception object inside a python_error term, so the
%boundary can re-raise the ORIGINAL, structured fields intact, instead of
%a flattened transcript of it. Handing Obj back through janus converts
%the blob to the very object the callback raised.
petta_py_original_exception(error(python_error(_, Obj), _), Obj) :-
    py_is_object(Obj).

%Run a Python callable inside one engine transaction: the same
%petta_transaction/1 the MeTTa (transaction ...) form compiles to, so
%foreign-space enlistment and nesting behave identically from both
%languages. py_call re-enters Python on the calling thread; an exception
%there aborts the transaction, every dynamic change rolls back, and the
%Python side re-raises the original.
petta_py_transaction(F, R) :-
    petta_transaction(py_call(F:'__call__'(), R)).

petta_py_contains(Space, Tagged) :-
    petta_py_decode_shared(Tagged, Pattern, _),
    match(Space, Pattern, found, found), !.

%Clear a space: a Python provider owns its storage, so it clears (or
%refuses, loudly, when it cannot); everything else, Prolog providers and
%native spaces with their announce-when-watched and tabling-death rules,
%is the engine's metta_host_clear_space/1.
petta_py_clear(Space) :-
    petta_py_foreign(Space), !,
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_clear(SpaceStr), _).
petta_py_clear(Space) :-
    metta_host_clear_space(Space).

%The host's clause of the hooks-idle ownership seams: the engine hands the
%handler census in as clause references, and this side answers from the one
%reference it installed, the subscription bridge, without consulting any
%engine internals. Idle means this unwatched space's only handler is the
%bridge itself.
:- multifile metta_host_add_hooks_idle/2.
metta_host_add_hooks_idle(Space, [OnlyRef]) :-
    \+ petta_py_subscribed_space(Space),
    petta_py_subscription_hook_ref(added, OnlyRef).

:- multifile metta_host_remove_hooks_idle/2.
metta_host_remove_hooks_idle(Space, [OnlyRef]) :-
    \+ petta_py_subscribed_space(Space),
    petta_py_subscription_hook_ref(removed, OnlyRef).

%Fresh space names for callers that want an anonymous space. The & prefix is
%load-bearing: 'is-space' recognises it, and a $ name would read as a variable.
%A released name goes back into a pool and is handed out again, because a
%space's module cannot be destroyed (SWI keeps modules for the process), so
%reuse is what keeps a churn of short-lived spaces from growing the module
%table forever. A candidate that already holds anything, foreign
%registrations included, is skipped: fresh means fresh.
:- dynamic petta_py_space_counter/1.
:- dynamic petta_py_free_space/1.
petta_py_space_counter(0).

petta_py_new_space(Name) :-
    ( retract(petta_py_free_space(Name))
      -> true
    ; petta_py_next_space(Name) ).

petta_py_next_space(Name) :-
    retract(petta_py_space_counter(N)),
    N1 is N + 1,
    assertz(petta_py_space_counter(N1)),
    atom_concat('&pyspace_', N1, Candidate),
    ( petta_py_space_untouched(Candidate)
      -> Name = Candidate
    ; petta_py_next_space(Name) ).

petta_py_space_untouched(Name) :-
    \+ petta_py_foreign(Name),
    \+ metta_host_stored(Name, _).

%Release a space: everything cleared, the name pooled for reuse.
petta_py_release_space(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    petta_py_clear(Name),
    ( petta_py_free_space(Name) -> true ; assertz(petta_py_free_space(Name)) ).

%%%%%%%%%% Query %%%%%%%%%%
%
% A query is a list of patterns run as one conjunction through the engine's own
% match/4, its native [','|Patterns] form, so joins are the matcher's joins.
% VarNames selects which variables come back, as one row per answer.

petta_py_query(Space, PatternsTagged, VarNames, Row) :-
    petta_py_decode_shared(["e", PatternsTagged], Patterns, Bindings),
    petta_py_match_goal(Space, Patterns, Goal),
    call(Goal),
    petta_py_row(VarNames, Bindings, Row).

petta_py_match_goal(Space, [P], match(Space, P, answered, answered)) :- !.
petta_py_match_goal(Space, Ps, match(Space, [','|Ps], answered, answered)).

petta_py_query_all(Space, PatternsTagged, VarNames, Rows) :-
    findall(Row, petta_py_query(Space, PatternsTagged, VarNames, Row), Rows).

%The seam's own decision for this query, shown without running it, is the
%engine's metta_host_explain_match/3; this renders its term report as the
%wire shape, classes to strings and origin terms to prose
%[tested test_explain_reflects_the_plan].
petta_py_explain(Space, PatternsTagged, Report) :-
    petta_py_decode_shared(["e", PatternsTagged], Patterns, _),
    metta_host_explain_match(Space, Patterns, Explained),
    petta_py_render_explain(Explained, Report).

petta_py_render_explain(explain(stored, _, _, _), ["stored", [], [], []]).
petta_py_render_explain(explain(refused, [Entry], _, _),
                        ["refused", [EText], [], []]) :-
    swrite(Entry, EText).
petta_py_render_explain(explain(foreign, Classes, ClaimedIdx, RestIdx),
                        ["foreign", Rendered, ClaimedIdx, RestIdx]) :-
    maplist(petta_py_render_class, Classes, Rendered).

petta_py_render_class(class(ClassAtom, Origin), [Class, OriginText]) :-
    atom_string(ClassAtom, Class),
    petta_py_render_origin(Origin, OriginText).

petta_py_render_origin(declared(Entry, Fidelity, Det), Text) :-
    swrite(Entry, EText),
    ( var(Det) -> DetText = unstated ; DetText = Det ),
    format(string(Text), "declared: (handles ~w ~w ~w)",
           [EText, Fidelity, DetText]).
petta_py_render_origin(provider, "the provider's own pushdown method").
petta_py_render_origin(unclaimed,
                       "unclaimed; silence is inexact and candidates re-unify").
petta_py_render_origin(refused(Refusing), Text) :-
    swrite(Refusing, RText),
    format(string(Text), "the declared entry ~w answers Refuse", [RText]).

%A query with a guard and a bound: the guard decodes IN THE SAME variable
%scope as the patterns, so $age in both is one variable; after the match
%joins, the guard evaluates in the space's module and must answer true.
%Limit 0 means every answer.
%The guard translates ONCE, before the match enumerates: its variables are
%the same Prolog variables the patterns bind, so each answer runs the
%already-compiled goals against its own bindings, and backtracking retracts
%them. Translating inside the enumeration would recompile per candidate
%row, which measured at ~500ms per 2000-row guarded query.
petta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row) :-
    petta_py_decode_shared(["e", [GuardTagged | PatternsTagged]], [Guard | Patterns], Bindings),
    petta_py_match_goal(Space, Patterns, Goal),
    petta_py_module(Space, Module),
    petta_py_in_module(Module, translate_expr(Guard, Goals, Out)),
    call(Goal),
    petta_py_call_goals(Module, Goals),
    Out == true,
    petta_py_row(VarNames, Bindings, Row).

petta_py_query_guarded_all(Space, PatternsTagged, GuardTagged, VarNames, Limit, Rows) :-
    Query = petta_py_query_guarded(Space, PatternsTagged, GuardTagged, VarNames, Row),
    ( Limit > 0
      -> findall(Row, limit(Limit, Query), Rows)
    ; findall(Row, Query, Rows) ).

%The bound is applied here whatever happens below, so pushing it down cannot
%change an answer. It is pushed only for ONE pattern against a foreign space:
%across a join the bound belongs to the joined rows, and an outer match
%truncated at N would lose the rows its later candidates would have joined
%to. A guarded query keeps the bound here too, since the guard decides how
%many candidates become answers.
petta_py_query_limit_all(Space, PatternsTagged, VarNames, Limit, Rows) :-
    (   PatternsTagged = [PatternTagged],
        metta_foreign_space(Space)
    ->  findall(Row,
                limit(Limit,
                      petta_py_bounded_query(Space, PatternTagged, VarNames,
                                             Limit, Row)),
                Rows)
    ;   findall(Row,
                limit(Limit, petta_py_query(Space, PatternsTagged, VarNames, Row)),
                Rows)
    ).

petta_py_bounded_query(Space, PatternTagged, VarNames, Limit, Row) :-
    petta_py_decode_shared(["e", [PatternTagged]], [Pattern], Bindings),
    match_foreign(Space, Pattern, [limit(Limit)], answered, answered),
    petta_py_row(VarNames, Bindings, Row).

%A row holds one encoded value per requested name; a variable the answer left
%unbound comes back as itself:
%The acyclicity guard is the engine's own semantics, not a transport
%limit: match_native guards every OUT template with acyclic_term/1, so a
%rational-tree instantiation is not an answer there, and the engine's
%matching is unify_with_occurs_check throughout (spaces.pl
%petta_match_atoms, the arbiter's variable cases). The query lanes keep
%their bindings OUTSIDE the out template, so without this guard a cyclic
%join sailed past match_native's check and the row encode walked it to a
%stack overflow. Same semantics as match/4: the cyclic candidate FAILS
%this row and enumeration continues. Guarded once per row, not per
%column.
petta_py_row(Names, Bindings, Row) :-
    acyclic_term(Bindings),
    petta_py_row_columns(Names, Bindings, Row).

petta_py_row_columns([], _, []).
petta_py_row_columns([Name0|Names], Bindings, [Value|Values]) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    ( memberchk(Name-V, Bindings) -> petta_py_encode(V, Value)
    ; Value = ["v", Name0] ),
    petta_py_row_columns(Names, Bindings, Values).

%%%%%%%%%% Space modules %%%%%%%%%%
%
% On an engine carrying the per-space-equation patch, a space's compiled
% clauses live in a module named after it and space_module/2 says which; a
% stock engine keeps everything in user. Asking rather than assuming keeps
% this shim loadable on both.

petta_py_module(Space, Module) :-
    ( current_predicate(space_module/2) -> space_module(Space, Module)
    ; Module = user ).

petta_py_in_module(Module, Goal) :-
    ( current_predicate(with_metta_module/2) -> with_metta_module(Module, Goal)
    ; call(Goal) ).

%The translator's own acceptance for one typed argument position,
%exposed to Python: Value admits Type when ('get-type' *-> true ;
%'get-metatype') succeeds with Type bound, the exact check a typed call
%compiles, run in Space's module so its ':' declarations and &self's
%both answer, protocol types included. Both terms decode with shared
%variables, so a repeated variable in the target ((Pair $t $t))
%constrains. Refusal answers the value's own type candidates for the
%message; 'get-type' always answers at least '%Undefined%'.
petta_py_cast(Space, ValueW, TypeW, Out) :-
    petta_py_decode_shared(ValueW, Value, _),
    petta_py_decode_shared(TypeW, Type, _),
    petta_py_module(Space, Module),
    ( petta_py_in_module(Module,
          ( 'get-type'(Value, Type) *-> true ; 'get-metatype'(Value, Type) ))
      -> Out = ["s", "ok"]
    ; petta_py_in_module(Module, findall(T, 'get-type'(Value, T), Ts)),
      maplist(petta_py_encode, Ts, TsW),
      Out = ["e", TsW] ).

%%%%%%%%%% Evaluation %%%%%%%%%%
%
% Evaluation is the engine's own translate_expr/3 over the term, then its
% goals, exactly what a ! directive runs: compiled and called in the space's
% module, so the space's own equations answer. Answers enumerate on
% backtracking.

%Every answer carries its Well Founded Semantics truth: call_delays is
%one '$wfs_call' around the goal, answering true for an unconditional
%derivation and the conjunction of unknown tabled goals otherwise, per
%answer, INSIDE the enumeration, which is the only place the condition
%exists (findall erases it). An unconditional answer encodes exactly as
%before; an undefined one crosses under the u tag so the third truth
%value reaches Python instead of masquerading as an ordinary answer.
%The wrapper is unconditional on purpose: every gate on "tabling in use"
%has a first-tabled-call window that would answer silently wrong exactly
%once, and callees make per-predicate checks unsound. Measured cost on
%the trivial-eval crossing: five to ten percent (interleaved A/B against
%a plain twin, 222-236k against 248-249k calls per second); real
%evaluations amortize it below that.
petta_py_eval(Space, Tagged, Encoded) :-
    petta_py_eval_(Space, Tagged, plain, Encoded).

petta_py_eval_(Space, Target, Residuals, Encoded) :-
    petta_py_target_term(Space, Target, Term),
    petta_py_module(Space, Module),
    ( petta_py_direct_goal(Module, Term, Goal, Out)
      -> petta_py_in_module(Module, call_delays(call(Module:Goal), Delays))
    ; petta_py_in_module(Module, ( translate_cached_expr(Term, Goals, Out),
                                   call_delays(petta_py_call_goals(Module, Goals),
                                               Delays) )) ),
    petta_py_encode_truth(Out, Delays, Residuals, Encoded).

petta_py_encode_truth(Out, Delays, Residuals, Encoded) :-
    ( Delays == true
      -> petta_py_encode(Out, Encoded)
    ; petta_py_encode(Out, Inner),
      term_string(Delays, Why),
      ( Residuals == residual
        -> delays_residual_program(Delays, _:Clauses),
           term_string(Clauses, ResidualText),
           Encoded = ["u", Inner, Why, ResidualText]
      ; Encoded = ["u", Inner, Why] ) ).

%The fast path: a flat call of a compiled function whose arguments are all
%plain data needs no translation, just the call. translate_expr costs two
%orders more than the call itself on such terms, and they are what an API
%client evaluates all day. Anything with structure or evaluable arguments
%(a special form, a nested call, a symbol that names a function) takes the
%translator, whose judgment stays authoritative.
%Every head translate_expr treats structurally (its HV == chain and the
%stream rewrites): these must always take the translator, whatever their
%arguments look like.
petta_py_special('add-atom').     petta_py_special('and-then').
petta_py_special(call).           petta_py_special(case).
petta_py_special(catch).          petta_py_special(chain).
petta_py_special(collapse).       petta_py_special(cut).
petta_py_special(eval).           petta_py_special('filter-atom').
petta_py_special(foldall).        petta_py_special('foldl-atom').
petta_py_special(forall).         petta_py_special(hyperpose).
petta_py_special(if).             petta_py_special(let).
petta_py_special('let*').         petta_py_special('map-atom').
petta_py_special(match).          petta_py_special(once).
petta_py_special('or-else').      petta_py_special(prog1).
petta_py_special(progn).          petta_py_special(quote).
petta_py_special(reduce).         petta_py_special('remove-atom').
petta_py_special(sealed).         petta_py_special(superpose).
petta_py_special(test).           petta_py_special(transaction).
petta_py_special(translatePredicate).
petta_py_special(with_mutex).     petta_py_special('trace!').
petta_py_special(unique).         petta_py_special('alpha-unique').
petta_py_special(union).          petta_py_special(intersection).
petta_py_special(subtraction).

petta_py_direct_goal(Module, [F|Args], Goal, Out) :-
    atom(F),
    fun(F),
    \+ petta_py_special(F),
    petta_py_plain_args(Args),
    length(Args, N),
    Arity is N + 1,
    arity(F, Arity),
    current_predicate(Module:F/Arity),
    append(Args, [Out], Full),
    Goal =.. [F|Full].

petta_py_plain_args([]).
petta_py_plain_args([A|As]) :-
    ( number(A) -> true
    ; string(A) -> true
    ; A == true -> true
    ; A == false -> true
    ; atom(A), \+ fun(A) -> true
    ; py_is_object(A) ),
    petta_py_plain_args(As).

petta_py_call_goals(_, []).
petta_py_call_goals(Module, [G|Gs]) :-
    call(Module:G),
    petta_py_call_goals(Module, Gs).

petta_py_eval_all(Space, Tagged, Encoded) :-
    findall(E, petta_py_eval(Space, Tagged, E), Encoded).

%eval with named host values, the same door petta_py_run_using opens for
%run: each Name-Value pair substitutes the bare symbol Name throughout the
%target before it evaluates, so a tensor or any other object reaches a
%rule by name and by IDENTITY rather than through a printed form. The
%target is read first, because substitution is over the term
%[tested test_eval_using_carries_identity].
petta_py_eval_using_all(Space, Target, Pairs, Encoded) :-
    petta_py_target_term(Space, Target, Term0),
    maplist(petta_py_using_pair, Pairs, Bindings),
    metta_host_substitute(Bindings, Term0, Term),
    %The substituted TERM evaluates directly. Re-encoding it to a wire and
    %handing that back to the ordinary entry point looks tidier and is
    %wrong: a substituted host value is a boxed reference, and a round
    %trip through the encoder is exactly the copy `using` exists to
    %avoid.
    findall(E, petta_py_eval_term(Space, Term, E), Encoded).

petta_py_eval_term(Space, Term, Encoded) :-
    petta_py_module(Space, Module),
    ( petta_py_direct_goal(Module, Term, Goal, Out)
      -> petta_py_in_module(Module, call_delays(call(Module:Goal), Delays))
    ; petta_py_in_module(Module, ( translate_cached_expr(Term, Goals, Out),
                                   call_delays(petta_py_call_goals(Module, Goals),
                                               Delays) )) ),
    petta_py_encode_truth(Out, Delays, plain, Encoded).

%Which of PeTTa's own evaluation paths produced each answer, reported without
%changing what the ordinary entry points return:
%
%  value           an equation, builtin or special form applied
%  not-reducible   no rule applied, so the answer is the written term itself,
%                  which is what PeTTa does with any head it cannot call
%  empty           the goal produced no answer at all, which is what (empty)
%                  and a match with no candidates do
%
%PeTTa had no name for these, so the taxonomy was taken from the mechanised
%Hyperon specification, which is the only part borrowed
%[source: LeaTTa checkout, MettaHyperonFull/Core/Result.lean, EvalStatus].
%The distinction that matters is the one that surface behaviour hides: empty
%is a pruned branch and not-reducible is an unevaluated term, and reading
%both as "nothing happened" is what made an earlier strict mode fire on
%(empty) and on a match with no candidates. An error is the fourth outcome
%there and is not reported here, because the caller already receives it as
%an exception.
%
%The head decides between value and not-reducible, using the same test the
%translator uses when it chooses between emitting a call and building data,
%so this reports the branch the engine actually took rather than guessing
%from the answer [tested test_eval_status_reports_the_four_outcomes].
petta_py_eval_status_all(Space, Tagged, Results) :-
    petta_py_decode_shared(Tagged, Term, _),
    petta_py_module(Space, Module),
    ( metta_reducible_head(Module, Term) -> Status = value
                                          ; Status = 'not-reducible' ),
    findall([Status, E], petta_py_eval(Space, Tagged, E), Answers),
    ( Answers == [] -> Results = [[empty, none]] ; Results = Answers ).

%The residual variant additionally derives, per undefined answer, the
%residual program from its delays (the loop through tnot responsible),
%the explanation surface eval(residuals=True) opts into.
petta_py_eval_res_all(Space, Tagged, Encoded) :-
    findall(E, petta_py_eval_(Space, Tagged, residual, E), Encoded).

%%%%%%%%%% Python-backed MeTTa functions %%%%%%%%%%
%
% A registered operation is an ordinary MeTTa function whose body lives in
% Python. Arguments cross encoded so Python sees real atoms; results cross
% back encoded. kind det calls once; kind many enumerates a Python iterator
% through py_iter/2, which is genuine nondeterminism. The raw kinds skip the
% encoding for speed and receive janus's default conversion instead, which
% suits operations over object references such as tensors.

:- dynamic petta_py_op_spec/3.

%An operation that answers nothing sends the declined sentinel, which turns
%into failure here: the semidet reading of a Python None or a raised Decline.
petta_py_declined(TR) :- TR = [T, D], petta_py_tag(T, x), petta_py_tag(D, declined).

%A variable that crosses and comes back is the CALLER'S variable, not a fresh
%one with the same name. Without this the boundary silently broke variable
%identity, which is the whole of why no relational use of a Python operation
%worked: a native (= (mcons $h $t) ($h 2 3)) answers an expression whose head
%IS $x, so binding the result to (9 2 3) binds $x to 9, while the same shape
%through a registered operation answered a fresh $_34678 that binding did
%nothing to [tested: test_a_variable_crossing_python_comes_back_the_same_variable].
%
%The decoder already shares by name WITHIN one term, which is what makes an
%answer mentioning $x twice mention one variable. It just started from an
%empty table. Seeding it with the arguments is the whole fix, and the seed is
%expanded on first use by petta_py_shared_table/2, so a call whose result
%holds no variable pays nothing at all for it.
%petta_py_failure/2 is bindings/python/bridge.pl's, and a registered operation was the one
%Python caller not reaching it. That is not a cosmetic gap: without it janus's
%own error term reaches MeTTa carrying the live exception OBJECT and a live
%TRACEBACK object, which is the defect petta_py_failure/2 was written to fix
%for py-call and py-atom, and it names a Python file and line and no MeTTa
%call at all. What a program gets instead is
%(Error (python_error ZeroDivisionError "division by zero") (context (op 1) ...)),
%which it can branch on, compare and print after the failure
%[tested: test_an_operation_failure_names_the_metta_call].
%
%The catch is written out here rather than going through petta_py_guard/2, its
%three other callers' spelling, because the wrapper is a predicate call and
%this is the hot path: guard plus catch cost two inferences per call where the
%catch alone costs one [measured 2026-08-17: the encoded operation at 14.01
%through the wrapper, 13.01 written out]. Same catcher, same recovery.
petta_py_dispatch_det(Name, Args, Result) :-
    maplist(petta_py_encode, Args, TA),
    catch(py_call(petta_ops:dispatch(Name, TA), TR),
          Error, TR = '$petta_op_error'(Error)),
    (   TR = '$petta_op_error'(DetError)
    ->  petta_py_op_erring(Name, Args, DetError, Result)
    ;   \+ petta_py_declined(TR),
        %The shape test and this whole branch are written out because
        %this is the hot path: a plain wire is two elements, the explicit
        %answer four or five, the inlined unification costs no inference,
        %and even one helper call showed up as +1 per call on the extcost
        %gate [measured 2026-08-17: encoded 57248 against its 54248
        %baseline through a petta_py_dispatch_det_result/4 helper, and
        %54248 written out].
        (   TR = [_, _, _, _|_]
        ->  petta_py_answer_result(TR, Name, Args, Result)
        ;   petta_py_decode_shared_(TR, Result, variables_of(Args), _)
        )
    ).

%The guard wraps the whole enumeration and that is safe in both directions:
%catch/3 keeps Goal's choice points and re-establishes the catcher on
%backtracking, so a generator yielding two values and then raising is caught
%on the third [measured 2026-08-17: catch/3 over member/2 gives all three
%solutions, and a throw on the last one is caught].
petta_py_dispatch_many(Name, Args, Result) :-
    maplist(petta_py_encode, Args, TA),
    (   petta_on_error_mode(Name, [Name|Args], DeclaredMode),
        DeclaredMode \== abort
    ->  Mode = DeclaredMode
    ;   Mode = abort
    ),
    catch(( py_iter(petta_ops:dispatch_many(Name, TA, Mode), TR0), TR = TR0 ),
          Error, TR = '$petta_op_error'(Error)),
    (   TR = '$petta_op_error'(ManyError)
    ->  petta_py_op_erring(Name, Args, ManyError, Result)
    ;   TR = [_, _, _, _|_]
    ->  petta_py_answer_result(TR, Name, Args, Result)
    ;   petta_py_decode_shared_(TR, Result, variables_of(Args), _)
    ).

%An operation's declared error mode, consulted only in the recovery, so
%the success path pays one functor test. keep reduces the failed call to
%its (Error ...) atom; empty answers nothing, the semidet reading;
%control signals and transport failures always pass to the thrower.
petta_py_op_erring(Name, Args, Error, Result) :-
    (   control_exception(Error)
    ->  petta_py_failure([Name|Args], Error)
    ;   petta_transport_failure(Error)
    ->  petta_py_failure([Name|Args], Error)
    ;   petta_on_error_mode(Name, [Name|Args], Mode)
    ->  (   Mode == keep
        ->  petta_error_answer([Name|Args], Error, Result)
        ;   Mode == empty
        ->  fail
        ;   petta_py_failure([Name|Args], Error)
        )
    ;   petta_py_failure([Name|Args], Error)
    ).

%The name petta_py_encode/2 wrote for a variable, so a returned ["v", Name]
%finds the variable it came from.
petta_py_named_variable(Variable, Name-Variable) :- term_to_atom(Variable, Name).

%Raw results skip the wire encoding, so a Python boolean arrives as janus's
%@(true)/@(false); normalize to the language booleans exactly as 'py-call'
%does, so raw operations compose with if, and, or:
petta_py_raw_norm('@'(true), true) :- !.
petta_py_raw_norm('@'(false), false) :- !.
petta_py_raw_norm(R, R).

%A raw None is janus's @(none); it reads as no answer, the same semidet rule
%the encoded path applies, since MeTTa has no None value to hand back:
%The same catcher the encoded paths carry, and for the same reason: without it
%a raw operation's failure reaches MeTTa as janus's own term, holding the live
%exception OBJECT, a live TRACEBACK and an unbound context, so `(catch (op 1))`
%answered
%(Error (python_error ZeroDivisionError <ZeroDivisionError>)
%       (context $_26320 (python_stack <traceback>)))
%which names an address, cannot be compared and says nothing about which MeTTa
%call failed. Skipping the wire encoding is a speed decision about ARGUMENTS
%and results; it was never a decision to report failures differently
%[tested: test_a_raw_operation_fails_like_an_encoded_one].
%
%It costs one inference, and that is the floor rather than a choice: "the
%overhead of calling a goal through catch/3 is comparable to call/1"
%[source: SWI-Prolog manual, catch/3]. The zero-cost alternative was looked
%for and rejected. prolog:prolog_exception_hook/5 fires only on an actual
%exception, and it is a process-global singleton `library(prolog_stack)`,
%trap/1 and the GUI debugger already use, it "is never called recursively",
%and converting this error means calling back into Python to render the
%message, which is exactly what a non-reentrant hook must not do.
%
%Against the crossing it guards, one inference is not the number that matters:
%a raw operation costs 0.87 microseconds where a MeTTa function costs 0.09
%[measured 2026-08-17], so janus dominates it by an order of magnitude.
petta_py_dispatch_raw_det(Name, Args, Result) :-
    catch(py_call(petta_ops:dispatch_raw(Name, Args), R0),
          Error, petta_py_failure([Name|Args], Error)),
    R0 \== '@'(none),
    petta_py_raw_norm(R0, Result).

petta_py_dispatch_raw_many(Name, Args, Result) :-
    catch(py_iter(petta_ops:dispatch_raw_many(Name, Args), R0),
          Error, petta_py_failure([Name|Args], Error)),
    R0 \== '@'(none),
    petta_py_raw_norm(R0, Result).

%Register every arity of a Python-backed function in one step, checked
%before anything mutates: a name whose compiled predicate would collide
%with a static procedure ((+)/3, say) throws HERE, with no state touched,
%and every previously registered arity of the name is replaced rather than
%left behind for calls the new callable no longer serves.
%The dogfood route: registration parameters read from the contract atoms in
%&petta rather than passed. The Python keywords are sugar that asserts the
%atoms ((op Name Arity Kind) per arity, (inverse Name) when a backwards
%direction exists), and this compiles the predicate FROM them, through
%exactly the builders the passed-parameter route uses, so the clause is
%identical by construction and the cube gate proves it stays that way.
petta_py_compile_op(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    findall(Arity-Kind, petta_contract_fact([op, Name, Arity, Kind]), Pairs),
    (   Pairs == []
    ->  throw(error(petta_contract_missing_op(Name), none))
    ;   true
    ),
    pairs_keys(Pairs, Arities),
    Pairs = [_-Kind|_],
    (   forall(member(_-K, Pairs), K == Kind)
    ->  true
    ;   throw(error(petta_contract_conflict(Name, Pairs), none))
    ),
    (   petta_contract_fact([inverse, Name])
    ->  Invertible = true
    ;   Invertible = false
    ),
    petta_py_register_op_set(Name, Arities, Kind, Invertible).

%A (handles ...) declaration, written and coherence-checked in one
%transaction: the new entry is asserted, every critical pair over the
%context is routed, and a disagreeing tie throws petta_contract_conflict,
%which rolls the assert back. The overlap is caught at declaration time
%naming both entries, not on the first query that falls into it.
petta_py_declare_handles(Space, Tagged, Ctx0) :-
    ( atom(Ctx0) -> Ctx = Ctx0 ; atom_string(Ctx, Ctx0) ),
    transaction(( petta_py_add(Space, Tagged),
                  petta_handles_coherent(Ctx) )).

:- multifile prolog:error_message//1.
prolog:error_message(petta_contract_missing_op(Name)) -->
    [ 'compiling ~w from the contract found no (op ~w Arity Kind) atom in \c
       &petta; the registration sugar asserts them before compiling, so \c
       reaching this means the atoms and the compile call got out of \c
       order'-[Name, Name] ].
prolog:error_message(petta_contract_conflict(Name, Pairs)) -->
    [ 'the contract atoms for ~w disagree on its kind across arities: ~w. \c
       One operation has one kind'-[Name, Pairs] ].

petta_py_register_op_set(Name0, Arities, Kind, Invertible) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    petta_py_set_invertible(Name, Invertible),
    %OPEN before any mutation: the tier refusal and the name probe both run
    %while there is still nothing to undo, and each one's diagnostic names
    %what to do about it. The unregister of prior arities may release the
    %name; the adopt below claims it again, so the set's final state is
    %claimed whatever order the arities land in.
    forall(member(A, Arities),
           (   petta_py_op_spec(Name, A, _)
           ->  true
           ;   PredArity is A + 1,
               metta_host_open_function(Name, python, PredArity)
           )),
    forall(petta_py_op_spec(Name, Old, _), petta_py_unregister_op(Name, Old)),
    forall(member(A, Arities), petta_py_register_op(Name, A, Kind)).

%The name probe, its owner-naming refusal and the petta_op_name_taken
%message live in the engine now (metta_host_open_function/3): the protocol
%was host-agnostic bookkeeping every binding restated in order. The one
%shortcut kept here is the caller's: an arity this file already registered
%occupies its own functor, so re-opening it proves nothing.

%Register a Python-backed function of the given MeTTa arity. The compiled
%predicate carries one extra output argument, the engine's own convention:
petta_py_register_op(Name0, Arity, Kind) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    petta_py_unregister_op(Name, Arity),
    length(Args, Arity),
    append(Args, [Result], HeadArgs),
    Head =.. [Name | HeadArgs],
    petta_py_op_body(Kind, Name, Args, Result, Forward),
    petta_py_directed_body(Name, Kind, Args, Result, Forward, Body),
    %Into &self's module, which every other space inherits, so the operation is
    %callable from all of them and its name is free: asserting into the module
    %the ENGINE resolves in is what made 217 ordinary names unusable at MeTTa
    %arity 1.
    petta_py_module('&self', Base),
    assertz(Base:(Head :- Body)),
    assertz(petta_py_op_spec(Name, Arity, Kind)),
    %Adopt AFTER the dispatch clause is in place: the engine marks the name a
    %function of the BASE tier (which every space inherits, so the operation
    %stays callable after a named space defines an equation of the same
    %name), refreshes dependents against the clause that already exists, and
    %claims the name for python.
    PredArity is Arity + 1,
    metta_host_adopt_function(Name, python, Kind, PredArity).

%The engine asks who a dispatch goal really is, so a purity refusal names the
%operation rather than this file's dispatcher. The name is the goal's first
%argument in all four kinds, which is why it is recoverable exactly.
:- multifile metta_effect_operation_name/3.
metta_effect_operation_name(petta_py_dispatch_det(Name, Args, _), Name, Arity) :-
    petta_py_dispatch_arity(Args, Arity).
metta_effect_operation_name(petta_py_dispatch_many(Name, Args, _), Name, Arity) :-
    petta_py_dispatch_arity(Args, Arity).
metta_effect_operation_name(petta_py_dispatch_raw_det(Name, Args, _), Name, Arity) :-
    petta_py_dispatch_arity(Args, Arity).
metta_effect_operation_name(petta_py_dispatch_raw_many(Name, Args, _), Name, Arity) :-
    petta_py_dispatch_arity(Args, Arity).

%The MeTTa arity, which is the argument list's length: the engine's extra
%output slot is the dispatch goal's third argument and not one of these.
petta_py_dispatch_arity(Args, Arity) :- is_list(Args), !, length(Args, Arity).
petta_py_dispatch_arity(_, unknown).

petta_py_op_body(det,      Name, Args, R, petta_py_dispatch_det(Name, Args, R)).
petta_py_op_body(many,     Name, Args, R, petta_py_dispatch_many(Name, Args, R)).
petta_py_op_body(raw_det,  Name, Args, R, petta_py_dispatch_raw_det(Name, Args, R)).
petta_py_op_body(raw_many, Name, Args, R, petta_py_dispatch_raw_many(Name, Args, R)).

:- dynamic petta_py_op_invertible/1.

petta_py_set_invertible(Name, Invertible) :-
    retractall(petta_py_op_invertible(Name)),
    ( ( Invertible == true ; Invertible == "true" )
      -> assertz(petta_py_op_invertible(Name)) ; true ).

%An operation that declared an inverse compiles a MODE TEST into its clause,
%and one that did not compiles exactly the body it compiled before. That is
%the point of deciding it here rather than in the dispatch: a direction almost
%no operation can serve must not cost every operation a check per call.
%
%The three modes read in the order a reader would ask them. Ground arguments
%are an ordinary forward call whatever the result slot holds, so a forward
%call never reaches the inverse even when the caller left the result unbound.
%Otherwise a bound result with unbound arguments is the relational position,
%which is what (let (f $h $t) (1 2 3) ...) compiles to. Anything else is
%forwards, and fails the way it always did, because an operation cannot
%invent a result from nothing.
%
%This is Curry's mode-directed reading of a function as a relation, done by
%hand because a foreign function cannot be narrowed: Curry does not invert its
%own `external` functions either, so an explicit backwards direction is the
%same answer Prolog's plus/3 and succ/2 give for their non-narrowable
%builtins [tested: test_a_registered_operation_runs_backwards].
petta_py_directed_body(Name, Kind, Args, Result, Forward, Body) :-
    (   petta_py_op_invertible(Name)
    ->  petta_py_inverse_goal(Kind, Name, Result, Args, Backward),
        Body = (   ground(Args)
               ->  Forward
               ;   nonvar(Result)
               ->  Backward
               ;   Forward
               )
    ;   Body = Forward
    ).

%The inverse crosses the way the operation's FORWARD direction crosses. An
%author writes one function pair, and a raw operation whose inverse went
%through the wire encoding saw `str` for a symbol going forwards and `Sym`
%coming back, which is one pair and two value conventions
%[tested: test_a_raw_operations_inverse_crosses_raw_too].
petta_py_inverse_goal(Kind, Name, Result, Args, Goal) :-
    (   petta_py_raw_kind(Kind)
    ->  Goal = petta_py_dispatch_inverse_raw(Name, Result, Args)
    ;   Goal = petta_py_dispatch_inverse(Name, Result, Args)
    ).

petta_py_raw_kind(raw_det).
petta_py_raw_kind(raw_many).

%One result in, argument tuples out. It enumerates, because an inverse is a
%relation: a result with two preimages answers twice, and one with none fails,
%which is failure rather than an error exactly as it is forwards.
%
%The arity is checked here rather than trusted, because the inverse is the
%author's own Python and a tuple of the wrong width would otherwise unify
%against nothing and read as "no solution" rather than as the mistake it is.
petta_py_dispatch_inverse(Name, Result, Args) :-
    petta_py_encode(Result, TR),
    catch(py_iter(petta_ops:dispatch_inverse(Name, TR), TArgs),
          Error, petta_py_failure([Name, Result], Error)),
    petta_py_inverse_width(Name, Args, TArgs),
    maplist(petta_py_decode_one, TArgs, Args).

petta_py_dispatch_inverse_raw(Name, Result, Args) :-
    catch(py_iter(petta_ops:dispatch_inverse_raw(Name, Result), RawArgs),
          Error, petta_py_failure([Name, Result], Error)),
    petta_py_inverse_width(Name, Args, RawArgs),
    maplist(petta_py_raw_norm, RawArgs, Args).

petta_py_inverse_width(Name, Args, Answered) :-
    length(Args, Arity),
    (   is_list(Answered), length(Answered, Arity)
    ->  true
    ;   petta_py_inverse_arity_error(Name, Arity, Answered)
    ).

petta_py_decode_one(Tagged, Term) :- petta_py_decode_shared(Tagged, Term, _).

petta_py_inverse_arity_error(Name, Arity, TArgs) :-
    ( is_list(TArgs) -> length(TArgs, Got) ; Got = 1 ),
    throw(error(petta_py_inverse_arity(Name, Arity, Got),
                context(petta, 'the inverse answered the wrong number of arguments'))).

:- multifile prolog:error_message//1.

%A tuple of the wrong width would otherwise unify against nothing and read as
%"this result has no preimage", which is the one answer an inverse is entitled
%to give and the one that hides the mistake.
prolog:error_message(petta_py_inverse_arity(Name, Wanted, Got)) -->
    [ 'the inverse of ~w answered an argument tuple of width ~d, and the \c
       operation takes ~d'-[Name, Got, Wanted], nl,
      '  an inverse returns the arguments as a tuple of that width, or the \c
       bare value at arity one' ].

%Remove one registered arity of an operation, leaving other arities alone.
%When nothing defines the name any more, forget the function entirely, the
%same forgetting 'remove-atom'/3 does when a last equation goes: fun/1 and
%arity/2 retract, so the next compile treats the name as data again:
petta_py_unregister_op(Name0, Arity) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %The drop is guarded by this file's own bookkeeping, so only arities this
    %file registered are dropped; the engine's drop then retracts the base
    %tier's clauses and the arity row generically.
    ( petta_py_op_spec(Name, Arity, _)
      -> PredArity is Arity + 1,
         metta_host_drop_function(Name, PredArity),
         retractall(petta_py_op_spec(Name, Arity, _))
    ; true ),
    %"does anything still define this name at any arity" is a question about
    %OUR clauses, and clause/3 raises permission_error(access,
    %private_procedure, _) on a protected system predicate rather than
    %answering it, so unregistering an operation named print or format threw
    %from here instead of unregistering. A builtin is never a clause of ours
    %[tested test_unregistering_a_name_a_system_predicate_shares_does_not_throw].
    ( \+ petta_py_name_still_defined(Name)
      -> metta_host_forget_function(Name)
    ; true ).

%Does anything still define this name at any arity? Two tiers are asked by
%name because ONE of them cannot be reached by generating: current_predicate/1
%with the arity unbound enumerates a module's own predicates and the ones
%explicitly imported into it, and NOT the ones it reaches through its base
%chain. A registered operation's clauses are in the base tier's module and a
%Prolog function's are in the host's, so asking either alone released a name
%the other still defined: registering an operation over a Prolog registration
%was refused, correctly, and dropped the Prolog one's arity/2 and fun/1 on the
%way out, so the call it had been answering came back unreduced
%[tested test_a_prolog_registration_is_not_silently_replaced].
petta_py_name_still_defined(Name) :-
    ( petta_py_module('&self', Module) ; petta_engine_module(Module) ),
    current_predicate(Module:Name/A),
    functor(Head, Name, A),
    \+ predicate_property(Module:Head, built_in),
    clause(Module:Head, _, _),
    !.

%The names a source declared for itself, so register_prolog can answer what it
%registered without being told. The membership record is the engine's, not the
%library's, which is what makes the extension a unit rather than a list the
%library has to keep: it registers, and the engine remembers
%[source: PostgreSQL, "the objects of the extension go together"].
%The file is compared after resolving both sides, because the engine records
%SWI's canonical absolute path and a caller passes whatever they typed.
%Read off the FILE record rather than off extension membership. An extension
%is optional on the Prolog side, so asking through one made a file with
%`metta_export` and no `metta_extension` look like a failed registration when
%every name in it had registered.
%What a source declares, read WITHOUT running it, so register_prolog can
%refuse a file that declares nothing before consulting it. It used to consult
%first and check after, so a provider file with no declaration raised and
%installed the provider anyway: catching the error made everything work, which
%is the one outcome that teaches an author to ignore an error.
petta_py_source_declares(Source0, Declares) :-
    ( atom(Source0) -> Source = Source0 ; atom_string(Source, Source0) ),
    metta_source_declarations(Source, Declarations),
    petta_py_classify_declarations(Declarations, Declares).

%The same question of source held in memory, which has no file to open.
petta_py_string_declares(Text, Declares) :-
    metta_string_declarations(Text, Declarations),
    petta_py_classify_declarations(Declarations, Declares).

petta_py_classify_declarations(Declarations, Declares) :-
    ( memberchk(export(_), Declarations) -> Exports = true ; Exports = false ),
    ( memberchk(extension(_), Declarations) -> Extension = true
    ; Extension = false ),
    petta_py_declares(Exports, Extension, Declares).

petta_py_declares(true, true, "both").
petta_py_declares(true, false, "exports").
petta_py_declares(false, true, "extension").
petta_py_declares(false, false, "nothing").

petta_py_declared_exports(Source0, Names) :-
    ( atom(Source0) -> Source = Source0 ; atom_string(Source, Source0) ),
    ( absolute_file_name(Source, Resolved, [file_errors(fail)]) -> true
    ; Resolved = Source ),
    findall(S,
            ( metta_file_export(Recorded, Name),
              ( Recorded == Resolved -> true ; Recorded == Source ),
              atom_string(Name, S) ),
            Names0),
    sort(Names0, Names).

%The names one extension installed, asked before releasing them so the caller
%can be told what went.
petta_py_extension_members(Name0, Names) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    findall(S, ( metta_extension_member(Name, Member), atom_string(Member, S) ), Names).

%Everything one extension installed, released together.
petta_py_unregister_extension(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    unregister_metta_extension(Name).

%Every function or translator special-form name the language knows, for
%completion and docs. The translator clause table is the special-form
%registry; asking it keeps this answer current when a form is added there.
petta_py_builtins(Names) :-
    findall(N, fun(N), Functions),
    petta_py_special_form_names(SpecialForms),
    append(Functions, SpecialForms, Language0),
    sort(Language0, Language),
    maplist(atom_string, Language, Names).

petta_py_special_form_names(Names) :-
    petta_engine_module(Engine),
    findall(Name,
            ( clause(Engine:translate_special_dl(Name, _, _, _, _), _),
              atom(Name) ),
            Names0),
    sort(Names0, Names).

petta_py_is_function(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name).

%Whether a function ANSWERS from this space: it has clauses its module can
%see, its own or inherited from user. Another space's equations live in that
%space's module and are invisible here, so they do not count.
petta_py_function_visible(Space0, Name0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name),
    petta_py_module(Space, Module),
    catch_recover(( current_predicate(Module:Name/Arity),
                    functor(Head, Name, Arity),
                    clause(Module:Head, _, _) ),
                  fail), !.

petta_py_arities(Name0, As) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    findall(A, arity(Name, A), As).

%Every stored equation for a name, live from the space. Pattern-directed:
%a native space answers by first-argument index on '=', a foreign space
%enumerates and unifies, and the open tail in the head pattern is Prolog
%unification against stored lists, not the MeTTa matcher.
petta_py_equations(Space, Name0, Encoded) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    Pattern = [=, [Name|_], _],
    findall(E, ( metta_host_stored(Space, Pattern),
                 petta_py_encode(Pattern, E) ), Encoded).

%The Prolog clauses a name compiled to, dis for the translator: one
%listing per registered arity, resolved in this space's module so a named
%space shows the clauses it would run. Fails on a name the engine never
%compiled, and the Python side turns that into its own refusal.
petta_py_disassemble(Space, Name0, Text) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    findall(A, arity(Name, A), As0),
    As0 \== [],
    sort(As0, As),
    space_module(Space, Module),
    with_output_to(string(Text),
                   forall(member(A, As),
                          (   current_predicate(Module:Name/A)
                          ->  listing(Module:Name/A)
                          ;   true ))).

%%%%%%%%%% Derivation trees %%%%%%%%%%
%
% The classic proof-tree meta-interpreter, rendered in MeTTa terms: every
% compiled clause remembers its source equation through translated_from/2,
% so each node names the equation that fired, a stored atom is a leaf, and a
% builtin call is an opaque leaf. Control constructs recurse into the branch
% they execute. A finite depth emits a truncated node rather than claiming no
% proof. Negative depth means unbounded; Python puts that search behind the
% same time and inference guards as evaluation.

petta_py_derivation(Space, Tagged, Depth, TreeTagged) :-
    petta_py_decode_shared(Tagged, Term, _),
    Term = [F|Args],
    atom(F),
    append(Args, [Out], FullArgs),
    Goal =.. [F|FullArgs],
    petta_py_module(Space, Module),
    petta_py_in_module(Module, petta_py_solve(Module, Goal, Depth, Tree)),
    petta_py_encode_tree(Tree, [F|Args], Out, TreeTagged).

petta_py_solve(M, Goal, D, Tree) :-
    petta_py_solve_barrier(M, Goal, D, Tree, _).

%A cut prunes the clauses that follow it and the choicepoints that precede
%it in the same body. Recorded as a leaf and simply called, it pruned
%neither, so the tree proved conclusions the program cannot reach: two
%equations for one head, the first cutting, proved both while run answered
%only the first.
%
%That is the naive incorporation the literature names and rejects: "A naive
%incorporation of cuts treats them as a builtin predicate, effectively
%adding a clause solve(!) <- !. This clause does not achieve the correct
%behavior of cut. The cut in the clause commits to the current solve clause
%rather than pruning the search tree." What has to be modelled instead is
%the cut's SCOPE, the clause in which the cut is a goal
%[source: Sterling and Shapiro, The Art of Prolog, 2nd ed., p327, ch17].
%That page states the problem and refers the solution out, so the technique
%below is this engine's own.
%
%Passing a cut signal upward prunes the later clauses but not the earlier
%goals, so the cut throws instead. Every construct that is a cut barrier in
%Prolog, a clause body, call/1, once/1, \+/1, findall/3 and an if-then-else
%condition, catches its own throw and turns it into failure, which discards
%the goals inside it and the clauses beside it together. That is what a cut
%does [tested: test_derivation_honours_a_cut].
petta_py_solve_barrier(M, Goal, D, Tree, Status) :-
    gensym('$petta_py_cut_', Barrier),
    catch(petta_py_solve_(M, Goal, D, Tree, Status, Barrier),
          petta_py_cut(Barrier),
          fail).

petta_py_solve_(_, Goal, 0, [truncated(Goal)], truncated, _) :- !.
petta_py_solve_(_, true, _, [], complete, _) :- !.
petta_py_solve_(_, '!', _, [builtin(!)], complete, Barrier) :- !,
    ( true ; throw(petta_py_cut(Barrier)) ).
petta_py_solve_(M, (If -> Then ; Else), D, Tree, Status, Barrier) :- !,
    ( petta_py_solve_barrier(M, If, D, IfTree, IfStatus)
      -> ( IfStatus == truncated
           -> Tree = IfTree, Status = truncated
         ; petta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
           append(IfTree, ThenTree, Tree) )
    ; petta_py_solve_(M, Else, D, Tree, Status, Barrier) ).
petta_py_solve_(M, (If -> Then), D, Tree, Status, Barrier) :- !,
    ( petta_py_solve_barrier(M, If, D, IfTree, IfStatus)
      -> ( IfStatus == truncated
           -> Tree = IfTree, Status = truncated
         ; petta_py_solve_(M, Then, D, ThenTree, Status, Barrier),
           append(IfTree, ThenTree, Tree) )
    ; fail ).
petta_py_solve_(M, (A ; B), D, Tree, Status, Barrier) :- !,
    ( petta_py_solve_(M, A, D, Tree, Status, Barrier)
    ; petta_py_solve_(M, B, D, Tree, Status, Barrier) ).
petta_py_solve_(M, (A, B), D, Tree, Status, Barrier) :- !,
    petta_py_solve_(M, A, D, TA, SA, Barrier),
    ( SA == truncated
      -> Tree = TA, Status = truncated
    ; petta_py_solve_(M, B, D, TB, Status, Barrier),
      append(TA, TB, Tree) ).
petta_py_solve_(M, call(A), D, Tree, Status, _) :- !,
    petta_py_solve_barrier(M, A, D, Tree, Status).
petta_py_solve_(M, once(A), D, Tree, Status, _) :- !,
    once(petta_py_solve_barrier(M, A, D, Tree, Status)).
petta_py_solve_(M, \+ A, D, Tree, Status, _) :- !,
    ( once(petta_py_solve_barrier(M, A, D, TA, SA))
      -> ( SA == truncated
           -> Tree = TA, Status = truncated
         ; fail )
    ; Tree = [builtin(\+ A)], Status = complete ).
petta_py_solve_(M, findall(Template, Goal, List), D, Tree, Status, _) :- !,
    findall([Template, SubTree, SubStatus],
            petta_py_solve_barrier(M, Goal, D, SubTree, SubStatus),
            Results),
    petta_py_findall_results(Results, Values, Tree, Status),
    ( Status == complete -> List = Values ; true ).

%A clause compiled from a MeTTa equation is a step worth showing, and its body
%is walked further. Everything else, engine machinery and space facts alike, is
%called whole and appears as one leaf, so the tree stays in MeTTa terms. The
%lookup is module-qualified: a named space's equations live in its module, and
%clause/3 falls back to user through module inheritance for the rest. Only the
%clause INSPECTION is guarded (an uninspectable goal is an opaque leaf); a
%body or builtin that ERRS propagates, because (/ 1 0) failing into "no
%proof" would be a lie about why:
%One barrier serves every clause of the goal, because a cut in the body of
%one clause discards the clauses after it as well as its own alternatives.
petta_py_solve_(M, Goal, D, Tree, Status, _) :-
    \+ predicate_property(M:Goal, built_in),
    gensym('$petta_py_cut_', Barrier),
    catch(petta_py_solve_clause(M, Goal, D, Tree, Status, Barrier),
          petta_py_cut(Barrier),
          fail).
petta_py_solve_(M, Goal, _, [builtin(Goal)], complete, _) :-
    predicate_property(M:Goal, built_in), !,
    call(M:Goal).

petta_py_solve_clause(M, Goal, D, Tree, Status, Barrier) :-
    catch_recover(clause(M:Goal, Body, Ref), fail),
    ( translated_from(Ref, Source)
      -> petta_py_next_depth(D, D1),
         petta_py_solve_(M, Body, D1, Sub, Status, Barrier),
         Tree = [step(Goal, Source, Sub)]
    ; call(M:Body),
      petta_py_leaf(Goal, Tree),
      Status = complete ).

petta_py_findall_results([], [], [], complete).
petta_py_findall_results(
    [[Value, SubTree, SubStatus]|Results], [Value|Values], Tree, Status) :-
    petta_py_findall_results(Results, Values, RestTree, RestStatus),
    append(SubTree, RestTree, Tree),
    ( SubStatus == truncated -> Status = truncated ; Status = RestStatus ).

petta_py_next_depth(D, D) :- D < 0, !.
petta_py_next_depth(D, D1) :- D1 is D - 1.

%A match over a space names the atom it found; anything else names its goal:
petta_py_leaf(match(Space, Pattern, _, _), [fact(Space, Pattern)]) :- !.
petta_py_leaf(Goal, [fact('&self', Fact)]) :-
    functor(Goal, Space, _),
    atom_concat('&', _, Space), !,
    Goal =.. [Space|Fact].
petta_py_leaf(Goal, [builtin(Goal)]).

%The tree crosses as nested tagged expressions:
%  (derivation Conclusion Steps...) with each step
%  (step Conclusion (= Head Body) Substeps...), (fact Atom), (builtin Text),
%  or (truncated Goal).
petta_py_encode_tree(Steps, Root, Out, ["e", [["s", "derivation"], RootE | StepEs]]) :-
    petta_py_encode([Root, '=', Out], ["e", [R, _, O]]),
    RootE = ["e", [["s", "answer"], R, O]],
    maplist(petta_py_encode_step, Steps, StepEs).

petta_py_encode_step(step(Goal, Source, Sub), ["e", [["s", "step"], GoalE, SourceE | SubEs]]) :-
    petta_py_encode(Goal, GoalE0),
    petta_py_goal_term(GoalE0, GoalE),
    petta_py_encode(Source, SourceE),
    maplist(petta_py_encode_step, Sub, SubEs).
petta_py_encode_step(fact(Space, Fact), ["e", [["s", "fact"], SpaceE, FactE]]) :-
    petta_py_encode(Space, SpaceE),
    petta_py_encode(Fact, FactE).
petta_py_encode_step(builtin(Goal), ["e", [["s", "builtin"], ["g", Text]]]) :-
    term_string(Goal, Text).
petta_py_encode_step(truncated(Goal), ["e", [["s", "truncated"], ["g", Text]]]) :-
    term_string(Goal, Text).

%A compiled goal f(A1..An,Out) renders as the call (f A1..An) with its answer:
petta_py_goal_term(["e", [F | ArgsAndOut]], ["e", [["s", "call"], ["e", [F|Args]], Out]]) :-
    append(Args, [Out], ArgsAndOut), !.
petta_py_goal_term(E, ["e", [["s", "call"], E, ["s", "?"]]]).

%%%%%%%%%% Foreign spaces %%%%%%%%%%
%
% A space whose atoms live in a Python provider: a database, a dataframe, an
% API. The engine's hooks route match, add, remove and get-atoms here; the
% provider enumerates candidate atoms for a pattern, and unification against
% the pattern happens in Prolog, so the provider may over-approximate freely
% and soundness stays the engine's. Registration is dynamic, from Python.

:- multifile metta_foreign_space/1.
:- multifile metta_foreign_match/3.
:- multifile metta_foreign_add/2.
:- multifile metta_foreign_add_many/2.
:- multifile metta_foreign_plan/5.
:- multifile metta_foreign_remove/3.
:- multifile metta_foreign_atoms/2.
:- multifile metta_foreign_pushdown/3.
:- multifile metta_foreign_capability/2.
:- multifile metta_foreign_refuse/2.

:- dynamic petta_py_foreign/1.
:- dynamic petta_py_capability/2.

%What a Python provider provides, in the ENGINE's vocabulary.
%
%The seam had two capability models that never met. foreign.py derives the set
%from the narrow protocols a provider implements and enforces it well; the
%Prolog side reads metta_foreign_capability/2 and saw nothing, so
%foreign_provides/2 reported that every Python provider provides EVERYTHING.
%Not a correctness bug, because the Python half raises anyway, but it meant
%engine logic keyed on a declaration silently excluded exactly the providers
%most likely to be incomplete, and a sixth capability could never be added to
%the vocabulary: claimed by silence on one side, unheard on the other.
%
%A projection rather than a new obligation. The set is computed where it
%already was, at registration, and provider authors write nothing new
%[tested: test_a_python_providers_capabilities_reach_the_engine].

%Each clause guards on the python registry: the foreign hooks are
%multifile, and an engine-side foreign space (a Redis space, say) must
%fall through to its own contribution instead of being claimed here.
%metta_foreign_clear/1 is declared with the other five in engine/ext_points.pl
%now, so it is part of the seam a library author reads rather than something
%only this file knew about.

metta_foreign_space(Space) :- petta_py_foreign(Space).

metta_foreign_capability(Space, Capability) :-
    petta_py_foreign(Space),
    petta_py_capability(Space, Capability).

%The refusal, handed back to the side that has the words. This raises; see
%petta.foreign.foreign_refuse for why it may not return.
metta_foreign_refuse(Space, Capability) :-
    petta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    atom_string(Capability, CapabilityStr),
    py_call(petta_ops:foreign_refuse(SpaceStr, CapabilityStr), _).

%The declared-mode stream: the mode crosses WITH the call, the Python
%side enforces it where the provider's exceptions are native (a
%mid-iteration exception tunnels past every Prolog catch), and a kept
%failure arrives as the reserved ["x","error",AtomWire] item. The
%["x","end"] item marks exhaustion so an empty stream still claims the
%route and the engine never re-consults the provider through the
%fallback, which would consume a linear source twice.
metta_foreign_erring(Space, Pattern, Licensed, Mode, Item) :-
    petta_py_foreign(Space),
    ( memberchk(limit(Limit), Licensed) -> true ; Limit = @(none) ),
    petta_py_encode(Pattern, W),
    atom_string(Space, SpaceStr),
    atom_string(Mode, ModeStr),
    py_iter(petta_ops:foreign_match(SpaceStr, W, Limit, ModeStr), CW),
    petta_py_erring_item(CW, Pattern, Limit, Space, Item).

petta_py_erring_item([XTag, End], _, _, _, end) :-
    ( XTag == "x" ; XTag == x ),
    ( End == "end" ; End == end ), !.
petta_py_erring_item([XTag, Err, ErrorW], _, _, _, kept(Kept)) :-
    ( XTag == "x" ; XTag == x ),
    ( Err == "error" ; Err == error ), !,
    petta_py_decode_shared(ErrorW, Kept, _).
petta_py_erring_item(CW, Pattern, Limit, Space, answer) :-
    petta_py_answer_match(CW, Pattern, Limit, Space).

%Custom matching for Python grounded values, Hyperon's CustomMatch: a
%value whose class defines match_/1 owns its matching logic inside
%`unify`, no registration, exactly as any grounded atom. The hook
%streams the object's answers and holds each to the met operand through
%the provider answer form, so bindings, an explicit value and a residue
%all work; an annotation is refused by the kappa gate below because a
%bare value has no context to declare a semiring on, and weighted
%matching is a context's job. Errors abort: a value's matching logic
%has no (on-error ...) home, so a raising match_ is a defect at its own
%yield site.
metta_matchable_value(Blob) :-
    metta_host_object(Blob),
    py_call(petta_ops:is_matchable(Blob), R),
    R == @(true).
metta_custom_match(Blob, Other) :-
    petta_py_encode(Other, W),
    py_iter(petta_ops:match_object(Blob, W), CW),
    petta_py_answer_match(CW, Other, '$petta-matchable').

%Transactional participation for Python providers, driven by (writes Ctx
%transactional): the provider's own begin/commit/rollback methods.
metta_foreign_begin(Space) :-
    petta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_transaction(SpaceStr, "begin"), _).
metta_foreign_commit(Space) :-
    petta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_transaction(SpaceStr, "commit"), _).
metta_foreign_rollback(Space) :-
    petta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_transaction(SpaceStr, "rollback"), _).

%The option reaches a provider whose match accepts a limit keyword and nobody
%else, which foreign.py decides from the signature, so a provider that never
%heard of it is called with none.
metta_foreign_match(Space, Pattern, Options) :-
    petta_py_foreign(Space),
    ( memberchk(limit(Limit), Options) -> true ; Limit = @(none) ),
    petta_py_encode(Pattern, W),
    atom_string(Space, SpaceStr),
    py_iter(petta_ops:foreign_match(SpaceStr, W, Limit), CW),
    petta_py_answer_match(CW, Pattern, Limit, Space).

%What the provider claims about its own filtering for this pattern, asked
%only when there is a bound to act on, so an unbounded match does not pay for
%a crossing it gains nothing from. A provider with no pushdown method answers
%inexact, which is what every provider written before this says.
metta_foreign_pushdown(Space, Pattern, Class) :-
    petta_py_foreign(Space),
    petta_py_encode(Pattern, W),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_pushdown(SpaceStr, W), ClassStr),
    atom_string(Class, ClassStr).

metta_foreign_atoms(Space, Atom) :-
    petta_py_foreign(Space),
    atom_string(Space, SpaceStr),
    py_iter(petta_ops:foreign_atoms(SpaceStr), CW),
    petta_py_decode_shared(CW, Atom, _).

metta_foreign_add(Space, Term) :-
    petta_py_foreign(Space),
    petta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_add(SpaceStr, W), _).

%The claim seam. A provider without a Planner declares no plan capability, so
%the engine never asks; one that does may still decline per conjunction, which
%is a `None` on the Python side and a failure here.
%
%The rows are materialised and the goal replays them, rather than the goal
%calling back into Python per row. A claim is answered as a whole, so streaming
%would buy nothing and would hold a Python generator open across engine
%backtracking, which is the shape that makes a provider's state hard to reason
%about.
metta_foreign_plan(Space, Patterns, Claimed, Rest, petta_py_plan_rows(Claimed, Rows)) :-
    petta_py_foreign(Space),
    petta_py_capability(Space, plan),
    maplist(petta_py_encode, Patterns, PatternWs),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_plan(SpaceStr, PatternWs), Answer),
    Answer \== @(none),
    Answer = [ClaimedWs, RestWs, RowWs],
    %The claim is a PARTITION of the caller's own patterns, so each
    %returned wire is resolved back to the caller's TERM by matching the
    %wire it was sent as. Decoding the wires instead built fresh copies:
    %a variable shared across two patterns (every join variable) split
    %into two, and the identity was then restored only as a side effect
    %of refuse_lossy_plan's msort unification pairing the two lists in
    %the same order. That coincidence held for plain variables, whose
    %addresses sorted alike on both sides, and broke the moment the
    %caller's variables carried attributes: the lists paired crosswise,
    %the join variable aliased wrongly, and a planning provider silently
    %lost answers [tested test_planner_rows_may_be_bindings].
    petta_py_plan_selection(ClaimedWs, PatternWs, Patterns, Claimed),
    petta_py_plan_selection(RestWs, PatternWs, Patterns, Rest),
    maplist(petta_py_decode_plan_row(Space), RowWs, Rows).

%Each returned wire is one of the wires we sent, so the caller's own term
%is at the same position. Positions are consumed, so a conjunction that
%repeats a pattern maps one occurrence to one occurrence rather than
%collapsing them.
petta_py_plan_selection(Ws, PatternWs, Patterns, Selected) :-
    maplist(petta_py_wire_key, PatternWs, Keys),
    petta_py_plan_selection_(Ws, Keys, Patterns, Selected).

petta_py_plan_selection_([], _, _, []).
petta_py_plan_selection_([W|Ws], Keys, Patterns, [P|Ps]) :-
    petta_py_wire_key(W, Key),
    (   nth0(I, Keys, K), K == Key
    ->  nth0(I, Patterns, P),
        petta_py_plan_drop(I, Keys, RestWs, Patterns, RestPatterns)
    ;   throw(error(petta_foreign_plan_is_not_a_partition(unknown, Patterns,
                                                          [W], []),
                    context(metta_foreign_plan/5,
                            'a claim names a pattern that was not offered')))
    ),
    petta_py_plan_selection_(Ws, RestWs, RestPatterns, Ps).

%A wire crossing to Python and back is the same structure with janus's own
%text convention applied, so the comparison normalizes every leaf to an
%atom rather than demanding string-for-string identity.
petta_py_wire_key(W, Key) :-
    (   is_list(W)
    ->  maplist(petta_py_wire_key, W, Key)
    ;   string(W)
    ->  atom_string(Key, W)
    ;   Key = W
    ).

petta_py_plan_drop(I, Ws, RestWs, Ps, RestPs) :-
    nth0(I, Ws, _, RestWs),
    nth0(I, Ps, _, RestPs).

petta_py_decode_row(RowW, Row) :- maplist(petta_py_decode_for_add, RowW, Row).

%A theta row keeps its wire until replay: at decode time the claimed
%patterns still hold fresh variables, and only refuse_lossy_plan's
%partition check reconnects them with the caller's own, so applying the
%bindings here would bind copies nobody reads.
petta_py_decode_plan_row(Space, RowW, petta_answer(Space, RowW)) :-
    petta_py_answer_form(RowW, _, _, _, _), !.
petta_py_decode_plan_row(_, RowW, Row) :- petta_py_decode_row(RowW, Row).

%One solution per row, the claimed patterns unified with it. Unifying rather
%than trusting is what keeps a decoding mistake from becoming a wrong answer:
%a row of the wrong shape fails here instead of binding something odd.
%A plain row unifies with the claimed patterns, which is what forces the
%re-unification a theta row deletes: bindings for the patterns' own
%variables apply directly, one row per answer, residue closing as
%everywhere else.
petta_py_plan_rows(Claimed, Rows) :-
    member(Row, Rows),
    (   Row = petta_answer(Space, Wire)
    ->  petta_py_answer_match(Wire, Claimed, Space)
    ;   Claimed = Row
    ).

%The batch seam. A provider without a BulkAdder declares no add-many capability,
%so this fails and the engine falls back to one metta_foreign_add/2 per atom.
metta_foreign_add_many(Space, Terms) :-
    petta_py_foreign(Space),
    petta_py_capability(Space, 'add-many'),
    maplist(petta_py_encode, Terms, Ws),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_add_many(SpaceStr, Ws), _).

metta_foreign_remove(Space, Term, Removed) :-
    petta_py_foreign(Space),
    petta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:foreign_remove(SpaceStr, W), R0),
    petta_py_bool(R0, Removed).

petta_py_register_foreign(Space0, Capabilities) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    ( petta_py_foreign(Space) -> true ; assertz(petta_py_foreign(Space)) ),
    %A newly registered provider is a new source: the linear-consumption
    %mark belongs to the drained OBJECT, and this is the door a fresh one
    %arrives through.
    petta_source_reset(Space),
    retractall(petta_py_capability(Space, _)),
    forall(member(Capability0, Capabilities),
           ( ( atom(Capability0) -> Capability = Capability0
             ; atom_string(Capability, Capability0) ),
             assertz(petta_py_capability(Space, Capability)) )).

petta_py_unregister_foreign(Space0) :-
    ( atom(Space0) -> Space = Space0 ; atom_string(Space, Space0) ),
    retractall(petta_py_capability(Space, _)),
    retractall(petta_py_foreign(Space)).

%%%%%%%%%% Subscriptions %%%%%%%%%%
%
% Standing queries: when Python has subscribers, every space write crosses
% to petta_ops for pattern matching and callbacks, synchronously, inside
% the write. The hook clauses exist only while at least one space is watched.
% Their guard is one dynamic fact per subscribed space, first-arg indexed, so
% an unwatched space never crosses to Python while another space is watched.

:- multifile metta_on_atom_added/2.
:- multifile metta_on_atom_removed/2.
:- dynamic petta_py_subscribed_space/1.
:- dynamic petta_py_subscription_hook_ref/2.

petta_py_notify_atom_added(Space, Term) :-
    atom(Space),
    petta_py_subscribed_space(Space),
    petta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:atom_added(SpaceStr, W), _).

petta_py_notify_atom_removed(Space, Term) :-
    atom(Space),
    petta_py_subscribed_space(Space),
    petta_py_encode(Term, W),
    atom_string(Space, SpaceStr),
    py_call(petta_ops:atom_removed(SpaceStr, W), _).

petta_py_install_subscription_hook(Kind) :-
    petta_py_subscription_hook_ref(Kind, Ref),
    \+ clause_property(Ref, erased), !.
petta_py_install_subscription_hook(added) :-
    retractall(petta_py_subscription_hook_ref(added, _)),
    assertz((metta_on_atom_added(Space, Term) :-
                petta_py_notify_atom_added(Space, Term)), Ref),
    assertz(petta_py_subscription_hook_ref(added, Ref)).
petta_py_install_subscription_hook(removed) :-
    retractall(petta_py_subscription_hook_ref(removed, _)),
    assertz((metta_on_atom_removed(Space, Term) :-
                petta_py_notify_atom_removed(Space, Term)), Ref),
    assertz(petta_py_subscription_hook_ref(removed, Ref)).

petta_py_remove_subscription_hooks :-
    forall(retract(petta_py_subscription_hook_ref(_, Ref)),
           ( clause_property(Ref, erased) -> true ; erase(Ref) )).


petta_py_subscriptions(Spaces) :-
    maplist(atom_string, SpaceAtoms, Spaces),
    with_mutex('$petta_py_subscriptions',
               petta_py_subscriptions_locked(SpaceAtoms)).

petta_py_subscriptions_locked(SpaceAtoms) :-
    retractall(petta_py_subscribed_space(_)),
    forall(member(Space, SpaceAtoms),
           assertz(petta_py_subscribed_space(Space))),
    ( SpaceAtoms == []
      -> petta_py_remove_subscription_hooks
    ; petta_py_install_subscription_hook(added),
      petta_py_install_subscription_hook(removed) ).

%%%%%%%%%% Protocol types for host objects %%%%%%%%%%
%
% The engine asks metta_grounded_extra_type/2 for names beyond an object's own
% classes; the answer comes from the Python-side protocol registry, so a
% library teaches typing without touching Prolog.

:- multifile metta_grounded_type_names/2.

%Values cross the boundary boxed so janus cannot rewrite them; the names
%are computed on the held value, in Python, and cross as plain text: the
%classes off the method resolution order, then every satisfied protocol.
metta_grounded_type_names(X, Names) :-
    py_is_object(X),
    py_call(petta_ops:type_names(X), Names).

%(context-space) lives in the engine now (engine/metta.pl); the shim keeps
%nothing to add for it.

%%%%%%%%%% Retranslation on late definitions %%%%%%%%%%
%
% The engine decides call-against-data per equation at compile time, so a
% body mentioning a name that only becomes a function later stays data: the
% classic case is (= (f) (g)) in one run and (= (g) 5) in the next, and the
% Python case is an operation registered after equations that call it.
% The dependent-recompile that used to ride here as clauses of the
% metta_on_function_changed/1 and metta_on_function_removed/1 EVENTS is the
% engine's own now (function_changed/2 and function_removed/1 in
% engine/spaces.pl): an event observer must be optional, and an engine without
% this host in the process has to repair its own compiled code. The
% invalidation was already the engine's, threaded with the module each write
% goes to, which is the only place that knows it
%[tested: specializer_invalidation:writing_in_one_space_leaves_another_alone,
%test_adding_in_one_space_never_removes_atoms_from_another].

%%%%%%%%%% Silence %%%%%%%%%%
%
% filereader.pl decides silent/1 from the CLI argv at load time; a library run
% has no argv, so the bridge sets it explicitly. Retract first, because two
% contradictory silent/1 clauses would leave the engine on whichever is first.
petta_py_set_silent(Silent) :-
    retractall(silent(_)),
    assertz(silent(Silent)).

%%%%%%%%%% Trusted fast cache I/O %%%%%%%%%%
%
%One fast_write carries the whole atom list. The text header pins both this
%container contract and the SWI release whose private term encoding produced
%the payload. Python validates it before calling the reader, and this section
%checks it again on the same stream before fast_read can see any payload byte.

%The fast cache and the digest are engine machinery now, the host run and
%load surface in engine/filereader.pl: this side maps the term outcomes to
%the wire and answers the ONE host question the engine asks through the
%metta_host_object/1 seam, whether a term is a live Python object (the
%bridge contributes that clause). Results: object(Atom) and symbol(Atom)
%name a refusing offender, saved(Count) and digest(Hash) land.

%The first atom in a space with no round-trip text spelling, so a host
%validating a save asks the grammar instead of keeping a second copy of its
%rules, which is how the host's copy came to miss three classes.
%
%This asked about the atoms' NAMES until 2026-08-19 and so missed a fourth
%class, which is not a name at all: a number whose printed form is not read
%back as that number. A space holding `(py-atom "float('inf')")`'s answer saved
%to a .metta file and loaded back came back holding the SYMBOL of that
%spelling, silently [measured 2026-08-19]. metta_unwritable_symbol/2 is the
%grammar's own answer about a whole atom, one of the four text services in
%engine/ext_points.pl, and it is the same question petta_py_fast_save/3 and
%petta_py_digest/2 below already ask.
petta_py_unwritable_atom(Space, Bad) :-
    'get-atoms'(Space, Atom),
    metta_unwritable_symbol(Atom, Unwritable), !,
    petta_py_encode(Unwritable, Bad).

%One boolean crossing for consumers that must validate a name before they
%mutate host state. The parser remains the authority, including reader token
%classes registered after startup.
petta_py_symbol_writable(Name, '@'(true)) :- metta_symbol_writable(Name), !.
petta_py_symbol_writable(_, '@'(false)).

%A refusal witness for a host error. Testing each one-character spelling
%against the grammar finds a delimiter or reserved literal opener without a
%second delimiter table; when only the whole token is reserved (True or a
%registered token class), its first character locates the competing token.
petta_py_symbol_refusal(Name0, Refusal) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    \+ metta_symbol_writable(Name),
    petta_py_symbol_refusal_detail(Name, Refusal).

petta_py_symbol_refusal_detail('', [empty]) :- !.
petta_py_symbol_refusal_detail(Name, [character, Character]) :-
    atom_codes(Name, Codes),
    member(Code, Codes),
    atom_codes(Character, [Code]),
    \+ metta_symbol_writable(Character),
    !.
petta_py_symbol_refusal_detail(Name, [token, Character]) :-
    atom_codes(Name, [First|_]),
    atom_codes(Character, [First]).

petta_py_fast_save(File, Space, Result) :-
    metta_host_save_fast(File, Space, Outcome),
    petta_py_persist_result(Outcome, Result).

petta_py_fast_load(File, Space) :-
    metta_host_load_fast(File, Space).

petta_py_persist_result(object(Atom), ["object", Encoded]) :- !,
    petta_py_encode(Atom, Encoded).
petta_py_persist_result(symbol(Atom), ["symbol", Encoded]) :- !,
    petta_py_encode(Atom, Encoded).
petta_py_persist_result(saved(Count), ["saved", Count]) :- !.
petta_py_persist_result(digest(Hash), ["digest", Hash]).

%%%%%%%%%% Content digest %%%%%%%%%%
%
%A space's content as one sha256: each atom canonicalized (fresh copy,
%numbered variables, quoted write) so alpha-equivalent equations print
%identically in every process, the lines multiset-sorted so insertion
%order cannot matter, then hashed as one utf8 document. Live objects
%print by address and are refused, the save contract.

petta_py_digest(Space, Result) :-
    metta_host_digest(Space, Outcome),
    petta_py_persist_result(Outcome, Result).
