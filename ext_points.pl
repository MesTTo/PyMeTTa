%%%% What kind of seam each extension point is %%%%
%
%Every seam below is declared multifile and then given a KIND on the line
%after it. The kind is the load-bearing fact about a seam, because a cut means
%opposite things in the three of them, and it lived in this comment until a
%checker had to restate it by hand. A restated list drifts, and this one had:
%the prose named five event hooks, omitting metta_backend_selftest/0 and
%wrongly including metta_dispatch_call/4, and both were contradicted by their
%own call sites. So it is data now, and the prose derives from it.
%
%EVENT: run for an effect and the answer discarded, forall(Hook, true). Every
%handler runs.
%
%OWNERSHIP: consulted for an answer, and the first handler that succeeds
%CLAIMS the request; the caller takes it with ->/2 or once/1, and a provider
%declines by failing.
%
%DECLARATION: a fact table the engine reads as data rather than calls for an
%effect. Every clause has to stay readable for the same reason an event
%handler has to stay reachable.
%
%SERVICE: the other direction. The three kinds above are all HANDLER seams,
%where an extension writes the clauses and the engine calls them; a service is
%a predicate the ENGINE defines and an extension is allowed to CALL. A foreign
%space backend needs one: it speaks text over a wire, so it has to turn a term
%into text and back, and before this kind existed it reached into
%src/parser.pl to do it. SQLite publishes the same half of its own contract
%and for the same reason, handing an extension an sqlite3_api_routines table
%of the host functions it may call so that an extension never links against
%internals [source: https://www.sqlite.org/vtab.html and loadext.html]. Naming
%the surface is what makes "reaches past the seam" a question a checker can
%answer, and two extensions had already answered it wrongly: morkspaces.pl and
%python/petta/shim.pl each wrapped metta_unwritable_symbol/2 under a private
%name of its own, which is what an undeclared dependency looks like from the
%outside [measured 2026-08-17].
%
%The cut rule follows from the kind rather than being a second list to keep.
%In an OWNERSHIP seam a clause guarded by a test that establishes "this
%request is mine" may cut freely, and lib/lib_redis.pl does:
%redis_space_conn(Space, _) fails for a space redis does not own, so a later
%provider's clauses are untouched, and the cut is a real optimisation there.
%In an EVENT or DECLARATION seam every clause must stay reachable, so a cut
%prunes that predicate's remaining clauses and silently disables every handler
%loaded after it. lib/lib_tabling.pl cut after metta_tabling_declared, a
%GLOBAL CONDITION rather than an ownership test: nothing about it says this
%handler is the one that should answer. With tabling declared, duals.pl's
%invalidation handler (asserted last, so ordered last) never ran and
%(not-provable (pq 2)) answered True and False at once.
%
%Write ( Condition -> Action ; true ) in an event handler, which keeps the
%guard's cost and prunes nothing. A cut is transparent through ,/2, ;/2 and
%the THEN branch of ->/2 and *->/2, and opaque everywhere else, including the
%CONDITION of ->/2, where the manual's own worked example is
%`t3 :- (a, !, b -> c ; d)` pruning a/0 and not t3/0
%[source: SWI-Prolog manual, !/0, scope-of-the-cut table]. So a checker that
%flags a cut in a condition is flagging correct code.
%
%Two checks enforce it and neither subsumes the other. A source scan reads
%every clause in the tree, including one a directive asserts, and a runtime
%scan reads clause/3 after the libraries have loaded, which is the only way to
%see a handler that Python installs or one whose body is built at run time
%[tested: tests/prolog/static_checks.pl, no_cut_in_an_event_hook and
%no_cut_in_a_live_hook_clause].
%
%ext_point_kind/2 is itself multifile, so a library that introduces a seam of
%its own declares its kind beside it and gets the same gate. Every seam has
%exactly one kind and that is checked rather than trusted
%[tested: every_seam_declares_one_kind], so a seam added without one fails the
%gate instead of going quietly unchecked.
:- multifile ext_point_kind/2.
%It is a seam itself, so it carries its own kind, and being a declaration it
%is covered by the cut check like any other.
ext_point_kind(ext_point_kind/2, declaration).

%Who writes a seam's clauses. This is the primitive the cut rule derives from,
%rather than the cut rule naming kinds directly: that rule is about a handler
%an extension contributed staying reachable, so it can only bite where an
%extension contributes the clauses. A service's clauses are the engine's own
%and cut freely, as swrite/2 does; reading the rule off the kind list alone
%would have called every one of them an offender.
ext_point_clauses_from(event,       extension).
ext_point_clauses_from(ownership,   extension).
ext_point_clauses_from(declaration, extension).
ext_point_clauses_from(service,     engine).
ext_point_clauses_from(host_service, engine).

%A seam whose clauses must all stay reachable: contributed by an extension,
%and not an ownership seam where the first success is meant to claim the
%request. Derived, so adding a kind does not mean editing a second list.
ext_point_every_clause_runs(Seam) :-
    ext_point_kind(Seam, Kind),
    ext_point_clauses_from(Kind, extension),
    Kind \== ownership.

%A handler seam is multifile because an extension adds clauses to it. A
%service is not, because an extension calling it must not be able to redefine
%it, and multifile is exactly the permission to try. The two directions are
%checked apart for that reason [tested: every_seam_kind_matches_its_direction].

%CALL DISPATCH: a handler is offered every compiled call site and either
%CLAIMS it, by binding Goal to something the engine runs instead, or fails and
%the ordinary call proceeds. Failing is the shipped default and the whole of
%what a handler must do to opt out.
%
%It was named metta_memoized_dispatch_call/4, for the first library that used
%it, and the name was the problem: nothing suggested it was the general
%dispatch seam, so nothing reached for it to do anything else. lib_memo binds
%Goal to a cache lookup, and it is still the only handler in the tree. This is
%Trino's applyX / Optional.empty() shape, and it was here before that reading.
%
%A function name alone does not identify a function, because a named space
%compiles its equations into a module of its own, so a handler that keeps
%state per function reads current_metta_module/1 to learn which module the
%call site is in. It reads it rather than being passed it because this hook is
%consulted on every compiled call site.
:- multifile metta_dispatch_call/4.
ext_point_kind(metta_dispatch_call/4, ownership).
%Function-change hooks, run once per compiled equation. Dynamic for the same
%reason the atom hooks below are: a handler needed only once a feature is used
%should cost nothing until then, so it is installed when that feature first
%runs rather than when its file loads. A resident handler clause costs four
%inferences on EVERY compiled equation [measured 2026-08-15: src/duals.pl's
%invalidation handler, 4001 on source-load's thousand equations].
:- multifile metta_on_function_changed/1.
ext_point_kind(metta_on_function_changed/1, event).
:- multifile metta_on_function_removed/1.
ext_point_kind(metta_on_function_removed/1, event).
:- dynamic metta_on_function_changed/1.
:- dynamic metta_on_function_removed/1.

%Space writes: every 'add-atom'/3 and 'remove-atom'/3 runs these hooks with
%the space and the term, after the write. A standing query, a subscription,
%an index or a mirror hangs off them; with no handlers nothing changes.
%A removal hook fires only when something was actually removed, and it carries
%the term the caller ASKED to remove rather than the occurrence that left. The
%two coincide for a ground request and diverge for a pattern: removal is
%multiset subtraction, so (remove-atom &s (p $x)) takes one of the atoms
%matching (p $x) and the hook cannot say which. A handler that needs the
%occurrence re-reads the space; python/petta/structures.py's LiveView is the
%worked instance [tested: test_liveview_mirrors_the_space].
:- multifile metta_on_atom_added/2.
ext_point_kind(metta_on_atom_added/2, event).
:- multifile metta_on_atom_removed/2.
ext_point_kind(metta_on_atom_removed/2, event).
:- dynamic metta_on_atom_added/2.
:- dynamic metta_on_atom_removed/2.

%Foreign spaces: a host runtime may declare a space whose atoms live outside
%the Prolog database, in a database, a dataframe, a service. match/4,
%'add-atom'/3, 'remove-atom'/3 and 'get-atoms'/2 consult these hooks first
%for a declared name; with no declarations nothing changes.
:- multifile metta_foreign_space/1.
ext_point_kind(metta_foreign_space/1, ownership).
:- multifile metta_foreign_match/3.
%A declared error mode's stream: like metta_foreign_match/3, with the
%mode enforced on the provider's own host, where its exceptions are
%native. Item is `answer` (the pattern is bound), kept(ErrorAtom), or
%`end` from an adapter that must mark exhaustion. Only adapters whose
%host exceptions cannot cross as Prolog exceptions implement this; a
%Prolog-hosted provider needs none, the engine's catch handles it.
:- multifile metta_foreign_erring/5.
%Transactional participation, driven by (writes Ctx transactional): one
%begin at the provider's first write inside the outermost transaction,
%then exactly one commit or rollback when it finishes.
:- multifile metta_foreign_begin/1.
:- multifile metta_foreign_commit/1.
:- multifile metta_foreign_rollback/1.
ext_point_kind(metta_foreign_match/3, ownership).
ext_point_kind(metta_foreign_erring/5, ownership).
ext_point_kind(metta_foreign_begin/1, ownership).
ext_point_kind(metta_foreign_commit/1, ownership).
ext_point_kind(metta_foreign_rollback/1, ownership).
%Custom matching for grounded values, Hyperon's CustomMatch: a host value
%may carry its own matching logic, consulted by petta_match_atoms/2 when
%that value meets a non-variable operand inside `unify`. The hook
%enumerates one solution per binding set, binding the other operand's
%variables; failure means no match. Variables always bind the value
%whole without consulting it, and values with no owner fall through to
%ground equality, so with no declarations nothing changes.
:- multifile metta_matchable_value/1.
:- multifile metta_custom_match/2.
ext_point_kind(metta_matchable_value/1, ownership).
ext_point_kind(metta_custom_match/2, ownership).
:- multifile metta_foreign_add/2.
ext_point_kind(metta_foreign_add/2, ownership).
%A provider's own BATCH crossing, optional. The atoms arrive as a list and the
%provider stores them however it likes; one without this clause gets a
%metta_foreign_add/2 per atom, which is what every provider written before it
%gets. The hooks are the provider's, exactly as they are for its per-atom add.
%
%A batch is a TRANSPORT optimisation and never a semantic one, so the engine
%routes only atoms whose add is a store and nothing more through here. That is
%not advice to the provider, it is enforced upstream: an equation or a type
%declaration in the list drops the whole batch to 'add-atom'/3 per atom.
:- multifile metta_foreign_add_many/2.
ext_point_kind(metta_foreign_add_many/2, ownership).
:- multifile metta_foreign_remove/3.
ext_point_kind(metta_foreign_remove/3, ownership).
:- multifile metta_foreign_atoms/2.
ext_point_kind(metta_foreign_atoms/2, ownership).
%Clear was the sixth of these all along and was declared nowhere: it lived in
%python/petta/shim.pl, so a Prolog provider that implemented clear, as
%lib/lib_redis.pl does, was reachable only when Python was in the process.
:- multifile metta_foreign_clear/1.
ext_point_kind(metta_foreign_clear/1, ownership).

%What the caller will do with a match. Options is a list; the only option
%today is limit(N), meaning the caller stops after N answers. It is `[]` when
%there is nothing to say, which is most calls.
%
%It is ADVISORY, and that is what makes it sound. A provider may
%over-approximate, so N candidates are not N answers, and a provider that
%truncated at N without knowing which of its candidates unify would
%under-answer, which is the one thing the contract forbids. So honour it only
%when you can tell an exact match from a candidate, and ignore it otherwise:
%the engine bounds the answers itself either way, and this changes only how
%much work the BACKEND does before the first one.
%
%Two levers a reader might expect here are already in place and need no
%option. The bound parts of a pattern reach a provider as ground atoms,
%including the bindings an enclosing join has made, so the second pattern of
%a join arrives as (other a0 $_) rather than (other $_ $_). And the engine
%stops pulling as soon as it has enough: a limit of 3 over a provider holding
%a thousand atoms pulls four [measured 2026-08-16].
%
%ONE hook, with the options always passed. There was a /2 beside this and the
%engine chose between them with `clause(metta_foreign_match(_,_,_), _)`, which
%asks whether ANY provider anywhere declared the bounded form. The Python shim
%declares it unconditionally, so with Python in the process that guard was true
%for every space, and a Prolog-only provider writing /2 had the /3 form called
%instead: the shim's clause failed on its own ownership check and the whole
%match answered nothing. Reproduced as `unbounded: 3, bounded: 0`
%[measured 2026-08-16]. A provider that has nothing to do with the options
%ignores the argument, which costs it one underscore and cannot go wrong.

%How much a provider's own filtering is worth, per PATTERN. Class is exact or
%inexact, and a space with no clause is inexact, which is the answer every
%provider written before this gets for free.
%
%  exact    every candidate you yield for this pattern unifies with it, so N
%           candidates are N answers and limit(N) is a requirement you may
%           truncate to
%  inexact  you reduce what you produce, and some of it may not match; the
%           engine re-unifies and limit(N) stays advice you must not truncate to
%
%This is Apache DataFusion's TableProviderFilterPushDown, whose Exact rung
%says it in the same words: "Your source guarantees that no output rows will
%have a false value for this predicate. Because the filter is fully evaluated
%at the source, DataFusion will not add a FilterExec for it", against Inexact,
%"Your source has the ability to reduce the data produced, but the output may
%still include rows that do not satisfy the predicate"
%[source: Apache DataFusion, Custom Table Providers].
%
%PER PATTERN, not per provider, which is the part worth copying. A backend is
%usually exact on equality against an indexed column and inexact on everything
%else, and one flag for the whole provider would force it to claim the weaker
%answer everywhere. The clause takes the pattern, so it can say which is which.
%
%DataFusion's third rung, Unsupported, is deliberately absent. It exists there
%because the planner decides whether to SEND a filter at all; here the pattern
%is the only thing a provider is given, so there is nothing to withhold, and a
%provider that ignores it is inexact in the only sense the engine acts on.
%
%What the engine does with exact: it stops pulling at N instead of at N+1,
%since it no longer needs the extra candidate to learn the bound is met. What
%it does NOT do is skip unification, which is not a filter here but the step
%that binds the pattern's variables, so an exact claim cannot make an answer
%wrong. It can only make a wrong claim cost answers, which is why
%check_space_provider tests it against the provider's own output
%[tested: a_bounded_match_carries_its_options,
%a_bound_is_withheld_from_an_unclaimed_pattern,
%test_a_false_exact_claim_is_caught].
:- multifile metta_foreign_pushdown/3.
ext_point_kind(metta_foreign_pushdown/3, ownership).

%A conjunction, offered WHOLE before the engine splits it. Succeed to claim
%some of it, binding Goal to a goal that enumerates bindings for Claimed; fail
%to decline, and the engine plans it exactly as it does today.
%
%   metta_foreign_plan(Space, Patterns, Claimed, Rest, Goal)
%
%This is the seam that makes a backend's own join reachable. Without it every
%conjunction is split one pattern at a time and re-dispatched per outer row,
%which is a nested-loop plan, and a nested-loop plan cannot reach the AGM bound
%however fast the provider is: for the triangle R(x,y), S(y,z), T(z,x) with each
%relation of size N the bound is N^1.5 and "it is not possible to achieve a
%running time of O(N^3/2) using only join plans" [source: Ngo/Re/Rudra and the
%worst-case-optimal join literature]. So this is not a tuning knob; it is the
%difference between a provider being allowed to be asymptotically better and
%not being allowed to.
%
%Four properties, each with a precedent elsewhere in this file:
%
%  - DECLINING IS THE DEFAULT. A provider with no clause gets today's behaviour
%    exactly, the same safe default the capability vocabulary has.
%  - A PARTIAL CLAIM IS LEGAL. Claimed plus Rest lets a backend take the two
%    patterns it owns and leave the third, so the seam is not all-or-nothing.
%    They must PARTITION Patterns: dropping a conjunct answers more rows than
%    the query asks for and the engine refuses it, because nothing downstream
%    would catch it.
%  - THE STRATEGY IS INVISIBLE. Leapfrog, a hash join, a SQL SELECT, a vector
%    index: the engine sees a goal. It supports none of them and therefore all.
%  - THE CLAIM IS EXACT, and this one is the exception to the seam's usual rule.
%    Elsewhere a provider may over-approximate because the engine re-unifies
%    each candidate, which is cheap. There is no cheap re-check for a join: the
%    only way to verify a row is to run the join. So claiming means answering
%    exactly, a provider that cannot must decline, and check_space_provider
%    verifies the claim against the engine's own split rather than trusting it.
%
%The caller's options are not passed. The engine still bounds the answers, so
%this costs work in the backend and never an answer, and a limit could not be
%honoured usefully anyway while a provider answers a whole batch at a time.
:- multifile metta_foreign_plan/5.
ext_point_kind(metta_foreign_plan/5, ownership).

%What a provider answers. Failure alone cannot say: metta_foreign_match/3 is a
%legitimate enumerator, so "no clause" and "no atoms match" look identical
%from the engine, and clause/2 cannot stand in either, because every provider
%in this tree writes ONE clause with a variable space and an ownership guard
%in the body, which unifies with any space at all.
%
%So it is declared, the way python/petta/foreign.py derives it from the narrow
%protocols a provider implements. The capabilities are add, remove, match,
%enumerate, clear, PLAN and RULES.
%
%`rules` is the odd one and it is the one that matters most. It says the
%space's atoms include EQUATIONS, which in MeTTa is the difference between a
%data source and a place a program lives. The provider stores one the way it
%stores any atom and the ENGINE compiles it, so a foreign rule is the same
%compiled clause a native one is; nothing in the provider knows what an
%equation is. A space without the declaration is refused an equation at
%add-atom rather than storing one that can never fire. A space that declares
%NOTHING is taken to provide everything, which is what every provider written
%before this assumed.
%
%Two things follow from a declaration, and the first is the one that matters:
%a space that enumerates but does not match now has its enumeration FILTERED
%here for a bound pattern, instead of answering nothing. The Python half has
%always said enumeration is enough ("An Enumerable provider need not implement
%Matcher"), and the Prolog half quietly required both. The second is that an
%operation a space does not provide raises with the space and the operation
%named, rather than failing into "there is nothing there".
:- multifile metta_foreign_capability/2.
ext_point_kind(metta_foreign_capability/2, declaration).

%Why a space says no, in the provider's own words. The engine refuses a
%capability a space does not declare, and "does not implement add" reads
%differently from "declines this add request"; a provider with a reason raises
%it here and the engine's generic permission_error is what a provider without
%one gets. It is expected to THROW rather than answer
%[tested: test_a_provider_states_its_own_refusal].
:- multifile metta_foreign_refuse/2.
ext_point_kind(metta_foreign_refuse/2, ownership).

%An exception that must never be recovered from. A caught abort, limit, alarm
%or interrupt is a stopped program pretending it succeeded, and the engine's
%recovery catches all consult this: control_exception(Ball) true means the
%ball is rethrown rather than handled.
%
%A library that introduces its own cancellation or budget signal adds a
%clause and every recovery site in the engine respects it, which is the only
%way it could: a signal the engine has never heard of is swallowed by the
%first recovery catch it meets, and the failure is silent. This is
%KeyboardInterrupt living outside Exception, given a seam.
%
%library(exceptions) says the same thing more directly, and was measured
%rather than assumed. Written its way a recovery site is
%catch(Goal, \+ petta_control_signal, _, Recover), the negated type its
%is_exception/3 already supports, and it is behaviour-identical: ten balls,
%errors and non-errors, control and ordinary, recovered or escaped the same
%way both ways. It costs too much. catch/4 puts a freeze/2 on the ball at
%CALL time, so the price is paid whether or not anything throws: 20,000
%quiet calls went 140,002 to 240,002 inferences, 1.71x, and 20,000 throwing
%ones 240,003 to 1,340,002, 5.58x [measured 2026-08-16]. The recovery catch
%wraps every candidate the translator tries, so the quiet number is the one
%that decides it [source: ai-swi-library-review.md, entry 2].
:- multifile control_exception/1.
ext_point_kind(control_exception/1, declaration).

%An APPLICABLE GROUNDED ATOM. MeTTa's own definition of a Grounded atom is
%that it "may contain any binary object, for example operation (including deep
%neural networks), collection or value" [source: metta-lang.dev/docs/learn,
%Atom kinds and types], and an operation is a thing you call. The engine leaves
%a grounded head unevaluated unless a handler claims it, so `((py-atom
%numpy.absolute) -5)` answered itself and a callable held in a MeTTa variable
%was not a callable at all.
%
%   metta_grounded_apply(Value, Args, Out)
%
%Value is the grounded atom in head position and Args are the arguments as the
%engine has them. Succeed to claim it and bind Out; fail and the expression
%stays unreduced, which is what every value that is not an operation should do.
%
%Nothing in the engine knows what makes a value applicable, which is the point:
%a Python bridge claims Python callables, and a bridge for something else
%claims its own. It is consulted only for a head that is neither a function
%name nor a partial application, so an ordinary call never reaches it.
:- multifile metta_grounded_apply/3.
ext_point_kind(metta_grounded_apply/3, ownership).

