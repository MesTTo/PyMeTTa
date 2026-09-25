% Purpose: reflect library declarations and compiled definitions.
% Assumes: loaded through _binding/shim.pl in its host module.
% Guarantees: reflection reads a native space identity without converting its
% expression to text or mistaking it for source paths [tested:
% test_a_parametric_namespace_lists_resolves_and_inherits_native_functions; commit=349d40951e1412b91cb3b60aa476826cf4654e63].
% Guarantees: metta_py_function_inherited/2 holds exactly when fun_home_in/3
% gives the name an equation home outside the space's own module, so a builtin
% is never something to override and a restricted space inherits nothing
% [tested 2026-09-25T16:27:30+10:00: test_override_declares_a_shadow_of_an_inherited_definition,
% test_an_engine_builtin_is_not_something_to_override,
% test_a_restricted_space_inherits_nothing_to_override].
% Guarantees: every door that reads a space's compiled definitions forces the
% view it reads, what a call from that space reaches, and nothing beside it
% [tested 2026-09-25T16:27:30+10:00: test_copying_a_space_leaves_the_space_it_copies_alone].
% Guarantees: metta_py_disassemble/3 lists each arity where its clauses are
% defined, so an engine builtin, which a space's module only imports, answers
% as a head the space defines does [tested 2026-09-25T23:30:47+10:00:
% test_compiled_lists_a_builtin_where_its_clauses_are_defined].

% metta_py_disassemble/3 prints a compiled definition with listing/1; declared
% here rather than left to the library index, which the no-autoload
% configuration (run.sh NO_AUTOLOAD=1) does not consult.
:- autoload(library(listing), [listing/1]).

%%%%%%%%%% What a library says about itself %%%%%%%%%%
%
%Everything one Prolog source declares, as [kind, value] pairs rather than the
%coarse verdict metta_register_prolog/3 reads before it loads anything: the
%caller here is building a description of a library, and "exports" does not
%say WHICH names, which capability the file needs, or what version it states.
%One scan either way, and the source is read and never consulted
%[source: engine/metta/interop.pl, metta_source_declarations/2].
metta_py_source_declarations(Source0, Rows) :-
    ( atom(Source0) -> Source = Source0 ; atom_string(Source, Source0) ),
    metta_source_declarations(Source, Declarations),
    findall([KindS, ValueS],
            ( member(Declaration, Declarations),
              Declaration =.. [Kind, Value],
              atom_string(Kind, KindS),
              metta_py_origin_part(Value, ValueS) ),
            Rows).

%Every head name one MeTTa source registers, with the index of the form that
%registers it, so the caller pairs each with the line its own position walk
%already knows. The engine owns which of its forms register a head; this
%crosses that answer once per source instead of per form
%[source: engine/metta/interop.pl, metta_string_registrations/2].
metta_py_registrations(Source0, Rows) :-
    ( string(Source0) -> Source = Source0 ; atom_string(Source0, Source) ),
    metta_string_registrations(Source, Rows0),
    findall([NameS, Index],
            ( member([Name, Index], Rows0), atom_string(Name, NameS) ),
            Rows).

%The engine's own digest of a file on disk, which is the identity a reload
%compares and therefore the identity a lockfile has to pin. Reading it here
%rather than hashing in the host is what keeps the two answers the same for a
%.gz source and for a fast image, whose digest is declared in its header
%rather than computed over its bytes
%[source: engine/filereader/source_lifecycle.pl, metta_source_digest/2].
metta_py_source_digest(Path0, Digest) :-
    ( atom(Path0) -> Path = Path0 ; atom_string(Path, Path0) ),
    filereader:metta_source_digest(Path, Digest0),
    atom_string(Digest0, Digest).

