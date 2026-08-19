; %%%% The engine's prelude: standard vocabulary, no import needed. %%%%
;
; Every form here is part of the core engine. The loader in metta.pl
; compiles these equations into the base tier at startup and registers
; each name as a builtin, so they are reachable from every space with no
; import!, shadowable per named space exactly as builtins are, and their
; atoms appear in NO space: a program enumerating &self sees only its
; own writes. Declarations land in the engine's prelude type register,
; where get-type and the call-site compiler read them after a program's
; own declarations, so a user redeclaration wins.
;
; The forms are Hyperon's standard vocabulary, promoted from
; lib/lib_he.metta by the same route unify, add-reduct, add-atoms,
; add-reducts and evalc took before them: standard library operations
; rather than compatibility shims, and a program should not have to
; import anything to reach them. The equations ARE the executable spec;
; the parameter-evaluation decisions (which arguments are Atom) are
; carried over from the library unchanged, with the reasoning kept
; beside each.

;;; Equality and reduction ;;;

;if-equal compares by ALPHA-EQUIVALENCE, not ==: Hyperon implements it
;with core.rs atoms_are_equivalent, atoms equal up to a consistent
;variable renaming, and the arbiter mechanises exactly that
;[source: LeaTTa MettaHyperonFull/Minimal/Stdlib.lean, ifEqualOp]. The
;library shim compared with ==, which misses (f $x $x) against
;(f $y $y); the promotion fixes the contract, the same way add-reduct's
;promotion fixed its.
(= (if-equal $A $B $Then $Else)
   (if (=alpha $A $B) $Then $Else))

(= (if-equal2 $A $B $Then $Else)
   (if (=alpha $A $B) $Then $Else))

;The non-Msg assert forms take Atom parameters and compare RESULT SETS,
;exactly as their own Msg twins below always did and as the arbiter
;declares them [source: same file, (: assertEqual (-> Atom Atom (->)))].
;The library evaluated the arguments applicatively and asserted once per
;combination, so a nondeterministic side asserted pairwise instead of
;set-wise; the two spellings agreed only on deterministic arguments.
;The return type stays %Undefined% for the reason type-cast's note
;records: an Atom RESULT type would leave the body untranslated.
(: assertEqual (-> Atom Atom %Undefined%))
(= (assertEqual $A $B)
   (assert (== (collapse (eval $A)) (collapse (eval $B)))))

(: assertAlphaEqual (-> Atom Atom %Undefined%))
(= (assertAlphaEqual $A $B)
   (assert (=alpha (collapse (eval $A)) (collapse (eval $B)))))

;The ToResult forms do not evaluate their second argument: it is the set
;of expected results, written as a tuple. Both parameters are Atom so
;neither is evaluated on the way in, and the first is collapsed here into
;the tuple of every result it produces. Hyperon's own corpus states the
;contract, in tests/corpus/a1_symbols.metta: "assertEqualToResult checks
;all the results of the first expression; it doesn't evaluate the second
;expression, which is treated as a set of expected results."
(: assertEqualToResult (-> Atom Atom %Undefined%))
(= (assertEqualToResult $A $B)
   (assert (== (collapse (eval $A)) $B)))

(: assertAlphaEqualToResult (-> Atom Atom %Undefined%))
(= (assertAlphaEqualToResult $A $B)
   (assert (=alpha (collapse (eval $A)) $B)))

;Every expected result must appear among the results produced.
;Subtracting the produced set from the expected one leaves nothing when
;all of them did.
(: assertIncludes (-> Atom Atom %Undefined%))
(= (assertIncludes $A $B)
   (assert (== (subtraction-atom $B (collapse (eval $A))) ())))

;The Msg variants carry a failure message. assert/2 already reports the
;failing expression, so each delegates and the message is accepted but
;unused.
(: assertEqualMsg (-> Atom Atom Atom %Undefined%))
(= (assertEqualMsg $A $B $M)
   (assert (== (collapse (eval $A)) (collapse (eval $B)))))

(: assertAlphaEqualMsg (-> Atom Atom Atom %Undefined%))
(= (assertAlphaEqualMsg $A $B $M)
   (assert (=alpha (collapse (eval $A)) (collapse (eval $B)))))

(: assertEqualToResultMsg (-> Atom Atom Atom %Undefined%))
(= (assertEqualToResultMsg $A $B $M)
   (assertEqualToResult $A $B))

