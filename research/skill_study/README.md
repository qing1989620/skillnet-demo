# Literature-grounded Skill research, 2026-11-07

The two research questions are verifiable Skill quality and better SkillNet
selection/orchestration. This additive package leaves the production library,
running local demo, prior assessment code and frozen datasets unchanged.

- [44-paper review](LITERATURE_REVIEW.md), with pinned reading versions,
  formal venues separately recorded, strengths, limitations and transfer ideas.
- [Research report](RESEARCH_REPORT.md) explains the two proposed methods,
  actual development experiments, negative results and remaining evidence gaps.
- [Experiment plan](experiment_plan.json) defines the development probes;
  it is not a registered confirmatory protocol.
- [Corrections](CORRECTIONS.md) preserves the initial shell-comment false leads.
- [All routing cohorts and policies](ROUTING_TABLES.md) prevents selective reporting.
- [Local model preparation](results/local-model-preparation.json) records verified
  SkillRouter weights and an incomplete CUDA dependency download. No model
  inference was run and no model metrics are reported. The optional forward-only
  probe and its pinned configuration are supplied for a later completed setup.
- [Judge pilot execution](NEXT_BATCH_REVIEW.md) describes 54 real, matched-material
  direct DeepSeek requests over 18 original D1 training examples, explicitly
  authorized by the user after initial offline preparation. Two fixed training
  examples exceeded the byte limit. 53 responses passed schema validation;
  382/389 citations passed the strict supplied-source locator check. These are
  not human quality accuracy or task-execution results.
- [Source binding](results/evidence-binding-summary.json) records a post-hoc
  independent resource fetch and version binding; model quote discrepancies
  and unassessed semantic support remain explicit.

Existing research environment, repository root:

```powershell
& '..\.venv-skill-quality\Scripts\python.exe' -X utf8 -m pytest research/skill_study/tests -q
& '..\.venv-skill-quality\Scripts\python.exe' -X utf8 -m research.skill_study.quality_pilot --output out/research/skill-study/NEW-QUALITY-ID
& '..\.venv-skill-quality\Scripts\python.exe' -X utf8 -m research.skill_study.routing_pilot --output out/research/skill-study/NEW-ROUTING-ID
& '..\.venv-skill-quality\Scripts\python.exe' -X utf8 -m research.skill_study.stub_audit --output out/research/skill-study/NEW-STUB-ID
```

The quality pilot uses only the frozen 200 D1 originals. The all-library JSONL
storage is read, but D2 records are never passed to the package inspectors.
Every registered file is rehashed. Binary/non-supported resources remain in
the inventory and are reported as opaque, never silently called executable.
Python files are parsed with AST only. A reconstructed *trusted standard-library*
argument parser is a mechanical reference independent of the custom constraint
rules, but it shares AST extraction and lexical preprocessing; community source is not
imported or executed. Unsupported syntax, parser factories and dynamic arguments
produce unknown, not a bad Skill rating. Literal CLI consistency is not runtime
success. Resource mentions may be examples or optional; they are review leads.

Controlled commands are in-memory edits of real D1 examples with known mechanical
defects/benign changes, not upstream changes, independent human gold or agent
task outcomes. Parent Skills, not variants, are the resampling unit. All routing
captures are historical, previously seen tasks; named-anchor retrieval results
are exploratory and cannot show causal utility or independent generalization.
The DPP implementation uses a lexical proxy and rank-derived relevance, not the
published DSR trained model. All policies and negative results are retained.

Paper texts are cached privately, excluded from Git. A separate literature
environment contains the dependencies in `requirements-literature.txt`:

```powershell
python -X utf8 -m research.skill_study.fetch_literature --cache PRIVATE-CACHE
python -X utf8 -m research.skill_study.prepare_review_windows PRIVATE-CACHE
python -X utf8 -m research.skill_study.build_literature_review --cache PRIVATE-CACHE
```

Preparation is not a reading claim: the annotated review was written after
targeted method/experiment/limitation excerpts were inspected by the current
Agent. Full text identity, authors and reviewed section fingerprints are in
`literature_review.json`; this is a purposeful scoping review, not a systematic
meta-analysis. Publication and reading versions can differ.

Outputs are write-once, include resource/input fingerprints and code snapshots,
and have a file manifest. Verify `manifest.json` using
`research.skill_quality.manifest.verify_files(output, manifest)`;
`code-manifest.json` uses the repository root and detects later code changes.
Historical code can also be checked out from its pinned Git revision or restored
from a run's `code-snapshot`. Only summaries/metadata are committed. No real API
calls or Skill executions are performed by the static-contract and lexical
routing pilots. The separate direct DeepSeek pilot performed 54 cloud model
requests after explicit authorization; it executed no community Skill code.
Its private responses/balance snapshots stay outside Git, and observed-token
tariff bounds are not presented as provider invoices. The historical USD 0
protocol and offline-preparation flags are preserved; the separate direct
authorization and run plan describe the subsequent paid batch.

The two authorization/price JSON snapshots preserve their exact original bytes
in Git because their hashes were frozen before the paid run. Other metadata can
use normal repository line endings. Private run code snapshots also retain the
original bytes needed for strict hash replay.
The real API batch's exact source/configuration is also preserved at revision
`292096d9c0928290fe63086b3d792737bd310856`. A later Linux type-check annotation
has an identical executable AST; replay the historical snapshot for exact
bytes instead of comparing its hash with the commented current source.