%Every source this process has loaded, with the space it loaded into and the
%digest it was loaded FROM, read inside one transaction so the table cannot
%change under the walk.
%
%A load in flight answers `loading` and no rows. The table is written at
%publish and a load that is still reading has no row yet, so a lock taken
%during one would record a program that is half loaded and read back as
%complete; refusing is the only honest answer, and the caller retries when the
%load it is racing has finished
%[source: engine/filereader/source_lifecycle.pl, with_source_load/3 asserts
%active_source_load/1 for the duration and publish_source_load/3 writes the
%row].
metta_py_source_loads(Status, Rows) :-
    transaction(
        (   filereader:active_source_load(_)
        ->  Status = "loading", Rows = []
        ;   Status = "settled",
            findall([PathS, SpaceS, DigestS],
                    ( filereader:metta_source_load(Path, Space, _, Digest),
                      atom_string(Path, PathS),
                      metta_py_origin_part(Space, SpaceS),
                      atom_string(Digest, DigestS) ),
                    Rows)
        )).

%Every repository revision this process pinned, by either git route. The
%predicate lives in lib/lib_gitimport/lib_gitimport.pl, which a build without
%library(process) still loads, so the guard is about the predicate EXISTING
%rather than about the platform.
metta_py_git_pins(Rows) :-
    (   current_predicate(git_pinned_dependency/2)
    ->  findall([UrlS, RevS],
                ( git_pinned_dependency(Url, Rev),
                  atom_string(Url, UrlS),
                  atom_string(Rev, RevS) ),
                Rows)
    ;   Rows = []
    ).

%The names one extension installed, asked before releasing them so the caller
%can be told what went. The membership is the engine's answer; this side puts
%each name on the wire as a string, so a member such as `none` is not read
%back as Python's own constant [source: engine/metta/interop.pl,
%metta_extension_members/2].
metta_py_extension_members(Name0, Names) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    metta_extension_members(Name, Members),
    maplist(atom_string, Members, Names).

%Registering Prolog as MeTTa functions, in one crossing. The sequence is the
%engine's, the one every binding runs [source: engine/metta/interop.pl,
%metta_register_prolog/3]; this side reads the wire: the origin as its kind
%beside its text, a name as a string, a rename as a [From, To] pair of
%strings, and the names registered back as strings.
metta_py_register_prolog(Kind0, Source, Names0, Registered) :-
    atom_string(Kind, Kind0),
    metta_py_prolog_origin(Kind, Source, Origin),
    maplist(metta_py_prolog_name, Names0, Names),
    metta_register_prolog(Origin, Names, Registered0),
    maplist(atom_string, Registered0, Registered).

metta_py_prolog_origin(file, Path, file(Path)).
metta_py_prolog_origin(text, Text, text(Text)).

metta_py_prolog_name([From0, To0], [From, To]) :-
    !,
    atom_string(From, From0),
    atom_string(To, To0).
metta_py_prolog_name(Name0, Name) :-
    atom_string(Name, Name0).