(: assertAlphaEqualToResultMsg (-> Atom Atom Atom %Undefined%))
(= (assertAlphaEqualToResultMsg $A $B $M)
   (assertAlphaEqualToResult $A $B))

;;; Error handling ;;;

(= (if-error $X $A $B)
   (if (= $X (cons Error $_))
       $A $B))

(= (return-on-error $result $B)
   (if-error $result
             $result
             $B))

;;; Evaluation control ;;;

(= (for-each-in-atom $L $f)
   (map-atom $L $f))

;;; Atomicity ;;;

;atomically runs its argument inside one transaction, the name the
;concurrency vocabulary uses for an atomic block: Haskell's STM spells it
;`atomically`, Clojure's spells it `dosync`, and `transaction` is the same
;operation under the database name. Before this it did not exist, so
;!(atomically (+ 1 1)) answered (atomically 2), an unknown head applied to
;its evaluated argument, rather than running anything atomically.
;
;It is sugar over (transaction ...), deliberately, so the two forms cannot
;drift: every guarantee here is petta_transaction/1's, answer preservation
;and whole-set commit-or-rollback included, and there is one implementation
;of them.
;
;They are still not the same operation, and this is the difference.
;transaction is a SPECIAL FORM whose body is compiled into the call site, so
;the body has to be written there: (let $b <a term> (transaction $b))
;answers the TERM, unrun, because there is nothing to compile at the call
;site but a variable. atomically takes its body as an unreduced Atom and
;evaluates it, so the body may be a term the program computed. The 183
;inferences that separate them, 773.05 against 956.07 over a three-answer
;body [measured 2026-08-19], are what evaluating a runtime term costs
;against compiling the body in place.
(: atomically (-> Atom %Undefined%))
(= (atomically $expr) (transaction (eval $expr)))

;;; Quoting ;;;

;Two clauses, and the second is not a deviation from the arbiter but
;its PeTTa-native encoding. Upstream carries only
;(= (unquote (quote $atom)) $atom): a non-quote argument matches no
;equation and minimal MeTTa's NotReducible leaves the call standing AS
;WRITTEN. PeTTa has no NotReducible; a call no equation matches answers
;nothing. The quote-wrapping catch-all is how the library encoded
;"stays as written" here, quote keeping the term inert and the printer
;rendering it as itself, so (repr (unquote 42)) answers "(unquote 42)"
;exactly as upstream observes. The cut in the first clause is what
;keeps the catch-all from also firing on quotes.
(: unquote (-> Atom %Undefined%))
(= (unquote (quote $A))
   (let $cut (cut) (eval $A)))
(= (unquote $A) (quote (unquote $A)))

(: noreduce-eq (-> Atom Atom Bool))
(= (noreduce-eq $A $B)
   (== $A $B))

;;; Types ;;;

(= (is-function (-> $A $B)) (let $temp (cut) True))
(= (is-function $X) False)

;get-type-space is a native builtin now: the engine's own get-type run
;with the selected space as context, upstream's selected-space spelling
;[source: pinned stdlib.md:849-868 via the arbiter]. The library's stub
;matched the literal &self and answered nothing for any named space.

;These two declarations are HERE rather than only in
;lib/lib_builtin_types.metta because this is the register the CALL SITE
;reads. Asking for a type is a question about an expression, and the
;engine was answering it by running the expression first: an op that
;appends to a Python list fired on (get-type (petta-effectful)) and the
;answer was Number, the type of what it returned. Every linter walk and
;every REPL inspection was invisibly effectful on a seam whose whole
;purpose is arbitrary effects.
;
;An Atom parameter in the engine's own surface register is deliberately
;NOT honoured at call sites, because several of those declarations
;describe the argument a CALLER writes rather than the value the
;predicate receives, and honouring them broke every maplist call
;[source: call_site_type_chains/2 in src/translator.pl]. get-type has no
;such gap: the declaration and the predicate agree that the argument
;arrives unreduced, so the prelude register, which IS honoured at call
;sites, is where it belongs.
;
;The answer then comes from the declaration, which is what the arbiter
;answers: (get-type (literal-return 2)) is Atom for
;(: literal-return (-> Number Atom)), whatever its body would reduce to
;[source: LeaTTa tests/semantics/types-meta/20_atom_return_literal.metta,
;MEASURED [Atom] from the mechanised interpreter and from hyperon
;0.2.10 alike].
;
;Both arrows are upstream's, with the one vocabulary translation this
;tree already applies: SpaceType is written Symbol here, the rule
;lib/lib_builtin_types.metta states for the whole surface. get-type is
;(-> Atom %Undefined%) and get-type-space is (-> SpaceType Atom Atom) at
;pinned stdlib.md:849-868. Either return spelling behaves identically in
;this engine, measured 2026-08-19 over an effectful call, a declared
;return, a value and a builtin application, so upstream's is kept because
;matching it costs nothing.
(: get-type (-> Atom %Undefined%))
(: get-type-space (-> Symbol Atom Atom))