%Whether a value is an operation at all, asked WITHOUT applying it. `bind!`
%needs to know before there are any arguments: a name bound to a callable is
%callable by that name, and a name bound to 5 is not.
:- multifile metta_grounded_applicable/1.
ext_point_kind(metta_grounded_applicable/1, ownership).

%An operation with NO effect a cache could hide.
%
%   metta_pure_operation(Name)
%
%Declared by whoever knows: the engine ships its own core list and a library
%adds its own. It is an ALLOW-list on purpose, and the asymmetry is the whole
%argument: a missing entry in a deny-list is a silent wrong answer, and a
%missing entry here is a loud refusal that someone fixes.
%
%What reads it is anything that may CACHE a result and hand the cached one back
%later: tabling and memoization both do. A goal that is not known pure is not
%known inert either, and treating unknown as inert cached a random draw, threw
%away a space write, and suppressed a println!.
:- multifile metta_pure_operation/1.
ext_point_kind(metta_pure_operation/1, declaration).

%The MeTTa name behind a bridge's dispatch goal.
%
%   metta_effect_operation_name(Goal, Name, Arity)
%
%A bridge compiles a MeTTa operation into a call on its OWN dispatcher, so a
%purity refusal that reads the goal's functor names the bridge rather than the
%program: `(tabled (uses-size $k))` refused `petta_py_dispatch_det/3` and
%advised declaring THAT pure, which is neither something an author wrote nor
%something that would help, since the refusal never reaches the operation's
%name. A bridge that can recover the name answers here, and the refusal then
%names what the program wrote and what metta_pure_operation/1 matches.
%
%It is the engine's only way to ask, and it has to be, because the engine
%knows no bridge by name: the Python one answers for its four dispatch kinds,
%and a bridge for something else answers for its own
%[tested: test_a_pure_python_operation_can_be_declared_and_cached].
:- multifile metta_effect_operation_name/3.
ext_point_kind(metta_effect_operation_name/3, ownership).