%Everything one extension installed, released together.
metta_py_unregister_extension(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    unregister_metta_extension(Name).

%Every function or translator special-form name the language knows, for
%completion and docs. The special forms come from the translator's published
%service rather than from its clause table: this used to read
%clause(Engine:translate_special_dl(...), _) directly, and the moment the
%compiler's clauses moved into a module of their own the read matched nothing
%and m.builtins() quietly answered 31 names short, with no error anywhere
%[measured 2026-08-22: 268 names before the translator became a module, 237
%after, 268 again through the service].
metta_py_builtins(Names) :-
    findall(N, fun(N), Functions),
    metta_py_special_form_names(SpecialForms),
    append(Functions, SpecialForms, Language0),
    sort(Language0, Language),
    maplist(atom_string, Language, Names).

%The same union narrowed to what ONE space can call. fun/1 is process-wide by
%design (the translator reads it to decide call against data wherever a term
%compiles), so the union above lists a head every space has registered,
%including one whose equations live in a module this space never sees. A
%namespace built on it advertised those heads, resolved them, and produced
%calls that answered themselves unreduced; and once the process had registered
%more than 750 names CPython stopped offering a suggestion for a typo at all,
%because its traceback machinery declines a candidate pool that large
%[measured 2026-09-07: 800 equations in one space made another space's
%namespace list 1,107 names and lose "Did you mean: 'dbl'?"; the same space
%alone lists 306]. The rule is the engine's own fun_here/1 with the module
%made explicit, metta_host_function_callable_from/2: an unscoped name (a
%builtin, a Python operation registered into &self, a prelude rule) answers
%everywhere, a scoped one answers where its clauses are visible from, which is
%its own module, a parent it inherits from, or &self.
metta_py_builtins(Space0, Names) :-
    metta_py_space_atom(Space0, Space),
    metta_py_module(Space, Module),
    findall(N, metta_host_function_callable_from(Module, N), Functions),
    metta_py_special_form_names(SpecialForms),
    append(Functions, SpecialForms, Language0),
    sort(Language0, Language),
    maplist(atom_string, Language, Names).

binding_forward(metta_py_function_generation/1).
%Whether ANY deprecation declaration exists, as 1/0 through the apply seam.
%The catalog is almost always empty, and the callable doors' first-call
%deprecation read through a fresh once/1 goal string measured 1,311
%inferences where this apply-seam probe is double digits, the same
%once-versus-apply gap metta_py_catalogue_member/1 documents below
%[tested: test_an_empty_deprecation_catalog_costs_one_cheap_probe].
metta_py_deprecation_declared(Flag) :-
    ( metta_deprecation(_, _, _) -> Flag = 1 ; Flag = 0 ).

metta_py_special_form_names(Names) :-
    findall(Name, metta_special_form_head(Name), Names0),
    sort(Names0, Names).

metta_py_is_function(Name0) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name).

%Point membership in the catalogue metta_py_builtins/2 lists for one space:
%one indexed fun/1 probe and the callable-from-here walk, then the
%special-form heads, instead of materializing and string-converting the
%whole catalogue. The bound namespace asks this on every attribute
%resolution, and the full read it replaces measured 1,347 inferences on the
%first access after any definition where this probe is double digits
%[measured 2026-08-24; consumer _FunctionNamespace._known].
metta_py_catalogue_member(Space0, Name0) :-
    metta_py_space_atom(Space0, Space),
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    (   fun(Name)
    ->  metta_py_module(Space, Module),
        metta_host_function_callable_from(Module, Name)
    ;   once(metta_special_form_head(Name))
    ).

%Whether a function ANSWERS from this space: it has clauses its module can
%see, its own or inherited from user. Another space's equations live in that
%space's module and are invisible here, so they do not count.
metta_py_function_visible(Space0, Name0) :-
    metta_py_space_atom(Space0, Space),
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name),
    %The question is about clauses, and a deferred function has none until
    %its equations translate; the clause probe below is a read the
    %undefined-predicate net never fires for.
    metta_py_module(Space, Module),
    spaces:metta_ensure_compiled_from(Module, Name),
    catch_recover(( spaces:metta_arity_ascending(Module, Name, Arity),
                    functor(Head, Name, Arity),
                    clause(Module:Head, _, _) ),
                  fail), !.

%Whether a head this space does NOT define answers here through the space
%chain: a space it inherits from defines it, or &self does and this is some
%other space, the walk fun_home_in/3 takes for every call. This is the
%question `@typing.override` asks, so a definition that shadows nothing is
%refused where it is written instead of answering beside the one it meant to
%replace.
%
%A BUILTIN is deliberately not an answer, which is why only an EQUATION home
%counts: shadowing a builtin is the same-space collision
%metta_py_function_visible/2 already refuses with its own message, and a
%restricted space, which reaches builtins alone, inherits nothing.
%
%fun_in/2 is a REGISTRATION fact rather than a clause fact -- register_fun_in/2
%asserts it when the equation lands -- so unlike the clause probe above this
%needs no metta_ensure_compiled/1 to be right on a definition nothing has
%evaluated yet [measured 2026-09-07: fun_in holds immediately after
%space.run("(= (area $r) ...)") with no evaluation in between].
metta_py_function_inherited(Space0, Name0) :-
    metta_py_space_atom(Space0, Space),
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    fun(Name),
    metta_py_module(Space, Module),
    \+ spaces:fun_in(Module, Name),
    spaces:fun_home_in(Module, Name, equations(_)), !.