;match-types is UNIFICATION with wildcards, not equality: %Undefined%
;and Atom on either side match anything, and otherwise the two types
;unify, bindings and all [source: LeaTTa Stdlib.lean, the corelib
;match-types equation]. The library compared with ==, which missed every
;one of those cases.
(= (match-types $t1 $t2 $then $else)
   (if (=alpha $t1 %Undefined%)
       $then
       (if (=alpha $t2 %Undefined%)
           $then
           (if (=alpha $t1 Atom)
               $then
               (if (=alpha $t2 Atom)
                   $then
                   (unify $t1 $t2 $then $else))))))

;Upstream's parameter order: the fold accumulator FIRST, then the
;candidate type, then the wanted type [source: same file,
;(= (match-type-or $folded $next $type) ...)]. The library had the
;accumulator first but swapped the two types through its own helper.
(= (match-type-or $folded $next $type)
   (or $folded (match-types $next $type True False)))

;type-cast, upstream's contract: the atom when the cast holds, the flat
;(Error $atom BadType) when it does not. UNDECLARED ON PURPOSE, and the
;absence carries behaviour: upstream ships this equation with no
;(: type-cast ...) line, so the operands evaluate before the equation
;runs, and an ill-typed subject reports its OWN error instead of being
;swallowed by an Atom mask. The arbiter measured exactly that against
;pinned Hyperon 0.2.10 [source: LeaTTa Stdlib.lean, the type-cast note
;and tests/semantics/types-basic/50-53]. The library declared Atom
;parameters and compared metatypes with ==; both diverged.
(= (type-cast $atom $type $space)
   (if (=alpha $type (get-metatype $atom))
       $atom
       (if (type-cast-holds $atom $type $space)
           $atom
           (Error $atom BadType))))

;The fold upstream writes inline, named here because PeTTa is
;applicative where the corelib chains; match-type-or does the wildcard
;and unification reading per candidate, so an undeclared atom
;(%Undefined%) casts to anything, which is upstream's answer too.
(= (type-cast-holds $atom $type $space)
   (foldl-atom (collapse (get-type-space $space $atom)) False $acc $declared
      (match-type-or $acc $declared $type)))

;;; Documentation ;;;
;
;The prelude documents its own vocabulary; the loader routes these into
;the engine's doc register, get-doc's first tier, so (help! type-cast)
;answers with no import and a program's own (@doc ...) atoms stay the
;program's. Descriptions follow the pinned corelib's where it has them.

(@doc if-equal
  (@desc "Selects the third argument when the first two are alpha-equivalent, atoms equal up to a consistent variable renaming, and the fourth otherwise")
  (@params ((@param "First atom") (@param "Second atom") (@param "Result on equivalence") (@param "Result otherwise")))
  (@return "Third or fourth argument"))
(@doc if-equal2
  (@desc "if-equal under its second historical name")
  (@params ((@param "First atom") (@param "Second atom") (@param "Result on equivalence") (@param "Result otherwise")))
  (@return "Third or fourth argument"))
(@doc assertEqual
  (@desc "Compares the result sets of two expressions; passes silently or raises a failed assertion naming the expression")
  (@params ((@param "First expression, not evaluated on the way in") (@param "Second expression, not evaluated on the way in")))
  (@return "unit"))
(@doc assertAlphaEqual
  (@desc "assertEqual up to alpha-equivalence of the result sets")
  (@params ((@param "First expression") (@param "Second expression")))
  (@return "unit"))
(@doc assertEqualToResult
  (@desc "Checks all the results of the first expression against the second expression, which is not evaluated and is read as the set of expected results")
  (@params ((@param "Expression to evaluate") (@param "Expected results, as written")))
  (@return "unit"))