%The STRUCTURE a grounded value also has, when it has one.
%
%   metta_grounded_structure(Value, Expression)
%
%The language names three things a grounded value may define for itself:
%"Grounded value type creators can define custom type, execution and matching
%logic for the value" [source: the language's Main concepts]. The two above are
%type and execution. This is matching, and it is what lets one atom answer to
%two readings without being two answers: a Python tuple stays the tuple when it
%is passed back to Python or read with py-dot, and reads as `(1 2)` when a
%program takes it apart.
%
%The disambiguation is the language's own, taken from how a space atom nested
%in another space already behaves: a query "just a variable, e.g. $x" matches
%the atom ITSELF, and a structured query is delegated inward
%[source: the language's Working with spaces]. So the handle is what a variable
%binds and what a space stores, and the structure is what an expression pattern
%and the atom-taking-apart operations see.
%
%Nothing here is Python's. A foreign space handle, a MORK record or an array
%answers it the same way, and no caller learns who did.
:- multifile metta_grounded_structure/2.
ext_point_kind(metta_grounded_structure/2, ownership).

%How a grounded value RENDERS, for a writer that has no other way to know.
%
%   metta_grounded_text(Value, Text)
%
%Without a provider the writer falls back to the term's own text, so this is
%never required and never fails a print. A Python object answers with repr(),
%which is what the language's own tutorials show: `(np-array (py-atom "[1, 2,
%3]"))` displays `array([1, 2, 3])`
%[source: metta-lang-docs/learn__tutorials__python_use__py_atom.md].
:- multifile metta_grounded_text/2.
ext_point_kind(metta_grounded_text/2, ownership).

