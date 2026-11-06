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