(@doc assertAlphaEqualToResult
  (@desc "assertEqualToResult up to alpha-equivalence")
  (@params ((@param "Expression to evaluate") (@param "Expected results, as written")))
  (@return "unit"))
(@doc assertIncludes
  (@desc "Passes when every expected result appears among the results the first expression produces")
  (@params ((@param "Expression to evaluate") (@param "Expected subset, as written")))
  (@return "unit"))
(@doc assertEqualMsg
  (@desc "assertEqual with a message argument, accepted and unused because the assertion already names the failing expression")
  (@params ((@param "First expression") (@param "Second expression") (@param "Message")))
  (@return "unit"))
(@doc assertAlphaEqualMsg
  (@desc "assertAlphaEqual with a message argument, accepted and unused")
  (@params ((@param "First expression") (@param "Second expression") (@param "Message")))
  (@return "unit"))
(@doc assertEqualToResultMsg
  (@desc "assertEqualToResult with a message argument, accepted and unused")
  (@params ((@param "Expression to evaluate") (@param "Expected results") (@param "Message")))
  (@return "unit"))
(@doc assertAlphaEqualToResultMsg
  (@desc "assertAlphaEqualToResult with a message argument, accepted and unused")
  (@params ((@param "Expression to evaluate") (@param "Expected results") (@param "Message")))
  (@return "unit"))
(@doc if-error
  (@desc "Selects the second argument when the first is an (Error ...) expression and the third otherwise")
  (@params ((@param "Value to inspect") (@param "Result on error") (@param "Result otherwise")))
  (@return "Second or third argument"))
(@doc return-on-error
  (@desc "Answers the first argument when it is an (Error ...) expression, stopping the computation there, and the second otherwise")
  (@params ((@param "Value to inspect") (@param "Result when the first is not an error")))
  (@return "The error, or the second argument"))
(@doc for-each-in-atom
  (@desc "Applies a function to every element of an expression; map-atom under its historical name")
  (@params ((@param "Expression to walk") (@param "Function to apply")))
  (@return "The mapped expression"))
(@doc unquote
  (@desc "Unquotes a quoted atom and evaluates it, e.g. (unquote (quote $x)) evaluates $x; a non-quote argument stays as written")
  (@params ((@param "Quoted atom")))
  (@return "Unquoted atom"))
(@doc noreduce-eq
  (@desc "Compares two atoms as written, neither evaluated")
  (@params ((@param "First atom, as written") (@param "Second atom, as written")))
  (@return "True or False"))
(@doc is-function
  (@desc "True when the argument is an arrow type")
  (@params ((@param "Type atom")))
  (@return "True or False"))
(@doc match-types
  (@desc "Checks if two types can be unified and returns the third argument if so, the fourth otherwise; %Undefined% and Atom on either side match anything")
  (@params ((@param "First type") (@param "Second type") (@param "Atom to be returned if types can be unified") (@param "Atom to be returned if types cannot be unified")))
  (@return "Third or fourth argument"))
(@doc match-type-or
  (@desc "Checks if two types (second and third arguments) can be unified and returns the result of OR between the first argument and the type checking result")
  (@params ((@param "Boolean value") (@param "First type") (@param "Second type")))
  (@return "True or False"))
(@doc type-cast
  (@desc "Casts atom passed as a first argument to the type passed as a second argument using space as a context")
  (@params ((@param "Atom to be casted") (@param "Type to cast atom to") (@param "Context atomspace")))
  (@return "Atom if casting is successful, (Error ... BadType) otherwise"))
(@doc type-cast-holds
  (@desc "Whether any declared type of the atom in the space unifies with the requested type; type-cast's fold, named because PeTTa is applicative where the corelib chains")
  (@params ((@param "Atom") (@param "Requested type") (@param "Context atomspace")))
  (@return "True or False"))
(@doc get-type-space
  (@desc "get-type run with the selected space as the context")
  (@params ((@param "Space to select") (@param "Atom to type")))
  (@return "The type, as get-type answers it in that space"))
(@doc get-doc
  (@desc "The documentation atom for a name, from the current space or the engine's own register, or nothing when there is none")
  (@params ((@param "The name to look up")))
  (@return "The (@doc ...) atom"))
(@doc get-doc-space
  (@desc "get-doc run against the selected space")
  (@params ((@param "Space to select") (@param "The name to look up")))
  (@return "The (@doc ...) atom"))
