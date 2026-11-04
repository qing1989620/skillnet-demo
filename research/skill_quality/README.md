# Skill quality evidence research — Phase A

This module prepares auditable research material without changing the product's retrieval, quality fields, weights, or reward gates. The current implementation covers the first offline gate of the supplied research protocol. It does not complete the 12-week study or establish an improvement in quality ratings or task success.

Read [the protocol review](audit/PROTOCOL_REVIEW.md), [the baseline audit](audit/BASELINE_AUDIT.md), [the E02 comparison protocol](audit/E02_PROTOCOL.md), and [the annotation SOP](audit/ANNOTATION_SOP.md) before using the exported samples.

## Environment

Use Python 3.11+ in a separate virtual environment. The checked environment is Windows / Python 3.12.10; its exact versions are in `requirements-lock-win-py312.txt`. This lock records a tested environment, rather than claiming the original authors used these versions.

```powershell
python -m venv ..\.venv-skill-quality
..\.venv-skill-quality\Scripts\python.exe -m pip install -r research/skill_quality/requirements-lock-win-py312.txt
```

The mypy binary wheel was blocked by this machine's application policy. Installing the same mypy version from its source distribution worked. If needed, use `pip install --force-reinstall --no-deps --no-binary=mypy mypy==2.4.1` inside the virtual environment.

## Reproduce the offline inventory

```powershell
python -m research.skill_quality.cli inspect --dry-run
python -m research.skill_quality.cli prepare --run-id my-phase-a-run
python -m research.skill_quality.cli verify --run-id my-phase-a-run
```

The frozen baseline commit in `configs/study-v1.yaml` must be an ancestor of the checkout, and all original delivery bytes must pass the repository's strict verifier. Research-only descendant commits are allowed. Snapshot identities retain the frozen source commit, independent of later research commits.

`prepare` performs the actual package reads, hashes, original five-dimensional heuristic capture, static text audit, exact-prefix Jaccard near-duplicate join, source/content-group split, unlabelled A/B exports, and raw-derived report. It creates `out/research/skill-quality/<run-id>/` once; existing files are never overwritten. `verify` checks the artifact manifest, the recorded research source hashes, and recomputes the metrics and report. Raw snapshots and annotation documents stay local and must not be added to a public PR without a separate license review.

Individual commands are `snapshot`, `scan`, `dedup`, `split`, `export-labels`, and `analyze`. Use them in dependency order on one new run directory. `--dry-run` writes nothing. Final frozen artifacts must not be edited; use a new run ID for revisions.

## Reproduce E00 separately

Original tests and `verify.py` write runtime logs. Run them in a separate worktree, preserving the research checkout and historical files:

```powershell
git worktree add --detach ..\skillnet-baseline-validation 0af2de6a9c8b129e174e3442b67c5f7cb4324db9
python -m research.skill_quality.baseline_audit --repo . --validation-root ..\skillnet-baseline-validation --output out/research/skill-quality/my-e00-run
```

On a later research descendant checkout, either use the same commit for both the audit and validation worktrees, or run the baseline-only audit before applying research commits. The audit intentionally refuses mismatched worktree commits. It removes inherited credentials from test subprocesses, disables external Python socket egress while retaining loopback, and records dependency versions, checks, logs, and return codes. This is a test egress guard, not an OS sandbox. Only trusted project tests run; external Skill resources are never imported or executed.

`baseline_adapter.retrieval_replay` separately captures the original benchmark's 76-skill library and the full 1,881-skill delivery library, each on the old 20/12 task sets. It requires the delivered dense encoder and no production API key. Every search is repeated, and the shadow-disabled result must be canonical-equivalent. Offline Fabric is explicitly marked as graph expansion with no LLM rerank. These historical task sets are not new blind tests.

## Gates and current limits

- `judge --dry-run` and `execute --dry-run` emit plans. Without dry-run, both return exit code 4 in Phase A. The general OpenRouter adapter has only been exercised through `httpx.MockTransport`; no real model/provider compatibility or pricing is claimed.
- The client requires an explicit approval object, confirmation of key rotation, a pricing fingerprint, a positive USD budget, and a durable ledger before live construction. A file lock prevents multiple writers; every request attempt reserves budget before dispatch and keeps its own settlement. Unknown/pending billing blocks further calls. There is no automatic retry after an unbilled timeout, and no JSON truncation repair.
- Generation-metadata reconciliation, account/day spend controls, immutable response caching, real provider probes, and model discovery remain Phase B work. A 64-character pricing fingerprint does not prove that a price quote is a guaranteed billing cap.
- Static flags are review leads. All initial gates require human review. The scanner does not claim semantic security analysis of script bodies or a legal license review.
- The source split has only three independent source/content components. The current D2 includes derived project cards, so it is provisional. No human labels exist, and no test labels have been opened. OS access-control sealing and semantic-neighbor review remain pending.
- `ranker.py` replays detached candidates and requires explicit version-bound sidecars for evidence ranking. Its uncalibrated shadow multiplier acts after the existing quality prior; it does not expose or replace the original raw-fusion components. A8/A9 utility learning is not implemented.
- `statistics.py` validates planned trial completeness and aggregates by task family before paired bootstrap. Tests use synthetic fixtures only. The CSV verifier is a mutation-tested fixture, not a real D4/D5 benchmark. Actual Skill execution has no host fallback and remains disabled.
- `model-registry`, human-label import/agreement analysis, real task manifests, verifier lineages, Pilot power estimation, formal P1/P2 analysis and paper figures are not completed.

Exit codes currently used by the Phase A CLI: 0 success, 2 existing output/invalid arguments, 3 integrity/input failures, 4 forbidden paid/Skill execution. The broader protocol's other exit codes are reserved for future implemented commands.

## Checks

```powershell
python -m pytest research/skill_quality/tests -q
python -m ruff check research/skill_quality
python -m ruff format --check research/skill_quality
python -m mypy --config-file research/skill_quality/mypy.ini research/skill_quality
git diff --check
```

The final checked cohort contains 1,244 original tests and 101 research boundary tests, all passing. The first baseline run had one optional SciPy check skipped; it was retained, SciPy was installed separately, and the full final cohort was rerun. No skipped check was reported as a pass.
