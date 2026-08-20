# Lowerings

The rewrite-seam registrations the Python seat ships: translator rules
registered through `!(add-translator-rule! ...)` whose bodies LOWER a
MeTTa form into a performance-directed shape before the translator
compiles it. LOWERING is the decided word for the performance-directed
translator-rule kind, and this folder is that seam's home inside the
seat, so a satellite PyMeTTa repository carries its lowerings with it.

Nothing ships here yet: every current registration lives in user
programs or in tests. A shipped lowering lands as a `.metta` file this
seat loads at import, with its measured numbers in the file header.