(@doc help!
  (@desc "Prints the documentation for a name, the engine's own vocabulary included")
  (@params ((@param "The name to look up")))
  (@return "unit"))
(@doc documented
  (@desc "Every name the CURRENT SPACE documents, one per solution; program-scoped on purpose, so the engine's own vocabulary does not bury yours")
  (@params ())
  (@return "A name"))
(@doc documented-space
  (@desc "documented, against the selected space")
  (@params ((@param "Space to select")))
  (@return "A name"))
(@doc defined-name
  (@desc "Every function name the current space defines, builtins excluded, once each")
  (@params ())
  (@return "A name"))
(@doc undocumented
  (@desc "Every defined name in the current space with no documentation anywhere; the gap worth closing")
  (@params ())
  (@return "A name"))
(@doc undocumented-space
  (@desc "undocumented, against the selected space")
  (@params ((@param "Space to select")))
  (@return "A name"))

;;; Derived forms ;;;
;
; A form below is written in MeTTa, as an equation that says what the call
; EXPANDS TO, plus the registration that makes the translator consult it
; before it reaches its own special-form table. Nothing here needs a clause in
; the compiler: the expansion goes back through the ordinary translator, so
; one definition decides what the form means and the kernel carries one form
; fewer. The Atom parameters are what make an argument arrive as syntax; the
; %Undefined% RESULT type is what makes the (quote ...) body translate, since
; an Atom result would leave the body untranslated and hand the quote itself
; back as the expansion.
;
; Every form here was A/B'd against the compiler clause it replaced, on the
; goals it compiles to and on compile-time inference counts, over the whole
; examples corpus [tested: translator_derived_forms,
; test_a_prelude_derived_form_matches_its_fused_twin_on_the_corpus].

;and-then and or-else ARE `if` with one branch decided, which is what their
;compiler clauses spelled out by hand. The expansion compiles one goal FEWER
;than the clause did, because if builds its branches through build_branch/4
;and drops the empty conjunct the hand-written pair kept [measured 2026-08-19:
;the same conditional, minus one `true` conjunct].
(: and-then (-> Atom Atom %Undefined%))
(= (and-then $a $b) (quote (if $a $b False)))
!(add-translator-rule! and-then)

(: or-else (-> Atom Atom %Undefined%))
(= (or-else $a $b) (quote (if $a True $b)))
!(add-translator-rule! or-else)

;The stream operations. Each was a rewrite rule in the compiler that produced
;exactly the MeTTa term below, so moving them changes nothing but where they
;live [measured 2026-08-19: byte-identical compiled goals].
(: trace! (-> Atom Atom %Undefined%))
(= (trace! $message $value) (quote (progn (println! $message) $value)))
!(add-translator-rule! trace!)

(: unique (-> Atom %Undefined%))
(= (unique $stream)
   (quote (call (superpose (unique-atom (collapse $stream))))))
!(add-translator-rule! unique)

(: alpha-unique (-> Atom %Undefined%))
(= (alpha-unique $stream)
   (quote (call (superpose (alpha-unique-atom (collapse $stream))))))
!(add-translator-rule! alpha-unique)

;The set operations name the shape they rewrite, `(superpose ...)` on both
;sides, exactly as the compiler's rewrite rules did. The second equation is
;what the compiler's identity clause was: a call that is not that shape is a
;program using the name as data, and `noeval` hands it back unevaluated
;rather than letting the expansion recurse [tested: translator_derived_forms].
(: union (-> Atom Atom %Undefined%))
(= (union (superpose $a) (superpose $b))
   (quote (call (superpose (union-atom (collapse (superpose $a))
                                       (collapse (superpose $b)))))))
(= (union $a $b) (quote (noeval (union $a $b))))
!(add-translator-rule! union)

(: intersection (-> Atom Atom %Undefined%))
(= (intersection (superpose $a) (superpose $b))
   (quote (call (superpose (intersection-atom (collapse (superpose $a))
                                              (collapse (superpose $b)))))))
(= (intersection $a $b) (quote (noeval (intersection $a $b))))
!(add-translator-rule! intersection)

(: subtraction (-> Atom Atom %Undefined%))
(= (subtraction (superpose $a) (superpose $b))
   (quote (call (superpose (subtraction-atom (collapse (superpose $a))
                                             (collapse (superpose $b)))))))
(= (subtraction $a $b) (quote (noeval (subtraction $a $b))))
!(add-translator-rule! subtraction)
