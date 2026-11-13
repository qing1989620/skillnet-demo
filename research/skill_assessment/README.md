# Single-Skill assessment, stage one

This additive module operationalizes the distinction between package quality,
documented preconditions, empirical capability, and conditional utility. It does
not alter production `Skill.quality`, routing, the running demo, or the frozen
`research/skill_quality` implementation. It makes no API calls and imports no
community Python code.

Read [the report](FIRST_STAGE_REPORT.md), [anchored rubric](RUBRIC.md) and
[validation protocol](VALIDATION_PROTOCOL.md). The method remains uncalibrated
against independent human labels and untested on real Skill executions.

From the repository root, using the existing research environment:

```powershell
& '..\.venv-skill-quality\Scripts\python.exe' -m pytest research/skill_assessment/tests -q
& '..\.venv-skill-quality\Scripts\python.exe' -m research.skill_assessment.pilot --output out/research/skill-assessment/NEW-UNIQUE-RUN-ID
```

The default frozen input is `out/research/skill-quality/20261104-phase-a-v3`.
Only three explicitly selected D1 cases are passed to the inspectors. Each
registered package file is rehashed; citations verify exact file/line/quote/SHA,
not semantic support. Python analysis uses the standard AST parser only.

Preflight facts are caller supplied and not authenticated by this prototype.
It is an explanatory precondition checker, not a security sandbox or empirical
ability certificate. A match is always labelled `not_executed`. CLI declarations
are checked only for literal long-option presence, not argument values, control
flow, dependency compatibility or runtime success. Resource and measurement
findings require contextual review; no static "safe" certificate is emitted.

The public six-row CSV task tests the owned verifier against a constructed
reference and ten deliberate mutations. These are not Agent outputs, human
gold, Skill execution trials or population accuracy estimates. Future empirical
evaluation requires hidden tasks and independently reviewed oracles/verifiers.

Outputs are write-once and include input hashes, code hashes and an artifact
manifest. To verify an output directory, use `verify_files(output, manifest)`
from `research.skill_quality.manifest` with its `artifact-manifest.json`; verify
`code-manifest.json` with the repository as root. Original package bytes are not
republished. `pilot_summary.json` contains only local findings and metadata.
