# Development corrections

2026-11-06, shell comment handling: the first D1 diagnostic run preserved
`# explanatory text` as positional CLI tokens. Inspection of its 14 flagged
examples showed comment-related false leads. The lexer now treats unquoted `#`
as a POSIX shell comment, while quoted `#` remains data. This is a development
correction using D1, with a negative-control regression test. Both the first
run and the two pre-fix source files are retained under the private output
directory. Revised runs use new IDs; no old result is overwritten. The
controlled-intervention labels describe CLI consistency, never overall Skill
quality, maliciousness or runtime success.

2026-11-07, cross-platform type metadata: the first Linux CI run rejected
the Windows-only `msvcrt.locking` attributes during static type checking.
The runtime tests had passed. A platform-specific attribute annotation was
added, matching the existing `fcntl` annotation; the executable Python AST is
identical to the source used for the 54 real requests. No model request was
repeated and no response or earlier code snapshot was changed. The executed
source/configuration bytes are preserved in the private run's `code-snapshot`
and in Git revision `292096d9c0928290fe63086b3d792737bd310856`. Historical replay
uses that snapshot rather than claiming the later commented source has the
same byte hash. The original CI failure logs are retained locally.