metta_py_arities(Name0, As) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %Compiled arities are registered at translation, so the read forces.
    spaces:metta_ensure_compiled(Name),
    findall(A, arity(Name, A), As).

%Every stored equation for a name, live from the space. Pattern-directed:
%a native space answers by first-argument index on '=', a foreign space
%enumerates and unifies, and the open tail in the head pattern is Prolog
%unification against stored lists, not the MeTTa matcher.
metta_py_equations(Space, Name0, Encoded) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    Pattern = [=, [Name|_], _],
    findall(E, ( metta_host_stored(Space, Pattern),
                 metta_py_encode(Pattern, E) ), Encoded).

%The (cost ...) row a head declares about itself, as the pair the engine
%RESOLVED: the declared class, and the measure the row named or the head's
%arrow decided. `none` when the head declares no row. The derivation stays in
%the engine so the docstring here, (explain ...) and the cost-rows benchmark
%lane all read one answer instead of three implementations of one rule.
metta_py_cost_declaration(Name0, Claim) :-
    current_metta_space(Space), metta_py_cost_declaration(Space, Name0, Claim).
metta_py_cost_declaration(Space, Name0, Claim) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    (   metta_head_property(Space, Name, [cost, Class, Measure])
    ->  Claim = [Class, Measure]
    ;   Claim = none
    ).

% One property bag per head, encoded by the existing atom wire. Context is a
% tagged space name or source-path list; the engine resolves the home.
metta_py_head_claims(Names, Rows) :-
    metta_py_head_claims([space, '&self'], Names, Rows).
metta_py_head_claims(Context, Names0, Rows) :-
    maplist(metta_py_claim_name, Names0, Names),
    metta_py_claim_scope(Context, Scope),
    metta_head_claims(Scope, Names, Claims),
    findall([NameS, Encoded],
            ( member([Name, Properties], Claims), atom_string(Name, NameS),
              maplist(metta_py_encode, Properties, Encoded) ), Rows).

metta_py_claim_scope([space, Space0], space(Space)) :-
    metta_py_space_atom(Space0, Space).
metta_py_claim_scope([sources, Paths0], sources(Paths)) :-
    maplist(metta_py_claim_name, Paths0, Paths).

metta_py_claim_name(Value, Name) :-
    ( atom(Value) -> Name = Value ; atom_string(Name, Value) ).

%The Prolog clauses a name compiled to, dis for the translator: one
%listing per registered arity, of the predicate a call from this space's
%module reaches, so a named space shows the clauses it would run. They are
%listed where they are DEFINED, which metta_py_clause_owner/3 reads from
%implementation_module: a head this space defines lives in its own module,
%while an engine builtin is only imported there, and listing/1 resolves
%Module:Name/Arity through '$find_predicate'/2, whose current_predicate/2
%never matches an imported predicate, so every builtin raised
%existence_error [source 2026-09-25T23:36:58+10:00: SWI-Prolog 10.1.14
%boot/dwim.pl find_predicate_/4 and library/listing.pl listing_/2]. Fails on a
%name the engine never compiled, and the Python side turns that into its own
%refusal.
metta_py_disassemble(Space, Name0, Text) :-
    ( atom(Name0) -> Name = Name0 ; atom_string(Name, Name0) ),
    %The listing below is a read, so a deferred function would show nothing
    %and register no arity; the disassembly IS the demand, made from the
    %space whose clauses it lists.
    space_module(Space, Module),
    spaces:metta_ensure_compiled_from(Module, Name),
    findall(A, arity(Name, A), As0),
    As0 \== [],
    sort(As0, As),
    with_output_to(string(Text),
                   forall(( member(A, As), current_predicate(Module:Name/A) ),
                          ( functor(Head, Name, A),
                            metta_py_clause_owner(Module, Head, Owner),
                            listing(Owner:Name/A) ))).