%%%% Native backends %%%%
%
%A backend is a space provider whose implementation is a shared library. It
%reaches the engine through the foreign-space seam above like any other
%provider; these two are the only things it needs that a Prolog provider does
%not, and both exist so the ENGINE never has to know a backend by name.
%
%The builtins a backend's bridge provides. Declared by the file that DEFINES
%them, so they exist exactly when the predicates behind them do: registering a
%name whose predicate is absent records no arity, and every call to it then
%compiles to a partial application. src/metta.pl registers whatever is declared
%here, and names nothing.
:- multifile metta_backend_builtin/1.
ext_point_kind(metta_backend_builtin/1, declaration).

%A backend's smoke test, run by src/main.pl's demo. Every handler runs, so a
%process with two backends tests both, and one with none tests nothing and says
%so by being silent.
:- multifile metta_backend_selftest/0.
ext_point_kind(metta_backend_selftest/0, event).

%%%% Services the engine publishes %%%%
%
%The seams above are all things the engine calls. These are the other
%direction: engine predicates an extension is allowed to call. An extension
%that reaches past them is depending on an internal that can be renamed under
%it, which for a backend is a gate failure rather than a style note
%[tested: a_backend_calls_only_published_surface].
%
%The MeTTa builtins are published too and are not repeated here: an extension
%calls 'add-atom'/3 or match/4 as the LANGUAGE, and builtin_fun/1 already says
%which names those are.
%
%TEXT. What being a shared library costs. A backend's atoms live on the far
%side of an FFI boundary that carries bytes, so every atom it stores is written
%and every atom it returns is read, and before these were declared MORK reached
%into src/parser.pl for all four, wrapping one under a private name.
%
%swrite/2 and sread/2 are one rule about spelling rather than two conveniences.
%swrite/2 will print a value that sread/2 does not read back as itself, and
%there are two ways for that to happen. MeTTa has no quoted-symbol syntax, so
%a name with whitespace, a parenthesis or a quote in it loses its identity on
%the round trip; and the writer prints numbers the reader's grammar cannot
%all read back, so a non-finite float goes out as inf, -inf or NaN (the
%arbiter's spellings) and a rational as 1r3, and each comes back a SYMBOL of
%that spelling. A backend cannot decide either for itself, the grammar owns them,
%and asking is what the other two are for: check before writing, and refuse
%rather than store an atom that will come back different.
%metta_symbol_writable/1 answers the first question about one name;
%metta_unwritable_symbol/2 answers both about a whole term, and its name is
%narrower than what it reports because names were the only class known to fail
%when this surface was declared.
%HOST SERVICE: a service again, engine-defined and engine-owned, but for
%the other caller: the HOST BINDING's transport (python/petta's shim today,
%any future binding's transport tomorrow). The backend direction has
%a_backend_calls_only_published_surface; this kind is what the host
%direction's twin reads, so the binding can no longer grow a dependency on
%an engine internal silently. The list is measured, not aspirational: it is
%exactly the engine predicates the shipped shim calls, and shrinking it is
%the shim-thinning work's scoreboard.
ext_point_kind(catch_recover/2, host_service).
ext_point_kind(claim_function_name/3, host_service).
ext_point_kind(clear_foreign_atoms/1, host_service).
ext_point_kind(clear_native_atoms/1, host_service).
ext_point_kind(foreign_provides/2, host_service).
ext_point_kind(fun_here/1, host_service).
ext_point_kind(load_imported_metta_file_impl/3, host_service).
ext_point_kind(parse_metta_source/2, host_service).
ext_point_kind(read_metta_source/2, host_service).
ext_point_kind(replacing_previous_load/4, host_service).
ext_point_kind(translate_expr/3, host_service).
ext_point_kind(foreign_pushdown_class/3, host_service).
ext_point_kind(function_changed/2, host_service).
ext_point_kind(get_native_atom/2, host_service).
ext_point_kind(import_when/4, host_service).
ext_point_kind(match_foreign/5, host_service).
ext_point_kind(metta_add_atom/3, host_service).
ext_point_kind(metta_add_atoms/2, host_service).
ext_point_kind(metta_atom_hook_clause/2, host_service).
ext_point_kind(metta_remove_atom/3, host_service).
ext_point_kind(metta_source_declarations/2, host_service).
ext_point_kind(metta_space_names/1, host_service).
ext_point_kind(metta_string_declarations/2, host_service).
ext_point_kind(metta_substitute_self/3, host_service).
ext_point_kind(metta_trace_source/4, host_service).
ext_point_kind(native_storage_module/2, host_service).
ext_point_kind(petta_annotations/2, host_service).
ext_point_kind(petta_contract_fact/1, host_service).
ext_point_kind(petta_error_answer/3, host_service).
ext_point_kind(petta_handles_coherent/1, host_service).
ext_point_kind(petta_handles_route/5, host_service).
ext_point_kind(petta_on_error_mode/3, host_service).
ext_point_kind(petta_refuse_guard/2, host_service).
ext_point_kind(petta_source_reset/1, host_service).
ext_point_kind(petta_transaction/1, host_service).
ext_point_kind(petta_transport_failure/1, host_service).
ext_point_kind(prepare_parsed_forms/1, host_service).
ext_point_kind(process_form/3, host_service).
ext_point_kind(recompile_definitions_mentioning/1, host_service).
ext_point_kind(refuse_lossy_plan/4, host_service).
ext_point_kind(refuse_other_tiers_name/2, host_service).
ext_point_kind(register_fun_in/2, host_service).
ext_point_kind(release_function_name/1, host_service).
ext_point_kind(sread_with_names/3, host_service).
ext_point_kind(translate_special_dl/5, host_service).
ext_point_kind(unregister_fun_everywhere/1, host_service).
ext_point_kind(unregister_metta_extension/1, host_service).
ext_point_kind(with_metta_module/2, host_service).
ext_point_kind(with_source_load/3, host_service).

ext_point_kind(swrite/2, service).
ext_point_kind(sread/2, service).
ext_point_kind(metta_symbol_writable/1, service).
ext_point_kind(metta_unwritable_symbol/2, service).

%ERRORS. An extension that throws reports in the vocabulary of whatever threw,
%so `Y is X * 2` on a symbol names is/2 rather than the operation the program
%wrote. These two are how a builtin avoids that, and EXTENDING.md has told
%extension authors to call both for longer than either was declared: the
%rethrow in a worked example at two places and the type error in a third
%[source: EXTENDING.md, "Making your errors read like a builtin's"]. Declaring
%them changes nothing about who may call them and puts a decision that was
%already made into the data that the checker reads.
ext_point_kind(throw_metta_type_error/3, service).
ext_point_kind(rethrow_metta_operation_error/2, service).

%CONTEXT. Which module the call site is in. A named space compiles its
%equations into a module of its own, so a function name alone does not identify
%a function, and a handler keeping state per function has to ask. It is read
%rather than passed because metta_dispatch_call/4 is consulted on every
%compiled call site and an extra argument there is not free.
ext_point_kind(current_metta_module/1, service).

%CONTEXT, the other half: which MODULE a space compiles into, and which space
%a module serves. Published because Phase 11 made them necessary rather than
%convenient. A space and its module were the same atom for every space but
%&self, so a library could pass a space name wherever a module was wanted and
%it worked by coincidence; they are different atoms now and
%with_metta_module/2 REFUSES a space name, so a library that runs a goal in a
%space has to ask. lib_memo.pl and lib_tabling.pl each carried a hand-written
%copy of the inverse before this
%[source: ai-phase11-module-survey.md section 1.3, which counted four copies
%of it, three of them outside src/spaces.pl].
ext_point_kind(space_module/2, service).
ext_point_kind(metta_module_space/2, service).

%Extra type candidates for grounded host objects, beyond the object's own
%classes: a protocol the object satisfies may name a type, so a declared
%(-> DLTensor ...) can hold across libraries.
:- multifile metta_grounded_extra_type/2.
ext_point_kind(metta_grounded_extra_type/2, declaration).

%A host bridge may compute an object's type names itself: values can sit in
%envelope objects the boundary must not rewrite, so the names, plain text,
%are what crosses rather than the value. What a bridge owns is the CLASS
%WALK: when one answers, its names stand in for the walk, and with none the
%local walk applies. It does not own metta_grounded_extra_type/2 above, which is
%consulted either way, because a declaration seam is additive and reading
%this one as owning the whole answer silently dropped every declared type
%in the shipped configuration
%[tested: python/tests/test_ops.py::test_a_declared_type_survives_the_library_being_loaded].
:- multifile metta_grounded_type_names/2.
ext_point_kind(metta_grounded_type_names/2, ownership).

%The host's own class enumeration, the fallback when no envelope bridge
%answered: walking a value's classes is host code by nature, so the host
%bridge supplies it and an engine with no host loaded has no clause here,
%which is the correct answer for a configuration in which no host value
%can exist.
:- multifile metta_grounded_class_type/2.
ext_point_kind(metta_grounded_class_type/2, ownership).

%A host bridge's own builtins, registered by the engine's registry directive
%from these declarations, so no list inside the engine names a host: the
%bridge declares, the engine registers whatever was declared.
:- multifile metta_host_builtin/1.
ext_point_kind(metta_host_builtin/1, declaration).

%A host claims an import whose source is its own kind of file and performs
%the whole job itself, lifecycle included, through the published
%import_when/4; with no host loaded, or none claiming, every import is a
%MeTTa import.
:- multifile metta_host_import/1.
ext_point_kind(metta_host_import/1, ownership).

%Whether a value is a live host object at all, the question in front of
%every grounded-type lookup: the engine's own cheap class tests run first,
%and this seam is the bridge's part, so an engine with no host loaded
%answers no at one failed lookup and never initializes anything.
:- multifile metta_host_object/1.
ext_point_kind(metta_host_object/1, ownership).

%A registered rewriter runs over every loaded form; a host installs one only
%while it is needed (the Python bridge registers its import-as alias rewrite
%when the first alias lands), so a program that never uses the feature pays
%one failed lookup per form and nothing more, the same install-on-demand
%shape the atom hooks use.
:- dynamic metta_form_rewriter/1.
:- multifile metta_form_rewriter/1.
ext_point_kind(metta_form_rewriter/1, ownership).

:- use_module(library(prolog_wrap)).

metta_dispatch_call(_, _, _, _) :- fail.
metta_on_function_changed(_).
metta_on_function_removed(_).

%Atom hooks wrap the write predicates only while a multifile handler exists.
%prolog_listen/2 sees clauses loaded later, so an engine without handlers keeps
%the original direct write path. Multiple handlers still run through forall/2.

metta_atom_hook_clause(added, Ref) :- clause(metta_on_atom_added(_, _), _, Ref).
metta_atom_hook_clause(removed, Ref) :- clause(metta_on_atom_removed(_, _), _, Ref).

%Both branches succeed or throw, never fail. This installer runs from inside a
%prolog_listen/2 closure, and that channel's contract is asymmetric: on an
%assertz "the hook is called after the clause has been added. If the hook
%fails the clause is REMOVED", and on a retract "if the hook fails, the clause
%is not removed" [source: SWI-Prolog 10.1 Reference Manual, Appendix B.9]. So
%a failure here silently erases the handler that was just installed, or leaves
%one the caller believes it erased, and either way a library's subscription
%simply never fires with no error to find. The disable branches were already
%total; these were not. Nothing observed fails, so this is the seam's own
%installer being made unable to fail quietly rather than a live bug
%[tested: a_handler_survives_its_own_installation].
%The wrapped predicate is the ENGINE's, so the module is asked rather than
%written: petta_engine_module/1 (src/metta.pl) answers where this file's
%clauses went. Writing `user` here meant "the engine" in one breath and "the
%host" in the next, and only the second reading survives Phase 11.
%
%The WRAPPER BODY is left unqualified deliberately. wrap_predicate/4 declares
%it `0` [source: library(prolog_wrap), meta_predicate wrap_predicate(:,+,-,0)],
%so SWI qualifies it with this file's own module at compile time, which is the
%same answer and is one SWI's code walker can follow: qualifying it by hand
%with a run-time variable made three live wrapper bodies unreachable from any
%root in tests/prolog/reachability.pl [measured 2026-08-19].
enable_metta_atom_hook(added) :-
    petta_engine_module(Engine),
    current_predicate_wrapper(Engine:metta_add_atom(_, _, _), metta_atom_added_hooks, _, _), !.
enable_metta_atom_hook(added) :-
    petta_engine_module(Engine),
    (   wrap_predicate(Engine:metta_add_atom(Space, Term, _Result), metta_atom_added_hooks, Wrapped,
                       run_metta_atom_added_hooks(Wrapped, Space, Term))
    ->  true
    ;   throw(error(petta_atom_hook_install_failed(added),
                    context(enable_metta_atom_hook/1,
                            'the write wrapper could not be installed')))
    ).
enable_metta_atom_hook(removed) :-
    petta_engine_module(Engine),
    current_predicate_wrapper(Engine:metta_remove_atom(_, _, _), metta_atom_removed_hooks, _, _), !.
enable_metta_atom_hook(removed) :-
    petta_engine_module(Engine),
    (   wrap_predicate(Engine:metta_remove_atom(Space, Term, Removed), metta_atom_removed_hooks, Wrapped,
                       run_metta_atom_removed_hooks(Wrapped, Space, Term, Removed))
    ->  true
    ;   throw(error(petta_atom_hook_install_failed(removed),
                    context(enable_metta_atom_hook/1,
                            'the write wrapper could not be installed')))
    ).

:- multifile prolog:error_message//1.
prolog:error_message(petta_atom_hook_install_failed(Kind)) -->
    [ 'the ~w-atom write wrapper could not be installed, so a handler asserted \c
       now would be removed again by prolog_listen/2 and never fire'-[Kind] ].

run_metta_atom_added_hooks(Wrapped, Space, Term) :-
    call(Wrapped),
    forall(metta_on_atom_added(Space, Term), true).

run_metta_atom_removed_hooks(Wrapped, Space, Term, Removed) :-
    call(Wrapped),
    ( Removed == true
      -> forall(metta_on_atom_removed(Space, Term), true)
      ; true ).

disable_metta_atom_hook(added) :-
    petta_engine_module(Engine),
    ( unwrap_predicate(Engine:metta_add_atom/3, metta_atom_added_hooks) -> true ; true ).
disable_metta_atom_hook(removed) :-
    petta_engine_module(Engine),
    ( unwrap_predicate(Engine:metta_remove_atom/3, metta_atom_removed_hooks) -> true ; true ).

sync_metta_atom_hook(Kind) :- ( metta_atom_hook_clause(Kind, _)
                                -> enable_metta_atom_hook(Kind)
                                ; disable_metta_atom_hook(Kind) ).

metta_atom_hook_changed(Kind, Action, Context) :-
    ( ( Action == asserta ; Action == assertz ; Action == rollback(retract) )
      -> enable_metta_atom_hook(Kind)
    ; ( Action == retract ; Action == rollback(asserta) ; Action == rollback(assertz) )
      -> ( metta_atom_hook_clause(Kind, Other), Other \== Context
           -> true ; disable_metta_atom_hook(Kind) )
    ; Action == retractall, Context = end(_)
      -> sync_metta_atom_hook(Kind)
    ; true ).

:- prolog_listen(metta_on_atom_added/2, metta_atom_hook_changed(added)).
:- prolog_listen(metta_on_atom_removed/2, metta_atom_hook_changed(removed)).
:- sync_metta_atom_hook(added).
:- sync_metta_atom_hook(removed).
:- initialization(sync_metta_atom_hook(added), restore_state).
:- initialization(sync_metta_atom_hook(removed), restore_state).
